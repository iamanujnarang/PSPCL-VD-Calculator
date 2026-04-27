import streamlit as st
import pandas as pd
import numpy as np
import io
import graphviz
from fpdf import FPDF

# --- PAGE CONFIG ---
st.set_page_config(page_title="PSPCL VD Calculator Pro", page_icon="⚡", layout="wide")

# --- CONSTANTS & ASSETS ---
PSPCL_LOGO = "https://pspcl.in/assets/images/logo.png"
INSTA_ICON = "https://upload.wikimedia.org/wikipedia/commons/a/a5/Instagram_icon.png"
FB_ICON = "https://upload.wikimedia.org/wikipedia/commons/1/1b/Facebook_icon.svg"
X_ICON = "https://upload.wikimedia.org/wikipedia/commons/b/b7/X_logo.jpg"
LINKEDIN_ICON = "https://upload.wikimedia.org/wikipedia/commons/c/ca/LinkedIn_logo_initials.png"
BEECLUE_LOGO = "https://beeclue.com/wp-content/uploads/2023/04/Beeclue-Logo-New.png"

VD_FACTORS = {
    "ACSR 100 SQMM": 0.0415, "ACSR 80 SQMM": 0.0512, "ACSR 50 SQMM": 0.0910,
    "ACSR 30 SQMM": 0.1520, "ACSR 20 SQMM": 0.2250, "XLPE CABLE 300 SQMM": 0.0146,
    "XLPE CABLE 150 SQMM": 0.0285, "XLPE CABLE 35 SQMM": 0.1150
}

# --- STYLING (The Custom CSS) ---
st.markdown(f"""
<style>
    .header-box {{ text-align: center; padding: 35px; background: white; border-radius: 20px; box-shadow: 0 4px 20px rgba(0,0,0,0.1); margin-bottom: 30px; border-top: 10px solid #ffcc00; }}
    .pspcl-main-logo {{ width: 220px; margin-bottom: 20px; }}
    .formula-section {{ background: #ffffff; padding: 35px; border-radius: 15px; border: 1px solid #e0e0e0; margin-top: 35px; box-shadow: 0 10px 30px rgba(0,0,0,0.05); }}
    .footer-container {{ text-align: center; margin-top: 80px; padding: 60px; border-top: 2px solid #f0f0f0; background: #fafafa; }}
    .social-logo {{ width: 45px; margin: 0 18px; transition: transform 0.4s ease; cursor: pointer; }}
    .social-logo:hover {{ transform: scale(1.4) rotate(5deg); }}
    .beeclue-footer-logo {{ width: 140px; margin-top: 15px; filter: grayscale(20%); }}
    .calculation-step {{ font-family: 'Courier New', monospace; color: #2e7d32; font-weight: bold; font-size: 1.1em; }}
</style>
""", unsafe_allow_html=True)

# --- HEADER SECTION ---
st.markdown(f"""
<div class="header-box">
    <img src="{PSPCL_LOGO}" class="pspcl-main-logo">
    <h1 style="color: #1a237e; margin: 0;">PUNJAB STATE POWER CORPORATION LIMITED</h1>
    <h3 style="color: #555;">Advanced 11kV Voltage Drop Calculation Engine</h3>
</div>
""", unsafe_allow_html=True)

# --- INITIALIZE SESSION STATE ---
if 'calc_data' not in st.session_state: st.session_state.calc_data = None
if 'metrics' not in st.session_state: st.session_state.metrics = {}

# --- SIDEBAR (Clean & Empty Defaults) ---
with st.sidebar:
    st.header("📋 Technical Inputs")
    feeder_name = st.text_input("Feeder Name", placeholder="e.g. 11kV Cantt")
    substation_name = st.text_input("Feeding Substation", placeholder="e.g. 66kV Mall Mandi")
    sub_div = st.text_input("Sub-Division Name", placeholder="e.g. South Sub-Division")
    division = st.text_input("Division Name", placeholder="e.g. City Division")
    
    st.divider()
    mdi_amps = st.number_input("Max Demand (MDI in Amps)", min_value=0.0, step=0.1, value=0.0)
    num_sections = st.number_input("Number of Sections", min_value=1, max_value=50, value=1)
    
    # Fundamental Calc
    mdi_kva = round(np.sqrt(3) * 11 * mdi_amps, 4)
    st.info(f"**Calculated MDI:** {mdi_kva} kVA")

# --- STEP 1: DATA GRID ---
st.subheader("📍 Step 1: Define Network Topology")
section_points = [f"{chr(65+i)}-{chr(66+i)}" for i in range(num_sections)]
df_template = pd.DataFrame({
    "SECTION": section_points,
    "CONDUCTOR": [None] * num_sections,
    "LENGTH (KM)": [0.0] * num_sections,
    "TAPPING LOAD (kVA)": [0.0] * num_sections
})

edited_df = st.data_editor(
    df_template,
    column_config={
        "SECTION": st.column_config.TextColumn("Point-to-Point", disabled=True),
        "CONDUCTOR": st.column_config.SelectboxColumn("Conductor Type", options=list(VD_FACTORS.keys()), required=True),
        "LENGTH (KM)": st.column_config.NumberColumn("Length (km)", min_value=0.0, format="%.3f"),
        "TAPPING LOAD (kVA)": st.column_config.NumberColumn("Load at Node (kVA)", min_value=0.0, format="%.1f")
    },
    use_container_width=True, num_rows="fixed"
)

# --- ACTION BUTTONS ---
btn_col1, btn_col2, btn_col3 = st.columns(3)

# --- CALCULATION ENGINE ---
if btn_col1.button("🚀 Run Full Calculation", type="primary", use_container_width=True):
    if edited_df["CONDUCTOR"].isnull().any():
        st.error("⚠️ Error: Sabhi sections ke liye Conductor select karna lazmi hai!")
    else:
        calc_df = edited_df.copy()
        loads = calc_df["TAPPING LOAD (kVA)"].tolist()
        upto_loads = [0] * len(loads)
        running_sum = 0
        
        # Backward Summation (Tail to Source)
        for i in range(len(loads)-1, -1, -1):
            running_sum += loads[i]
            upto_loads[i] = running_sum
            
        calc_df["UPTO LOAD (kVA)"] = upto_loads
        calc_df["FACTOR"] = calc_df["CONDUCTOR"].map(VD_FACTORS)
        calc_df["SECTION VD (V)"] = calc_df["LENGTH (KM)"] * calc_df["UPTO LOAD (kVA)"] * calc_df["FACTOR"]
        
        total_vd_sum = calc_df["SECTION VD (V)"].sum()
        max_load = upto_loads[0] if upto_loads else 0
        df_factor = mdi_kva / max_load if max_load > 0 else 0
        actual_vd_volts = total_vd_sum * df_factor
        final_vd_percent = (actual_vd_volts / (11000 - actual_vd_volts) * 100) if (11000 - actual_vd_volts) > 0 else 0
        
        st.session_state.calc_data = calc_df
        st.session_state.metrics = {
            "total_vd_sum": total_vd_sum, "max_load": max_load,
            "df_factor": df_factor, "actual_vd_volts": actual_vd_volts,
            "final_vd_percent": final_vd_percent, "mdi_kva": mdi_kva
        }

# --- RESULTS DISPLAY ---
if st.session_state.calc_data is not None:
    data = st.session_state.calc_data
    m = st.session_state.metrics
    
    st.subheader("📊 Step 2: Sectional Analysis")
    st.dataframe(data.style.format({"SECTION VD (V)": "{:.4f}", "UPTO LOAD (kVA)": "{:.1f}"}), use_container_width=True)
    
    # FORMULAS WITH LIVE CALC STEPS
    st.markdown('<div class="formula-section">', unsafe_allow_html=True)
    st.subheader("🧮 Mathematical Verification")
    
    mc1, mc2, mc3 = st.columns(3)
    with mc1:
        st.latex(r"D.F. = \frac{\sqrt{3} \times 11 \times MDI(A)}{Total\ kVA}")
        st.markdown(f'<p class="calculation-step">Step: {m["mdi_kva"]:.2f} / {m["max_load"]:.2f}</p>', unsafe_allow_html=True)
        st.metric("Demand Factor", f"{m['df_factor']:.4f}")
        
    with mc2:
        st.latex(r"Actual\ V.D. = \sum V.D. \times D.F.")
        st.markdown(f'<p class="calculation-step">Step: {m["total_vd_sum"]:.2f} × {m["df_factor"]:.4f}</p>', unsafe_allow_html=True)
        st.metric("Actual VD", f"{m['actual_vd_volts']:.2f} Volts")
        
    with mc3:
        st.latex(r"\% V.D. = \frac{Act.\ V.D.}{11000 - Act.\ V.D.} \times 100")
        st.markdown(f'<p class="calculation-step">Step: ({m["actual_vd_volts"]:.2f} / {11000 - m["actual_vd_volts"]:.2f}) × 100</p>', unsafe_allow_html=True)
        st.metric("Final % Drop", f"{m['final_vd_percent']:.3f}%")
    st.markdown('</div>', unsafe_allow_html=True)

    # EXCEL DOWNLOAD
    csv_buffer = io.StringIO()
    data.to_csv(csv_buffer, index=False)
    btn_col3.download_button("📥 Download Excel Report", csv_buffer.getvalue(), f"{feeder_name}_Calc.csv", "text/csv", use_container_width=True)

# --- SKETCH & PDF GENERATION ---
if btn_col2.button("🎨 Generate Diagram & PDF", use_container_width=True):
    if st.session_state.calc_data is None:
        st.warning("Pehle calculation perform karein!")
    else:
        res_df = st.session_state.calc_data
        m = st.session_state.metrics
        
        # Graphviz Sketch
        st.subheader("🎨 Network Single Line Diagram")
        sld = graphviz.Digraph()
        sld.attr(rankdir='BT', bgcolor='#ffffff')
        sld.node('SOURCE', f'SOURCE\n{substation_name}\n({m["max_load"]} kVA)', shape='house', color='blue', style='filled', fillcolor='#fff9c4')
        
        last_node = 'SOURCE'
        for idx, row in res_df.iterrows():
            curr_node = f"N{idx}"
            label = f"{row['SECTION'].split('-')[-1]}"
            is_cable = "CABLE" in row['CONDUCTOR'].upper()
            
            sld.node(curr_node, label, shape='doublecircle' if is_cable else 'circle', color='red')
            edge_lbl = f"{row['CONDUCTOR']}\n{row['LENGTH (KM)']}km\nVD: {row['SECTION VD (V)']:.2f}V"
            sld.edge(curr_node, last_node, label=edge_lbl, color='darkgreen', fontcolor='blue', penwidth='2')
            last_node = curr_node
        
        st.graphviz_chart(sld)
        
        # PDF EXPORT (Using fpdf2 style)
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("helvetica", "B", 18)
        pdf.cell(0, 15, "PSPCL VOLTAGE DROP ANALYSIS REPORT", align='C', ln=True)
        pdf.ln(5)
        
        pdf.set_font("helvetica", "B", 11)
        pdf.cell(50, 10, f"Feeder: {feeder_name}", ln=False)
        pdf.cell(50, 10, f"Sub-Div: {sub_div}", ln=True)
        pdf.cell(50, 10, f"Division: {division}", ln=False)
        pdf.cell(50, 10, f"MDI: {m['mdi_kva']} kVA", ln=True)
        pdf.ln(10)
        
        # Table Header
        pdf.set_fill_color(240, 240, 240)
        cols = [("Section", 30), ("Conductor", 55), ("Len", 25), ("Load", 35), ("VD(V)", 35)]
        for h, w in cols: pdf.cell(w, 10, h, 1, 0, 'C', fill=True)
        pdf.ln()
        
        # Table Body
        pdf.set_font("helvetica", "", 10)
        for _, r in res_df.iterrows():
            pdf.cell(30, 9, str(r['SECTION']), 1)
            pdf.cell(55, 9, str(r['CONDUCTOR'])[:25], 1)
            pdf.cell(25, 9, str(r['LENGTH (KM)']), 1)
            pdf.cell(35, 9, str(r['UPTO LOAD (kVA)']), 1)
            pdf.cell(35, 9, f"{r['SECTION VD (V)']:.3f}", 1)
            pdf.ln()
            
        pdf.ln(15)
        pdf.set_font("helvetica", "B", 13)
        pdf.set_text_color(200, 0, 0)
        pdf.cell(0, 10, f"FINAL VOLTAGE DROP: {m['final_vd_percent']:.3f} %", ln=True)
        
        # SDO STAMP
        pdf.ln(30)
        pdf.set_text_color(0, 0, 0)
        pdf.cell(125)
        pdf.multi_cell(60, 8, f"__________________\nSDO OP SUB-DIVISION\nPSPCL {sub_div.upper()}", align='C')
        
        pdf_bytes = pdf.output()
        st.download_button("📥 Download Official Signed PDF", bytes(pdf_bytes), f"{feeder_name}_Official.pdf", "application/pdf", use_container_width=True)

# --- FOOTER SECTION ---
st.markdown(f"""
<div class="footer-container">
    <p style="font-size: 1.4em; font-weight: bold; color: #333;">Developed for PSPCL Engineers by Anuj Narang</p>
    <div style="margin: 25px 0;">
        <a href="https://instagram.com/iamanujnarang" target="_blank"><img src="{INSTA_ICON}" class="social-logo"></a>
        <a href="https://facebook.com/iamanujnarang" target="_blank"><img src="{FB_ICON}" class="social-logo"></a>
        <a href="https://linkedin.com/in/iamanujnarang" target="_blank"><img src="{LINKEDIN_ICON}" class="social-logo"></a>
    </div>
    <p style="color: #888;">Strategic Partner</p>
    <a href="https://beeclue.com" target="_blank">
        <img src="{BEECLUE_LOGO}" class="beeclue-footer-logo">
    </a>
</div>
""", unsafe_allow_html=True)
