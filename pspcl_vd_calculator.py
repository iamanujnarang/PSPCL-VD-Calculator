import streamlit as st
import pandas as pd
import numpy as np
import io
import time
import graphviz
from fpdf import FPDF
from datetime import datetime

# ==========================================
# 1. GLOBAL CONFIGURATION & CONSTANTS
# ==========================================
st.set_page_config(
    page_title="PSPCL 11kV VD Calculator Pro",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Branding Assets (New White Horizontal Beeclue Logo)
PSPCL_LOGO = "https://upload.wikimedia.org/wikipedia/en/3/3a/Punjab_State_Power_Corporation_Limited_logo.png"
INSTA_ICON = "https://upload.wikimedia.org/wikipedia/commons/a/a5/Instagram_icon.png"
FB_ICON = "https://upload.wikimedia.org/wikipedia/commons/1/1b/Facebook_icon.svg"
X_ICON = "https://upload.wikimedia.org/wikipedia/commons/b/b7/X_logo.jpg"
LINKED_ICON = "https://upload.wikimedia.org/wikipedia/commons/c/ca/LinkedIn_logo_initials.png"
# NEW WHITE HORIZONTAL LOGO
BEECLUE_LOGO_WHITE = "https://beeclue.com/wp-content/uploads/2026/02/b-horizontal-logo-w-2048x506.png"

# Standard 11kV VD Factors (Volts per KM per kVA)
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
# 2. ADVANCED STYLING (CSS)
# ==========================================
st.markdown(f"""
<style>
    .main {{ background-color: #f8f9fa; }}
    .stApp {{ background-image: linear-gradient(rgba(255,255,255,0.92), rgba(255,255,255,0.92)); }}
    
    /* Header Section */
    .header-container {{
        text-align: center;
        padding: 35px;
        background: #ffffff;
        border-radius: 20px;
        box-shadow: 0 10px 25px rgba(0,0,0,0.08);
        margin-bottom: 30px;
        border-top: 10px solid #ffcc00;
    }}
    .pspcl-logo-img {{ height: 130px; margin-bottom: 15px; transition: 0.4s; }}
    .pspcl-logo-img:hover {{ transform: scale(1.05); }}
    
    /* Metrics Formula Box */
    .formula-box {{
        background: white;
        padding: 30px;
        border-radius: 15px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.05);
        border: 1px solid #eee;
        margin-top: 25px;
    }}
    
    /* Footer Styling with Dark Background for Beeclue Logo */
    .footer-section {{
        text-align: center;
        margin-top: 80px;
        padding: 60px 20px 40px 20px;
        background-color: #ffffff;
        border-top: 1px solid #f1f1f1;
    }}
    .social-btn {{
        width: 42px;
        margin: 0 14px;
        transition: transform 0.3s ease;
        cursor: pointer;
    }}
    .social-btn:hover {{ transform: translateY(-5px) scale(1.2); }}
    
    /* Special Dark Background for White Beeclue Logo */
    .beeclue-logo-box {{
        background-color: #001529; /* Dark Navy Blue */
        padding: 20px;
        border-radius: 10px;
        display: inline-block;
        margin-top: 15px;
        width: 250px;
        transition: 0.3s;
    }}
    .beeclue-logo-box:hover {{ background-color: #002140; transform: scale(1.02); }}
    .beeclue-footer-logo {{ width: 100%; }}
</style>
""", unsafe_allow_html=True)

# ==========================================
# 3. APP HEADER
# ==========================================
st.markdown(f"""
<div class="header-container">
    <img src="{PSPCL_LOGO}" class="pspcl-logo-img">
    <h1 style="color: #1a237e; margin: 0; font-weight: 800;">PUNJAB STATE POWER CORPORATION LIMITED</h1>
    <h2 style="color: #444; margin: 5px; font-weight: 400; letter-spacing: 1px;">11kV Voltage Drop Calculator</h2>
</div>
""", unsafe_allow_html=True)

# ==========================================
# 4. SIDEBAR INPUTS
# ==========================================
with st.sidebar:
    st.image(PSPCL_LOGO, width=100)
    st.title("⚙️ Control Panel")
    
    with st.expander("📝 Feeder Identification", expanded=True):
        feeder_name = st.text_input("Feeder Name", value="")
        sub_station = st.text_input("Feeding Substation", value="")
        sub_division = st.text_input("Sub-Division Name", value="")
        division_name = st.text_input("Division Name", value="")
    
    with st.expander("⚡ Electrical Parameters", expanded=True):
        mdi_amps = st.number_input("Max Demand (MDI) in Amps", min_value=0.0, step=0.1, value=0.0)
        num_sections = st.number_input("Total sections", min_value=1, max_value=50, value=1)
        
        mdi_kva = round(np.sqrt(3) * 11 * mdi_amps, 4)
        st.info(f"**Total MDI:** {mdi_kva} kVA")
    
    st.write("---")
    st.caption(f"App Version: 2.5.1 AEA Approved | {datetime.now().strftime('%d-%m-%Y')}")

# ==========================================
# 5. DATA ENTRY TABLE
# ==========================================
st.subheader("📋 Sectional Configuration & Load Distribution")
# labels Source to Tail
labels = [f"{chr(65+i)}-{chr(66+i)}" for i in range(num_sections)]
df_init = pd.DataFrame({
    "SECTION": labels,
    "CONDUCTOR TYPE": [None] * num_sections,
    "DISTANCE (KM)": [0.0] * num_sections,
    "NODE LOAD (kVA)": [0.0] * num_sections
})

edited_df = st.data_editor(
    df_init,
    column_config={
        "SECTION": st.column_config.TextColumn("Span ID", disabled=True),
        "CONDUCTOR TYPE": st.column_config.SelectboxColumn("Conductor/Cable Size", options=list(VD_FACTORS.keys()), required=True),
        "DISTANCE (KM)": st.column_config.NumberColumn("Length (km)", format="%.3f", min_value=0.0),
        "NODE LOAD (kVA)": st.column_config.NumberColumn("Load at Node (kVA)", format="%.1f", min_value=0.0)
    },
    use_container_width=True, num_rows="fixed"
)

# ==========================================
# 6. CALCULATION CORE & SESSION STATE
# ==========================================
# Re-initializing session state to ensure sketch is visible after re-click
if 'res_cache' not in st.session_state: st.session_state.res_cache = None
if 'met_cache' not in st.session_state: st.session_state.met_cache = {}
# Trigger for showing sketch
if 'show_sketch' not in st.session_state: st.session_state.show_sketch = False

c1, c2, c3 = st.columns(3)

def run_engine():
    with st.spinner("Processing network harmonics and loads..."):
        time.sleep(0.4)
        df = edited_df.copy()
        
        # Backward Summation (Tail to Source)
        loads = df["NODE LOAD (kVA)"].tolist()
        cum_loads = [0] * len(loads)
        running_sum = 0
        for i in range(len(loads)-1, -1, -1):
            running_sum += loads[i]
            cum_loads[i] = running_sum
            
        df["CUMULATIVE LOAD (kVA)"] = cum_loads
        df["VD FACTOR"] = df["CONDUCTOR TYPE"].map(VD_FACTORS)
        
        # Sectional VD Calculation
        df["SECTION VD (V)"] = df["DISTANCE (KM)"] * df["CUMULATIVE LOAD (kVA)"] * df["VD FACTOR"]
        
        total_sum_vd = df["SECTION VD (V)"].sum()
        max_source_load = cum_loads[0] if cum_loads else 0
        demand_f = mdi_kva / max_source_load if max_source_load > 0 else 0
        actual_vd_volts = total_sum_vd * demand_f
        final_percent = (actual_vd_volts / (11000 - actual_vd_volts) * 100) if (11000 - actual_vd_volts) > 0 else 0
        
        st.session_state.res_cache = df
        st.session_state.met_cache = {
            "sum_vd": total_sum_vd, "max_load": max_source_load, "df_val": demand_f,
            "actual_v": actual_vd_volts, "percent_val": final_percent
        }
        st.session_state.show_sketch = False # Reset sketch view on new calculation

# Trigger 1: Execution
if c1.button("🚀 EXECUTE CALCULATION", type="primary", use_container_width=True):
    if edited_df["CONDUCTOR TYPE"].isnull().any():
        st.error("Please select a Conductor for every section!")
    else:
        run_engine()

# ==========================================
# 7. RESULTS PRESENTATION
# ==========================================
if st.session_state.res_cache is not None:
    res_df = st.session_state.res_cache
    m = st.session_state.met_cache
    
    st.divider()
    st.subheader("📊 Analytical Summary")
    st.dataframe(res_df, use_container_width=True)
    
    # Formulas Box
    st.markdown('<div class="formula-box">', unsafe_allow_html=True)
    m_col1, m_col2, m_col3 = st.columns(3)
    
    with m_col1:
        st.latex(r"D.F. = \frac{MDI_{kVA}}{\sum Load_{kVA}}")
        st.metric("Demand Factor", f"{m['df_val']:.4f}")
    with m_col2:
        st.latex(r"V_{drop} = \sum VD \times D.F.")
        st.metric("Actual VD", f"{m['actual_v']:.2f} V")
    with m_col3:
        st.latex(r"\% VD = \frac{V_{drop}}{11000 - V_{drop}} \times 100")
        st.metric("Percentage Drop", f"{m['percent_val']:.3f} %")
    st.markdown('</div>', unsafe_allow_html=True)

    # Trigger 2: Show Sketch
    if c2.button("🎨 GENERATE SKETCH & PDF", use_container_width=True):
        st.session_state.show_sketch = True

    # Raw CSV Download
    csv_buf = res_df.to_csv(index=False).encode('utf-8')
    c3.download_button("📊 EXPORT DATA (CSV)", csv_buf, "Feeder_Data.csv", "text/csv", use_container_width=True)

# ==========================================
# 8. SKETCH & PDF (FIXED TRIGGER)
# ==========================================
if st.session_state.show_sketch and st.session_state.res_cache is not None:
    res_data = st.session_state.res_cache
    m_data = st.session_state.met_cache
    
    # Graphviz SLD (Circle vs Box)
    st.write("---")
    st.subheader("📐 Single Line Diagram (SLD) Topology")
    sld = graphviz.Digraph()
    sld.attr(rankdir='BT')
    
    # Source
    sld.node('S', f'SOURCE\n{sub_station}\n({m_data["max_load"]} kVA)', shape='house', style='filled', fillcolor='gold')
    
    prev = 'S'
    for i, r in res_data.iterrows():
        nid = f"N{i}"
        is_cable = "CABLE" in r['CONDUCTOR TYPE'].upper()
        # Differentiate: Cable = Box, Overhead = Circle
        sld.node(nid, r['SECTION'].split('-')[-1], shape='box' if is_c else 'circle', style='filled', fillcolor='#e1f5fe')
        sld.edge(nid, prev, label=f"{r['CONDUCTOR TYPE']}\n{r['DISTANCE (KM)']}km", color='red' if is_cable else 'black')
        prev = nid
    st.graphviz_chart(sld)

    # PDF Export (fpdf2)
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("helvetica", 'B', 16)
    pdf.cell(0, 15, "PSPCL OFFICIAL VOLTAGE DROP REPORT", ln=True, align='C')
    pdf.ln(5)
    
    pdf.set_font("helvetica", '', 11)
    pdf.cell(95, 10, f"Feeder Name: {feeder_name}")
    pdf.cell(95, 10, f"Sub-Division: {sub_division}", ln=True)
    pdf.ln(5)
    
    # Table Header
    pdf.set_fill_color(240, 240, 240)
    pdf.set_font("helvetica", 'B', 10)
    headers = [("Section", 30), ("Conductor", 55), ("Length", 25), ("Cum.Load", 35), ("Sec VD", 45)]
    for h, w in headers: pdf.cell(w, 10, h, 1, 0, 'C', True)
    pdf.ln()
    
    # Table Body
    pdf.set_font("helvetica", '', 9)
    for _, r in res_data.iterrows():
        pdf.cell(30, 9, str(r['SECTION']), 1, 0, 'C')
        pdf.cell(55, 9, str(r['CONDUCTOR TYPE'])[:22], 1)
        pdf.cell(25, 9, str(r['LENGTH (KM)']), 1, 0, 'C')
        pdf.cell(35, 9, f"{r['CUMULATIVE LOAD (kVA)']:.1f}", 1, 0, 'C')
        pdf.cell(45, 9, f"{r['SECTION VD (V)']:.3f}", 1, 1, 'C')
        
    pdf.ln(10)
    pdf.set_font("helvetica", 'B', 14)
    pdf.set_text_color(200, 0, 0)
    pdf.cell(0, 10, f"FINAL PERCENTAGE VOLTAGE DROP: {m_data['percent_val']:.3f} %", ln=True)
    
    # Signature
    pdf.ln(30)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(125)
    pdf.multi_cell(60, 6, f"__________________\nSDO OP SUB-DIVISION\nPSPCL {sub_division.upper()}", align='C')
    
    pdf_bytes = pdf.output()
    st.download_button("📥 DOWNLOAD OFFICIAL PDF", bytes(pdf_bytes), f"{feeder_name}_Report.pdf", "application/pdf", use_container_width=True)

# ==========================================
# 9. FOOTER SECTION (Branding Fixed)
# ==========================================
st.markdown(f"""
<div class="footer-section">
    <p style="font-size: 1.4em; font-weight: 700;">Made with ❤️ by Anuj Narang</p>
    <p style="color: #666;">Junior Engineer (Electrical) | PSPCL Professional Development</p>
    <div style="margin: 25px 0;">
        <a href="https://instagram.com/iamanujnarang"><img src="{INSTA_ICON}" class="social-btn"></a>
        <a href="https://facebook.com/iamanujnarang"><img src="{FB_ICON}" class="social-btn"></a>
        <a href="https://x.com/iamanujnarang"><img src="{X_ICON}" class="social-btn"></a>
        <a href="https://linkedin.com/in/iamanujnarang"><img src="{LINKED_ICON}" class="social-btn"></a>
    </div>
    <p style="color: #888; font-size: 0.9em; text-transform: uppercase;">Strategic Partner</p>
    
    <div class="beeclue-logo-box">
        <a href="https://beeclue.com" target="_blank">
            <img src="{BEECLUE_LOGO_WHITE}" class="beeclue-footer-logo">
        </a>
    </div>
    
</div>
""", unsafe_allow_html=True)
