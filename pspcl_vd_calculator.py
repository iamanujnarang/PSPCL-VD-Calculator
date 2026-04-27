import streamlit as st
import pandas as pd
import numpy as np
import io
import graphviz
from fpdf import FPDF
import base64

# --- PAGE CONFIG ---
st.set_page_config(page_title="PSPCL VD Calculator Pro", page_icon="⚡", layout="wide")

# --- CONSTANTS & ASSETS ---
# Direct link to a stable PSPCL logo source
PSPCL_LOGO = "https://raw.githubusercontent.com/iamanujnarang/assets/main/pspcl_logo.png" 
# Note: Agar upar wala link na chale toh niche wala fallback hai
FALLBACK_LOGO = "https://pspcl.in/assets/images/logo.png"

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

# --- STYLING ---
st.markdown(f"""
<style>
    .header-box {{ text-align: center; padding: 25px; background: #ffffff; border-radius: 15px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); margin-bottom: 25px; border-top: 8px solid #ffcc00; }}
    .pspcl-main-logo {{ height: 120px; width: auto; margin-bottom: 15px; }}
    .formula-section {{ background: #ffffff; padding: 30px; border-radius: 15px; border: 1px solid #dee2e6; margin-top: 30px; box-shadow: 0 10px 25px rgba(0,0,0,0.05); }}
    .footer-container {{ text-align: center; margin-top: 60px; padding: 40px; border-top: 1px solid #eee; background: #fdfdfd; }}
    .social-logo {{ width: 35px; margin: 0 10px; transition: 0.3s; cursor: pointer; }}
    .social-logo:hover {{ transform: scale(1.3); }}
    .beeclue-footer-logo {{ width: 120px; margin-top: 15px; }}
</style>
""", unsafe_allow_html=True)

# --- HEADER ---
st.markdown(f"""
<div class="header-box">
    <img src="{FALLBACK_LOGO}" class="pspcl-main-logo" onerror="this.src='https://upload.wikimedia.org/wikipedia/en/3/3a/Punjab_State_Power_Corporation_Limited_logo.png'">
    <h1 style="margin:0; color:#1a237e;">PUNJAB STATE POWER CORPORATION LIMITED</h1>
    <h2 style="margin:5px; color:#444;">11kV Voltage Drop Calculator</h2>
</div>
""", unsafe_allow_html=True)

# --- SESSION STATE ---
if 'res_df' not in st.session_state: st.session_state.res_df = None
if 'metrics' not in st.session_state: st.session_state.metrics = {}

# --- SIDEBAR ---
with st.sidebar:
    st.header("📝 Feeder Details")
    f_name = st.text_input("Feeder Name", value="")
    ss_name = st.text_input("Feeding Substation", value="")
    s_div = st.text_input("Sub-Division", value="")
    div = st.text_input("Division", value="")
    
    st.divider()
    st.header("⚡ Load Parameters")
    mdi_a = st.number_input("Max Demand (MDI Amps)", min_value=0.0, step=0.1, value=0.0)
    n_sec = st.number_input("Number of Sections", min_value=1, max_value=100, value=1)
    mdi_k = round(np.sqrt(3) * 11 * mdi_a, 4)
    st.info(f"Calculated MDI: {mdi_k} kVA")

# --- DATA ENTRY ---
st.subheader("📍 Network Configuration")
pts = [f"{chr(65+i)}-{chr(66+i)}" for i in range(n_sec)]
df_init = pd.DataFrame({
    "SECTION": pts,
    "CONDUCTOR SIZE": [None] * n_sec,
    "LENGTH (KM)": [0.0] * n_sec,
    "NODE LOAD (kVA)": [0.0] * n_sec
})

ed_df = st.data_editor(
    df_init,
    column_config={
        "SECTION": st.column_config.TextColumn("Section", disabled=True),
        "CONDUCTOR SIZE": st.column_config.SelectboxColumn("Conductor Type", options=list(VD_FACTORS.keys()), required=True),
        "LENGTH (KM)": st.column_config.NumberColumn("Length (km)", format="%.3f"),
        "NODE LOAD (kVA)": st.column_config.NumberColumn("Load at Node", format="%.1f")
    },
    use_container_width=True, num_rows="fixed"
)

# --- CALCULATION LOGIC ---
c1, c2, c3 = st.columns(3)

if c1.button("🚀 Calculate Voltage Drop", type="primary", use_container_width=True):
    df = ed_df.copy()
    if not df["CONDUCTOR SIZE"].isnull().any():
        # Cumulative Load (Tail to Source)
        node_loads = df["NODE LOAD (kVA)"].tolist()
        cum_loads = [0] * len(node_loads)
        temp_sum = 0
        for i in range(len(node_loads)-1, -1, -1):
            temp_sum += node_loads[i]
            cum_loads[i] = temp_sum
            
        df["CUMULATIVE LOAD (kVA)"] = cum_loads
        df["VD FACTOR"] = df["CONDUCTOR SIZE"].map(VD_FACTORS)
        df["SECTION VD (V)"] = df["LENGTH (KM)"] * df["CUMULATIVE LOAD (kVA)"] * df["VD FACTOR"]
        
        t_vd_sum = df["SECTION VD (V)"].sum()
        max_ld = cum_loads[0] if cum_loads else 0
        df_v = mdi_k / max_ld if max_ld > 0 else 0
        a_vd_v = t_vd_sum * df_v
        v_per = (a_vd_v / (11000 - a_vd_v) * 100) if (11000 - a_vd_v) > 0 else 0
        
        st.session_state.res_df = df
        st.session_state.metrics = {"t_vd": t_vd_sum, "max_ld": max_ld, "df_v": df_v, "a_vd_v": a_vd_v, "v_per": v_per}
    else:
        st.error("Please select Conductor for all sections.")

if st.session_state.res_df is not None:
    res = st.session_state.res_df
    m = st.session_state.metrics
    
    st.subheader("📊 Calculation Results")
    st.dataframe(res, use_container_width=True)
    
    st.markdown('<div class="formula-section">', unsafe_allow_html=True)
    f_col1, f_col2, f_col3 = st.columns(3)
    with f_col1:
        st.latex(r"D.F. = \frac{MDI(kVA)}{Total\ kVA}")
        st.metric("Demand Factor", f"{m['df_v']:.4f}")
    with f_col2:
        st.latex(r"Actual\ VD(V) = \sum VD \times DF")
        st.metric("Actual VD", f"{m['a_vd_v']:.2f} V")
    with f_col3:
        st.latex(r"\% VD = \frac{VD}{11000-VD} \times 100")
        st.metric("Voltage Drop", f"{m['v_per']:.3f} %")
    st.markdown('</div>', unsafe_allow_html=True)

# --- SKETCH & PDF EXPORT ---
if c2.button("🎨 Generate Sketch & Export PDF", use_container_width=True):
    if st.session_state.res_df is not None:
        res = st.session_state.res_df
        m = st.session_state.metrics
        
        # 1. Show Sketch in App
        dot = graphviz.Digraph()
        dot.attr(rankdir='BT')
        dot.node('S', f'{ss_name}\n(Source)\n{m["max_ld"]} kVA', shape='house', style='filled', fillcolor='gold')
        
        prev = 'S'
        for i, r in res.iterrows():
            nid = f"N{i}"
            is_c = "CABLE" in r['CONDUCTOR SIZE'].upper()
            dot.node(nid, r['SECTION'].split('-')[-1], shape='box' if is_c else 'circle', style='filled', fillcolor='#e3f2fd')
            dot.edge(nid, prev, label=f"{r['CONDUCTOR SIZE']}\n{r['LENGTH (KM)']}km", color='red' if is_c else 'black')
            prev = nid
        
        st.graphviz_chart(dot)
        
        # 2. PDF Generation
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", 'B', 16)
        pdf.cell(190, 10, "PSPCL 11kV VOLTAGE DROP REPORT", ln=True, align='C')
        pdf.ln(5)
        
        pdf.set_font("Arial", '', 11)
        pdf.cell(95, 8, f"Feeder: {f_name}")
        pdf.cell(95, 8, f"Sub-Division: {s_div}", ln=True)
        pdf.cell(95, 8, f"Substation: {ss_name}")
        pdf.cell(95, 8, f"Division: {div}", ln=True)
        pdf.ln(5)
        
        # Table
        pdf.set_font("Arial", 'B', 10)
        pdf.set_fill_color(230, 230, 230)
        pdf.cell(25, 10, "Section", 1, 0, 'C', True)
        pdf.cell(55, 10, "Conductor", 1, 0, 'C', True)
        pdf.cell(25, 10, "Length", 1, 0, 'C', True)
        pdf.cell(40, 10,
