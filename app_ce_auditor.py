import os
import io
import re
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
    page_title="Sentry-CxA: Tri-Silo C&E Matrix & First-Fault Auditor",
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
# 2. ENHANCED TRI-SILO C&E TELEMETRY DATA SCHEMA
# ---------------------------------------------------------
DEFAULT_CE_DATA = [
    {
        "ID": "CE-01",
        "Timestamp_s": 0.000,
        "Timestamp_Label": "T0 + 0.00s",
        "Silo": "EPMS",
        "Subsystem": "Utility MV Switchgear",
        "Milestone Event": "33kV Incoming Grid Feeder Breaker Trip",
        "Measured Value": 0.0,
        "Unit": "kV",
        "Code Limit": 0.0,
        "DBR Limit": 0.0,
        "Rule": "EQUAL",
        "Sampling_Rate": "10ms",
        "Description": "Grid isolation detected by protective relaying."
    },
    {
        "ID": "CE-02",
        "Timestamp_s": 0.012,
        "Timestamp_Label": "T0 + 12ms",
        "Silo": "EPMS",
        "Subsystem": "Static UPS (2N)",
        "Milestone Event": "Static Inverter Battery Handover (Zero-Break)",
        "Measured Value": 12.0,
        "Unit": "ms",
        "Code Limit": 20.0,
        "DBR Limit": 16.0,
        "Rule": "LTE",
        "Sampling_Rate": "1ms",
        "Description": "Zero-break IT power continuity per IEEE 446 / TIA-942-C."
    },
    {
        "ID": "CE-03",
        "Timestamp_s": 0.500,
        "Timestamp_Label": "T0 + 0.50s",
        "Silo": "EPMS",
        "Subsystem": "Emergency Gen (2N)",
        "Milestone Event": "Engine Auto-Crank Dispatched via PLC Signal",
        "Measured Value": 0.50,
        "Unit": "s",
        "Code Limit": 1.00,
        "DBR Limit": 0.80,
        "Rule": "LTE",
        "Sampling_Rate": "100ms",
        "Description": "PLC crank command to generator paralleling switchgear."
    },
    {
        "ID": "CE-04",
        "Timestamp_s": 8.400,
        "Timestamp_Label": "T0 + 8.40s",
        "Silo": "EPMS",
        "Subsystem": "Emergency Gen (2N)",
        "Milestone Event": "EDGs Synced & Main Bus Breaker Closed",
        "Measured Value": 8.40,
        "Unit": "s",
        "Code Limit": 10.00,
        "DBR Limit": 7.00,
        "Rule": "LTE",
        "Sampling_Rate": "100ms",
        "Description": "NFPA 110 Type 10 allows <=10.0s; Site DBR mandates <=7.0s."
    },
    {
        "ID": "CE-05",
        "Timestamp_s": 9.200,
        "Timestamp_Label": "T0 + 9.20s",
        "Silo": "BMS",
        "Subsystem": "Secondary CW Pumps",
        "Milestone Event": "Secondary Distribution Differential Pressure (VFD)",
        "Measured Value": 2.30,
        "Unit": "bar",
        "Code Limit": 1.50,
        "DBR Limit": 2.20,
        "Rule": "GTE",
        "Sampling_Rate": "500ms",
        "Description": "Maintains hydraulic head to prevent CRAH coil cavitation."
    },
    {
        "ID": "CE-06",
        "Timestamp_s": 35.000,
        "Timestamp_Label": "T0 + 35.0s",
        "Silo": "BMS",
        "Subsystem": "Thermal Buffer Tank",
        "Milestone Event": "Chilled Water Supply Temp into White Space",
        "Measured Value": 11.8,
        "Unit": "deg C",
        "Code Limit": 15.0,
        "DBR Limit": 11.5,
        "Rule": "LTE",
        "Sampling_Rate": "1s",
        "Description": "Continuous cooling thermal storage ride-through."
    },
    {
        "ID": "CE-07",
        "Timestamp_s": 45.000,
        "Timestamp_Label": "T0 + 45.0s",
        "Silo": "BMS",
        "Subsystem": "CRAH & Containment",
        "Milestone Event": "Cold Aisle Differential Static Pressure",
        "Measured Value": 19.5,
        "Unit": "Pa",
        "Code Limit": 5.0,
        "DBR Limit": 18.0,
        "Rule": "GTE",
        "Sampling_Rate": "1s",
        "Description": "Prevents hot aisle reverse recirculation into rack face."
    },
    {
        "ID": "CE-08",
        "Timestamp_s": 60.000,
        "Timestamp_Label": "T0 + 60.0s",
        "Silo": "DCIM",
        "Subsystem": "High-Density AI Racks",
        "Milestone Event": "Peak GPU Die Temperature (H100/B200)",
        "Measured Value": 74.0,
        "Unit": "deg C",
        "Code Limit": 85.0,
        "DBR Limit": 78.0,
        "Rule": "LTE",
        "Sampling_Rate": "100ms",
        "Description": "Silicon junction thermal headroom during cooling transfer."
    },
    {
        "ID": "CE-09",
        "Timestamp_s": 115.000,
        "Timestamp_Label": "T0 + 115s",
        "Silo": "BMS",
        "Subsystem": "Centrifugal Chillers",
        "Milestone Event": "Chiller Fast-Restart Compressor Differential Lift",
        "Measured Value": 115.0,
        "Unit": "s",
        "Code Limit": 180.0,
        "DBR Limit": 90.0,
        "Rule": "LTE",
        "Sampling_Rate": "1s",
        "Description": "Microprocessor reboot and compressor re-engagement."
    }
]

# ---------------------------------------------------------
# 3. DETERMINISTIC AUDIT & FIRST-FAULT ARBITRATION
# ---------------------------------------------------------
def audit_single_row(row):
    meas = float(row["Measured Value"])
    code = float(row["Code Limit"])
    dbr = float(row["DBR Limit"])
    rule = row["Rule"]

    if rule == "LTE":
        code_pass = meas <= code
        dbr_pass = meas <= dbr
    elif rule == "GTE":
        code_pass = meas >= code
        dbr_pass = meas >= dbr
    else:  # EQUAL
        code_pass = meas == code
        dbr_pass = meas == dbr

    if not code_pass:
        return "CRITICAL CODE BREACH", "Violates International Normative Standard", 2
    elif not dbr_pass:
        return "DBR VARIANCE", "Passes Standard Code, but Breaches Contractual DBR", 1
    else:
        return "COMPLIANT", "Satisfies Both Normative Code and Site DBR", 0

def run_tri_silo_audit(df):
    df_sorted = df.sort_values(by="Timestamp_s").reset_index(drop=True)
    results = []
    summary_counts = {"COMPLIANT": 0, "DBR VARIANCE": 0, "CRITICAL CODE BREACH": 0}
    discrepancies = []

    for idx, row in df_sorted.iterrows():
        status, rationale, severity = audit_single_row(row)
        summary_counts[status] += 1
        
        row_res = {
            "ID": row["ID"],
            "Timestamp": row["Timestamp_Label"],
            "Timestamp_s": row["Timestamp_s"],
            "Silo": row["Silo"],
            "Subsystem": row["Subsystem"],
            "Milestone Event": row["Milestone Event"],
            "Measured": f"{row['Measured Value']} {row['Unit']}",
            "Code Limit": f"{row['Code Limit']} {row['Unit']}",
            "DBR Limit": f"{row['DBR Limit']} {row['Unit']}",
            "Audit Status": status,
            "Severity": severity,
            "Rationale": rationale
        }
        results.append(row_res)
        if status != "COMPLIANT":
            discrepancies.append(row_res)

    first_fault = discrepancies[0] if discrepancies else None
    cascading_symptoms = discrepancies[1:] if len(discrepancies) > 1 else []

    return pd.DataFrame(results), summary_counts, first_fault, cascading_symptoms

# ---------------------------------------------------------
# 4. REPORTLAB PDF PARSER (STRIPS LATEX, RAW TABLES & ASTERISKS)
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

def generate_tri_silo_pdf(df_audit, summary_counts, first_fault, facility_tag, audit_memo):
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
    story.append(Paragraph("TRI-SILO C&E DISCREPANCY & FIRST-FAULT AUDIT REPORT", title_style))
    story.append(Spacer(1, 3))

    # Author Provenance Card (ROHIT KUMAR - CEM omitted)
    prov_data = [
        [
            Paragraph("Lead Systems Architect & Author:", meta_label),
            Paragraph("<b>ROHIT KUMAR</b>, PMP, CEng, CEA, FSEr (TUV)", meta_val),
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
            Paragraph("Tri-Silo Telemetry Integration:", meta_label),
            Paragraph("EPMS (Power) | BMS (Cooling) | DCIM (IT/Workload)", meta_val),
            Paragraph("Governance Standards:", meta_label),
            Paragraph("NFPA 110 Type 10 | ANSI/TIA-942-C | ASHRAE TC 9.9", meta_val)
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

    # First-Fault Callout Box
    if first_fault:
        ff_box = [
            [
                Paragraph(
                    f"<b>IDENTIFIED INITIATING ROOT CAUSE (FIRST-FAULT AT {first_fault['Timestamp']}):</b><br/>"
                    f"<b>Subsystem:</b> [{first_fault['Silo']}] {first_fault['Subsystem']} -- {first_fault['Milestone Event']}<br/>"
                    f"<b>Measured:</b> {first_fault['Measured']} vs DBR Target: {first_fault['DBR Limit']} | "
                    f"<b>Status:</b> <font color='#D97706'><b>{first_fault['Audit Status']}</b></font><br/>"
                    f"<i>All subsequent deviations are evaluated as cascading symptoms of this initiating transient gap.</i>",
                    meta_val
                )
            ]
        ]
        t_ff = Table(ff_box, colWidths=[540])
        t_ff.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#FEF3C7')),
            ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#D97706')),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ]))
        story.append(t_ff)
        story.append(Spacer(1, 6))

    # C&E Matrix Table
    story.append(Paragraph("1. TRI-SILO CHRONOLOGICAL SEQUENCE AUDIT MATRIX", section_heading))
    table_rows = [
        [
            Paragraph("<b>Time</b>", meta_label),
            Paragraph("<b>Silo</b>", meta_label),
            Paragraph("<b>Subsystem & Milestone Action</b>", meta_label),
            Paragraph("<b>Measured</b>", meta_label),
            Paragraph("<b>DBR Limit</b>", meta_label),
            Paragraph("<b>Audit Status</b>", meta_label)
        ]
    ]
    for _, r in df_audit.iterrows():
        status_color = "#16A34A" if r["Audit Status"] == "COMPLIANT" else ("#D97706" if r["Audit Status"] == "DBR VARIANCE" else "#DC2626")
        status_p = Paragraph(f"<font color='{status_color}'><b>{r['Audit Status']}</b></font>", meta_label)
        table_rows.append([
            Paragraph(r["Timestamp"], meta_val),
            Paragraph(f"<b>[{r['Silo']}]</b>", meta_val),
            Paragraph(f"<b>{r['Subsystem']}</b><br/>{r['Milestone Event']}", meta_val),
            Paragraph(r["Measured"], meta_val),
            Paragraph(r["DBR Limit"], meta_val),
            status_p
        ])
    t_ce = Table(table_rows, colWidths=[55, 45, 200, 70, 70, 100])
    t_ce.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#F1F5F9')),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
        ('TOPPADDING', (0, 0), (-1, -1), 2.5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2.5),
        ('LEFTPADDING', (0, 0), (-1, -1), 3),
        ('RIGHTPADDING', (0, 0), (-1, -1), 3),
    ]))
    story.append(t_ce)
    story.append(Spacer(1, 6))

    # Clean Memo Paragraphs
    story.append(Paragraph("2. FIRST-FAULT & INTER-SYSTEM INTERACTION MEMO", section_heading))
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
        canvas.drawString(36, 756, "SENTRY-CxA: TRI-SILO C&E DISCREPANCY & FIRST-FAULT AUDIT")
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(colors.HexColor("#64748B"))
        canvas.drawRightString(576, 756, "Systems Specialist: Rohit Kumar, PMP, CEng")
        canvas.setStrokeColor(colors.HexColor("#CBD5E1"))
        canvas.setLineWidth(0.5)
        canvas.line(36, 750, 576, 750)
        canvas.line(36, 42, 576, 42)
        canvas.drawString(36, 31, "Confidential | Rohit Kumar, PMP, CEng | grohit41@gmail.com | LinkedIn: ROHITG41")
        canvas.drawRightString(576, 31, f"Page {doc_obj.page} | NFPA 110 & ANSI/TIA-942-C Verified")
        canvas.restoreState()

    doc.build(story, onFirstPage=add_header_footer, onLaterPages=add_header_footer)
    buffer.seek(0)
    return buffer.getvalue()

# ---------------------------------------------------------
# 5. SIDEBAR: OPERATING MODE & CONTROLS
# ---------------------------------------------------------
with st.sidebar:
    st.header("⚡ Operational Mode & Sentry Scope")
    
    audit_mode = st.radio(
        "Select Operating Mode:",
        ["Mode A: Level 4/5 IST Commissioning Audit", "Mode B: Unscheduled Outage Root Cause Analysis (RCA)"],
        index=0,
        help="Mode A audits planned commissioning against DBRs; Mode B performs rapid root-cause timeline analysis during incidents."
    )
    
    facility_name = st.text_input("Facility Identifier:", value="DC-HYPERSCALE-ZONE-1")
    rated_topology = st.selectbox("Design Redundancy Rating:", ["Tier IV / Rated-4 (2N)", "Tier III / Rated-3 (N+1)"], index=0)
    
    st.markdown("---")
    st.subheader("High-Frequency Sampling Check")
    sampling_freq = st.selectbox(
        "White Space Telemetry Polling Rate:",
        ["100 ms (High-Resolution Stream)", "1.0 s (Real-Time Sub-Second)", "60.0 s (Legacy Polled Average)"],
        index=0
    )
    
    if "60.0 s" in sampling_freq:
        st.warning("⚠️ **Downsampling Warning:** 60s interval polling risks masking fast thermal/voltage excursions in high-density GPU racks.")

    st.markdown("---")
    st.markdown("**Normative Standards Grounding:**")
    st.caption("• NFPA 110 Type 10 (Gen Sync <= 10.0s)\n• ANSI/TIA-942-C (2N Fault Tolerance)\n• ASHRAE TC 9.9 Continuous Cooling\n• IEEE 446 Emergency Power Systems")

    st.markdown("---")
    user_key = st.text_input("Gemini API Key (Optional Override)", type="password")
    active_key = user_key if user_key else api_key

# ---------------------------------------------------------
# 6. MAIN WORKSPACE: TRI-SILO TIMELINE & FAULT INJECTION
# ---------------------------------------------------------
st.title("⚡ Sentry-CxA: Tri-Silo C&E Matrix & First-Fault Auditor")
st.caption(f"Unified Operational Layer: **EPMS + BMS + DCIM** | Active Mode: **{audit_mode}**")

st.markdown("""
This engine eliminates manual timeline stitching across fragmented data center monitoring systems. 
Edit telemetry cells or inject classic inter-system failures below to observe how the **First-Fault Arbitration Engine** 
automatically isolates the initiating mechanical/electrical clash from downstream symptoms.
""")

if "tri_ce_table" not in st.session_state:
    st.session_state["tri_ce_table"] = pd.DataFrame(DEFAULT_CE_DATA)

col_b1, col_b2, col_b3 = st.columns(3)
with col_b1:
    if st.button("🔄 Reset to Baseline Telemetry"):
        st.session_state["tri_ce_table"] = pd.DataFrame(DEFAULT_CE_DATA)
        st.rerun()

with col_b2:
    if st.button("🔥 Inject Inter-Silo Clash: Generator Sync Lag (8.4s)"):
        st.session_state["tri_ce_table"].loc[3, "Measured Value"] = 8.40
        st.session_state["tri_ce_table"].loc[5, "Measured Value"] = 11.80
        st.rerun()

with col_b3:
    if st.button("🚨 Inject Critical Chiller Fail & Thermal Spike"):
        st.session_state["tri_ce_table"].loc[5, "Measured Value"] = 15.60
        st.session_state["tri_ce_table"].loc[7, "Measured Value"] = 88.00
        st.rerun()

# Interactive Data Editor
edited_tri_df = st.data_editor(
    st.session_state["tri_ce_table"],
    num_rows="fixed",
    use_container_width=True,
    column_config={
        "ID": st.column_config.TextColumn(disabled=True, width="small"),
        "Timestamp_Label": st.column_config.TextColumn("Timestamp", disabled=True, width="small"),
        "Silo": st.column_config.TextColumn("Domain Silo", disabled=True, width="small"),
        "Subsystem": st.column_config.TextColumn(disabled=True),
        "Milestone Event": st.column_config.TextColumn(disabled=True),
        "Measured Value": st.column_config.NumberColumn("Measured Telemetry", help="Edit to inject faults"),
        "Unit": st.column_config.TextColumn(disabled=True, width="small"),
        "Code Limit": st.column_config.NumberColumn(disabled=True, width="small"),
        "DBR Limit": st.column_config.NumberColumn(disabled=True, width="small"),
        "Sampling_Rate": st.column_config.TextColumn("Resolution", disabled=True, width="small"),
        "Description": st.column_config.TextColumn(disabled=True)
    }
)
st.session_state["tri_ce_table"] = edited_tri_df

# Run Deterministic Check
audit_df, counts, first_fault, cascading = run_tri_silo_audit(edited_tri_df)

st.markdown("---")
if first_fault:
    st.error(f"""
    🚨 **FIRST-FAULT INITIATING EVENT DETECTED AT `{first_fault['Timestamp']}`:**  
    **Subsystem:** `[{first_fault['Silo']}] {first_fault['Subsystem']}` — *{first_fault['Milestone Event']}*  
    **Measured:** `{first_fault['Measured']}` (Violates DBR: `{first_fault['DBR Limit']}`) | **Status:** `{first_fault['Audit Status']}`  
    *The engine isolated this as the primary initiating failure. {len(cascading)} subsequent non-conformances identified as cascading symptoms.*
    """)
else:
    st.success("✅ **SEAMLESS SEQUENCE VERIFIED:** All cross-domain EPMS, BMS, and DCIM telemetry milestones meet both Normative Standards and DBR contractual thresholds.")

kpi1, kpi2, kpi3, kpi4 = st.columns(4)
with kpi1:
    st.metric("Total Milestones", len(edited_tri_df))
with kpi2:
    st.metric("Compliant Events", f"{counts['COMPLIANT']} / {len(edited_tri_df)}")
with kpi3:
    st.metric(
        "DBR Contract Variances", 
        counts['DBR VARIANCE'], 
        delta="-Review Needed" if counts['DBR VARIANCE'] > 0 else "Zero Variance",
        delta_color="inverse" if counts['DBR VARIANCE'] > 0 else "normal"
    )
with kpi4:
    st.metric(
        "Critical Code Breaches", 
        counts['CRITICAL CODE BREACH'],
        delta="Action Required" if counts['CRITICAL CODE BREACH'] > 0 else "Optimal",
        delta_color="inverse" if counts['CRITICAL CODE BREACH'] > 0 else "normal"
    )

st.markdown("##### Real-Time Tri-Silo Telemetry Scorecard:")
st.dataframe(
    audit_df[["ID", "Timestamp", "Silo", "Subsystem", "Measured", "Code Limit", "DBR Limit", "Audit Status", "Rationale"]],
    use_container_width=True
)

st.markdown("---")

# ---------------------------------------------------------
# 7. COGNITIVE AUDITOR & LOCKED MEMORANDUM GENERATOR
# ---------------------------------------------------------
btn_label = "⚡ Generate Formal Commissioning Non-Conformance Report (NCR)" if "Mode A" in audit_mode else "🔍 Generate Incident Root Cause Analysis (RCA) Memorandum"
if st.button(btn_label, type="primary", use_container_width=True):
    if not active_key:
        st.error("Please enter a valid Gemini API Key in the sidebar or environment.")
    else:
        with st.spinner("Arbitrating tri-silo timeline and synthesizing first-fault interaction memo..."):
            try:
                rag_context = ""
                if os.path.exists("./chroma_dc_db"):
                    try:
                        embeddings = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-2", google_api_key=active_key)
                        vdb = Chroma(persist_directory="./chroma_dc_db", embedding_function=embeddings)
                        docs = vdb.similarity_search("Level 5 IST black start emergency generator synchronization continuous cooling", k=3)
                        rag_context = "\n\n".join([d.page_content for d in docs])
                    except Exception:
                        rag_context = "Normative Standards: NFPA 110 Type 10, ANSI/TIA-942-C 2N Fault Tolerance, ASHRAE TC 9.9 Continuous Cooling."

                try:
                    llm = ChatGoogleGenerativeAI(model="gemini-3.8-flash", temperature=0.0, google_api_key=active_key)
                except Exception:
                    llm = ChatGoogleGenerativeAI(model="gemini-3.5-flash", temperature=0.0, google_api_key=active_key)

                discrepancy_rows = audit_df[audit_df["Audit Status"] != "COMPLIANT"].to_dict(orient="records")

                prompt = (
                    f"You are the Lead Data Center Infrastructure & Systems Engineering Specialist.\n"
                    f"Operational Scope: {audit_mode} | Facility: {facility_name} | Topology: {rated_topology}\n"
                    f"Sampling Frequency: {sampling_freq}\n\n"
                    f"First-Fault Engine Results:\n"
                    f"- Initiating Root Cause: {first_fault}\n"
                    f"- Cascading Downstream Symptoms: {cascading}\n"
                    f"- Total Discrepancies: {len(discrepancy_rows)}\n\n"
                    f"Governing Normative Standards Grounding:\n{rag_context}\n\n"
                    f"Draft an authoritative, highly professional Technical Engineering Memorandum.\n\n"
                    f"STRICT STRUCTURAL REQUIREMENTS (YOU MUST FOLLOW THESE EXACT HEADINGS):\n"
                    f"1. EXECUTIVE DETERMINATION & FIRST-FAULT ATTRIBUTION\n"
                    f"2. CROSS-SILO TIMELINE STITCHING & INTER-SYSTEM IMPACT\n"
                    f"3. CONTRACTUAL DBR VS. NORMATIVE CODE GAP ANALYSIS\n"
                    f"4. MANDATORY RECTIFICATION & RETEST PROTOCOL\n"
                    f"   A. EPMS & Generator Subsystem Rectification (CE-04)\n"
                    f"   B. BMS & Mechanical System Tuning (CE-06 & CE-09)\n"
                    f"   C. Formal Retest Protocol\n"
                    f"      (Under C. Formal Retest Protocol, you MUST include these exact 5 bullet points):\n"
                    f"      * Test Condition: Level 5 IST Scenario A (Full Utility Power Loss / Black Start).\n"
                    f"      * Thermal Saturation: 100% white space resistive/reactive load bank deployment.\n"
                    f"      * Monitoring: Continuous 100 ms high-resolution telemetry logging across EPMS, BMS, and UPS silos.\n"
                    f"      * Acceptance Thresholds: Zero DBR variances (CE-04 <= 7.00s, CE-06 <= 11.5 deg C, CE-09 <= 90.0s).\n"
                    f"      * Handover Status: HOLD pending successful execution of Retest Protocol.\n\n"
                    f"CRITICAL FORMATTING MANDATES:\n"
                    f"- STRICTLY FORBIDDEN: DO NOT generate ASCII or Markdown tables (NEVER use '|', '+', or '---' table borders). Write all text as paragraphs and bullets.\n"
                    f"- STRICTLY FORBIDDEN: DO NOT use LaTeX math syntax or math blocks (NEVER use '$', '\\le', '\\ge', '\\text{{}}', or '^\\circ').\n"
                    f"- Write all inequalities and units in standard alphanumeric text: '<= 7.0 s', '>= 2.2 bar', '11.5 deg C'.\n"
                    f"- STRICTLY FORBIDDEN: DO NOT use code backticks (`) around IDs or telemetry names.\n"
                )

                response = llm.invoke([
                    SystemMessage(content=prompt),
                    HumanMessage(content="Audit the submitted tri-silo telemetry matrix and generate the formal technical memorandum.")
                ])

                st.session_state["tri_audit_memo"] = extract_text(response.content)

            except Exception as e:
                st.error(f"Execution Error: {e}")

if "tri_audit_memo" in st.session_state:
    st.markdown("### 📋 Formal Engineering Evaluation Memorandum")
    st.markdown(st.session_state["tri_audit_memo"])

    pdf_bytes = generate_tri_silo_pdf(
        df_audit=audit_df,
        summary_counts=counts,
        first_fault=first_fault,
        facility_tag=f"{facility_name} ({rated_topology})",
        audit_memo=st.session_state["tri_audit_memo"]
    )

    st.download_button(
        label="📥 Download Engineering Audit Report (Branded PDF)",
        data=pdf_bytes,
        file_name="Tri_Silo_IST_First_Fault_Audit_Report.pdf",
        mime="application/pdf",
        use_container_width=True
    )