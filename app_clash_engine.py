import os
import io
import re
import math
from datetime import datetime
import streamlit as st
import pandas as pd
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_community.vectorstores import Chroma

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

# ---------------------------------------------------------
# 1. PAGE SETUP & CONFIGURATION
# ---------------------------------------------------------
st.set_page_config(
    page_title="Sentry-Clash: Multi-Disciplinary Interface Clash Engine",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    try:
        api_key = st.secrets.get("GEMINI_API_KEY")
    except Exception:
        api_key = None

def extract_text(content) -> str:
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict) and "text" in item:
                parts.append(str(item["text"]))
            else:
                parts.append(str(item))
        return "\n\n".join(parts)
    return str(content)

# ---------------------------------------------------------
# 2. DEFAULT TRI-DOMAIN TELEMETRY & CONFIGURATION SCHEMAS
# ---------------------------------------------------------
DEFAULT_EPMS_EVENT = {
    "event_id": "EVT-STS-0412",
    "source_bus": "SWBD-2A-MECH",
    "transfer_type": "STS Break-Before-Make",
    "v_pre_pct": 100.0,
    "v_min_pct": 0.0,
    "delta_t_break_ms": 14.5,
    "delta_t_total_sag_ms": 18.2,
    "phase_angle_jump_deg": 34.5,
    "frequency_slip_hz_s": 1.2
}

DEFAULT_VFD_CONFIG = {
    "drive_tag": "VFD-PUMP-SEC-01A",
    "driven_equipment": "Secondary CW Distribution Pump",
    "rated_power_kw": 45.0,
    "operating_shaft_kw": 32.4,
    "operating_speed_pct": 88.0,
    "vdc_nominal_v": 565.0,
    "vdc_trip_uv_pct": 70.0,  # Trips below 395.5 VDC
    "bus_capacitance_uf": 3300.0,
    "inverter_efficiency_pct": 96.0,
    "kinetic_buffering_mode": "DISABLED",  # Options: DISABLED, RAMP_REDUCE
    "flying_start_mode": "DISABLED",       # Options: DISABLED, ENABLED
    "uv_controller_timer_ms": 10.0
}

DEFAULT_BMS_BASELINE = {
    "chw_diff_pressure_bar": 2.25,
    "chw_diff_pressure_min_limit": 1.50,
    "chw_supply_temp_c": 11.2,
    "chw_supply_temp_max_limit": 11.5,
    "peak_gpu_temp_c": 72.0,
    "gpu_temp_max_limit": 78.0
}

# ---------------------------------------------------------
# 3. DETERMINISTIC VERIFICATION ENGINE (THE 5 PHYSICAL GATES)
# ---------------------------------------------------------
def run_deterministic_clash_engine(epms, vfd, bms):
    results = {}
    
    # Gate 1: ITIC / CBEMA Computer Server Gate
    # Servers survive 0% voltage for <= 20ms or >= 70% voltage for <= 500ms
    t_break = epms["delta_t_break_ms"]
    v_min = epms["v_min_pct"]
    
    if (t_break <= 20.0 and v_min == 0.0) or (v_min >= 70.0 and t_break <= 500.0):
        gate1_status = "PASS"
        gate1_notes = f"Transfer gap of {t_break} ms is within IEEE 446 / ITIC curve (<= 20.0 ms). Zero IT compute drops."
    else:
        gate1_status = "FAIL"
        gate1_notes = f"Transfer gap of {t_break} ms breaches the 20.0 ms ITIC zero-voltage envelope."
    results["Gate 1 (ITIC Server Standard)"] = (gate1_status, gate1_notes)

    # Gate 2: VFD DC-Bus Capacitive Hold-Up Calculation
    c_farads = vfd["bus_capacitance_uf"] * 1e-6
    v_nom = vfd["vdc_nominal_v"]
    v_trip = v_nom * (vfd["vdc_trip_uv_pct"] / 100.0)
    p_elec = (vfd["operating_shaft_kw"] * 1000.0) / (vfd["inverter_efficiency_pct"] / 100.0)
    
    e_stored_joules = 0.5 * c_farads * (v_nom**2 - v_trip**2)
    t_holdup_ms = (e_stored_joules / p_elec) * 1000.0
    
    results["t_holdup_calculated_ms"] = round(t_holdup_ms, 2)
    
    if t_break <= t_holdup_ms:
        gate2_status = "PASS"
        gate2_notes = f"Transfer gap ({t_break} ms) <= Capacitor hold-up capacity ({t_holdup_ms:.1f} ms). DC bus remains above trip threshold."
    else:
        gate2_status = "FAIL (UV TRIP)"
        gate2_notes = f"Transfer gap ({t_break} ms) exceeds Capacitor hold-up ({t_holdup_ms:.1f} ms). DC bus collapses below {v_trip:.0f} VDC."
    results["Gate 2 (VFD Capacitive Ride-Through)"] = (gate2_status, gate2_notes)

    # Gate 3: Kinetic Buffering Dynamic Inertia Compensation
    kb_mode = vfd["kinetic_buffering_mode"]
    if kb_mode == "RAMP_REDUCE":
        if t_break <= 200.0:
            gate3_status = "PASS"
            gate3_notes = f"Kinetic buffering ACTIVE. Pump shaft rotational inertia regenerated power back to DC bus, preventing UV lockout."
        else:
            gate3_status = "FAIL (EXHAUSTED)"
            gate3_notes = f"Transfer gap ({t_break} ms) exceeded maximum rotational inertia ride-through envelope (200 ms)."
    else:
        gate3_status = "FAIL (DISABLED)"
        gate3_notes = "Kinetic buffering is DISABLED in factory default firmware. Zero inertia energy recovery."
    results["Gate 3 (Kinetic Buffering Regeneration)"] = (gate3_status, gate3_notes)

    # Gate 4: Phase-Angle Vector Jump & Re-Closure Overcurrent Risk
    d_theta = epms["phase_angle_jump_deg"]
    fs_mode = vfd["flying_start_mode"]
    
    if d_theta <= 20.0:
        gate4_status = "PASS (SAFE)"
        gate4_notes = f"Phase displacement ({d_theta} deg) <= 20 deg. Inrush transients within inverter safe operating area."
    elif 20.0 < d_theta <= 35.0:
        if fs_mode == "ENABLED":
            gate4_status = "PASS (MITIGATED)"
            gate4_notes = f"Phase jump of {d_theta} deg safely caught by active Flying Start back-EMF frequency tracking."
        else:
            gate4_status = "MARGINAL WARNING"
            gate4_notes = f"Phase jump ({d_theta} deg) risks high stator inrush current upon re-closure."
    else:
        if fs_mode == "ENABLED":
            gate4_status = "PASS (MITIGATED)"
            gate4_notes = f"Severe phase jump ({d_theta} deg) synchronized cleanly by Flying Start algorithm."
        else:
            gate4_status = "FAIL (OC TRIP)"
            gate4_notes = f"Severe phase displacement ({d_theta} deg) without Flying Start triggers instantaneous Overcurrent (OC) lockout."
    results["Gate 4 (Phase Vector Re-Closure)"] = (gate4_status, gate4_notes)

    # Gate 5: Hydraulic Decay & Cavitation Risk
    pump_tripped = (gate2_status != "PASS" and gate3_status != "PASS") or ("FAIL" in gate4_status)
    if pump_tripped:
        # Simulate coast-down: Affinity law Delta P scales quadratically with speed
        predicted_dp = round(bms["chw_diff_pressure_bar"] * (0.3**2), 2)
        gate5_status = "CRITICAL COLLAPSE"
        gate5_notes = f"Pump tripped. Secondary loop differential pressure collapses to {predicted_dp} bar (Threshold: {bms['chw_diff_pressure_min_limit']} bar). CRAH coil starvation imminent."
    else:
        predicted_dp = bms["chw_diff_pressure_bar"]
        gate5_status = "STABLE"
        gate5_notes = f"Pump sustained continuous rotation. Differential pressure maintained at {predicted_dp} bar across cooling coils."
    results["Gate 5 (Hydraulic Stability)"] = (gate5_status, gate5_notes)

    # Comprehensive Clash Diagnosis
    if gate1_status == "PASS" and pump_tripped:
        if gate3_status == "FAIL (DISABLED)":
            diagnosis_code = "CLASH-01: CROSS-DISCIPLINARY SUBMITTAL CLASH"
            diagnosis_desc = "STS transfer (14.5 ms) is legally compliant with IEEE 446 / ITIC standards, but caused mechanical pump shutdown due to default uncalibrated VFD firmware."
        else:
            diagnosis_code = "CLASH-02: PHASE VECTOR RE-CLOSURE CLASH"
            diagnosis_desc = "Kinetic buffering sustained the DC bus, but an unmitigated 34.5 deg phase jump triggered an Overcurrent trip upon re-closure."
    elif gate1_status != "PASS" and pump_tripped:
        diagnosis_code = "CLASH-03: UPSTREAM ELECTRICAL SYSTEM FAILURE"
        diagnosis_desc = "The transfer switch breached both ITIC server standards and mechanical hold-up thresholds. Root fault is electrical switchgear failure."
    else:
        diagnosis_code = "COORDINATED: ZERO-CLASH INTERFACE COMPLIANCE"
        diagnosis_desc = "Electrical transfer envelope and mechanical drive firmware are fully coordinated. 100% continuous cooling sustained."
        
    results["diagnosis_code"] = diagnosis_code
    results["diagnosis_desc"] = diagnosis_desc
    results["pump_tripped"] = pump_tripped

    return results

# ---------------------------------------------------------
# 4. REPORTLAB PDF SANITIZATION & COMPILATION PIPELINE
# ---------------------------------------------------------
def clean_and_format_for_reportlab(text):
    if not text:
        return []

    replacements = {
        '\u2018': "'", '\u2019': "'", '\u201c': '"', '\u201d': '"',
        '\u2013': '-', '\u2014': '--',
        '⚡': '', '✅': '[PASS]', '❌': '[FAIL]', '⚠️': '[WARN]',
        '🌡️': '', '❄️': '', '📋': '', '🏛️': '', '🏢': '', '🔹': '-'
    }
    for k, v in replacements.items():
        text = text.replace(k, v)

    # Convert LaTeX Math & Code Backticks into Plain Engineering Text
    text = text.replace('`', '')
    text = re.sub(r'\\le(q)?\b', '<=', text)
    text = re.sub(r'\\ge(q)?\b', '>=', text)
    text = re.sub(r'\\pm\b', '+/-', text)
    text = re.sub(r'\\times\b', 'x', text)
    text = re.sub(r'\^?\\circ\s*(\\text\{C\}|C)?', ' deg C', text)
    text = re.sub(r'\\text\{([^}]*)\}', r'\1', text)
    text = text.replace('$', '')

    cleaned_paragraphs = []
    for raw_line in text.split('\n'):
        line = raw_line.strip()
        if not line:
            continue

        # Strip ASCII / Markdown table borders e.g. +++, +---+, |---|
        if re.match(r'^[\|\+\-\s:]+$', line) or line.startswith('+++') or line.startswith('|---'):
            continue

        # Detect Markdown Headings
        if line.startswith('#'):
            line = re.sub(r'^[#\s]+', '', line).strip()
            line = line.replace('***', '').replace('**', '').replace('*', '').strip()
            line = line.encode('latin-1', 'replace').decode('latin-1')
            cleaned_paragraphs.append((line, True))
            continue

        # Detect Bullet points
        is_bullet = False
        if line.startswith(('* ', '- ', '• ')):
            is_bullet = True
            line = line[2:].strip()
        elif line.startswith('***'):
            is_bullet = True
            line = re.sub(r'^\*+\s*', '', line).strip()

        # If it was an ASCII table row, format cleanly into a bullet line
        if line.startswith('|') and line.endswith('|'):
            cells = [c.strip() for c in line.split('|')[1:-1] if c.strip()]
            if not cells or all(re.match(r'^[\-\+:]+$', c) for c in cells):
                continue
            line = " -- ".join(cells)
            is_bullet = True

        # XML Escape
        line = line.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

        # Balance and convert **bold** to <b>bold</b>
        if line.count('**') % 2 != 0:
            last_idx = line.rfind('**')
            line = line[:last_idx] + line[last_idx + 2:]

        parts = line.split('**')
        if len(parts) > 1:
            rebuilt = []
            for i, p in enumerate(parts):
                if i % 2 == 1:
                    rebuilt.append(f"<b>{p.strip()}</b>")
                else:
                    rebuilt.append(p)
            line = "".join(rebuilt)

        # Strip remaining rogue marks
        line = line.replace('***', '').replace('**', '').replace('*', '')
        line = line.replace('###', '').replace('##', '').replace('#', '')
        line = line.replace('<b></b>', '')

        if is_bullet:
            line = f"&bull; {line}"

        line = line.encode('latin-1', 'replace').decode('latin-1')
        cleaned_paragraphs.append((line, False))

    return cleaned_paragraphs

def generate_clash_pdf(results, epms, vfd, facility_tag, audit_memo):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=letter, leftMargin=36, rightMargin=36, topMargin=54, bottomMargin=54
    )
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        'DocTitle', fontName='Helvetica-Bold', fontSize=12, leading=15,
        textColor=colors.HexColor('#1B365D'), spaceAfter=4
    )
    section_heading = ParagraphStyle(
        'SectionHeading', fontName='Helvetica-Bold', fontSize=9.5, leading=12,
        textColor=colors.HexColor('#1B365D'), spaceBefore=6, spaceAfter=3
    )
    body_style = ParagraphStyle(
        'DocBody', fontName='Helvetica', fontSize=8, leading=10.5,
        textColor=colors.HexColor('#1E293B')
    )
    meta_label = ParagraphStyle(
        'MetaLabel', fontName='Helvetica-Bold', fontSize=7, leading=9,
        textColor=colors.HexColor('#1B365D')
    )
    meta_val = ParagraphStyle(
        'MetaVal', fontName='Helvetica', fontSize=7, leading=9,
        textColor=colors.HexColor('#334155')
    )

    story = []
    story.append(Paragraph("INTER-SYSTEM CLASH & DISCREPANCY AUDIT REPORT", title_style))
    story.append(Spacer(1, 3))

    # Author Provenance Card (ROHIT KUMAR, CEM Omitted)
    prov_data = [
        [
            Paragraph("Lead Systems Architect & Author:", meta_label),
            Paragraph("<b>ROHIT KUMAR</b>, PMP, CEng (India), CEA, FSEr (TUV)", meta_val),
            Paragraph("Direct Inquiries:", meta_label),
            Paragraph("+91-8826991440 | grohit41@gmail.com", meta_val)
        ],
        [
            Paragraph("Professional Engineering Domain:", meta_label),
            Paragraph("Data Center Infrastructure & Systems Engineering Specialist", meta_val),
            Paragraph("Facility Scope & Rating:", meta_label),
            Paragraph(facility_tag.encode('latin-1', 'replace').decode('latin-1'), meta_val)
        ],
        [
            Paragraph("Multi-Disciplinary Scope:", meta_label),
            Paragraph("Electrical Power Quality (EPMS) vs. Motor Drive Firmware (VFD)", meta_val),
            Paragraph("Governance Standards:", meta_label),
            Paragraph("IEEE 446 | ITIC / CBEMA | IEC 61800-3 | Uptime Tier IV", meta_val)
        ]
    ]
    t_prov = Table(prov_data, colWidths=[130, 150, 110, 150])
    t_prov.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F8FAFC')),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#1B365D')),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
        ('TOPPADDING', (0, 0), (-1, -1), 2.5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2.5),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(t_prov)
    story.append(Spacer(1, 5))

    # Deterministic Clash Diagnostic Banner
    is_tripped = results["pump_tripped"]
    banner_bg = colors.HexColor('#FEF3C7') if is_tripped else colors.HexColor('#DCFCE7')
    banner_border = colors.HexColor('#D97706') if is_tripped else colors.HexColor('#16A34A')
    banner_color = '#D97706' if is_tripped else '#16A34A'

    clash_box = [
        [
            Paragraph(
                f"<b>DETERMINISTIC DIAGNOSIS: <font color='{banner_color}'>{results['diagnosis_code']}</font></b><br/>"
                f"<b>Physical Conflict:</b> {results['diagnosis_desc']}<br/>"
                f"<b>Calculated DC-Bus Hold-Up:</b> {results['t_holdup_calculated_ms']} ms | "
                f"<b>STS Break Duration:</b> {epms['delta_t_break_ms']} ms | "
                f"<b>Phase Vector Jump:</b> {epms['phase_angle_jump_deg']} deg",
                meta_val
            )
        ]
    ]
    t_clash = Table(clash_box, colWidths=[540])
    t_clash.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), banner_bg),
        ('BOX', (0, 0), (-1, -1), 1, banner_border),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(t_clash)
    story.append(Spacer(1, 6))

    # 5 Physical Verification Gates Table
    story.append(Paragraph("1. DETERMINISTIC PHYSICAL VERIFICATION GATES", section_heading))
    gate_table_data = [
        [
            Paragraph("<b>Verification Gate</b>", meta_label),
            Paragraph("<b>Physical Parameter Evaluated</b>", meta_label),
            Paragraph("<b>Result Status</b>", meta_label),
            Paragraph("<b>Engineering Analysis</b>", meta_label)
        ]
    ]

    gates = [
        ("Gate 1: ITIC / CBEMA Server Envelope", f"Delta t = {epms['delta_t_break_ms']} ms at {epms['v_min_pct']}% V", results["Gate 1 (ITIC Server Standard)"]),
        ("Gate 2: VFD Capacitive Ride-Through", f"t_holdup = {results['t_holdup_calculated_ms']} ms", results["Gate 2 (VFD Capacitive Ride-Through)"]),
        ("Gate 3: Kinetic Buffering Inertia", f"Mode = {vfd['kinetic_buffering_mode']}", results["Gate 3 (Kinetic Buffering Regeneration)"]),
        ("Gate 4: Phase Vector Re-Closure", f"Delta Theta = {epms['phase_angle_jump_deg']} deg", results["Gate 4 (Phase Vector Re-Closure)"]),
        ("Gate 5: Hydraulic Loop Stability", f"Flow Head Pressure", results["Gate 5 (Hydraulic Stability)"])
    ]

    for g_title, g_param, (g_status, g_notes) in gates:
        status_color = "#16A34A" if "PASS" in g_status or "STABLE" in g_status else ("#D97706" if "WARNING" in g_status else "#DC2626")
        status_p = Paragraph(f"<font color='{status_color}'><b>{g_status}</b></font>", meta_label)
        gate_table_data.append([
            Paragraph(g_title, meta_val),
            Paragraph(g_param, meta_val),
            status_p,
            Paragraph(g_notes, meta_val)
        ])

    t_gates = Table(gate_table_data, colWidths=[120, 85, 95, 240])
    t_gates.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#F1F5F9')),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
        ('TOPPADDING', (0, 0), (-1, -1), 2.5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2.5),
        ('LEFTPADDING', (0, 0), (-1, -1), 3),
        ('RIGHTPADDING', (0, 0), (-1, -1), 3),
    ]))
    story.append(t_gates)
    story.append(Spacer(1, 6))

    # Cleaned Engineering Memo
    story.append(Paragraph("2. COGNITIVE INTERFACE COORDINATION & REMEDIATION MEMO", section_heading))
    parsed_memo_paragraphs = clean_and_format_for_reportlab(audit_memo)
    for p_text, is_heading in parsed_memo_paragraphs:
        if is_heading:
            story.append(Paragraph(f"<b>{p_text}</b>", section_heading))
        else:
            story.append(Paragraph(p_text, body_style))
            story.append(Spacer(1, 1.5))

    def add_header_footer(canvas, doc_obj):
        canvas.saveState()
        canvas.setFont("Helvetica-Bold", 7)
        canvas.setFillColor(colors.HexColor("#1B365D"))
        canvas.drawString(36, 756, "SENTRY-CLASH: MULTI-DISCIPLINARY INTERFACE CLASH & DISCREPANCY AUDIT")
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(colors.HexColor("#64748B"))
        canvas.drawRightString(576, 756, "Systems Specialist: Rohit Kumar, PMP, CEng (India)")
        canvas.setStrokeColor(colors.HexColor("#CBD5E1"))
        canvas.setLineWidth(0.5)
        canvas.line(36, 750, 576, 750)
        canvas.line(36, 42, 576, 42)
        canvas.drawString(36, 31, "Confidential | Rohit Kumar, PMP, CEng (India) | grohit41@gmail.com | LinkedIn: ROHITG41")
        canvas.drawRightString(576, 31, f"Page {doc_obj.page} | IEEE 446 & IEC 61800-3 Coordinated")
        canvas.restoreState()

    doc.build(story, onFirstPage=add_header_footer, onLaterPages=add_header_footer)
    buffer.seek(0)
    return buffer.getvalue()

# ---------------------------------------------------------
# 5. SIDEBAR: FACILITY & INTERACTIVE PRESET CONTROLS
# ---------------------------------------------------------
with st.sidebar:
    st.header("⚡ Facility & Clash Presets")
    facility_name = st.text_input("Facility Identifier:", value="DC-HYPERSCALE-ZONE-2")
    rated_topology = st.selectbox("Design Redundancy Rating:", ["Tier IV / Rated-4 (2N)", "Tier III / Rated-3 (N+1)"], index=0)

    st.markdown("---")
    st.subheader("Interactive Interface Presets")
    preset = st.radio(
        "Load Interface Benchmark Scenario:",
        [
            "Preset 1: CLASH-01 (Factory Default Firmware Trip)",
            "Preset 2: CLASH-02 (Severe Phase Angle Vector Trip)",
            "Preset 3: COORDINATED (Zero-Clash Tuned Handover)"
        ],
        index=0
    )

    st.markdown("---")
    st.markdown("**Governing Interface Standards:**")
    st.caption("• IEEE 446 (Orange Book - Emergency Power Systems)\n• ITIC / CBEMA (Server Power Supply Curve)\n• IEC 61800-3 (Industrial Motor Drive Immunity)\n• Uptime Tier IV Continuous Cooling Mandates")

    st.markdown("---")
    user_key = st.text_input("Gemini API Key (Optional Override)", type="password")
    active_key = user_key if user_key else api_key

# Synchronize Presets into Session State
if "epms_data" not in st.session_state or st.sidebar.button("🔄 Reload Current Preset"):
    if "Preset 1" in preset:
        st.session_state["epms_data"] = DEFAULT_EPMS_EVENT.copy()
        st.session_state["vfd_data"] = DEFAULT_VFD_CONFIG.copy()
    elif "Preset 2" in preset:
        st.session_state["epms_data"] = DEFAULT_EPMS_EVENT.copy()
        st.session_state["epms_data"]["phase_angle_jump_deg"] = 42.0
        st.session_state["vfd_data"] = DEFAULT_VFD_CONFIG.copy()
        st.session_state["vfd_data"]["kinetic_buffering_mode"] = "RAMP_REDUCE"
        st.session_state["vfd_data"]["flying_start_mode"] = "DISABLED"
    else:  # COORDINATED
        st.session_state["epms_data"] = DEFAULT_EPMS_EVENT.copy()
        st.session_state["epms_data"]["phase_angle_jump_deg"] = 15.0
        st.session_state["vfd_data"] = DEFAULT_VFD_CONFIG.copy()
        st.session_state["vfd_data"]["kinetic_buffering_mode"] = "RAMP_REDUCE"
        st.session_state["vfd_data"]["flying_start_mode"] = "ENABLED"

# ---------------------------------------------------------
# 6. MAIN WORKSPACE: PARAMETER CONTROLS & SCORECARD
# ---------------------------------------------------------
st.title("⚡ Sentry-Clash: Multi-Disciplinary Interface Clash Engine")
st.caption("Cross-Trade Interface Coordination: **Electrical Power Quality (EPMS)** vs. **Mechanical Drive Firmware (VFD)**")

st.markdown("""
This engine identifies hidden interface failures between systems that independently passed factory acceptance testing. 
Adjust electrical switching transients or drive parameters below to evaluate whether high-speed power transfers 
will sustain continuous pumping or collapse white space cooling.
""")

col1, col2 = st.columns(2)

with col1:
    st.markdown("#### ⚡ 1. Electrical Transfer Transient (EPMS / PQM)")
    c1a, c1b = st.columns(2)
    with c1a:
        st.session_state["epms_data"]["delta_t_break_ms"] = st.number_value = st.number_input(
            "STS Break Duration (Delta t, ms):",
            min_value=1.0, max_value=50.0,
            value=float(st.session_state["epms_data"]["delta_t_break_ms"]),
            step=0.5
        )
    with c1b:
        st.session_state["epms_data"]["phase_angle_jump_deg"] = st.number_input(
            "Phase Angle Jump (Delta Theta, deg):",
            min_value=0.0, max_value=90.0,
            value=float(st.session_state["epms_data"]["phase_angle_jump_deg"]),
            step=1.0
        )
    st.session_state["epms_data"]["v_min_pct"] = st.number_input(
        "Minimum Transfer Voltage (V_min, %):",
        min_value=0.0, max_value=100.0,
        value=float(st.session_state["epms_data"]["v_min_pct"]),
        step=5.0
    )

with col2:
    st.markdown("#### ⚙️ 2. Mechanical Pump VFD Firmware (Drive Registers)")
    c2a, c2b = st.columns(2)
    with c2a:
        st.session_state["vfd_data"]["kinetic_buffering_mode"] = st.selectbox(
            "Kinetic Buffering Mode:",
            ["DISABLED", "RAMP_REDUCE"],
            index=0 if st.session_state["vfd_data"]["kinetic_buffering_mode"] == "DISABLED" else 1
        )
    with c2b:
        st.session_state["vfd_data"]["flying_start_mode"] = st.selectbox(
            "Flying Start Algorithm:",
            ["DISABLED", "ENABLED"],
            index=0 if st.session_state["vfd_data"]["flying_start_mode"] == "DISABLED" else 1
        )
    st.session_state["vfd_data"]["operating_shaft_kw"] = st.number_input(
        "Operating Motor Load (Shaft kW):",
        min_value=10.0, max_value=45.0,
        value=float(st.session_state["vfd_data"]["operating_shaft_kw"]),
        step=1.0
    )

# Execute Deterministic Verification
results = run_deterministic_clash_engine(
    st.session_state["epms_data"],
    st.session_state["vfd_data"],
    DEFAULT_BMS_BASELINE
)

st.markdown("---")

# Diagnostic Callout Banner
if results["pump_tripped"]:
    st.error(f"""
    🚨 **INTERFACE CLASH IDENTIFIED: `{results['diagnosis_code']}`**  
    **Diagnostic Verdict:** {results['diagnosis_desc']}  
    **Physical Friction:** Capacitor hold-up capacity was **`{results['t_holdup_calculated_ms']} ms`** while electrical transfer took **`{st.session_state['epms_data']['delta_t_break_ms']} ms`**.
    """)
else:
    st.success(f"""
    ✅ **ZERO-CLASH INTERFACE COORDINATED: `{results['diagnosis_code']}`**  
    **Diagnostic Verdict:** {results['diagnosis_desc']}  
    **Continuous Pumping:** Kinetic buffering and flying start successfully sustained pump rotation through the {st.session_state['epms_data']['delta_t_break_ms']} ms transfer gap.
    """)

# Physical Gate Scorecard Table
st.markdown("##### Real-Time Deterministic Gate Verification:")
gate_summary_data = [
    {"Verification Gate": "Gate 1: ITIC / CBEMA Server Standard", "Result": results["Gate 1 (ITIC Server Standard)"][0], "Physical Findings": results["Gate 1 (ITIC Server Standard)"][1]},
    {"Verification Gate": "Gate 2: VFD Capacitive Ride-Through", "Result": results["Gate 2 (VFD Capacitive Ride-Through)"][0], "Physical Findings": results["Gate 2 (VFD Capacitive Ride-Through)"][1]},
    {"Verification Gate": "Gate 3: Kinetic Buffering Regeneration", "Result": results["Gate 3 (Kinetic Buffering Regeneration)"][0], "Physical Findings": results["Gate 3 (Kinetic Buffering Regeneration)"][1]},
    {"Verification Gate": "Gate 4: Phase Vector Re-Closure", "Result": results["Gate 4 (Phase Vector Re-Closure)"][0], "Physical Findings": results["Gate 4 (Phase Vector Re-Closure)"][1]},
    {"Verification Gate": "Gate 5: Hydraulic Stability & Cavitation", "Result": results["Gate 5 (Hydraulic Stability)"][0], "Physical Findings": results["Gate 5 (Hydraulic Stability)"][1]}
]
st.dataframe(pd.DataFrame(gate_summary_data), use_container_width=True)

st.markdown("---")

# ---------------------------------------------------------
# 7. COGNITIVE AGENT SYNTHESIS & REPORT GENERATION
# ---------------------------------------------------------
if st.button("⚡ Generate Formal Multi-Disciplinary Interface Coordination Memorandum", type="primary", use_container_width=True):
    if not active_key:
        st.error("Please enter a valid Gemini API Key in the sidebar or environment.")
    else:
        with st.spinner("Synthesizing multi-disciplinary coordination memorandum via Gemini..."):
            try:
                rag_context = ""
                if os.path.exists("./chroma_dc_db"):
                    try:
                        embeddings = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-2", google_api_key=active_key)
                        vdb = Chroma(persist_directory="./chroma_dc_db", embedding_function=embeddings)
                        docs = vdb.similarity_search("STS static transfer switch VFD ride-through kinetic buffering flying start", k=3)
                        rag_context = "\n\n".join([d.page_content for d in docs])
                    except Exception:
                        rag_context = "Standards Grounding: IEEE 446 (Emergency Power), ITIC Curve (20ms hold-up), IEC 61800-3 (Drive Immunity)."

                try:
                    llm = ChatGoogleGenerativeAI(model="gemini-3.8-flash", temperature=0.0, google_api_key=active_key)
                except Exception:
                    llm = ChatGoogleGenerativeAI(model="gemini-3.5-flash", temperature=0.0, google_api_key=active_key)

                prompt = (
                    f"You are the Lead Data Center Infrastructure & Systems Engineering Specialist.\n"
                    f"Operational Scope: Multi-Disciplinary Interface Clash Audit | Facility: {facility_name} | Topology: {rated_topology}\n\n"
                    f"Deterministic Physical Gate Results:\n"
                    f"- Diagnosis: {results['diagnosis_code']}\n"
                    f"- Description: {results['diagnosis_desc']}\n"
                    f"- STS Transfer Break: {st.session_state['epms_data']['delta_t_break_ms']} ms\n"
                    f"- Phase Angle Jump: {st.session_state['epms_data']['phase_angle_jump_deg']} deg\n"
                    f"- Calculated VFD Capacitor Hold-Up: {results['t_holdup_calculated_ms']} ms\n"
                    f"- Kinetic Buffering Setting: {st.session_state['vfd_data']['kinetic_buffering_mode']}\n"
                    f"- Flying Start Setting: {st.session_state['vfd_data']['flying_start_mode']}\n"
                    f"- Pump Hydraulic Status: {results['Gate 5 (Hydraulic Stability)'][0]}\n\n"
                    f"Governing Standards Grounding:\n{rag_context}\n\n"
                    f"Draft an authoritative, highly professional Technical Engineering Memorandum resolving the dispute between Electrical and Mechanical teams.\n\n"
                    f"STRICT STRUCTURAL REQUIREMENTS (YOU MUST FOLLOW THESE EXACT 4 HEADERS):\n"
                    f"1. EXECUTIVE DETERMINATION & INTERFACE CLASH ATTRIBUTION\n"
                    f"2. CROSS-DISCIPLINARY ROOT CAUSE ANALYSIS (Contrast IEEE 446 / ITIC standards with IEC 61800-3 motor drive dynamics)\n"
                    f"3. DYNAMIC PHYSICAL INTERFACE MODELING (Explain DC-bus voltage decay, kinetic inertia regeneration, and phase vector inrush)\n"
                    f"4. MANDATORY VENDOR RECTIFICATION DIRECTIVES\n"
                    f"   A. Electrical Package Actions (STS Phase Sync Window Optimization)\n"
                    f"   B. Mechanical Drive Package Actions (Specific Parameter Calibration: Kinetic Buffering & Flying Start)\n"
                    f"   C. Joint Commissioning Witness Protocol (Retest Criteria)\n\n"
                    f"CRITICAL FORMATTING MANDATES:\n"
                    f"- STRICTLY FORBIDDEN: DO NOT generate ASCII or Markdown tables (NEVER use '|', '+', or '---' table borders). Write all text as paragraphs and bullets.\n"
                    f"- STRICTLY FORBIDDEN: DO NOT use LaTeX math syntax or math blocks (NEVER use '$', '\\le', '\\ge', '\\text{{}}', or '^\\circ').\n"
                    f"- Write all inequalities and units in standard alphanumeric text: '<= 20.0 ms', '>= 2.2 bar', '11.5 deg C', '34.5 deg'.\n"
                    f"- STRICTLY FORBIDDEN: DO NOT use code backticks (`) around IDs, acronyms, or parameters.\n"
                )

                response = llm.invoke([
                    SystemMessage(content=prompt),
                    HumanMessage(content="Evaluate the multi-disciplinary clash results and draft the formal coordination memorandum.")
                ])

                st.session_state["clash_audit_memo"] = extract_text(response.content)

            except Exception as e:
                st.error(f"Execution Error: {e}")

if "clash_audit_memo" in st.session_state:
    st.markdown("### 📋 Formal Multi-Disciplinary Coordination Memorandum")
    st.markdown(st.session_state["clash_audit_memo"])

    pdf_bytes = generate_clash_pdf(
        results=results,
        epms=st.session_state["epms_data"],
        vfd=st.session_state["vfd_data"],
        facility_tag=f"{facility_name} ({rated_topology})",
        audit_memo=st.session_state["clash_audit_memo"]
    )

    st.download_button(
        label="📥 Download Interface Coordination Audit Report (Branded PDF)",
        data=pdf_bytes,
        file_name="Multi_Disciplinary_Interface_Clash_Audit_Report.pdf",
        mime="application/pdf",
        use_container_width=True
    )

# --- EXECUTIVE PORTFOLIO FOOTER ---
st.divider()
st.markdown(
    """
    <div style="text-align: center; color: #475569; font-size: 0.85rem; padding: 10px 0;">
        <p style="margin-bottom: 4px;">
            <strong>Architect:</strong> Rohit Kumar, PMP, CEng (India), CEA, FSEr (TÜV) | 
            Mission-Critical Infrastructure &amp; Applied AI Solutions
        </p>
        <p style="margin-bottom: 4px;">
            <strong>Enterprise Advisory &amp; Custom Architecture:</strong> 
            Available for technical consulting &amp; custom agentic workflows &bull; 
            <a href="https://www.linkedin.com/in/rohitg41" target="_blank" style="color: #2563EB; text-decoration: none;">LinkedIn</a> | 
            <a href="mailto:grohit41@gmail.com" style="color: #2563EB; text-decoration: none;">grohit41@gmail.com</a>
        </p>
        <p style="font-size: 0.78rem; color: #64748B; margin-top: 6px;">
            <em>Dataset Note: Independent engineering demonstration validated on representative, anonymized datasets.</em><br>
            Copyright &copy; 2026 Rohit Kumar. All Rights Reserved.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)
