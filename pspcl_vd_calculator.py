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

# Assets & Branding Links
PSPCL_LOGO = "https://upload.wikimedia.org/wikipedia/en/3/3a/Punjab_State_Power_Corporation_Limited_logo.png"
INSTA_ICON = "https://upload.wikimedia.org/wikipedia/commons/a/a5/Instagram_icon.png"
FB_ICON = "https://upload.wikimedia.org/wikipedia/commons/1/1b/Facebook_icon.svg"
X_ICON = "https://upload.wikimedia.org/wikipedia/commons/b/b7/X_logo.jpg"
LINKED_ICON = "https://upload.wikimedia.org/wikipedia/commons/c/ca/LinkedIn_logo_initials.png"
BEECLUE_LOGO = "https://beeclue.com/wp-content/uploads/2023/04/Beeclue-Logo-New.png"

# Technical Constants (Standard 11kV Factors)
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
    /* Main Layout Styling */
    .main {{ background-color: #f8f9fa; }}
    .stApp {{ background-image: linear-gradient(rgba(255,255,255,0.9), rgba(255,255,255,0.9)); }}
    
    /* Header Section */
    .header-container {{
        text-align: center;
        padding: 40px;
        background: #ffffff;
        border-radius: 20px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.1);
        margin-bottom: 30px;
        border-bottom: 5px solid #ffcc00;
    }}
    .pspcl-logo-img {{ height: 140px; margin-bottom: 20px; transition: 0.5s; }}
    .pspcl-logo-img:hover {{ transform: scale(1.05); }}
    
    /* Result Cards & Formulas */
    .metric-card {{
        background: white;
        padding: 25px;
        border-radius: 15px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.05);
        border: 1px solid #eee;
        transition: 0.3s;
    }}
    .metric-card:hover {{ transform: translateY(-5px); box-shadow: 0 8px 25px rgba(0,0,0,0.1); }}
    
    /* Footer Styling */
    .footer-section {{
        text-align: center;
        margin-top: 80px;
        padding: 60px 20px;
        background-color: #ffffff;
        border-top: 2px solid #f1f1f1;
        border-radius: 30px 30px 0 0;
    }}
    .social-btn {{
        width: 45px;
        margin: 0 15px;
        transition: transform 0.3s ease;
        cursor: pointer;
        filter: drop-shadow(0 2px 5px rgba(0,0,0,0.1));
    }}
    .social-btn:hover {{ transform: translateY(-10px) scale(1.2); }}
</style>
""", unsafe_allow_html=True)

# ==========================================
# 3. APP HEADER
# ==========================================
st.markdown(f"""
<div class="header-container">
    <img src="{PSPCL_LOGO}" class="pspcl-logo-img">
    <h1 style="color: #003366; font-family: 'Segoe UI', Tahoma; font-weight: 800;">PUNJAB STATE POWER CORPORATION LIMITED</h1>
    <h2 style="color: #555; font-weight: 400; letter-spacing: 1px;">11kV Voltage Drop Calculator</h2>
</div>
""", unsafe_allow_html=True)

# ==========================================
# 4. SIDEBAR & INPUTS
# ==========================================
with st.sidebar:
    st.image(PSPCL_LOGO, width=100)
    st.title("⚙️ System Control")
    
    with st.expander("📌 Feeder Identification", expanded=True):
        feeder_name = st.text_input("Feeder Name", value="", help="Enter the 11kV Feeder Name")
        sub_station = st.text_input("Feeding Substation", value="")
        sub_division = st.text_input("Sub-Division Name", value="")
        division_name = st.text_input("Division Name", value="")
    
    with st.expander("⚡ Electrical Parameters", expanded=True):
        mdi_amps = st.number_input("Max Demand (MDI) in Amps", min_value=0.0, step=0.1, value=0.0)
        num_sections = st.number_input("Total Network Sections", min_value=1, max_value=50, value=1)
        # Power Calculation Formula
        mdi_kva = round(np.sqrt(3) * 11 * mdi_amps, 4)
        st.info(f"**Total MDI:** {mdi_kva} kVA")
    
    st.write("---")
    st.caption(f"App Version: 2.4.0 | Date: {datetime.now().strftime('%d-%m-%Y')}")

# ==========================================
# 5. DATA INPUT ENGINE
# ==========================================
st.subheader("📋 Sectional Configuration & Load Distribution")
st.info("Tip: Start from the Source (A-B) and move towards the Tail node.")

# Generate default labels
labels = [f"{chr(65+i)}-{chr(66+i)}" for i in range(num_sections)]
init_data = pd.DataFrame({
    "SECTION": labels,
    "CONDUCTOR TYPE": [None] * num_sections,
    "DISTANCE (KM)": [0.0] * num_sections,
    "NODE LOAD (kVA)": [0.0] * num_sections
})

# Dynamic Data Editor
edited_df = st.data_editor(
    init_data,
    column_config={
        "SECTION": st.column_config.TextColumn("Span ID", disabled=True),
        "CONDUCTOR TYPE": st.column_config.SelectboxColumn("Conductor/Cable Size", options=list(VD_FACTORS.keys()), required=True),
        "DISTANCE (KM)": st.column_config.NumberColumn("Length (km)", format="%.3f", min_value=0.0),
        "NODE LOAD (kVA)": st.column_config.NumberColumn("Load at Node (kVA)", format="%.1f", min_value=0.0)
    },
    use_container_width=True,
    num_rows="fixed"
)

# ==========================================
# 6. CALCULATION CORE (BACKEND LOGIC)
# ==========================================
if 'res_cache' not in st.session_state: st.session_state.res_cache = None
if 'met_cache' not in st.session_state: st.session_state.met_cache = {}

col_btn1, col_btn2, col_btn3 = st.columns(3)

def perform_calculations():
    with st.spinner("Processing network harmonics and loads..."):
        time.sleep(0.5) # UI Smoothness
        df = edited_df.copy()
        
        # 1. Reverse Summation for Cumulative Load (Tail-to-Source)
        loads = df["NODE LOAD (kVA)"].tolist()
        cum_loads = [0] * len(loads)
        running_sum = 0
        for i in range(len(loads)-1, -1, -1):
            running_sum += loads[i]
            cum_loads[i] = running_sum
            
        df["CUMULATIVE LOAD (kVA)"] = cum_loads
        df["VD FACTOR"] = df["CONDUCTOR TYPE"].map(VD_FACTORS)
        
        # 2. Sectional VD Calculation (Voltage = L * I * Factor)
        df["SECTION VD (V)"] = df["DISTANCE (KM)"] * df["CUMULATIVE LOAD (kVA)"] * df["VD FACTOR"]
        
        # 3. Final Aggregation
        total_sum_vd = df["SECTION VD (V)"].sum()
        max_source_load = cum_loads[0] if cum_loads else 0
        demand_f = mdi_kva / max_source_load if max_source_load > 0 else 0
        actual_vd_volts = total_sum_vd * demand_f
        final_percent = (actual_vd_volts / (11000 - actual_vd_volts) * 100) if (11000 - actual_vd_volts) > 0 else 0
        
        st.session_state.res_cache = df
        st.session_state.met_cache = {
            "sum_vd": total_sum_vd, "max_load": max_source_load, "df": demand_f,
            "actual_
