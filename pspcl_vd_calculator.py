import streamlit as st
import pandas as pd
import numpy as np
import io
import time
import graphviz
from fpdf import FPDF
from datetime import datetime

# ==========================================
# 1. GLOBAL CONFIGURATION
# ==========================================
st.set_page_config(
    page_title="PSPCL 11kV VD Calculator",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Assets
PSPCL_LOGO = "https://upload.wikimedia.org/wikipedia/en/thumb/3/3a/Punjab_State_Power_Corporation_Limited_logo.png/220px-Punjab_State_Power_Corporation_Limited_logo.png"
INSTA_ICON = "https://upload.wikimedia.org/wikipedia/commons/a/a5/Instagram_icon.png"
FB_ICON = "https://upload.wikimedia.org/wikipedia/commons/1/1b/Facebook_icon.svg"
X_ICON = "https://upload.wikimedia.org/wikipedia/commons/b/b7/X_logo.jpg"
LINKED_ICON = "https://upload.wikimedia.org/wikipedia/commons/c/ca/LinkedIn_logo_initials.png"
BEECLUE_LOGO_WHITE = "https://beeclue.com/wp-content/uploads/2026/02/b-horizontal-logo-w-2048x506.png"

# Voltage Drop Factors (Standard PSPCL Reference)
VD_FACTORS = {
    "ACSR 100 SQMM (Dog)": 0.0415,
    "ACSR 80 SQMM (Wolf)": 0.0512,
    "ACSR 50 SQMM (Rabbit)": 0.0910,
    "ACSR 30 SQMM (Weasel)": 0.1520,
    "ACSR 20 SQMM (Squirrel)": 0.2250,
    "XLPE CABLE 300 SQMM": 0.0146,
    "XLPE CABLE 150 SQMM": 0.0285,
    "XLPE CABLE 35 SQMM": 0.1150
}

# ==========================================
# 2. ADVANCED CSS STYLING
# ==========================================
st.markdown(f"""
<style>
    .main {{ background-color: #f4f7f9; }}
    .header-container {{
        text-align: center;
        padding: 40px;
        background: #ffffff;
        border-radius: 20px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.05);
        margin-bottom: 30px;
        border-top: 10px solid #ffcc00;
    }}
    .pspcl-header-logo {{ height: 140px; margin-bottom: 20px; }}
    
    .formula-card {{
        background: white;
        padding: 25px;
        border-radius: 15px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.05);
        border: 1px solid #e0e0e0;
        margin-top: 20px;
    }}
    
    .footer-box {{
        text-align: center;
        margin-top: 80px;
        padding: 60px 20px;
        background: #ffffff;
        border-top: 2px solid #eee;
    }}
    
    .social-icon {{
        width: 40px;
        margin: 0 12px;
        transition: 0.3s;
    }}
    .social-icon:hover {{ transform: translateY(-5px); }}
    
    .beeclue-dark-container {{
        background-color: #001c3d;
        padding: 25px;
        border-radius: 12px;
        display: inline-block;
        margin-top: 20px;
        width: 280px;
    }}
    .beeclue-img {{ width: 100%; height: auto; }}
</style>
""", unsafe_allow_html=True)

# ==========================================
# 3. HEADER
# ==========================================
st.markdown(f"""
<div class="header-container">
    <img src="{PSPCL_LOGO}" class="pspcl-header-logo">
    <h1 style="color: #003366; margin:0; font-weight: 800;">PUNJAB STATE POWER CORPORATION LIMITED</h1>
    <h2 style="color: #444; margin:5px; font-weight: 400;">11kV Voltage Drop Calculator</h2>
</div>
""", unsafe_allow_html=True)

# ==========================================
# 4. SIDEBAR SETTINGS
# ==========================================
with st.sidebar:
    st.image(PSPCL_LOGO, width=120)
    st.title("⚙️ Feeder Parameters")
    
    feeder_name = st.text_input("Feeder Name", value="")
    ss_name = st.text_input("Substation Name", value="")
    sdiv_name = st.text_input("Sub-Division", value="")
    div_name = st.text_input("Division", value="")
    
    st.divider()
    mdi_a = st.number_input("Max Demand (Amps)", min_value=0.0, step=0.1)
    num_sec = st.number_input("Number of Sections", min_value=1, max_value=50, step=1)
    
    mdi_kva = round(np.sqrt(3) * 11 * mdi_a, 4)
    st.success(f"**Current MDI:** {mdi_kva} kVA")
    st.caption(f"System Date: {datetime.now().strftime('%d-%m-%Y')}")

# ==========================================
# 5. MAIN DATA EDITOR
# ==========================================
st.subheader("📍 Network Sectional Data")
section_labels = [f"{chr(65+i)}-{chr(66+i)}" for i in range(num_sec)]

input_df = pd.DataFrame({
    "SECTION": section_labels,
    "CONDUCTOR TYPE": [None] * num_sec,
    "LENGTH (KM)": [0.0] * num_sec,
    "LOAD AT NODE (kVA)": [0.0] * num_sec
})

edited_df = st.data_editor(
    input_df,
    column_config={
        "SECTION": st.column_config.TextColumn("Span", disabled=True),
        "CONDUCTOR TYPE": st.column_config.SelectboxColumn("Type", options=list(VD_FACTORS.keys()), required=True),
        "LENGTH (KM)": st.column_config.NumberColumn("Length", format="%.3f"),
        "LOAD AT NODE (kVA)": st.column_config.NumberColumn("kVA Load", format="%.1f")
    },
    use_container_width=True, num_rows="fixed"
)

# ==========================================
# 6. CALCULATION CORE
# ==========================================
if 'final_results' not in st.session_state: st.session_state.final_results = None
if 'metrics' not in st.session_state: st.session_state.metrics = {}

btn_col1, btn_col2, btn_col3 = st.columns(3)

def run_calculations():
    df = edited_df.copy()
    node_loads = df["LOAD AT NODE (kVA)"].tolist()
    
    # Cumulative Sum (Source to Tail logic)
    cum_loads = [0] * len(node_loads)
    temp_sum = 0
    for i in range(len(node_loads)-1, -1, -1):
        temp_sum += node_loads[i]
        cum_loads[i] = temp_sum
        
    df["CUMULATIVE LOAD (kVA)"] = cum_loads
    df["FACTOR"] = df["CONDUCTOR TYPE"].map(VD_FACTORS)
    df["VD VOLTS"] = df["LENGTH (KM)"] * df["CUMULATIVE LOAD (kVA)"] * df["FACTOR"]
    
    # Aggregates
    sum_vd = df["VD VOLTS"].sum()
    total_node_kva = cum_loads[0] if cum_loads else 0
    demand_factor = mdi_kva / total_node_kva if total_node_kva > 0 else 0
    actual_vd = sum_vd * demand_factor
    reg_percent = (actual_vd / (11000 - actual_vd) * 100) if (11000 - actual_vd) > 0 else 0
    
    st.session_state.final_results = df
    st.session_state.metrics = {
        "sum_vd": sum_vd, "total_kva": total_node_kva, "df": demand_factor,
        "actual_vd": actual_vd, "percent": reg_percent
    }

if btn_col1.button("🚀 CALCULATE VD", type="primary", use_container_width=True):
    if edited_df["CONDUCTOR TYPE"].isnull().any():
        st.error("Select Conductor for all sections!")
    else:
        run_calculations()

# ==========================================
# 7. DISPLAY RESULTS & FORMULAS
# ==========================================
if st.session_state.final_results is not None:
    res = st.session_state.final_results
    m = st.session_state.metrics
    
    st.divider()
    st.subheader("📊 Results Overview")
    st.dataframe(res, use_container_width=True)
    
    st.markdown('<div class="formula-card">', unsafe_allow_html=True)
    m1, m2, m3 = st.columns(3)
    with m1:
        st.latex(r"D.F. = \frac{MDI_{kVA}}{\sum Load}")
        st.metric("Demand Factor", f"{m['df']:.4f}")
    with m2:
        st.latex(r"Actual\ V = \sum VD \times DF")
        st.metric("Voltage Drop", f"{m['actual_vd']:.2f} V")
    with m3:
        st.latex(r"\% VD = \frac{V}{11000-V} \times 100")
        st.metric("Regulation", f"{m['percent']:.3f} %")
    st.markdown('</div>', unsafe_allow_html=True)

    # ==========================================
    # 8. SKETCH & PDF (FIXED LOGIC)
    # ==========================================
    if btn_col2.button("🎨 GENERATE SKETCH & PDF", use_container_width=True):
        st.subheader("📐 Feeder Single Line Diagram")
        sld = graphviz.Digraph()
        sld.attr(rankdir='BT', size='12,12')
        
        # Source
        sld.node('S', f'SOURCE\n{ss_name}\n{m["total_kva"]}kVA', shape='house', style='filled', fillcolor='#ffecb3')
        
        last = 'S'
        for i, r in res.iterrows():
            curr = f"N{i}"
            is_cable = "CABLE" in r["CONDUCTOR TYPE"].upper()
            # FIX: Cable = Box, Overhead = Circle
            node_shape = 'box' if is_cable else 'circle'
            sld.node(curr, r['SECTION'].split('-')[-1], shape=node_shape, style='filled', fillcolor='#e3f2fd')
            sld.edge(curr, last, label=f"{r['CONDUCTOR TYPE']}\n{r['LENGTH (KM)']}km", color='red' if is_cable else 'black')
            last = curr
        st.graphviz_chart(sld)

        # PDF Export
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("helvetica", 'B', 16)
        pdf.cell(0, 15, "PSPCL 11kV VOLTAGE DROP REPORT", ln=True, align='C')
        pdf.ln(10)
        
        pdf.set_font("helvetica", '', 12)
        pdf.cell(95, 10, f"Feeder: {feeder_name}")
        pdf.cell(95, 10, f"Sub-Div: {sdiv_name}", ln=True)
        pdf.ln(5)
        
        # Header
        pdf.set_fill_color(240, 240, 240)
        pdf.set_font("helvetica", 'B', 10)
        for h, w in [("Section", 30), ("Conductor", 55), ("Len", 25), ("Cum.kVA", 35), ("VD(V)", 45)]:
            pdf.cell(w, 10, h, 1, 0, 'C', True)
        pdf.ln()
        
        # Body
        pdf.set_font("helvetica", '', 9)
        for _, r in res.iterrows():
            pdf.cell(30, 9, str(r['SECTION']), 1, 0, 'C')
            pdf.cell(55, 9, str(r['CONDUCTOR TYPE'])[:22], 1)
            pdf.cell(25, 9, str(r['LENGTH (KM)']), 1, 0, 'C')
            pdf.cell(35, 9, f"{r['CUMULATIVE LOAD (kVA)']:.1f}", 1, 0, 'C')
            pdf.cell(45, 9, f"{r['VD VOLTS']:.3f}", 1, 1, 'C')
            
        pdf.ln(10)
        pdf.set_font("helvetica", 'B', 14)
        pdf.cell(0, 10, f"FINAL PERCENTAGE VOLTAGE DROP: {m['percent']:.3f} %", ln=True)
        
        pdf_out = pdf.output()
        st.download_button("📥 DOWNLOAD OFFICIAL PDF", bytes(pdf_out), f"{feeder_name}_VD_Report.pdf", "application/pdf", use_container_width=True)

    csv_buf = res.to_csv(index=False).encode('utf-8')
    btn_col3.download_button("📊 EXPORT RAW DATA", csv_buf, "Feeder_Data.csv", "text/csv", use_container_width=True)

# ==========================================
# 9. FOOTER & BRANDING
# ==========================================
st.markdown(f"""
<div class="footer-box">
    <p style="font-size: 1.5em; font-weight: 700; color: #222;">Made with ❤️ by Anuj Narang</p>
    <p style="color: #666; margin-bottom: 30px;">Junior Engineer (Electrical) | PSPCL Professional Development</p>
    
    <div style="margin-bottom: 35px;">
        <a href="https://instagram.com/iamanujnarang"><img src="{INSTA_ICON}" class="social-icon"></a>
        <a href="https://facebook.com/iamanujnarang"><img src="{FB_ICON}" class="social-icon"></a>
        <a href="https://x.com/iamanujnarang"><img src="{X_ICON}" class="social-icon"></a>
        <a href="https://linkedin.com/in/iamanujnarang"><img src="{LINKED_ICON}" class="social-icon"></a>
    </div>
    
    <p style="color: #999; font-size: 0.9em; text-transform: uppercase;">Strategic Partner</p>
    <div class="beeclue-dark-container">
        <a href="https://beeclue.com" target="_blank">
            <img src="{BEECLUE_LOGO_WHITE}" class="beeclue-img">
        </a>
    </div>
    <div style="margin-top: 30px; font-size: 0.8em; color: #bbb;">
        © 2026 Anuj Narang. All Rights Reserved.
    </div>
</div>
""", unsafe_allow_html=True)
