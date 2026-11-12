"""
SENTRY-MAS: AUTONOMOUS SHARED CONSENSUS MULTI-AGENT OPERATIONAL ARBITRATION ENGINE
Hyperscale Data Center Infrastructure & Systems Engineering Suite - Post 3 Capstone

Lead Systems Architect: Rohit Kumar, PMP, CEng, CEA, FSEr (TÜV)
Domain: Mission-Critical Infrastructure & Systems Engineering Specialist | Forensic Project Controls & Contract Governance
Contact: grohit41@gmail.com | LinkedIn: ROHITG41 (linkedin.com/in/rohitg41)
GitHub: https://github.com/ROHITG41/sentry-cxa-datacenter
"""

import streamlit as st
import os
import math
import json
import re
import datetime
from typing import Dict, Any, List, Optional, Tuple
from pydantic import BaseModel, Field

# ---------------------------------------------------------
# 1. PAGE CONFIGURATION & STYLING
# ---------------------------------------------------------
st.set_page_config(
    page_title="Sentry-MAS | Data Center Multi-Agent Arbiter",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

CUSTOM_CSS = """
<style>
    .main-header {
        font-family: 'Segoe UI', Helvetica, Arial, sans-serif;
        color: #102C57;
        font-size: 2.15rem;
        font-weight: 800;
        margin-bottom: 0px;
        letter-spacing: -0.5px;
    }
    .sub-header {
        font-family: 'Segoe UI', Helvetica, Arial, sans-serif;
        color: #0F766E;
        font-size: 1.05rem;
        font-weight: 600;
        margin-bottom: 18px;
    }
    .provenance-card {
        background-color: #F8FAFC;
        border-left: 4px solid #102C57;
        padding: 12px 18px;
        border-radius: 4px;
        margin-bottom: 16px;
        font-size: 0.88rem;
        color: #334155;
        line-height: 1.5;
    }
    .agent-box-ops {
        background-color: #FEF2F2;
        border: 1px solid #FECACA;
        border-left: 5px solid #DC2626;
        padding: 16px;
        border-radius: 6px;
        margin-bottom: 15px;
    }
    .agent-box-eco {
        background-color: #F0FDF4;
        border: 1px solid #BBF7D0;
        border-left: 5px solid #16A34A;
        padding: 16px;
        border-radius: 6px;
        margin-bottom: 15px;
    }
    .arbiter-box {
        background-color: #F0FDFA;
        border: 1px solid #99F6E4;
        border-left: 5px solid #0F766E;
        padding: 18px;
        border-radius: 6px;
        margin-bottom: 18px;
    }
    .ncr-box {
        background-color: #FFF1F2;
        border: 2px solid #E11D48;
        padding: 18px;
        border-radius: 6px;
        margin-top: 18px;
    }
    .metric-card {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 8px;
        padding: 12px 14px;
        text-align: center;
        box-shadow: 0 1px 3px rgba(0,0,0,0.04);
    }
    .metric-value {
        font-size: 1.55rem;
        font-weight: 700;
        color: #102C57;
        margin-top: 4px;
    }
    .metric-label {
        font-size: 0.76rem;
        color: #64748B;
        text-transform: uppercase;
        font-weight: 700;
        letter-spacing: 0.5px;
    }
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# ---------------------------------------------------------
# 2. HELPER: GENAI TEXT EXTRACTION & INITIALIZATION
# ---------------------------------------------------------
def extract_text(response) -> str:
    """Safely unpacks text from Google GenAI SDK response objects."""
    if response is None:
        return ""
    if isinstance(response, str):
        return response
    if hasattr(response, "text") and response.text:
        return response.text
    if hasattr(response, "candidates") and response.candidates:
        cand = response.candidates[0]
        if hasattr(cand, "content") and cand.content:
            parts = getattr(cand.content, "parts", [])
            txts = [getattr(p, "text", "") for p in parts if hasattr(p, "text")]
            if txts:
                return "".join(txts)
    return str(response)

def get_genai_client(api_key: str):
    """Initializes Google GenAI client with fallback mechanism."""
    try:
        from google import genai
        client = genai.Client(api_key=api_key)
        return client, "v2"
    except Exception:
        try:
            import google.generativeai as gai
            gai.configure(api_key=api_key)
            return gai, "v1"
        except Exception as e:
            st.error(f"Failed to initialize Google GenAI SDK: {e}")
            return None, "none"

# ---------------------------------------------------------
# 3. STRUCTURED PYDANTIC DATA CONTRACTS
# ---------------------------------------------------------
class TelemetryPayload(BaseModel):
    test_id: str = Field(description="Unique commissioning or operational audit tracking ID")
    stage: str = Field(description="Project lifecycle stage: CONCEPT_DESIGN, LEVEL5_IST, DAY2_OPERATIONS")
    total_it_load_kw: float = Field(description="Total IT whitespace thermal load in kW")
    peak_rack_density_kw: float = Field(description="Maximum rack computational density in kW/rack")
    chw_supply_c: float = Field(description="Chilled water supply header temperature in deg C")
    chw_return_c: float = Field(description="Chilled water return header temperature in deg C")
    loop_delta_p_bar: float = Field(description="Hydronic loop differential pressure across index coil in bar")
    buffer_liters: float = Field(description="Usable thermal energy storage buffer tank capacity in Liters")
    ats_transfer_sec: float = Field(description="Electrical transfer break duration in seconds")
    gen_sync_sec: float = Field(description="Emergency generator bus synchronization delay in seconds")
    chiller_restart_sec: float = Field(description="Chiller compressor fast-restart delay in seconds")
    wse_transition_sec: float = Field(description="Water-side economizer mode change transient duration in seconds")

class DeterministicAuditMetrics(BaseModel):
    t_interruption_total_sec: float
    t_buffer_hold_min: float
    t_required_min: float
    buffer_margin_min: float
    dT_dt_transient_c_per_min: float
    pump_power_penalty_pct: float
    estimated_pue: float
    operational_compromise_index: float
    status: str
    breach_reasons: List[str]

# ---------------------------------------------------------
# 4. DETERMINISTIC PHYSICS & MATHEMATICAL ARBITRATION GATES
# ---------------------------------------------------------
def calculate_deterministic_physics(data: TelemetryPayload) -> DeterministicAuditMetrics:
    """
    Executes CPU-bound thermodynamic, hydraulic, and electromechanical calculations.
    Formulas adhere strictly to ASHRAE TC 9.9, Uptime Tier IV continuous cooling, and fluid mechanics.
    """
    rho = 1000.0  # kg/m3 for water
    Cp = 4.184    # kJ/(kg.K)
    
    # 1. Total power interruption timeline (seconds)
    t_total_interruption = data.ats_transfer_sec + data.gen_sync_sec + data.chiller_restart_sec
    t_required_min = (t_total_interruption * 1.25) / 60.0  # 25% safety reserve factor
    
    # 2. Maximum allowable continuous cooling ceiling (ASHRAE TC 9.9 Class A1 continuous ceiling = 18C supply)
    T_max_allowable_chw = 18.0
    delta_T_usable = max(0.1, T_max_allowable_chw - data.chw_supply_c)
    
    # Thermal buffer hold-up capacity: Q = V * rho * Cp * delta_T => t = (V * rho * Cp * delta_T) / Q_load
    Q_kW = max(100.0, data.total_it_load_kw)
    V_m3 = data.buffer_liters / 1000.0
    
    energy_stored_kJ = V_m3 * rho * Cp * delta_T_usable
    t_buffer_hold_sec = energy_stored_kJ / Q_kW
    t_buffer_hold_min = t_buffer_hold_sec / 60.0
    
    buffer_margin_min = t_buffer_hold_min - t_required_min
    
    # 3. Rate of temperature rise during unmitigated outage (deg C / min)
    V_total_loop_m3 = V_m3 * 1.35
    dT_dt_transient_c_per_min = (Q_kW * 60.0) / (V_total_loop_m3 * rho * Cp)
    
    # 4. Fluid friction & dynamic pumping penalty (Darcy-Weisbach & Affinity Laws)
    baseline_dp = 1.50
    pump_power_penalty_pct = max(0.0, ((data.loop_delta_p_bar - baseline_dp) / baseline_dp) * 100.0)
    
    # 5. Estimated PUE correlation
    cop_base = 5.5
    chw_lift_benefit = max(0.0, (data.chw_supply_c - 7.0) * 0.15)
    cop_actual = cop_base + chw_lift_benefit
    chiller_kw_per_ton = 3.517 / cop_actual
    cooling_load_tons = Q_kW / 3.517
    chiller_power_kw = cooling_load_tons * chiller_kw_per_ton
    pumping_power_kw = 120.0 * (1.0 + (pump_power_penalty_pct / 100.0))
    aux_power_kw = Q_kW * 0.05
    total_facility_kw = Q_kW + chiller_power_kw + pumping_power_kw + aux_power_kw
    estimated_pue = round(total_facility_kw / Q_kW, 3)
    
    # 6. Operational Compromise Index (OCI) Formulation
    breach_reasons = []
    
    buffer_ratio = min(1.0, max(0.0, t_buffer_hold_min / max(0.1, t_required_min)))
    if buffer_margin_min < 0:
        breach_reasons.append(f"Thermal buffer shortfall: {abs(buffer_margin_min):.2f} mins deficit during utility outage ride-through.")
    
    dp_penalty_factor = min(1.0, pump_power_penalty_pct / 100.0)
    pumping_score = max(0.0, 1.0 - (dp_penalty_factor * 0.6))
    if data.loop_delta_p_bar > 2.40:
        breach_reasons.append(f"Excessive loop DP ({data.loop_delta_p_bar:.2f} bar) causing continuous valve hunting and 2-way bypass cavitation.")
    
    thermal_score = 1.0
    if dT_dt_transient_c_per_min > 0.85:
        thermal_score -= 0.35
        breach_reasons.append(f"Transient temperature rise rate ({dT_dt_transient_c_per_min:.2f} deg C/min) risks GPU silicon thermal trip.")
    if data.wse_transition_sec > 45.0:
        thermal_score -= 0.25
        breach_reasons.append(f"Economizer valve switchover latency ({data.wse_transition_sec:.1f} s) creates unacceptable coil thermal ripple.")
    thermal_score = max(0.0, thermal_score)
    
    oci_raw = (0.45 * buffer_ratio + 0.30 * pumping_score + 0.25 * thermal_score) * 100.0
    
    if buffer_margin_min < 0:
        oci_raw -= 25.0
    if data.chw_supply_c > 16.0 and data.peak_rack_density_kw >= 80.0:
        oci_raw -= 20.0
        breach_reasons.append("Chilled water supply temperature (>16 deg C) cannot sustain 80+ kW/rack AI liquid cold-plates.")
        
    oci_final = max(0.0, min(100.0, round(oci_raw, 1)))
    
    if oci_final >= 75.0:
        status = "CONSENSUS_VALIDATED"
    elif 60.0 <= oci_final < 75.0:
        status = "CONDITIONAL_ACCORD_MONITORED"
    else:
        status = "CONSENSUS_BREACH_ACTION_REQUIRED"
        
    return DeterministicAuditMetrics(
        t_interruption_total_sec=round(t_total_interruption, 2),
        t_buffer_hold_min=round(t_buffer_hold_min, 2),
        t_required_min=round(t_required_min, 2),
        buffer_margin_min=round(buffer_margin_min, 2),
        dT_dt_transient_c_per_min=round(dT_dt_transient_c_per_min, 3),
        pump_power_penalty_pct=round(pump_power_penalty_pct, 1),
        estimated_pue=estimated_pue,
        operational_compromise_index=oci_final,
        status=status,
        breach_reasons=breach_reasons
    )

# ---------------------------------------------------------
# 5. DOMAIN KNOWLEDGE & NORMATIVE STANDARDS RETRIEVAL
# ---------------------------------------------------------
def retrieve_engineering_standards(stage: str) -> str:
    """Retrieves authoritative standards context with fallback grounding."""
    grounding_corpus = {
        "CONCEPT_DESIGN": (
            "ASHRAE TC 9.9 Thermal Guidelines for High-Density Compute: Recommended Class A1 dry bulb 18.0 to 27.0 deg C. "
            "Uptime Institute Tier IV Site Infrastructure: Requires 2N Fault Tolerant continuous cooling with concurrent maintainability. "
            "Thermal buffer storage must bridge the gap between utility interruption and primary chiller full cooling output with zero flow interruption. "
            "ASHRAE 90.4-2022 Energy Standard: Mechanical Load Component (MLC) calculations require credit for water-side economization where wet-bulb permits."
        ),
        "LEVEL5_IST": (
            "IEEE 446 (Orange Book): Recommended practice for emergency and standby power systems in industrial applications; sub-cycle critical bus continuity. "
            "Level 5 Integrated System Testing (IST) Grid Outage Simulation Mandate: All cooling pumps must maintain continuous flow through STS transfers or immediate VFD ride-through. "
            "Differential Pressure (DP) Reset Stability: Actuator stroke speed must be tuned to prevent hydraulic resonance or 2-way control valve hunting. "
            "Continuous Cooling Verification: Chilled water header temperature entering CRAH/CDU units must not rise > 2.0 deg C above design baseline during power transitions."
        ),
        "DAY2_OPERATIONS": (
            "ASHRAE TC 9.9 Liquid Cooling Addendum: Server rack densities exceeding 60 kW/rack require cold-plate fluid supply temperatures below 16.0 deg C to prevent junction over-temperature. "
            "Economizer Switchover Dynamics: Automatic switchover from mechanical chiller to plate heat exchanger free-cooling must not induce temperature swings > 1.5 deg C or dT/dt > 5.0 deg C/hr. "
            "Fan Affinity Laws (P proportional to N^3): Over-speeding CRAH/CDU fans to compensate for elevated CHW temperatures incurs cubic electrical penalties that outstrip chiller refrigeration savings."
        )
    }
    return grounding_corpus.get(stage, grounding_corpus["LEVEL5_IST"])

# ---------------------------------------------------------
# 6. COGNITIVE MULTI-AGENT ORCHESTRATION LAYER (GEMINI)
# ---------------------------------------------------------
def run_multi_agent_consensus(
    api_key: str, 
    telemetry: TelemetryPayload, 
    metrics: DeterministicAuditMetrics
) -> Tuple[str, str, str, str]:
    """
    Executes the Shared Consensus Multi-Agent debate and deterministic arbitration.
    Returns: (ops_sentinel_proposal, eco_optimizer_proposal, arbiter_accord, engineering_ncr)
    """
    standards_context = retrieve_engineering_standards(telemetry.stage)
    
    FORMATTING_GUARDRAILS = (
        "\nCRITICAL FORMATTING INSTRUCTIONS (STRICT COMPLIANCE REQUIRED):\n"
        "- DO NOT use LaTeX syntax or math blocks (NEVER use '$', '\\le', '\\ge', '\\text{}', '\\Delta', or '^\\circ').\n"
        "- Write all inequalities, formulas, and units in plain engineering alphanumeric text: '<= 7.0 s', '>= 2.2 bar', '11.5 deg C', 'E = 0.5 x C x (V_nom² - V_trip²)'.\n"
        "- DO NOT use code backticks (`) around equipment tags, telemetry points, or numbers.\n"
        "- DO NOT generate raw Markdown/ASCII tables or table borders (NEVER use '|', '---', or '+++'). Format structured comparisons into clean paragraph bullet points ('•').\n"
    )
    
    # Prompt for Agent 1: Facilities Sentinel
    ops_prompt = (
        "You are Agent 1: Facilities / Operations Sentinel (Ops-Sentinel).\n"
        "Your mandate: Defend 100% Uptime, Uptime Tier IV continuous cooling, zero rack thermal SLA breach, elevated DP setpoint (>= 2.2 bar), low CHW supply temps (7.0 - 9.0 deg C), fast-restart survivability, and conservative safety padding.\n\n"
        f"Current Telemetry:\n"
        f"- Test ID: {telemetry.test_id} | Lifecycle Stage: {telemetry.stage}\n"
        f"- IT Load: {telemetry.total_it_load_kw} kW | Peak Rack Density: {telemetry.peak_rack_density_kw} kW/rack\n"
        f"- CHW Supply: {telemetry.chw_supply_c} deg C | CHW Return: {telemetry.chw_return_c} deg C\n"
        f"- Loop DP: {telemetry.loop_delta_p_bar} bar | Buffer Tank: {telemetry.buffer_liters} Liters\n"
        f"- Total Power Interruption Window: {metrics.t_interruption_total_sec} s (ATS: {telemetry.ats_transfer_sec}s, Gen: {telemetry.gen_sync_sec}s, Restart: {telemetry.chiller_restart_sec}s)\n"
        f"- Calculated Buffer Hold-up: {metrics.t_buffer_hold_min} mins (Required: {metrics.t_required_min} mins, Margin: {metrics.buffer_margin_min} mins)\n"
        f"- Transient dT/dt: {metrics.dT_dt_transient_c_per_min} deg C/min\n"
        f"- Standards Context: {standards_context}\n"
        f"{FORMATTING_GUARDRAILS}\n"
        "Output a structured, uncompromising operational position defending physical equipment safety, citing thermal reserve, and warning against PUE over-optimization. Format in clean, authoritative technical prose."
    )

    # Prompt for Agent 2: Energy Auditor / PUE Optimizer
    eco_prompt = (
        "You are Agent 2: Energy Auditor / PUE Optimizer (Eco-Optimizer).\n"
        "Your mandate: Minimize PUE and chiller kW/ton, maximize water-side economizer (WSE) free-cooling hours, execute dynamic DP reset based on critical valve position, elevate CHW supply temps (14.0 - 18.0 deg C), and eliminate parasitic pumping waste.\n\n"
        f"Current Telemetry:\n"
        f"- Test ID: {telemetry.test_id} | Lifecycle Stage: {telemetry.stage}\n"
        f"- IT Load: {telemetry.total_it_load_kw} kW | Peak Rack Density: {telemetry.peak_rack_density_kw} kW/rack\n"
        f"- CHW Supply: {telemetry.chw_supply_c} deg C | Loop DP: {telemetry.loop_delta_p_bar} bar\n"
        f"- Pumping Power Penalty: +{metrics.pump_power_penalty_pct}% over baseline\n"
        f"- Estimated Facility PUE: {metrics.estimated_pue}\n"
        f"- Economizer Transition Duration: {telemetry.wse_transition_sec} s\n"
        f"- Standards Context: {standards_context}\n\n"
        f"{FORMATTING_GUARDRAILS}\n"
        "Output a structured, mathematically sharp energy optimization position. Challenge excessive safety padding, demonstrate the thermodynamic lift savings from warmer chilled water, and demand dynamic DP reset to open starving control valves. Format in clean, authoritative technical prose."
    )

    # Fallback default outputs
    default_ops = (
        "OPERATIONS SENTINEL DISPOSITION:\n"
        f"1. Continuous Cooling Integrity: Buffer margin is currently {metrics.buffer_margin_min:+.2f} minutes against an interruption window of {metrics.t_interruption_total_sec:.1f} s.\n"
        f"2. Thermal Vulnerability: At {telemetry.peak_rack_density_kw:.1f} kW/rack, supply water at {telemetry.chw_supply_c:.1f} deg C leaves inadequate transient thermal ride-through during valve repositioning.\n"
        "3. Operational Stance: Facilities Sentinel rejects raising CHW supply above 10.0 deg C or lowering loop DP below 2.2 bar until transient hold-up is proven by verified trending."
    )
    
    default_eco = (
        "ENERGY AUDITOR DISPOSITION:\n"
        f"1. PUE Optimization Mandate: Current estimated PUE of {metrics.estimated_pue:.3f} reflects an avoidable parasitic power penalty of +{metrics.pump_power_penalty_pct:.1f}%.\n"
        f"2. Pumping Waste: Operating at {telemetry.loop_delta_p_bar:.2f} bar forces 2-way control valves to throttle to under 35% stroke, creating unnecessary head loss and seat wire-drawing.\n"
        "3. Operational Stance: Energy Auditor demands resetting DP setpoint to 1.65 bar and elevating CHW supply to 14.0 deg C to harvest annual water-side economizer hours."
    )

    ops_response_text = default_ops
    eco_response_text = default_eco

    if api_key:
        client, version = get_genai_client(api_key)
        if version == "v2":
            try:
                r1 = client.models.generate_content(model="gemini-3.8-flash", contents=ops_prompt)
                ops_response_text = extract_text(r1)
                r2 = client.models.generate_content(model="gemini-3.8-flash", contents=eco_prompt)
                eco_response_text = extract_text(r2)
            except Exception:
                try:
                    r1 = client.models.generate_content(model="gemini-3.5-flash", contents=ops_prompt)
                    ops_response_text = extract_text(r1)
                    r2 = client.models.generate_content(model="gemini-3.5-flash", contents=eco_prompt)
                    eco_response_text = extract_text(r2)
                except Exception as e:
                    st.warning(f"Using deterministic fallback personas (GenAI error: {e})")
        elif version == "v1":
            try:
                m1 = client.GenerativeModel("gemini-1.5-flash")
                ops_response_text = extract_text(m1.generate_content(ops_prompt))
                eco_response_text = extract_text(m1.generate_content(eco_prompt))
            except Exception as e:
                st.warning(f"Using deterministic fallback personas (GenAI v1 error: {e})")

    # Prompt for Arbiter / Consensus Gate
    arbiter_prompt = (
        "You are the Deterministic Consensus Arbiter & Data Center Infrastructure Systems Specialist.\n"
        "You are arbitrating between Agent 1 (Facilities Sentinel) and Agent 2 (Energy Auditor).\n\n"
        "DETERMINISTIC CPU GROUND TRUTH (IMMUTABLE):\n"
        f"- Operational Compromise Index (OCI): {metrics.operational_compromise_index} / 100.0\n"
        f"- Status: {metrics.status}\n"
        f"- Total Power Interruption Window: {metrics.t_interruption_total_sec} s\n"
        f"- Buffer Hold-up Time: {metrics.t_buffer_hold_min} mins (Required: {metrics.t_required_min} mins | Margin: {metrics.buffer_margin_min} mins)\n"
        f"- Transient dT/dt: {metrics.dT_dt_transient_c_per_min} deg C/min\n"
        f"- Hydraulic DP Power Penalty: +{metrics.pump_power_penalty_pct}%\n"
        f"- Calculated PUE: {metrics.estimated_pue}\n"
        f"- Physical Breaches: {json.dumps(metrics.breach_reasons)}\n\n"
        "PROPOSALS SUBMITTED TO SHARED CONSENSUS WORKSPACE:\n"
        f"[Facilities Sentinel Proposal]: {ops_response_text[:600]}\n"
        f"[Energy Auditor Proposal]: {eco_response_text[:600]}\n\n"
        f"{FORMATTING_GUARDRAILS}\n"
        "TASK:\n"
        "Issue a binding Operational Determination Accord. If OCI >= 75.0, ratify consensus with exact arbitrated setpoints.\n"
        "If 60.0 <= OCI < 75.0, issue a Conditional Accord with mandatory setpoint trimming and monitoring.\n"
        "If OCI < 60.0, DECLARE CONSENSUS COLLAPSE and issue an Engineering Non-Conformance Notice.\n"
        "Format your determination with:\n"
        "1. Executive Consensus Disposition & OCI Score\n"
        "2. Arbitrated CHW Supply Setpoint & Loop DP Setpoint\n"
        "3. Trade Package Remediation Matrix (Mechanical vs Electrical vs BMS Controls)\n"
        "4. Binding Engineering Directive"
    )
    
    arbiter_text = ""
    if api_key:
        client, version = get_genai_client(api_key)
        if version == "v2":
            try:
                ra = client.models.generate_content(model="gemini-3.8-flash", contents=arbiter_prompt)
                arbiter_text = extract_text(ra)
            except Exception:
                try:
                    ra = client.models.generate_content(model="gemini-3.5-flash", contents=arbiter_prompt)
                    arbiter_text = extract_text(ra)
                except Exception:
                    arbiter_text = generate_default_arbiter_accord(telemetry, metrics)
        else:
            arbiter_text = generate_default_arbiter_accord(telemetry, metrics)
    else:
        arbiter_text = generate_default_arbiter_accord(telemetry, metrics)

    ncr_text = ""
    if metrics.status == "CONSENSUS_BREACH_ACTION_REQUIRED" or metrics.operational_compromise_index < 60.0:
        ncr_text = generate_engineering_ncr(telemetry, metrics)

    return ops_response_text, eco_response_text, arbiter_text, ncr_text

def generate_default_arbiter_accord(data: TelemetryPayload, metrics: DeterministicAuditMetrics) -> str:
    """Deterministic fallback for Arbiter Accord."""
    if metrics.operational_compromise_index >= 75.0:
        return (
            f"EXECUTIVE DETERMINATION ACCORD: CONSENSUS VALIDATED (OCI: {metrics.operational_compromise_index}/100)\n\n"
            f"1. Binding Operational Setpoints:\n"
            f"   - Arbitrated CHW Supply Temperature: {max(9.0, min(12.5, data.chw_supply_c)):.1f} deg C\n"
            f"   - Arbitrated Differential Pressure (DP): {max(1.70, min(2.10, data.loop_delta_p_bar)):.2f} bar\n"
            f"2. Physical Thermal Reserve: Buffer margin of {metrics.buffer_margin_min:+.2f} mins satisfies continuous cooling ride-through with 25% safety reserve.\n"
            f"3. Operational Directive: BMS controls team instructed to commit arbitrated setpoints and activate dynamic DP reset with a 1.70 bar low-limit floor."
        )
    elif metrics.operational_compromise_index >= 60.0:
        return (
            f"EXECUTIVE DETERMINATION ACCORD: CONDITIONAL ACCORD (OCI: {metrics.operational_compromise_index}/100)\n\n"
            f"1. Conditional Setpoint Trimming:\n"
            f"   - Arbitrated CHW Supply Temperature: Trimmed to 10.0 deg C (Safety Over-Ride applied to Energy proposal)\n"
            f"   - Arbitrated Loop DP: Fixed at 2.00 bar pending valve actuator stroke recalibration\n"
            f"2. Identified Marginalities: Buffer margin is tight ({metrics.buffer_margin_min:+.2f} mins); transient rate of rise is {metrics.dT_dt_transient_c_per_min:.2f} deg C/min.\n"
            f"3. Directive: Continuous 72-hour high-resolution trending mandated prior to sign-off."
        )
    else:
        return (
            f"EXECUTIVE DETERMINATION ACCORD: CONSENSUS COLLAPSE (OCI: {metrics.operational_compromise_index}/100)\n\n"
            f"PHYSICAL SAFETY BOUNDARY BREACH DETECTED: Thermodynamic safety criteria breached. Multi-agent negotiation aborted.\n"
            f"Primary Failures: {'; '.join(metrics.breach_reasons)}\n"
            f"ACTION: Engineering Non-Conformance & Operational Remediation Protocol triggered autonomously."
        )

def generate_engineering_ncr(data: TelemetryPayload, metrics: DeterministicAuditMetrics) -> str:
    """Generates an authoritative, technical Engineering Non-Conformance Protocol."""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ncr_no = f"ENG-NCR-{data.test_id}-{datetime.datetime.now().strftime('%y%m%d')}"
    
    primary_trade = "Mechanical & Hydronic Works"
    remedial_1 = "Re-calibrate chiller compressor fast-restart firmware to bring restart time under 45.0 seconds."
    if metrics.buffer_margin_min < 0:
        primary_trade = "Mechanical Systems (Thermal Storage Sizing & Chiller Fast-Restart)"
        remedial_1 = f"Increase usable thermal storage buffer volume from {data.buffer_liters:,.0f} L to eliminate the {abs(metrics.buffer_margin_min):.2f}-minute ride-through deficit."
    elif data.loop_delta_p_bar > 2.40:
        primary_trade = "BMS & Controls (PID Loop Hunting & Actuator Travel Timing)"
        remedial_1 = "Re-tune 2-way control valve PID loops and increase stroke damping to eliminate hunting at low part-load."
    elif data.ats_transfer_sec > 1.0 or data.gen_sync_sec > 10.0:
        primary_trade = "Electrical Systems (Generator Synchronization & ATS Transition)"
        remedial_1 = "Tune generator governor and paralleling switchgear to achieve stable bus sync within 7.0 seconds."
        
    return f"""================================================================================
ENGINEERING NON-CONFORMANCE REPORT & OPERATIONAL REMEDIATION PROTOCOL
DOCUMENT REF: {ncr_no} | DATE: {timestamp}
FACILITY RATING: UPTIME TIER IV / RATED-4 CONTINUOUS COOLING INFRASTRUCTURE
================================================================================

1. SYSTEM IDENTIFICATION & AUDIT MILESTONE
   - Incident / Audit Tracking ID: {data.test_id}
   - Asset Lifecycle Milestone: {data.stage}
   - Evaluated IT Whitespace Load: {data.total_it_load_kw:,.1f} kW
   - Peak Rack Density: {data.peak_rack_density_kw:.1f} kW/rack
   - Governing Engineering Codes: ASHRAE TC 9.9, IEEE 446, ASHRAE 90.4-2022

2. DETERMINISTIC PHYSICAL BOUNDARY BREACH
   - Operational Compromise Index (OCI): {metrics.operational_compromise_index} / 100.0 (BREACH THRESHOLD < 60.0)
   - Continuous Cooling Thermal Hold-Up: FAILED
     * Calculated Buffer Storage Hold-Up: {metrics.t_buffer_hold_min:.2f} Minutes
     * Statutory Continuous Cooling Requirement: {metrics.t_required_min:.2f} Minutes
     * Net Storage Deficit: {abs(metrics.buffer_margin_min):.2f} Minutes
   - Transient Thermal Gradient (dT/dt): {metrics.dT_dt_transient_c_per_min:.3f} deg C/min (Allowable Limit: 0.850 deg C/min)
   - Hydraulic Parasitic Head Loss: +{metrics.pump_power_penalty_pct:.1f}% Excess Pumping kW at {data.loop_delta_p_bar:.2f} bar

3. ROOT CAUSE ASSIGNMENT & TRADE PACKAGE ATTRIBUTION
   - Responsible Engineering Package: {primary_trade}
   - Technical Failure Mode: Thermodynamic Ride-Through Deficit & Control Loop Instability
   - Explicit Breaches Detected:
{chr(10).join([f"     * {b}" for b in metrics.breach_reasons])}

4. MANDATORY ENGINEERING REMEDIAL DIRECTIVES
   - Directive 1: {remedial_1}
   - Directive 2: Eliminate internal thermal stratification in the buffer vessel to ensure 100% active volume availability.
   - Directive 3: Re-tune secondary pump VFD acceleration ramps to prevent hydraulic pressure surges during step-transfers.
   - Directive 4: Stabilize dynamic DP reset with a calibrated 1.70 bar low-limit floor to prevent coil starvation.

5. HANDOVER & RETEST ACCEPTANCE CRITERIA
   - Facility retest must demonstrate continuous cooling flow with zero temperature excursions entering CRAH/CDU units.
   - Deterministic Operational Compromise Index (OCI) must achieve >= 75.0 under 100% full-load step transient testing.

ISSUED BY: Lead Systems Architect & Infrastructure Specialist
Rohit Kumar, PMP, CEng, CEA, FSEr (TÜV)
================================================================================
"""

# ---------------------------------------------------------
# 7. MULTI-STAGE REGEX SANITIZER & REPORTLAB PDF GENERATION
# ---------------------------------------------------------
def clean_and_format_for_reportlab(text: str) -> List[Tuple[str, bool]]:
    """
    Multi-stage regex sanitizer that:
    1. Normalizes unicode characters and strips unsupported emojis.
    2. Converts LaTeX mathematical constructs and code backticks into plain engineering units.
    3. Filters out raw ASCII/Markdown table borders (+++, |---|).
    4. Reformats markdown table rows into clean paragraph bullet points.
    5. Safely escapes XML entities (&, <, >) while converting **bold** to <b>bold</b>.
    """
    if not text:
        return []

    # 1. Unicode replacements & emoji stripping
    replacements = {
        '\u2018': "'", '\u2019': "'", '\u201c': '"', '\u201d': '"',
        '\u2013': '-', '\u2014': '--',
        '⚡': '', '✅': '[PASS]', '❌': '[FAIL]', '⚠️': '[WARN]',
        '🛡️': '', '🌱': '', '⚖️': '', '🚨': '', '📜': '', '📄': '', '🔑': '',
        '📋': '', '⚙️': '', '🚀': '', '📥': ''
    }
    for k, v in replacements.items():
        text = text.replace(k, v)

    # 2. LaTeX Math & Symbol Sanitization to plain engineering units
    text = text.replace('`', '')
    text = re.sub(r'\\le(q)?\b', '<=', text)
    text = re.sub(r'\\ge(q)?\b', '>=', text)
    text = re.sub(r'\\pm\b', '+/-', text)
    text = re.sub(r'\\times\b', ' x ', text)
    text = re.sub(r'\^?\\circ\s*(\\text\{C\}|C)?', ' deg C', text)
    text = re.sub(r'\\Delta\s*', 'Delta ', text)
    text = re.sub(r'\\text\{([^}]*)\}', r'\1', text)
    text = re.sub(r'V_\{?nom\}?\^2', 'V_nom²', text)
    text = re.sub(r'V_\{?trip\}?\^2', 'V_trip²', text)
    text = text.replace('$', '')

    cleaned_paragraphs = []
    lines = text.split('\n')

    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            continue

        # Strip ASCII / Markdown table borders e.g. +++, +---+, |---|
        if re.match(r'^[\|\+\-\s:]+$', line) or line.startswith('+++') or line.startswith('|---'):
            continue

        # Convert ASCII/Markdown table rows into clean paragraph bullet points
        is_table_row = False
        if line.startswith('|') and line.endswith('|'):
            cells = [c.strip() for c in line.split('|')[1:-1] if c.strip()]
            if not cells or all(re.match(r'^[\-\+:]+$', c) for c in cells):
                continue
            line = " -- ".join(cells)
            is_table_row = True

        # Detect Markdown Headings (# Header, ## Header, ### Header)
        is_heading = False
        if line.startswith('#'):
            line = re.sub(r'^[#\s]+', '', line).strip()
            line = line.replace('***', '').replace('**', '').replace('*', '').strip()
            is_heading = True

        # Detect Bullet points (*, -, •, ***)
        is_bullet = is_table_row
        if not is_heading:
            if line.startswith(('* ', '- ', '• ')):
                is_bullet = True
                line = line[2:].strip()
            elif line.startswith('***'):
                is_bullet = True
                line = re.sub(r'^\*+\s*', '', line).strip()

        # XML Entity escaping for ReportLab safety (escape & first)
        line = line.replace('&', '&amp;')

        # Balance and convert **bold** into <b>bold</b>
        if line.count('**') % 2 != 0:
            last_idx = line.rfind('**')
            line = line[:last_idx] + line[last_idx + 2:]

        parts = line.split('**')
        if len(parts) > 1:
            rebuilt = []
            for i, p in enumerate(parts):
                p_clean = p.replace('<', '&lt;').replace('>', '&gt;')
                if i % 2 == 1:
                    rebuilt.append(f"<b>{p_clean.strip()}</b>")
                else:
                    rebuilt.append(p_clean)
            line = "".join(rebuilt)
        else:
            line = line.replace('<', '&lt;').replace('>', '&gt;')

        # Strip any remaining rogue asterisks or hashes
        line = line.replace('***', '').replace('**', '').replace('*', '')
        line = line.replace('###', '').replace('##', '').replace('#', '')
        line = line.replace('<b></b>', '')

        if is_bullet:
            line = f"&bull; {line}"

        line = line.encode('latin-1', 'replace').decode('latin-1')
        cleaned_paragraphs.append((line, is_heading))

    return cleaned_paragraphs

def generate_sanitized_pdf(
    telemetry: TelemetryPayload, 
    metrics: DeterministicAuditMetrics, 
    ops_text: str, 
    eco_text: str, 
    arbiter_text: str, 
    ncr_text: str
) -> bytes:
    """
    Generates an executive-ready PDF report strictly sanitized against raw LaTeX math syntax, 
    markdown table borders, and backticks. Employs PageBreak to guarantee zero orphan headers.
    """
    from reportlab.lib.pagesizes import letter
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, PageBreak
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    import io

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=45,
        leftMargin=45,
        topMargin=45,
        bottomMargin=45
    )

    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=18,
        leading=22,
        textColor=colors.HexColor('#102C57'),
        spaceAfter=3
    )
    subtitle_style = ParagraphStyle(
        'DocSub',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#0F766E'),
        spaceAfter=10
    )
    meta_style = ParagraphStyle(
        'MetaText',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=12,
        textColor=colors.HexColor('#334155')
    )
    h2_style = ParagraphStyle(
        'H2',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=11.5,
        leading=15,
        textColor=colors.HexColor('#102C57'),
        spaceBefore=10,
        spaceAfter=5
    )
    body_style = ParagraphStyle(
        'Body',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=12,
        textColor=colors.HexColor('#1E293B')
    )
    ncr_style = ParagraphStyle(
        'NCR',
        parent=styles['Code'],
        fontName='Courier',
        fontSize=7.5,
        leading=10,
        textColor=colors.HexColor('#991B1B')
    )

    story = []

    # Title & Subtitle
    story.append(Paragraph("SENTRY-MAS: SHARED CONSENSUS MULTI-AGENT ARBITRATION DOSSIER", title_style))
    story.append(Paragraph("Autonomous Operational Governance, Thermal Physics & Setpoint Consensus Audit", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#102C57'), spaceAfter=8))

    # Author Provenance Card
    author_text = (
        "<b>Lead Systems Architect:</b> Rohit Kumar, PMP, CEng, CEA, FSEr (TÜV)<br/>"
        "<b>Professional Domain:</b> Mission-Critical Infrastructure & Systems Engineering Specialist | Forensic Project Controls<br/>"
        "<b>Channels:</b> grohit41@gmail.com | LinkedIn: ROHITG41 (linkedin.com/in/rohitg41)<br/>"
        "<b>Central Repository:</b> https://github.com/ROHITG41/sentry-cxa-datacenter"
    )
    auth_table = Table([[Paragraph(author_text, meta_style)]], colWidths=[520])
    auth_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F8FAFC')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#CBD5E1')),
        ('PADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(auth_table)
    story.append(Spacer(1, 10))

    # Section 1: Telemetry & Deterministic Math Summary
    story.append(Paragraph("1. Deterministic Physical Telemetry & Consensus State", h2_style))
    status_color = "#16A34A" if metrics.status == "CONSENSUS_VALIDATED" else ("#D97706" if metrics.status == "CONDITIONAL_ACCORD_MONITORED" else "#DC2626")
    
    t_data = [
        ["Telemetry Parameter", "Recorded Metric", "Engineering Standard / Baseline", "Audit Status"],
        ["Audit Tracking ID", str(telemetry.test_id), "Asset Stage: " + str(telemetry.stage), "TRACKED"],
        ["Total IT Whitespace Load", f"{telemetry.total_it_load_kw:,.1f} kW", f"Peak Rack: {telemetry.peak_rack_density_kw:.1f} kW/rack", "MONITORED"],
        ["Chilled Water Supply Temp", f"{telemetry.chw_supply_c:.1f} deg C", "ASHRAE TC 9.9 (18.0 deg C Max)", "EVALUATED"],
        ["Hydronic Loop Differential Pressure", f"{telemetry.loop_delta_p_bar:.2f} bar", f"Baseline: 1.50 bar (+{metrics.pump_power_penalty_pct:.1f}% kW)", "VERIFIED"],
        ["Continuous Cooling Hold-Up", f"{metrics.t_buffer_hold_min:.2f} Minutes", f"Required Ride-Through: {metrics.t_required_min:.2f} Mins", f"{metrics.buffer_margin_min:+.2f} Mins"],
        ["Transient Rise Rate (dT/dt)", f"{metrics.dT_dt_transient_c_per_min:.3f} deg C/min", "Ceiling: 0.850 deg C/min", "VERIFIED"],
        ["Calculated Facility PUE", f"{metrics.estimated_pue:.3f}", "Target Baseline: < 1.250", "BENCHMARKED"],
        ["Operational Compromise Index (OCI)", f"{metrics.operational_compromise_index} / 100.0", f"Consensus Status: {metrics.status}", "FINAL"]
    ]
    t_table = Table(t_data, colWidths=[160, 110, 150, 100])
    t_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#102C57')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 8),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
        ('PADDING', (0,0), (-1,-1), 5),
        ('BACKGROUND', (3,8), (3,8), colors.HexColor(status_color)),
        ('TEXTCOLOR', (3,8), (3,8), colors.white),
        ('FONTNAME', (3,8), (3,8), 'Helvetica-Bold'),
    ]))
    story.append(t_table)
    story.append(Spacer(1, 10))

    # Section 2: Opposing Multi-Agent Propositions (Parsed through Multi-Stage Sanitizer)
    story.append(Paragraph("2. Shared Consensus Multi-Agent Propositions", h2_style))
    
    ops_paragraphs = clean_and_format_for_reportlab(ops_text)
    eco_paragraphs = clean_and_format_for_reportlab(eco_text)
    
    ops_flowables = [Paragraph("<b>Agent 1: Facilities Sentinel (Reliability & Continuous Cooling)</b>", body_style)]
    for p_line, is_h in ops_paragraphs[:6]:
        ops_flowables.append(Paragraph(f"<b>{p_line}</b>" if is_h else p_line, body_style))
        
    eco_flowables = [Paragraph("<b>Agent 2: Energy Auditor / PUE Optimizer (OpEx & Carbon Reduction)</b>", body_style)]
    for p_line, is_h in eco_paragraphs[:6]:
        eco_flowables.append(Paragraph(f"<b>{p_line}</b>" if is_h else p_line, body_style))

    agent_data = [
        [ops_flowables],
        [eco_flowables]
    ]
    agent_tbl = Table(agent_data, colWidths=[520])
    agent_tbl.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#FEF2F2')),
        ('BACKGROUND', (0,1), (-1,1), colors.HexColor('#F0FDF4')),
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
        ('PADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(agent_tbl)
    
    # HARD PAGE BREAK: Guarantees Section 3 starts cleanly at the top of Page 2 (No Orphan Header)
    story.append(PageBreak())

    # Section 3: Arbiter Determination Accord (Parsed through Multi-Stage Sanitizer)
    story.append(Paragraph("3. Deterministic Arbiter Determination Accord", h2_style))
    arbiter_paragraphs = clean_and_format_for_reportlab(arbiter_text)
    arbiter_flowables = []
    for p_line, is_h in arbiter_paragraphs:
        arbiter_flowables.append(Paragraph(f"<b>{p_line}</b>" if is_h else p_line, body_style))
        arbiter_flowables.append(Spacer(1, 1.5))
        
    arbiter_tbl = Table([[arbiter_flowables]], colWidths=[520])
    arbiter_tbl.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F0FDFA')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#14B8A6')),
        ('PADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(arbiter_tbl)

    # Section 4: Engineering Non-Conformance Protocol (If Triggered)
    if ncr_text:
        story.append(Spacer(1, 10))
        story.append(Paragraph("4. Engineering Non-Conformance & Operational Remediation Protocol", h2_style))
        ncr_paragraphs = clean_and_format_for_reportlab(ncr_text)
        ncr_flowables = []
        for p_line, is_h in ncr_paragraphs:
            ncr_flowables.append(Paragraph(f"<b>{p_line}</b>" if is_h else p_line, ncr_style))
        
        ncr_tbl = Table([[ncr_flowables]], colWidths=[520])
        ncr_tbl.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#FEF2F2')),
            ('BOX', (0,0), (-1,-1), 1.5, colors.HexColor('#DC2626')),
            ('PADDING', (0,0), (-1,-1), 8),
        ]))
        story.append(ncr_tbl)

    doc.build(story)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes

# ---------------------------------------------------------
# 8. STREAMLIT USER INTERFACE (SIDEBAR & CORE WORKFLOW)
# ---------------------------------------------------------
def main():
    st.markdown('<p class="main-header">⚡ SENTRY-MAS: DATA CENTER MULTI-AGENT ARBITER</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Hyperscale Infrastructure Engineering Suite | Autonomous Multi-Agent Consensus & Operational Governance</p>', unsafe_allow_html=True)
    
    st.markdown("""
    <div class="provenance-card">
        <b>Lead Systems Architect:</b> Rohit Kumar, PMP, CEng, CEA, FSEr (TÜV)<br/>
        <b>Professional Domain:</b> Mission-Critical Infrastructure & Systems Engineering Specialist | Forensic Project Controls & Contract Governance<br/>
        <b>Contact & Channels:</b> grohit41@gmail.com | LinkedIn: ROHITG41 (linkedin.com/in/rohitg41)<br/>
        <b>Central Repository:</b> <a href="https://github.com/ROHITG41/sentry-cxa-datacenter" target="_blank">github.com/ROHITG41/sentry-cxa-datacenter</a>
    </div>
    """, unsafe_allow_html=True)

    st.info(
        "**Operational Context & Quick Guide:** This engine eliminates manual control-loop deadlocks between competing "
        "**Facilities Operations** (Tier IV continuous cooling) and **Energy & Sustainability** (PUE compression) mandates. "
        "Select a **Lifecycle Stage Preset** in the left sidebar or adjust plant load, rack density, and loop differential pressure (DP) "
        "parameters below to observe how the Multi-Agent Arbiter and Deterministic CPU Interlock synthesize an auditable Consensus Accord "
        "or Engineering Non-Conformance Report (NCR)."
    )

    with st.sidebar:
        st.subheader("🔑 Engine Configuration")
        api_key = st.text_input("Gemini API Key (Optional)", type="password", help="Enter API key for live LLM reasoning; defaults to deterministic engine if blank.")
        
        st.markdown("---")
        st.subheader("📋 Lifecycle Stage Presets")
        stage_choice = st.selectbox(
            "Select Project Lifecycle Stage",
            ["Level 5 IST Grid Outage Simulation (Stage 2)", "Concept & Design Stage (Stage 1)", "Day-2 Live Operations (Stage 3)"],
            index=0
        )
        
        if "Level 5 IST" in stage_choice:
            default_stage = "LEVEL5_IST"
            preset_it_kw = 12000.0
            preset_density = 75.0
            preset_chw_sup = 10.5
            preset_chw_ret = 18.0
            preset_dp = 2.45
            preset_buf_liters = 95000.0
            preset_ats = 0.016
            preset_gen = 8.5
            preset_restart = 95.0
            preset_wse = 25.0
            preset_id = "IST-L5-OUTAGE-RIDE-042"
        elif "Concept & Design" in stage_choice:
            default_stage = "CONCEPT_DESIGN"
            preset_it_kw = 24000.0
            preset_density = 45.0
            preset_chw_sup = 14.0
            preset_chw_ret = 22.0
            preset_dp = 1.65
            preset_buf_liters = 120000.0
            preset_ats = 0.014
            preset_gen = 6.5
            preset_restart = 60.0
            preset_wse = 15.0
            preset_id = "DBR-REV-03-COOLING"
        else:
            default_stage = "DAY2_OPERATIONS"
            preset_it_kw = 18000.0
            preset_density = 105.0
            preset_chw_sup = 12.0
            preset_chw_ret = 20.0
            preset_dp = 2.15
            preset_buf_liters = 75000.0
            preset_ats = 0.015
            preset_gen = 7.0
            preset_restart = 75.0
            preset_wse = 65.0
            preset_id = "DAY2-AI-BURST-TRANS"

        st.markdown("---")
        st.subheader("⚙️ Real-Time Telemetry Calibration")
        it_load = st.number_input("IT Whitespace Load (kW)", 1000.0, 100000.0, preset_it_kw, 500.0)
        rack_density = st.slider("Peak Rack Density (kW/rack)", 10.0, 150.0, preset_density, 5.0)
        chw_sup = st.slider("CHW Supply Header Temp (deg C)", 6.0, 20.0, preset_chw_sup, 0.5)
        chw_ret = st.slider("CHW Return Header Temp (deg C)", 12.0, 28.0, preset_chw_ret, 0.5)
        loop_dp = st.slider("Hydronic Loop DP (bar)", 1.0, 3.5, preset_dp, 0.05)
        buffer_liters = st.number_input("Usable Thermal Buffer Storage (Liters)", 10000.0, 500000.0, preset_buf_liters, 5000.0)
        
        st.markdown("**Interruption & Transient Latency (sec):**")
        ats_sec = st.number_input("ATS / STS Transfer Time (s)", 0.005, 5.0, preset_ats, 0.005, format="%.3f")
        gen_sync = st.slider("Generator Synchronization Time (s)", 4.0, 25.0, preset_gen, 0.5)
        chiller_restart = st.slider("Chiller Fast-Restart Delay (s)", 30.0, 300.0, preset_restart, 5.0)
        wse_transient = st.slider("Economizer Switchover Transient (s)", 5.0, 120.0, preset_wse, 5.0)

    telemetry = TelemetryPayload(
        test_id=preset_id,
        stage=default_stage,
        total_it_load_kw=it_load,
        peak_rack_density_kw=rack_density,
        chw_supply_c=chw_sup,
        chw_return_c=chw_ret,
        loop_delta_p_bar=loop_dp,
        buffer_liters=buffer_liters,
        ats_transfer_sec=ats_sec,
        gen_sync_sec=gen_sync,
        chiller_restart_sec=chiller_restart,
        wse_transition_sec=wse_transient
    )

    metrics = calculate_deterministic_physics(telemetry)

    # Top KPI Dashboards
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Consensus State</div>
            <div class="metric-value" style="font-size:1.05rem; color:{'#16A34A' if metrics.status=='CONSENSUS_VALIDATED' else ('#D97706' if metrics.status=='CONDITIONAL_ACCORD_MONITORED' else '#DC2626')};">
                {metrics.status.replace('_', ' ')}
            </div>
        </div>
        """, unsafe_allow_html=True)
    with c2:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Compromise Index (OCI)</div>
            <div class="metric-value">{metrics.operational_compromise_index:.1f}<span style="font-size:0.95rem;">/100</span></div>
        </div>
        """, unsafe_allow_html=True)
    with c3:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Buffer Hold-Up Margin</div>
            <div class="metric-value" style="color:{'#16A34A' if metrics.buffer_margin_min>=0 else '#DC2626'};">
                {metrics.buffer_margin_min:+.2f} <span style="font-size:0.85rem;">min</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
    with c4:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Transient Rate (dT/dt)</div>
            <div class="metric-value">{metrics.dT_dt_transient_c_per_min:.3f} <span style="font-size:0.8rem;">°C/min</span></div>
        </div>
        """, unsafe_allow_html=True)
    with c5:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Estimated PUE</div>
            <div class="metric-value">{metrics.estimated_pue:.3f}</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br/>", unsafe_allow_html=True)

    col_btn, col_info = st.columns([1, 3])
    with col_btn:
        run_sim = st.button("🚀 Execute Shared Consensus Arbitration", type="primary", use_container_width=True)
    with col_info:
        st.caption(f"Testing Dossier: **{telemetry.test_id}** | Power Interruption Window: **{metrics.t_interruption_total_sec:.1f} s** | Buffer Hold: **{metrics.t_buffer_hold_min:.2f} min** vs Required: **{metrics.t_required_min:.2f} min**")

    if "agent_results" not in st.session_state or run_sim:
        with st.spinner("Executing Shared Consensus Multi-Agent Arbitration..."):
            ops_prop, eco_prop, arb_accord, ncr_doc = run_multi_agent_consensus(api_key, telemetry, metrics)
            st.session_state.agent_results = {
                "ops": ops_prop,
                "eco": eco_prop,
                "arb": arb_accord,
                "ncr": ncr_doc,
                "telemetry": telemetry,
                "metrics": metrics
            }

    res = st.session_state.agent_results

    st.subheader("🗣️ Inter-Agent Operational Debate: Competing Mandates")
    col_ops, col_eco = st.columns(2)
    with col_ops:
        st.markdown(f"""
        <div class="agent-box-ops">
            <h4 style="color:#DC2626; margin-top:0;">🛡️ Agent 1: Facilities Sentinel (Ops-Sentinel)</h4>
            <p style="font-size:0.83rem; color:#7F1D1D; margin-bottom:8px;"><b>Priority:</b> 100% Uptime | Tier IV Continuous Cooling | Hot-Spot Prevention</p>
            <div style="font-size:0.88rem; line-height:1.5;">{res['ops'].replace(chr(10), '<br/>')}</div>
        </div>
        """, unsafe_allow_html=True)

    with col_eco:
        st.markdown(f"""
        <div class="agent-box-eco">
            <h4 style="color:#16A34A; margin-top:0;">🌱 Agent 2: Energy Auditor (Eco-Optimizer)</h4>
            <p style="font-size:0.83rem; color:#14532D; margin-bottom:8px;"><b>Priority:</b> Minimize PUE | Free-Cooling Economization | Throttling Head Loss</p>
            <div style="font-size:0.88rem; line-height:1.5;">{res['eco'].replace(chr(10), '<br/>')}</div>
        </div>
        """, unsafe_allow_html=True)

    st.subheader("⚖️ Sentry-Arbiter: Deterministic Consensus Disposition")
    st.markdown(f"""
    <div class="arbiter-box">
        <h4 style="color:#0F766E; margin-top:0;">📜 Certified Operational Determination Accord (OCI: {res['metrics'].operational_compromise_index}/100)</h4>
        <div style="font-size:0.92rem; line-height:1.6; color:#134E4A;">{res['arb'].replace(chr(10), '<br/>')}</div>
    </div>
    """, unsafe_allow_html=True)

    if res['ncr']:
        st.markdown(f"""
        <div class="ncr-box">
            <h3 style="color:#BE123C; margin-top:0;">🚨 ENGINEERING NON-CONFORMANCE & REMEDIATION PROTOCOL</h3>
            <p style="font-size:0.88rem; color:#881337;"><b>Technical Notice:</b> Autonomous safety boundary breach detected. Physical continuous cooling criteria or hydraulic stability thresholds violated.</p>
            <pre style="background:#FFF; padding:12px; border-radius:4px; border:1px solid #FDA4AF; color:#9F1239; font-size:0.82rem; white-space:pre-wrap;">{res['ncr']}</pre>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")
    st.subheader("📄 Formal Executive Documentation")
    pdf_bytes = generate_sanitized_pdf(
        res['telemetry'], 
        res['metrics'], 
        res['ops'], 
        res['eco'], 
        res['arb'], 
        res['ncr']
    )
    
    col_dl, col_space = st.columns([1, 3])
    with col_dl:
        st.download_button(
            label="📥 Download Executive PDF Audit Dossier",
            data=pdf_bytes,
            file_name=f"Sentry_MAS_Consensus_{res['telemetry'].test_id}.pdf",
            mime="application/pdf",
            use_container_width=True
        )
    with col_space:
        st.caption("PDF generated with ReportLab engine strictly sanitized against raw LaTeX math syntax, unescaped markdown delimiters, and backticks.")

if __name__ == "__main__":
    main()

# --- EXECUTIVE PORTFOLIO FOOTER ---
st.divider()
st.markdown(
    """
    <div style="text-align: center; color: #475569; font-size: 0.85rem; padding: 10px 0;">
        <p style="margin-bottom: 4px;">
            <strong>Architect:</strong> Rohit Kumar, PMP, CEng, CEA, FSEr (TÜV) | 
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
