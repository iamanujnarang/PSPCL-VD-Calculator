import streamlit as st
import pandas as pd
import numpy as np
import io

# --- PAGE CONFIG ---
st.set_page_config(page_title="PSPCL VD Calculator Pro", page_icon="⚡", layout="wide")

# --- LOGOS & LINKS ---
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
    .header-box {{ text-align: center; padding: 20px; background: white; border-radius: 15px; box-shadow: 0 4px 15px rgba(0,0,0,0.05); margin-bottom: 20px; border-top: 5px solid #ffcc00; }}
    .footer-container {{ text-align: center; margin-top: 50px; padding: 20px; border-top: 1px solid #ddd; }}
    .social-logo {{ width: 25px; margin: 0 10px; }}
    .formula-card {{ background: #f0f4f8; padding: 15px; border-radius: 10px; border-left: 5px solid #004a99; margin-bottom: 20px; }}
</style>
""", unsafe_allow_html=True)

# --- HEADER ---
st.markdown(f'<div class="header-box"><img src="{PSPCL_LOGO}" width="100"><h1>PUNJAB STATE POWER CORPORATION LIMITED</h1><h3>11kV Voltage Drop Pro Tool</h3></div>', unsafe_allow_html=True)

# --- SIDEBAR & INPUTS ---
with st.sidebar:
    st.header("📋 Feeder Details")
    feeder_name = st.text_input("Feeder Name", "")
    sub_division = st.text_input("Sub-Division", "")
    division = st.text_input("Division", "")
    
    st.divider()
    st.header("⚡ Load Parameters")
    mdi_amps = st.number_input("Max Demand (MDI in Amps)", min_value=0.0, value=0.0, step=1.0)
    # kVA from Amps for Demand Factor numerator
    mdi_kva = round(np.sqrt(3) * 11 * mdi_amps, 2)
    st.caption(f"Equivalent MDI: {mdi_kva} kVA")
    
    st.divider()
    num_sections = st.number_input("Number of Sections", min_value=1, max_value=100, value=2)

# --- DATA ENTRY ---
col_main, col_formula = st.columns([2.5, 1.5])

with col_main:
    st.subheader("📝 Section Data (Tail to Source)")
    points = [f"{chr(65+i)}-{chr(66+i)}" for i in range(num_sections)]
    init_data = pd.DataFrame({
        "POINT": points,
        "CONDUCTOR SIZE": [None] * num_sections,
        "DISTANCE (KM)": [0.0] * num_sections,
        "SECTION WISE LOAD (kVA)": [0.0] * num_sections
    })

    edited_df = st.data_editor(
        init_data,
        column_config={
            "CONDUCTOR SIZE": st.column_config.SelectboxColumn("CONDUCTOR", options=list(VD_FACTORS.keys()), required=True),
            "DISTANCE (KM)": st.column_config.NumberColumn(format="%.3f"),
            "SECTION WISE LOAD (kVA)": st.column_config.NumberColumn(format="%.1f")
        },
        use_container_width=True, num_rows="dynamic"
    )

    # --- CALCULATION LOGIC ---
    df = edited_df.copy()
    section_loads = df["SECTION WISE LOAD (kVA)"].tolist()
    upto_loads = [0] * len(section_loads)
    
    running_total = 0
    for i in range(len(section_loads) - 1, -1, -1):
        running_total += section_loads[i]
        upto_loads[i] = running_total
        
    df["UPTO LOAD (kVA)"] = upto_loads
    df["VD FACTOR"] = df["CONDUCTOR SIZE"].map(VD_FACTORS)
    df["VD (VOLTS)"] = df["DISTANCE (KM)"] * df["UPTO LOAD (kVA)"] * df["VD FACTOR"]

    total_vd_v = df["VD (VOLTS)"].sum()
    
    # Demand Factor Logic: MDI kVA / Section A-B Upto Load
    total_kw_kva = upto_loads[0] if len(upto_loads) > 0 else 1
    demand_factor = mdi_kva / total_kw_kva if total_kw_kva > 0 else 0
    
    actual_vd = total_vd_v * demand_factor
    # Formula: %VD = (Actual VD / (11000 - Actual VD)) * 100
    denom = (11000 - actual_vd)
    vd_percent = (actual_vd / denom * 100) if denom > 0 else 0

with col_formula:
    st.subheader("🔹 Formulas Applied")
    st.markdown(f"""
    <div class="formula-card">
        <b>1. Demand Factor (D.F.)</b><br>
        $$\\text{{D.F.}} = \\frac{{\\sqrt{{3}} \\times 11 \\times \\text{{MDI (Amps)}}}}{{\\text{{Section A-B Upto Load}}}}$$
        <small>Result: {demand_factor:.4f}</small>
    </div>
    <div class="formula-card">
        <b>2. Actual Voltage Drop</b><br>
        $$\\text{{Actual V.D.}} = \\text{{Total V.D.}} \\times \\text{{D.F.}}$$
        <small>Result: {actual_vd:.2f} Volts</small>
    </div>
    <div class="formula-card">
        <b>3. Percentage Voltage Drop</b><br>
        $$\\% \\text{{V.D.}} = \\frac{{\\text{{Actual V.D.}}}}{{11000 - \\text{{Actual V.D.}}}} \\times 100$$
        <small>Final Result: <b>{vd_percent:.3f}%</b></small>
    </div>
    """, unsafe_allow_html=True)

# --- RESULTS TABLE ---
st.divider()
st.subheader("📊 Final Calculation Table")
st.dataframe(df, use_container_width=True)

# --- EXPORT LOGIC ---
def convert_to_csv():
    output = io.StringIO()
    output.write(f"VOLTAGE DROP CALCULATION REPORT - {feeder_name.upper()}\n")
    output.write(f"SUB DIVISION: {sub_division.upper()}, DIVISION: {division.upper()}\n\n")
    output.write("POINT,CONDUCTOR SIZE,DISTANCE (KM),SECTION LOAD (kVA),UPTO LOAD (kVA),VD FACTOR,TOTAL VD (VOLTS)\n")
    for _, r in df.iterrows():
        output.write(f"{r['POINT']},{r['CONDUCTOR SIZE']},{r['DISTANCE (KM)']},{r['SECTION WISE LOAD (kVA)']},{r['UPTO LOAD (kVA)']},{r['VD FACTOR']},{r['VD (VOLTS)']}\n")
    
    output.write(f"\nMAX DEMAND (MDI Amps),{mdi_amps}\n")
    output.write(f"TOTAL VD (VOLTS),{total_vd_v:.4f}\n")
    output.write(f"DEMAND FACTOR,{demand_factor:.4f}\n")
    output.write(f"ACTUAL VD (VOLTS),{actual_vd:.4f}\n")
    output.write(f"PERCENTAGE VD (%),{vd_percent:.4f}%\n")
    output.write(f"\n\nSDO {sub_division.upper()}\nStamp & Sign\n")
    return output.getvalue()

st.download_button("📥 Download Official CSV Report", convert_to_csv(), f"VD_Report_{feeder_name}.csv", "text/csv")

# --- FOOTER ---
st.markdown(f"""
<div class="footer-container">
    <p>Made with ❤️ by <b>Anuj Narang</b></p>
    <div>
        <a href="https://instagram.com/iamanujnarang"><img src="{INSTA_ICON}" class="social-logo"></a>
        <a href="https://facebook.com/iamanujnarang"><img src="{FB_ICON}" class="social-logo"></a>
        <a href="https://x.com/iamanujnarang"><img src="{X_ICON}" class="social-logo"></a>
        <a href="https://linkedin.com/in/iamanujnarang"><img src="{LINKEDIN_ICON}" class="social-logo"></a>
    </div>
    <p style="margin-top:10px; font-size: 0.9em;">Powered by <a href="https://beeclue.com" target="_blank">Beeclue Tech</a></p>
</div>
""", unsafe_allow_html=True)
