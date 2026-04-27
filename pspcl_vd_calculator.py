import streamlit as st
import pandas as pd
import numpy as np
import io
import graphviz
from fpdf import FPDF

# --- PAGE CONFIG ---
st.set_page_config(page_title="PSPCL VD Calculator Pro", page_icon="⚡", layout="wide")

# --- ASSETS ---
PSPCL_LOGO = "https://pspcl.in/assets/images/logo.png"
INSTA_ICON = "https://upload.wikimedia.org/wikipedia/commons/a/a5/Instagram_icon.png"
FB_ICON = "https://upload.wikimedia.org/wikipedia/commons/1/1b/Facebook_icon.svg"
X_ICON = "https://upload.wikimedia.org/wikipedia/commons/b/b7/X_logo.jpg"
LINKEDIN_ICON = "https://upload.wikimedia.org/wikipedia/commons/c/ca/LinkedIn_logo_initials.png"

VD_FACTORS = {
    "ACSR 100 SQMM": 0.0415, "ACSR 80 SQMM": 0.0512, "ACSR 50 SQMM": 0.0910,
    "ACSR 30 SQMM": 0.1520, "ACSR 20 SQMM": 0.2250, "XLPE CABLE 300 SQMM": 0.0146,
    "XLPE CABLE 150 SQMM": 0.0285, "XLPE CABLE 35 SQMM": 0.1150
}

# --- STYLING ---
st.markdown(f"""
<style>
    .header-box {{ text-align: center; padding: 25px; background: white; border-radius: 15px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); margin-bottom: 25px; border-top: 6px solid #ffcc00; }}
    .formula-section {{ background: #ffffff; padding: 30px; border-radius: 15px; border: 1px solid #dee2e6; margin-top: 30px; box-shadow: 0 10px 25px rgba(0,0,0,0.05); }}
    .footer-container {{ text-align: center; margin-top: 60px; padding: 40px; border-top: 1px solid #eee; }}
    .social-logo {{ width: 35px; margin: 0 15px; transition: 0.3s; }}
    .social-logo:hover {{ transform: scale(1.3); }}
</style>
""", unsafe_allow_html=True)

# --- HEADER ---
st.markdown(f'<div class="header-box"><img src="{PSPCL_LOGO}" width="100"><h1>PUNJAB STATE POWER CORPORATION LIMITED</h1><h3>11kV Voltage Drop Calculation Tool</h3></div>', unsafe_allow_html=True)

# --- SIDEBAR ---
with st.sidebar:
    st.header("📝 Feeder Details")
    feeder_name = st.text_input("Feeder Name", value="11kV Mall Mandi")
    substation_name = st.text_input("Feeding Substation", value="66kV Mall Mandi")
    sub_div = st.text_input("Sub-Division", value="Mall Mandi")
    div = st.text_input("Division", value="City Center")
    
    st.divider()
    st.header("⚡ Load & Sections")
    mdi_amps = st.number_input("Max Demand (MDI Amps)", min_value=0.0, value=100.0, step=0.1)
    num_sections = st.number_input("Number of Sections", min_value=1, max_value=100, value=5)
    
    mdi_kva = round(np.sqrt(3) * 11 * mdi_amps, 4)
    st.success(f"MDI in kVA: {mdi_kva}")

# --- DATA ENTRY ---
st.subheader("📍 Step 1: Sectional Data Entry")
points = [f"{chr(65+i)}-{chr(66+i)}" for i in range(num_sections)]
df_input = pd.DataFrame({
    "POINT": points,
    "CONDUCTOR SIZE": ["ACSR 100 SQMM"] * num_sections,
    "DISTANCE (KM)": [1.0] * num_sections,
    "SECTION LOAD (kVA)": [100.0] * num_sections
})

edited_df = st.data_editor(df_input, use_container_width=True, num_rows="fixed")

# --- CALCULATION LOGIC ---
df = edited_df.copy()
loads = df["SECTION LOAD (kVA)"].fillna(0).tolist()
upto_loads = [0] * len(loads)
temp_sum = 0
for i in range(len(loads)-1, -1, -1):
    temp_sum += loads[i]
    upto_loads[i] = temp_sum

df["UPTO LOAD (kVA)"] = upto_loads
df["VD FACTOR"] = df["CONDUCTOR SIZE"].map(VD_FACTORS).fillna(0)
df["VD (VOLTS)"] = df["DISTANCE (KM)"] * df["UPTO LOAD (kVA)"] * df["VD FACTOR"]

total_vd_volts = df["VD (VOLTS)"].sum()
total_load_at_source = upto_loads[0] if upto_loads else 0
df_val = mdi_kva / total_load_at_source if total_load_at_source > 0 else 0
actual_vd_v = total_vd_volts * df_val
vd_percent = (actual_vd_v / (11000 - actual_vd_v) * 100) if (11000 - actual_vd_v) > 0 else 0

# --- SEPARATE BUTTONS ---
c1, c2 = st.columns(2)
with c1:
    calc_btn = st.button("🚀 Calculate & Show Formulas", type="primary", use_container_width=True)
with c2:
    sketch_btn = st.button("🎨 Generate Sketch & PDF", use_container_width=True)

# --- DISPLAY CALCULATIONS ---
if calc_btn or 'calc_done' in st.session_state:
    st.session_state.calc_done = True
    st.subheader("📊 Calculation Results")
    
    # Grand Total Row
    summary_row = pd.DataFrame({
        "POINT": ["**GRAND TOTAL**"], "CONDUCTOR SIZE": ["-"], 
        "DISTANCE (KM)": [df["DISTANCE (KM)"].sum()],
        "SECTION LOAD (kVA)": [df["SECTION LOAD (kVA)"].sum()], 
        "UPTO LOAD (kVA)": [0.0], "VD (VOLTS)": [total_vd_volts]
    })
    st.dataframe(pd.concat([df, summary_row], ignore_index=True), use_container_width=True)

    # Formulas Section
    st.markdown('<div class="formula-section">', unsafe_allow_html=True)
    f_col1, f_col2, f_col3 = st.columns(3)
    with f_col1:
        st.latex(r"D.F. = \frac{\sqrt{3} \times 11 \times MDI(A)}{Total\ kVA}")
        st.metric("Demand Factor", f"{df_val:.4f}")
    with f_col2:
        st.latex(r"Actual\ V.D. = \sum V.D. \times D.F.")
        st.metric("Actual VD", f"{actual_vd_v:.2f} Volts")
    with f_col3:
        st.latex(r"\% V.D. = \frac{Act.\ V.D.}{11000 - Act.\ V.D.} \times 100")
        st.metric("% Voltage Drop", f"{vd_percent:.3f}%")
    st.markdown('</div>', unsafe_allow_html=True)

# --- SKETCH & PDF OPTION ---
if sketch_btn:
    st.subheader("🎨 Feeder Sketch")
    dot = graphviz.Digraph()
    dot.attr(rankdir='BT')
    dot.node('SS', f'{substation_name}\n(Source)', shape='house', style='filled', fillcolor='gold')
    
    prev = 'SS'
    for i, row in df.iterrows():
        node_id = f"P{i}"
        point = row['POINT'].split('-')[-1]
        is_cable = "CABLE" in row['CONDUCTOR SIZE'].upper()
        
        label = f"{row['CONDUCTOR SIZE']}\n{row['DISTANCE (KM)']}km | VD: {row['VD (VOLTS)']:.2f}V\nCum: {row['UPTO LOAD (kVA)']}kVA"
        
        dot.node(node_id, point, shape='doublecircle' if is_cable else 'circle', style='filled', fillcolor='aliceblue')
        dot.edge(node_id, prev, label=label, color='red', style='dashed' if is_cable else 'solid', penwidth='2')
        prev = node_id
    
    st.graphviz_chart(dot)

    # PDF Export with SDO Stamp
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 10, "PSPCL VOLTAGE DROP REPORT", ln=True, align='C')
    pdf.set_font("Arial", '', 12)
    pdf.ln(5)
    pdf.cell(200, 10, f"Feeder: {feeder_name} | Sub-Division: {sub_div}", ln=True, align='C')
    pdf.ln(10)
    
    # Simple Table in PDF
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(30, 10, "Section", 1)
    pdf.cell(60, 10, "Conductor", 1)
    pdf.cell(30, 10, "Dist(km)", 1)
    pdf.cell(30, 10, "Load(kVA)", 1)
    pdf.cell(30, 10, "VD(Volts)", 1)
    pdf.ln()
    
    pdf.set_font("Arial", '', 10)
    for i, row in df.iterrows():
        pdf.cell(30, 10, str(row['POINT']), 1)
        pdf.cell(60, 10, str(row['CONDUCTOR SIZE']), 1)
        pdf.cell(30, 10, str(row['DISTANCE (KM)']), 1)
        pdf.cell(30, 10, str(row['SECTION LOAD (kVA)']), 1)
        pdf.cell(30, 10, f"{row['VD (VOLTS)']:.2f}", 1)
        pdf.ln()

    pdf.ln(20)
    pdf.set_font("Arial", 'B', 11)
    pdf.cell(0, 10, f"Actual % Voltage Drop: {vd_percent:.3f}%", ln=True)
    
    # SDO STAMP SECTION
    pdf.ln(30)
    pdf.cell(120) # Move to right
    pdf.multi_cell(60, 10, f"__________________\nSDO OP SUB-DIV\nPSPCL {sub_div.upper()}", align='C')
    
    pdf_output = pdf.output(dest="S").encode("latin-1")
    st.download_button("📥 Download PDF Report with SDO Stamp", pdf_output, f"{feeder_name}_Report.pdf", "application/pdf")

# --- FOOTER ---
st.markdown(f'<div class="footer-container"><b>Made with ❤️ by Anuj Narang</b><br>Powered by Beeclue Tech</div>', unsafe_allow_html=True)
