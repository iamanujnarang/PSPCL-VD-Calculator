import streamlit as st
import pandas as pd
import numpy as np
import io

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
    .header-box {{ text-align: center; padding: 25px; background: white; border-radius: 15px; box-shadow: 0 4px 15px rgba(0,0,0,0.05); margin-bottom: 25px; border-top: 6px solid #ffcc00; }}
    .formula-card {{ background: #f8fafc; padding: 20px; border-radius: 12px; border: 1px solid #e2e8f0; border-left: 6px solid #004a99; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.02); }}
    .result-badge {{ padding: 10px 20px; border-radius: 8px; font-weight: bold; font-size: 1.2em; display: inline-block; margin-top: 10px; }}
    .footer-container {{ text-align: center; margin-top: 60px; padding: 30px; border-top: 1px solid #eee; background: #fff; }}
    .social-logo {{ width: 28px; margin: 0 12px; transition: 0.3s; }}
    .social-logo:hover {{ transform: scale(1.1); }}
</style>
""", unsafe_allow_html=True)

# --- HEADER ---
st.markdown(f'<div class="header-box"><img src="{PSPCL_LOGO}" width="110"><h1>PUNJAB STATE POWER CORPORATION LIMITED</h1><h3 style="font-weight:400; color:#666;">Official 11kV Voltage Drop Calculation Tool</h3></div>', unsafe_allow_html=True)

# --- SIDEBAR CONFIG ---
with st.sidebar:
    st.header("🏢 Office Info")
    feeder_name = st.text_input("Feeder Name", placeholder="e.g. 11kV New Amritsar")
    sub_division = st.text_input("Sub-Division", placeholder="e.g. Mall Mandi")
    division = st.text_input("Division", placeholder="e.g. City Center")
    
    st.divider()
    st.header("⚡ Load Parameters")
    mdi_amps = st.number_input("Max Demand (MDI in Amps)", min_value=0.0, step=0.5, format="%.1f")
    # Calculation for display
    mdi_kva_calc = round(np.sqrt(3) * 11 * mdi_amps, 2)
    st.info(f"Equivalent Load: **{mdi_kva_calc} kVA**")
    
    st.divider()
    num_sections = st.number_input("Default Sections", min_value=1, max_value=100, value=2)

# --- MAIN DATA ENTRY ---
st.subheader("📋 Step 1: Enter Section Data (Source to Tail)")
# Note: User enters source to tail, we calculate tail to source for Upto Load
points = [f"{chr(65+i)}-{chr(66+i)}" for i in range(num_sections)]
init_data = pd.DataFrame({
    "POINT": points,
    "CONDUCTOR SIZE": [None] * num_sections,
    "DISTANCE (KM)": [0.0] * num_sections,
    "SECTION WISE LOAD (kVA)": [0.0] * num_sections
})

# Grid Layout for Editor and Sketch
col_ed, col_sk = st.columns([3, 1])

with col_ed:
    edited_df = st.data_editor(
        init_data,
        column_config={
            "POINT": st.column_config.TextColumn("POINT", disabled=True),
            "CONDUCTOR SIZE": st.column_config.SelectboxColumn("CONDUCTOR", options=list(VD_FACTORS.keys()), required=True),
            "DISTANCE (KM)": st.column_config.NumberColumn(format="%.3f"),
            "SECTION WISE LOAD (kVA)": st.column_config.NumberColumn(format="%.1f")
        },
        use_container_width=True, num_rows="dynamic"
    )

with col_sk:
    st.markdown("**Feeder Flow**")
    sketch = ["⚡ S/Stn"]
    for p in edited_df["POINT"]:
        sketch.append("  ↓")
        sketch.append(f"[{p}]")
    sketch.append("  🔚 End")
    st.code("\n".join(sketch))

# --- CALCULATION CORE ---
df = edited_df.copy()
# Tail-to-Source Cumulative Load
sec_loads = df["SECTION WISE LOAD (kVA)"].fillna(0).tolist()
upto_loads = [0] * len(sec_loads)
running_total = 0
for i in range(len(sec_loads) - 1, -1, -1):
    running_total += sec_loads[i]
    upto_loads[i] = running_total

df["UPTO LOAD (kVA)"] = upto_loads
df["VD FACTOR"] = df["CONDUCTOR SIZE"].map(VD_FACTORS).fillna(0)
df["VD (VOLTS)"] = df["DISTANCE (KM)"] * df["UPTO LOAD (kVA)"] * df["VD FACTOR"]

# Final Math
total_vd_v = df["VD (VOLTS)"].sum()
# Demand Factor = (sqrt(3)*11*MDI) / Total Load at A-B
total_kw_at_source = upto_loads[0] if len(upto_loads) > 0 else 0
demand_factor = mdi_kva_calc / total_kw_at_source if total_kw_at_source > 0 else 0

actual_vd = total_vd_v * demand_factor
vd_denominator = (11000 - actual_vd)
vd_percent = (actual_vd / vd_denominator * 100) if vd_denominator > 0 else 0

# --- BOTTOM SUMMARY SECTION ---
st.divider()
st.subheader("📊 Step 2: Calculation Results & Formulas")

# Display Result Table first
st.dataframe(df.style.format({"DISTANCE (KM)": "{:.3f}", "UPTO LOAD (kVA)": "{:.1f}", "VD (VOLTS)": "{:.4f}"}), use_container_width=True)

# Formulas Section at the Bottom
f_col1, f_col2, f_col3 = st.columns(3)

with f_col1:
    st.markdown(f"""
    <div class="formula-card">
        <b>1. Demand Factor (D.F.)</b><br>
        $$\\text{{D.F.}} = \\frac{{\\sqrt{{3}} \\times 11 \\times {mdi_amps}}}{{{total_kw_at_source}}}$$
        <div class="result-badge" style="background:#e0f2fe; color:#0369a1;">Result: {demand_factor:.4f}</div>
    </div>
    """, unsafe_allow_html=True)

with f_col2:
    st.markdown(f"""
    <div class="formula-card">
        <b>2. Actual Voltage Drop</b><br>
        $$\\text{{Actual V.D.}} = {total_vd_v:.2f} \\times {demand_factor:.4f}$$
        <div class="result-badge" style="background:#fef3c7; color:#92400e;">Result: {actual_vd:.2f} V</div>
    </div>
    """, unsafe_allow_html=True)

with f_col3:
    status_bg = "#dcfce7" if vd_percent < 9 else "#fee2e2"
    status_text = "#166534" if vd_percent < 9 else "#991b1b"
    st.markdown(f"""
    <div class="formula-card">
        <b>3. Percentage Voltage Drop</b><br>
        $$\\% \\text{{V.D.}} = \\frac{{{actual_vd:.2f}}}{{11000 - {actual_vd:.2f}}} \\times 100$$
        <div class="result-badge" style="background:{status_bg}; color:{status_text};">Final: {vd_percent:.3f}%</div>
    </div>
    """, unsafe_allow_html=True)

# --- EXPORT TO CSV ---
def convert_to_csv():
    output = io.StringIO()
    output.write(f"VOLTAGE DROP CALCULATION OF {feeder_name.upper()} FEEDER UNDER {sub_division.upper()} SUB DIVISION\n")
    output.write("POINT,CONDUCTOR SIZE,DISTANCE (IN KM),SECTION WISE LOAD (kVA),UPTO LOAD (kVA),VD FACTOR,TOTAL VOLTAGE DROP (IN VOLTS)\n")
    output.write("A,B,C,D,E,F,G= (CxExF)\n")
    for _, r in df.iterrows():
        output.write(f"{r['POINT']},{r['CONDUCTOR SIZE']},{r['DISTANCE (KM)']},{r['SECTION WISE LOAD (kVA)']},{r['UPTO LOAD (kVA)']},{r['VD FACTOR']},{r['VD (VOLTS)']}\n")
    output.write(f"\n,,,,,,TOTAL VD (VOLTS): {total_vd_v:.4f}\n")
    output.write(f",,,,,,DEMAND FACTOR: {demand_factor:.4f}\n")
    output.write(f",,,,,,ACTUAL VD (VOLTS): {actual_vd:.4f}\n")
    output.write(f",,,,,,PERCENTAGE VD (%): {vd_percent:.4f}%\n")
    output.write(f"\n\n,,,,,,SDO {sub_division.upper()}\n")
    output.write(",,,,,,Stamp & Sign\n")
    return output.getvalue()

st.download_button(
    label="📥 Download Official PSPCL Report (CSV)",
    data=convert_to_csv(),
    file_name=f"VD_Report_{feeder_name}.csv",
    mime="text/csv",
)

# --- FOOTER ---
st.markdown(f"""
<div class="footer-container">
    <p style="font-size:1.1em;">Made with ❤️ by <b>Anuj Narang</b></p>
    <div>
        <a href="https://instagram.com/iamanujnarang" target="_blank"><img src="{INSTA_ICON}" class="social-logo"></a>
        <a href="https://facebook.com/iamanujnarang" target="_blank"><img src="{FB_ICON}" class="social-logo"></a>
        <a href="https://x.com/iamanujnarang" target="_blank"><img src="{X_ICON}" class="social-logo"></a>
        <a href="https://linkedin.com/in/iamanujnarang" target="_blank"><img src="{LINKEDIN_ICON}" class="social-logo"></a>
    </div>
    <p style="margin-top:20px; color:#888;">Powered by <a href="https://beeclue.com" target="_blank" style="color:#004a99; text-decoration:none;"><b>Beeclue Tech</b></a></p>
</div>
""", unsafe_allow_html=True)
