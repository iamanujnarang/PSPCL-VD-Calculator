import streamlit as st
import pandas as pd
import numpy as np
import io

# --- PAGE CONFIG ---
st.set_page_config(
    page_title="PSPCL VD Calculator Pro",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- LOGOS & LINKS ---
PSPCL_LOGO = "https://pspcl.in/assets/images/logo.png"
INSTA_ICON = "https://upload.wikimedia.org/wikipedia/commons/a/a5/Instagram_icon.png"
FB_ICON = "https://upload.wikimedia.org/wikipedia/commons/1/1b/Facebook_icon.svg"
X_ICON = "https://upload.wikimedia.org/wikipedia/commons/b/b7/X_logo.jpg"
LINKEDIN_ICON = "https://upload.wikimedia.org/wikipedia/commons/c/ca/LinkedIn_logo_initials.png"

# --- VD FACTORS ---
VD_FACTORS = {
    "ACSR 100 SQMM": 0.0415,
    "ACSR 80 SQMM": 0.0512,
    "ACSR 50 SQMM": 0.0910,
    "ACSR 30 SQMM": 0.1520,
    "ACSR 20 SQMM": 0.2250,
    "XLPE CABLE 300 SQMM": 0.0146,
    "XLPE CABLE 150 SQMM": 0.0285,
    "XLPE CABLE 35 SQMM": 0.1150
}

# --- STYLING ---
st.markdown(f"""
<style>
    .header-box {{
        text-align: center;
        padding: 20px;
        background: white;
        border-radius: 15px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.05);
        margin-bottom: 20px;
    }}
    .footer-container {{
        text-align: center;
        margin-top: 50px;
        padding: 20px;
        border-top: 1px solid #ddd;
    }}
    .social-logo {{
        width: 30px;
        margin: 0 10px;
        vertical-align: middle;
    }}
    .main-logo {{
        width: 120px;
        margin-bottom: 10px;
    }}
</style>
""", unsafe_allow_html=True)

# --- HEADER ---
st.markdown(f"""
<div class="header-box">
    <img src="{PSPCL_LOGO}" class="main-logo">
    <h1 style="color: #004a99; margin:0;">PUNJAB STATE POWER CORPORATION LIMITED</h1>
    <h3 style="color: #555;">11kV Voltage Drop Calculator (Bifurcation Pro)</h3>
</div>
""", unsafe_allow_html=True)

# --- SIDEBAR INPUTS ---
with st.sidebar:
    st.header("⚙️ Configuration")
    feeder_name = st.text_input("Feeder Name", "11kV NEW AMRITSAR")
    sub_division = st.text_input("Sub-Division", "MALL MANDI")
    division = st.text_input("Division", "CITY CENTER")
    
    st.divider()
    num_sections = st.number_input("Number of Sections", min_value=1, max_value=100, value=2)
    
    st.divider()
    st.info("Note: 'Upto Load' is calculated from Tail to Source (Cumulative).")

# --- DATA ENTRY ---
col_main, col_viz = st.columns([3, 1])

with col_main:
    # Auto-generate point labels
    points = [f"{chr(65+i)}-{chr(66+i)}" for i in range(num_sections)]
    
    init_data = pd.DataFrame({
        "POINT": points,
        "CONDUCTOR SIZE": ["ACSR 100 SQMM"] * num_sections,
        "DISTANCE (KM)": [0.5] * num_sections,
        "SECTION WISE LOAD (kVA)": [0.0] * num_sections
    })

    st.subheader("📝 Section Data")
    edited_df = st.data_editor(
        init_data,
        column_config={
            "CONDUCTOR SIZE": st.column_config.SelectboxColumn("CONDUCTOR", options=list(VD_FACTORS.keys()), required=True),
            "DISTANCE (KM)": st.column_config.NumberColumn(min_value=0.0, format="%.3f"),
            "SECTION WISE LOAD (kVA)": st.column_config.NumberColumn(min_value=0.0, format="%.1f")
        },
        use_container_width=True,
        num_rows="dynamic"
    )

    # --- CALCULATION LOGIC (TAIL TO SOURCE) ---
    df = edited_df.copy()
    section_loads = df["SECTION WISE LOAD (kVA)"].tolist()
    upto_loads = [0] * len(section_loads)
    
    # Calculate Upto Load starting from the last row
    running_total = 0
    for i in range(len(section_loads) - 1, -1, -1):
        running_total += section_loads[i]
        upto_loads[i] = running_total
        
    df["UPTO LOAD (kVA)"] = upto_loads
    df["VD FACTOR"] = df["CONDUCTOR SIZE"].map(VD_FACTORS)
    df["TOTAL VOLTAGE DROP (VOLTS)"] = df["DISTANCE (KM)"] * df["UPTO LOAD (kVA)"] * df["VD FACTOR"]

    # Final Totals
    total_vd_v = df["TOTAL VOLTAGE DROP (VOLTS)"].sum()
    vd_percent = (total_vd_v / 11000) * 100

    st.divider()
    st.subheader("📊 Calculation Summary")
    st.dataframe(df, use_container_width=True)

    c1, c2 = st.columns(2)
    c1.metric("Total VD (Volts)", f"{total_vd_v:.3f} V")
    c2.metric("VD Percentage", f"{vd_percent:.3f} %", delta_color="inverse")

with col_viz:
    st.subheader("📍 Feeder Sketch")
    sketch = ["Substation"]
    for p in df["POINT"]:
        sketch.append("   ↓")
        sketch.append(f"[{p}]")
    sketch.append("   Tail")
    st.code("\n".join(sketch))

# --- EXPORT TO CSV (AS PER IMAGE LAYOUT) ---
def convert_df_to_csv(df_final):
    output = io.StringIO()
    # Title Row
    output.write(f"VOLTAGE DROP OF {feeder_name.upper()} FEEDER UNDER {sub_division.upper()} SUB DIVISION UNDER {division.upper()} DIVISION\n")
    # Sub-headers as per image
    output.write("POINT,CONDUCTOR SIZE,DISTANCE (IN KM),SECTION WISE LOAD (kVA),UPTO LOAD (kVA),VD FACTOR,TOTAL VOLTAGE DROP (IN VOLTS)\n")
    output.write("A,B,C,D,E,F,G= (CxExF)\n")
    
    # Data rows
    for index, row in df_final.iterrows():
        output.write(f"{row['POINT']},{row['CONDUCTOR SIZE']},{row['DISTANCE (KM)']},{row['SECTION WISE LOAD (kVA)']},{row['UPTO LOAD (kVA)']},{row['VD FACTOR']},{row['TOTAL VOLTAGE DROP (VOLTS)']}\n")
    
    # Totals and Stamp
    output.write(f"\n,,,,,,TOTAL VD: {total_vd_v:.4f} V\n")
    output.write(f",,,,,,ACTUAL VD %: {vd_percent:.4f}%\n")
    output.write(f"\n\n,,,,,,SDO {sub_division.upper()}\n")
    output.write(f",,,,,,Stamp & Sign\n")
    
    return output.getvalue()

st.download_button(
    label="📥 Download Exported CSV (Official Layout)",
    data=convert_df_to_csv(df),
    file_name=f"VD_Calculation_{feeder_name}.csv",
    mime="text/csv"
)

# --- FOOTER ---
st.markdown(f"""
<div class="footer-container">
    <p>Made with ❤️ by <strong>Anuj Narang</strong></p>
    <div>
        <a href="https://instagram.com/iamanujnarang"><img src="{INSTA_ICON}" class="social-logo"></a>
        <a href="https://facebook.com/iamanujnarang"><img src="{FB_ICON}" class="social-logo"></a>
        <a href="https://x.com/iamanujnarang"><img src="{X_ICON}" class="social-logo"></a>
        <a href="https://linkedin.com/in/iamanujnarang"><img src="{LINKEDIN_ICON}" class="social-logo"></a>
    </div>
    <p style="margin-top:15px;">Powered by <a href="https://beeclue.com" target="_blank">Beeclue Tech</a></p>
</div>
""", unsafe_allow_html=True)
