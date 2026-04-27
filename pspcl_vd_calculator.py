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

# Branding Assets
PSPCL_LOGO = "https://upload.wikimedia.org/wikipedia/en/3/3a/Punjab_State_Power_Corporation_Limited_logo.png"
INSTA_ICON = "https://upload.wikimedia.org/wikipedia/commons/a/a5/Instagram_icon.png"
FB_ICON = "https://upload.wikimedia.org/wikipedia/commons/1/1b/Facebook_icon.svg"
X_ICON = "https://upload.wikimedia.org/wikipedia/commons/b/b7/X_logo.jpg"
LINKED_ICON = "https://upload.wikimedia.org/wikipedia/commons/c/ca/LinkedIn_logo_initials.png"
BEECLUE_LOGO = "https://beeclue.com/wp-content/uploads/2023/04/Beeclue-Logo-New.png"

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
    .header-container {{
        text-align: center;
        padding: 35px;
        background: #ffffff;
        border-radius: 20px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.1);
        margin-bottom: 25px;
        border-top: 10px solid #ffcc00;
    }}
    .pspcl-logo-img {{ height: 130px; margin-bottom: 15px; transition: 0.4s; }}
    .pspcl-logo-img:hover {{ transform: scale(1.05); }}
    
    .metric-card {{
        background: white;
        padding: 20px;
        border-radius: 12px;
        box-shadow: 0 4px 10px rgba(0,0,0,0.05);
        border-left: 5px solid #1a237e;
    }}
    
    .footer-section {{
        text-align: center;
        margin-top: 70px;
        padding: 50px 20px;
        background: #ffffff;
        border-top: 1px solid #eee;
    }}
    .social-btn {{
        width: 40px;
        margin: 0 12px;
        transition: transform 0.3s ease;
        cursor: pointer;
    }}
    .social-btn:hover {{ transform: translateY(-5px) scale(1.2); }}
</style>
""", unsafe_allow_html=True)

# ==========================================
# 3. APP HEADER
# ==========================================
st.markdown(f"""
<div class="header-container">
    <img src="{PSPCL_LOGO}" class="pspcl-logo-img">
    <h1 style="color: #1a237e; margin: 0; font-weight: 800;">PUNJAB STATE POWER CORPORATION LIMITED</h1>
    <h2 style="color: #444; margin: 5px;">11kV Voltage Drop Calculator</h2>
</div>
""", unsafe_allow_html=True)

# ==========================================
# 4. SIDEBAR INPUTS
# ==========================================
with st.sidebar:
    st.image(PSPCL_LOGO, width=100)
    st.title("⚙️ System Control")
    
    feeder_name = st.text_input("Feeder Name", value="")
    sub_station = st.text_input("Feeding Substation", value="")
    sub_division = st.text_input("Sub-Division", value="")
    division_name = st.text_input("Division", value="")
    
    st.divider()
    mdi_amps = st.number_input("Max Demand (MDI Amps)", min_value=0.0, step=0.1, value=0.0)
    num_sections = st.number_input("Total Sections", min_value=1, max_value=50, value=1)
    
    mdi_kva = round(np.sqrt(3) * 11 * mdi_amps, 4)
    st.info(f"**Calculated MDI:** {mdi_kva} kVA")
    st.caption(f"Last Updated: {datetime.now().strftime('%d-%m-%Y')}")

# ==========================================
# 5. DATA ENTRY TABLE
# ==========================================
st.subheader("📍 Sectional Load Configuration")
labels = [f"{chr(65+i)}-{chr(66+i)}" for i in range(num_sections)]
df_init = pd.DataFrame({
    "SECTION": labels,
    "CONDUCTOR TYPE": [None] * num_sections,
    "LENGTH (KM)": [0.0] * num_sections,
    "NODE LOAD (kVA)": [0.0] * num_sections
})

edited_df = st.data_editor(
    df_init,
    column_config={
        "SECTION": st.column_config.TextColumn("Span ID", disabled=True),
        "CONDUCTOR TYPE": st.column_config.SelectboxColumn("Conductor/Cable", options=list(VD_FACTORS.keys()), required=True),
        "LENGTH (KM)": st.column_config.NumberColumn("Length", format="%.3f"),
        "NODE LOAD (kVA)": st.column_config.NumberColumn("Load (kVA)", format="%.1f")
    },
    use_container_width=True, num_rows="fixed"
)

# ==========================================
# 6. CALCULATION ENGINE
# ==========================================
if 'res_cache' not in st.session_state: st.session_state.res_cache = None
if 'met_cache' not in st.session_state: st.session_state.met_cache = {}

c1, c2, c3 = st.columns(3)

def run_engine():
    with st.spinner("Processing electrical harmonics..."):
        time.sleep(0.4)
        df = edited_df.copy()
        
        # Cumulative Load (Tail to Source)
        node_loads = df["NODE LOAD (kVA)"].tolist()
        cum_loads = [0] * len(node_loads)
        running_sum = 0
        for i in range(len(node_loads)-1, -1, -1):
            running_sum += node_loads[i]
            cum_loads[i] = running_sum
            
        df["CUMULATIVE LOAD (kVA)"] = cum_loads
        df["VD FACTOR"] = df["CONDUCTOR TYPE"].map(VD_FACTORS)
        df["SECTION VD (V)"] = df["LENGTH (KM)"] * df["CUMULATIVE LOAD (kVA)"] * df["VD FACTOR"]
        
        # Aggregation
        total_sum_vd = df["SECTION VD (V)"].sum()
        max_source_load = cum_loads[0] if cum_loads else 0
        demand_f = mdi_kva / max_source_load if max_source_load > 0 else 0
        actual_vd_volts = total_sum_vd * demand_f
        final_percent = (actual_vd_volts / (11000 - actual_vd_volts) * 100) if (11000 - actual_vd_volts) > 0 else 0
        
        st.session_state.res_cache = df
        st.session_state.met_cache = {
            "sum_vd": total_sum_vd,
            "max_load": max_source_load,
            "df_val": demand_f,
            "actual_v": actual_vd_volts,
            "percent_val": final_percent
        }

if c1.button("🚀 EXECUTE CALCULATION", type="primary", use_container_width=True):
    if edited_df["CONDUCTOR TYPE"].isnull().any():
        st.error("Please select a Conductor Type for all entries!")
    else:
        run_engine()

# ==========================================
# 7. RESULTS PRESENTATION
# ==========================================
if st.session_state.res_cache is not None:
    res_df = st.session_state.res_cache
    m = st.session_state.met_cache
    
    st.divider()
    st.subheader("📊 Calculation Output")
    st.dataframe(res_df, use_container_width=True)
    
    # Mathematical Formulas
    st.markdown('<div style="background:white; padding:30px; border-radius:15px; border:1px solid #eee;">', unsafe_allow_html=True)
    m_col1, m_col2, m_col3 = st.columns(3)
    
    with m_col1:
        st.latex(r"D.F. = \frac{MDI_{kVA}}{\sum Load_{kVA}}")
        st.metric("Demand Factor", f"{m['df_val']:.4f}")
    with m_col2:
        st.latex(r"V_{drop} = \sum VD \times D.F.")
        st.metric("Actual VD", f"{m['actual_v']:.2f} V")
    with m_col3:
        st.latex(r"\% VD = \frac{V_{drop}}{11000 - V_{drop}} \times 100")
        st.metric("Voltage Regulation", f"{m['percent_val']:.3f} %")
    st.markdown('</div>', unsafe_allow_html=True)

    # ==========================================
    # 8. SKETCH & PDF
    # ==========================================
    if c2.button("🎨 GENERATE SKETCH & PDF", use_container_width=True):
        st.subheader("📐 Single Line Diagram (SLD)")
        sld = graphviz.Digraph()
        sld.attr(rankdir='BT', size='8,8')
        
        # Source
        sld.node('S', f'SOURCE\n{sub_station}\n({m["max_load"]} kVA)', shape='house', style='filled', fillcolor='gold')
        
        prev = 'S'
        for i, r in res_df.iterrows():
            nid = f"N{i}"
            is_c = "CABLE" in r['CONDUCTOR TYPE'].upper()
            sld.node(nid, r['SECTION'].split('-')[-1], shape='box' if is_c else 'circle', style='filled', fillcolor='#e1f5fe')
            sld.edge(nid, prev, label=f"{r['CONDUCTOR TYPE']}\n{r['DISTANCE (KM)']}km")
            prev = nid
        st.graphviz_chart(sld)

        # PDF Export
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("helvetica", 'B', 16)
        pdf.cell(0, 15, "PSPCL OFFICIAL VOLTAGE DROP REPORT", ln=True, align='C')
        pdf.ln(5)
        
        pdf.set_font("helvetica", 'B', 11)
        pdf.cell(95, 10, f"Feeder: {feeder_name}")
        pdf.cell(95, 10, f"Sub-Div: {sub_division}", ln=True)
        pdf.ln(5)
        
        # Table
        pdf.set_fill_color(240, 240, 240)
        pdf.set_font("helvetica", 'B', 10)
        headers = [("Section", 30), ("Conductor", 55), ("Len", 25), ("Cum.kVA", 35), ("VD(V)", 45)]
        for h, w in headers: pdf.cell(w, 10, h, 1, 0, 'C', True)
        pdf.ln()
        
        pdf.set_font("helvetica", '', 9)
        for _, r in res_df.iterrows():
            pdf.cell(30, 9, str(r['SECTION']), 1, 0, 'C')
            pdf.cell(55, 9, str(r['CONDUCTOR TYPE'])[:20], 1)
            pdf.cell(25, 9, str(r['DISTANCE (KM)']), 1, 0, 'C')
            pdf.cell(35, 9, f"{r['CUMULATIVE LOAD (kVA)']:.1f}", 1, 0, 'C')
            pdf.cell(45, 9, f"{r['SECTION VD (V)']:.3f}", 1, 1, 'C')
            
        pdf.ln(10)
        pdf.set_font("helvetica", 'B', 14)
        pdf.cell(0, 10, f"FINAL PERCENTAGE VOLTAGE DROP: {m['percent_val']:.3f} %", ln=True)
        
        pdf.ln(30)
        pdf.cell(130)
        pdf.multi_cell(60, 6, f"__________________\nSDO OP SUB-DIVISION\nPSPCL {sub_division.upper()}", align='C')
        
        pdf_bytes = pdf.output()
        st.download_button("📥 DOWNLOAD OFFICIAL PDF", bytes(pdf_bytes), f"{feeder_name}_Report.pdf", "application/pdf", use_container_width=True)

    csv_data = res_df.to_csv(index=False).encode('utf-8')
    c3.download_button("📊 EXPORT DATA (CSV)", csv_data, "Feeder_Export.csv", "text/csv", use_container_width=True)

# ==========================================
# 9. FOOTER
# ==========================================
st.markdown(f"""
<div class="footer-section">
    <p style="font-size: 1.4em; font-weight: 700;">Made with ❤️ by Anuj Narang</p>
    <p style="color: #666;">Junior Engineer (Electrical) | PSPCL Professional Tool</p>
    <div style="margin: 25px 0;">
        <a href="https://instagram.com/iamanujnarang"><img src="{INSTA_ICON}" class="social-btn"></a>
        <a href="https://facebook.com/iamanujnarang"><img src="{FB_ICON}" class="social-btn"></a>
        <a href="https://x.com/iamanujnarang"><img src="{X_ICON}" class="social-btn"></a>
        <a href="https://linkedin.com/in/iamanujnarang"><img src="{LINKED_ICON}" class="social-btn"></a>
    </div>
    <p style="color: #888; font-size: 0.9em; text-transform: uppercase;">In Strategic Partnership with</p>
    <a href="https://beeclue.com"><img src="{BEECLUE_LOGO}" style="width: 140px; margin-top: 10px;"></a>
</div>
""", unsafe_allow_html=True)
