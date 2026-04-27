import streamlit as st
import pandas as pd
import numpy as np
import io
import graphviz
from fpdf import FPDF

# --- PAGE CONFIG ---
st.set_page_config(page_title="PSPCL VD Calculator Pro", page_icon="⚡", layout="wide")

# --- CONSTANTS & LOGOS ---
PSPCL_LOGO = "https://pspcl.in/assets/images/logo.png"
INSTA_ICON = "https://upload.wikimedia.org/wikipedia/commons/a/a5/Instagram_icon.png"
FB_ICON = "https://upload.wikimedia.org/wikipedia/commons/1/1b/Facebook_icon.svg"
X_ICON = "https://upload.wikimedia.org/wikipedia/commons/b/b7/X_logo.jpg"
LINKEDIN_ICON = "https://upload.wikimedia.org/wikipedia/commons/c/ca/LinkedIn_logo_initials.png"
BEECLUE_LOGO = "https://beeclue.com/wp-content/uploads/2023/04/Beeclue-Logo-New.png" # Example URL

VD_FACTORS = {
    "ACSR 100 SQMM": 0.0415, "ACSR 80 SQMM": 0.0512, "ACSR 50 SQMM": 0.0910,
    "ACSR 30 SQMM": 0.1520, "ACSR 20 SQMM": 0.2250, "XLPE CABLE 300 SQMM": 0.0146,
    "XLPE CABLE 150 SQMM": 0.0285, "XLPE CABLE 35 SQMM": 0.1150
}

# --- CUSTOM CSS (Enlarged Logo & Hover Effects) ---
st.markdown(f"""
<style>
    .header-box {{ text-align: center; padding: 30px; background: white; border-radius: 15px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); margin-bottom: 25px; border-top: 8px solid #ffcc00; }}
    .pspcl-main-logo {{ width: 180px; margin-bottom: 15px; }}
    .formula-section {{ background: #ffffff; padding: 30px; border-radius: 15px; border: 1px solid #dee2e6; margin-top: 30px; box-shadow: 0 10px 25px rgba(0,0,0,0.05); }}
    .footer-container {{ text-align: center; margin-top: 60px; padding: 50px; border-top: 1px solid #eee; background: #fdfdfd; }}
    .social-logo {{ width: 40px; margin: 0 15px; transition: transform 0.3s ease; cursor: pointer; }}
    .social-logo:hover {{ transform: scale(1.4); }}
    .beeclue-footer-logo {{ width: 120px; margin-top: 10px; transition: 0.3s; }}
    .beeclue-footer-logo:hover {{ opacity: 0.8; }}
</style>
""", unsafe_allow_html=True)

# --- HEADER (Bigger Logo) ---
st.markdown(f"""
<div class="header-box">
    <img src="{PSPCL_LOGO}" class="pspcl-main-logo">
    <h1>PUNJAB STATE POWER CORPORATION LIMITED</h1>
    <h3>11kV Voltage Drop Calculation Tool (Professional Version)</h3>
</div>
""", unsafe_allow_html=True)

# --- SESSION STATE ---
if 'df_result' not in st.session_state:
    st.session_state.df_result = None
if 'summary_metrics' not in st.session_state:
    st.session_state.summary_metrics = {}

# --- SIDEBAR (Blank Defaults) ---
with st.sidebar:
    st.header("📝 Feeder Details")
    feeder_name = st.text_input("Feeder Name", placeholder="e.g. 11kV Mall Mandi")
    substation_name = st.text_input("Feeding Substation", placeholder="e.g. 66kV Substation")
    sub_div = st.text_input("Sub-Division", placeholder="e.g. Mall Mandi")
    div = st.text_input("Division", placeholder="e.g. City Center Amritsar")
    
    st.divider()
    st.header("⚡ Load & Sections")
    mdi_amps = st.number_input("Max Demand (MDI Amps)", min_value=0.0, value=0.0, step=0.1)
    num_sections = st.number_input("Number of Sections", min_value=1, max_value=100, value=1)
    
    mdi_kva = round(np.sqrt(3) * 11 * mdi_amps, 4)
    st.success(f"MDI in kVA: {mdi_kva}")

# --- DATA ENTRY ---
st.subheader("📍 Step 1: Sectional Data Entry")
points = [f"{chr(65+i)}-{chr(66+i)}" for i in range(num_sections)]
df_init = pd.DataFrame({
    "POINT": points,
    "CONDUCTOR SIZE": [None] * num_sections,
    "DISTANCE (KM)": [0.0] * num_sections,
    "SECTION LOAD (kVA)": [0.0] * num_sections
})

edited_df = st.data_editor(
    df_init,
    column_config={
        "POINT": st.column_config.TextColumn("Section", disabled=True),
        "CONDUCTOR SIZE": st.column_config.SelectboxColumn("Conductor Type", options=list(VD_FACTORS.keys()), required=True),
        "DISTANCE (KM)": st.column_config.NumberColumn("Length (km)", format="%.3f"),
        "SECTION LOAD (kVA)": st.column_config.NumberColumn("Tapping Load (kVA)", format="%.1f")
    },
    use_container_width=True, num_rows="fixed"
)

# --- ACTIONS ---
col1, col2, col3 = st.columns(3)

if col1.button("🚀 Calculate Voltage Drop", type="primary", use_container_width=True):
    df = edited_df.copy()
    if df["CONDUCTOR SIZE"].isnull().any():
        st.error("Error: Saare sections ke liye Conductor Size choose karein!")
    else:
        # Cumulative Load Logic
        loads = df["SECTION LOAD (kVA)"].fillna(0).tolist()
        upto_loads = [0] * len(loads)
        temp_sum = 0
        for i in range(len(loads)-1, -1, -1):
            temp_sum += loads[i]
            upto_loads[i] = temp_sum
        
        df["UPTO LOAD (kVA)"] = upto_loads
        df["VD FACTOR"] = df["CONDUCTOR SIZE"].map(VD_FACTORS).fillna(0)
        df["VD (VOLTS)"] = df["DISTANCE (KM)"] * df["UPTO LOAD (kVA)"] * df["VD FACTOR"]
        
        total_vd = df["VD (VOLTS)"].sum()
        total_load_kva = upto_loads[0] if upto_loads else 0
        df_val = mdi_kva / total_load_kva if total_load_kva > 0 else 0
        actual_vd = total_vd * df_val
        vd_per = (actual_vd / (11000 - actual_vd) * 100) if (11000 - actual_vd) > 0 else 0
        
        st.session_state.df_result = df
        st.session_state.summary_metrics = {
            "total_vd": total_vd, "total_load": total_load_kva,
            "df_val": df_val, "actual_vd": actual_vd, "vd_per": vd_per
        }

if st.session_state.df_result is not None:
    res = st.session_state.df_result
    met = st.session_state.summary_metrics
    
    st.subheader("📊 Step 2: Calculation Analysis Table")
    st.dataframe(res, use_container_width=True)
    
    # Formulas with Live Calculations
    st.markdown('<div class="formula-section">', unsafe_allow_html=True)
    st.subheader("🧮 Detailed Mathematical Steps")
    f1, f2, f3 = st.columns(3)
    with f1:
        st.latex(r"D.F. = \frac{\sqrt{3} \times 11 \times MDI(A)}{Total\ kVA}")
        st.write(f"**Step:** {mdi_kva} / {met['total_load']:.2f}")
        st.metric("Demand Factor", f"{met['df_val']:.4f}")
    with f2:
        st.latex(r"Actual\ V.D. = \sum V.D. \times D.F.")
        st.write(f"**Step:** {met['total_vd']:.2f} × {met['df_val']:.4f}")
        st.metric("Actual VD", f"{met['actual_vd']:.2f} Volts")
    with f3:
        st.latex(r"\% V.D. = \frac{Actual\ V.D.}{11000 - Actual\ V.D.} \times 100")
        st.write(f"**Step:** ({met['actual_vd']:.2f} / {11000 - met['actual_vd']:.2f}) × 100")
        st.metric("Final % VD", f"{met['vd_per']:.3f}%")
    st.markdown('</div>', unsafe_allow_html=True)

    csv = res.to_csv(index=False).encode('utf-8')
    col3.download_button("📊 Download Excel (CSV)", csv, f"{feeder_name}_Report.csv", "text/csv", use_container_width=True)

# --- SKETCH & PDF ---
if col2.button("🎨 Generate Sketch & PDF", use_container_width=True):
    if st.session_state.df_result is None:
        st.warning("Pehle calculation complete karein!")
    else:
        df = st.session_state.df_result
        met = st.session_state.summary_metrics
        
        st.subheader("🎨 Feeder Sketch (SLD)")
        dot = graphviz.Digraph()
        dot.attr(rankdir='BT')
        dot.node('SS', f'{substation_name}\n(Source)\n{met["total_load"]} kVA', shape='house', style='filled', fillcolor='gold')
        
        prev = 'SS'
        for i, row in df.iterrows():
            nid = f"P{i}"
            is_cable = "CABLE" in row['CONDUCTOR SIZE'].upper()
            label = f"{row['CONDUCTOR SIZE']}\n{row['DISTANCE (KM)']}km | {row['VD (VOLTS)']:.2f}V"
            dot.node(nid, row['POINT'].split('-')[-1], shape='doublecircle' if is_cable else 'circle', style='filled', fillcolor='aliceblue')
            dot.edge(nid, prev, label=label, color='red', style='dashed' if is_cable else 'solid', penwidth='2')
            prev = nid
        st.graphviz_chart(dot)
        
        # Official PDF
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", 'B', 16)
        pdf.cell(200, 10, "PSPCL VOLTAGE DROP OFFICIAL REPORT", ln=True, align='C')
        pdf.ln(10)
        pdf.set_font("Arial", '', 12)
        pdf.cell(100, 10, f"Feeder: {feeder_name}")
        pdf.cell(100, 10, f"Sub-Division: {sub_div}", ln=True)
        pdf.ln(5)
        
        pdf.set_font("Arial", 'B', 10)
        for c in ["Section", "Conductor", "Dist", "Load", "VD"]: pdf.cell(38, 10, c, 1, 0, 'C')
        pdf.ln()
        pdf.set_font("Arial", '', 9)
        for _, r in df.iterrows():
            pdf.cell(38, 8, str(r['POINT']), 1)
            pdf.cell(38, 8, str(r['CONDUCTOR SIZE'])[:15], 1)
            pdf.cell(38, 8, str(r['DISTANCE (KM)']), 1)
            pdf.cell(38, 8, str(r['SECTION LOAD (kVA)']), 1)
            pdf.cell(38, 8, f"{r['VD (VOLTS)']:.2f}", 1)
            pdf.ln()
        
        pdf.ln(15)
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(0, 10, f"Calculated Voltage Drop: {met['vd_per']:.3f}%", ln=True)
        
        # SDO Stamp
        pdf.ln(25)
        pdf.cell(120)
        pdf.multi_cell(60, 7, f"__________________\nSDO OP SUB-DIV\nPSPCL {sub_div.upper()}", align='C')
        
        pdf_bytes = pdf.output(dest='S').encode('latin-1')
        st.download_button("📥 Download PDF Report", pdf_bytes, f"{feeder_name}_Official_Report.pdf", "application/pdf", use_container_width=True)

# --- FOOTER (All Links Fixed) ---
st.markdown(f"""
<div class="footer-container">
    <p style="font-size:1.2em; font-weight:bold;">Made with ❤️ by Anuj Narang</p>
    <div style="margin: 20px 0;">
        <a href="https://instagram.com/iamanujnarang" target="_blank"><img src="{INSTA_ICON}" class="social-logo"></a>
        <a href="https://facebook.com/iamanujnarang" target="_blank"><img src="{FB_ICON}" class="social-logo"></a>
        <a href="https://x.com/iamanujnarang" target="_blank"><img src="{X_ICON}" class="social-logo"></a>
        <a href="https://linkedin.com/in/iamanujnarang" target="_blank"><img src="{LINKEDIN_ICON}" class="social-logo"></a>
    </div>
    <p style="color:#666; margin-bottom:5px;">In Association with</p>
    <a href="https://beeclue.com" target="_blank">
        <img src="https://beeclue.com/wp-content/uploads/2023/04/Beeclue-Logo-New.png" class="beeclue-footer-logo">
    </a>
</div>
""", unsafe_allow_html=True)
