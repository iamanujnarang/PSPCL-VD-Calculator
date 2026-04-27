import streamlit as st
import pandas as pd
import numpy as np
import io
import graphviz
from fpdf import FPDF
import base64

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

# --- SIDEBAR (Empty Defaults) ---
with st.sidebar:
    st.header("📝 Feeder Details")
    feeder_name = st.text_input("Feeder Name", placeholder="Enter Feeder Name")
    substation_name = st.text_input("Feeding Substation", placeholder="Enter Substation Name")
    sub_div = st.text_input("Sub-Division", placeholder="Enter Sub-Division")
    div = st.text_input("Division", placeholder="Enter Division")
    
    st.divider()
    st.header("⚡ Load & Sections")
    mdi_amps = st.number_input("Max Demand (MDI Amps)", min_value=0.0, value=0.0, step=0.1)
    num_sections = st.number_input("Number of Sections", min_value=1, max_value=100, value=1)
    
    mdi_kva = round(np.sqrt(3) * 11 * mdi_amps, 4)
    st.success(f"MDI in kVA: {mdi_kva}")

# --- DATA ENTRY ---
st.subheader("📍 Step 1: Sectional Data Entry")
points = [f"{chr(65+i)}-{chr(66+i)}" for i in range(num_sections)]
df_input = pd.DataFrame({
    "POINT": points,
    "CONDUCTOR SIZE": [None] * num_sections,
    "DISTANCE (KM)": [0.0] * num_sections,
    "SECTION LOAD (kVA)": [0.0] * num_sections
})

edited_df = st.data_editor(df_input, use_container_width=True, num_rows="fixed")

# --- CALCULATION LOGIC ---
df = edited_df.dropna(subset=["CONDUCTOR SIZE"]).copy()

if not df.empty:
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

    # --- BUTTONS ---
    c1, c2, c3 = st.columns(3)
    with c1:
        calc_btn = st.button("🚀 Calculate & Show Formulas", type="primary", use_container_width=True)
    with c2:
        sketch_btn = st.button("🎨 Generate Sketch & PDF", use_container_width=True)
    with c3:
        # Excel (CSV) Download Option
        csv_data = io.StringIO()
        df.to_csv(csv_data, index=False)
        st.download_button("📊 Download Excel (CSV)", csv_data.getvalue(), f"{feeder_name}_Calc.csv", "text/csv", use_container_width=True)

    if calc_btn:
        st.subheader("📊 Calculation Results")
        st.dataframe(df, use_container_width=True)

        st.markdown('<div class="formula-section">', unsafe_allow_html=True)
        f_col1, f_col2, f_col3 = st.columns(3)
        with f_col1:
            st.latex(r"D.F. = \frac{\sqrt{3} \times 11 \times MDI(A)}{Total\ kVA}")
            st.write(f"**Calculation:** {mdi_kva} / {total_load_at_source}")
            st.metric("Demand Factor", f"{df_val:.4f}")
        with f_col2:
            st.latex(r"Actual\ V.D. = \sum V.D. \times D.F.")
            st.write(f"**Calculation:** {total_vd_volts:.2f} × {df_val:.4f}")
            st.metric("Actual VD", f"{actual_vd_v:.2f} V")
        with f_col3:
            st.latex(r"\% V.D. = \frac{Act.\ V.D.}{11000 - Act.\ V.D.} \times 100")
            st.write(f"**Calculation:** ({actual_vd_v:.2f} / (11000 - {actual_vd_v:.2f})) × 100")
            st.metric("% Voltage Drop", f"{vd_percent:.3f}%")
        st.markdown('</div>', unsafe_allow_html=True)

    if sketch_btn:
        st.subheader("🎨 Feeder Sketch")
        dot = graphviz.Digraph()
        dot.attr(rankdir='BT')
        dot.node('SS', f'{substation_name}\n(Source)', shape='house', style='filled', fillcolor='gold')
        
        prev = 'SS'
        for i, row in df.iterrows():
            node_id = f"P{i}"
            is_cable = "CABLE" in row['CONDUCTOR SIZE'].upper()
            label = f"{row['CONDUCTOR SIZE']}\nVD: {row['VD (VOLTS)']:.2f}V"
            dot.node(node_id, row['POINT'].split('-')[-1], shape='doublecircle' if is_cable else 'circle')
            dot.edge(node_id, prev, label=label, color='red')
            prev = node_id
        
        st.graphviz_chart(dot)

        # PDF Generation
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", 'B', 16)
        pdf.cell(200, 10, f"PSPCL REPORT: {feeder_name}", ln=True, align='C')
        pdf.ln(10)
        
        # SDO Stamp Section at bottom
        pdf.set_y(-50)
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(130)
        pdf.multi_cell(60, 8, f"__________________\nSDO OP SUB-DIV\nPSPCL {sub_div.upper()}", align='C')
        
        pdf_output = pdf.output(dest="S").encode("latin-1")
        st.download_button("📥 Download PDF Report", pdf_output, "Report.pdf", "application/pdf")

else:
    st.info("Pehle Sidebar mein data bharo aur Conductor Size select karo.")

# --- FOOTER ---
st.markdown(f'<div class="footer-container"><b>Made with ❤️ by Anuj Narang</b><br>Powered by Beeclue Tech</div>', unsafe_allow_html=True)
