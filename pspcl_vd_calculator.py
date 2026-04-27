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

# --- STYLING WITH HOVER EFFECTS ---
st.markdown(f"""
<style>
    .header-box {{ text-align: center; padding: 25px; background: white; border-radius: 15px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); margin-bottom: 25px; border-top: 6px solid #ffcc00; }}
    .formula-section {{ background: #ffffff; padding: 30px; border-radius: 15px; border: 1px solid #dee2e6; margin-top: 30px; box-shadow: 0 10px 25px rgba(0,0,0,0.05); }}
    .footer-container {{ text-align: center; margin-top: 60px; padding: 40px; border-top: 1px solid #eee; background: #fdfdfd; }}
    
    /* --- HOVER ANIMATION LOGIC --- */
    .social-logo {{ 
        width: 35px; 
        margin: 0 15px; 
        transition: transform 0.3s ease-in-out, filter 0.3s ease-in-out; 
        cursor: pointer;
    }}
    .social-logo:hover {{ 
        transform: scale(1.3); /* Icon bada ho jayega */
        filter: brightness(1.2); /* Thoda shine karega */
    }}
    
    .stMetric {{ background: #f8f9fa; padding: 15px; border-radius: 10px; border: 1px solid #eee; }}
</style>
""", unsafe_allow_html=True)

# --- HEADER (Professional Word Removed) ---
st.markdown(f'<div class="header-box"><img src="{PSPCL_LOGO}" width="100"><h1>PUNJAB STATE POWER CORPORATION LIMITED</h1><h3>11kV Voltage Drop Calculation Tool</h3></div>', unsafe_allow_html=True)

# --- SIDEBAR ---
with st.sidebar:
    st.header("📝 Feeder Details")
    feeder_name = st.text_input("Feeder Name", placeholder="e.g. 11kV Mall Mandi")
    sub_div = st.text_input("Sub-Division", placeholder="e.g. Mall Mandi")
    div = st.text_input("Division", placeholder="e.g. City Center")
    
    st.divider()
    st.header("⚡ Load & Sections")
    mdi_amps = st.number_input("Max Demand (MDI Amps)", min_value=0.0, value=0.0, step=0.1, format="%.1f")
    num_sections = st.number_input("Number of Sections", min_value=1, max_value=100, value=2)
    
    mdi_kva = round(np.sqrt(3) * 11 * mdi_amps, 4)
    st.success(f"MDI in kVA: {mdi_kva}")

# --- DATA EDITOR ---
st.subheader("📍 Step 1: Sectional Data Entry")
points = []
for i in range(num_sections):
    points.append(f"{chr(65+i)}-{chr(66+i)}")

df_input = pd.DataFrame({
    "POINT": points,
    "CONDUCTOR SIZE": [None] * num_sections,
    "DISTANCE (KM)": [0.0] * num_sections,
    "SECTION LOAD (kVA)": [0.0] * num_sections
})

edited_df = st.data_editor(
    df_input,
    column_config={
        "POINT": st.column_config.TextColumn("Section", disabled=True),
        "CONDUCTOR SIZE": st.column_config.SelectboxColumn("Conductor Type", options=list(VD_FACTORS.keys()), required=True),
        "DISTANCE (KM)": st.column_config.NumberColumn("Length (km)", format="%.3f", min_value=0.0),
        "SECTION LOAD (kVA)": st.column_config.NumberColumn("Tapping Load (kVA)", format="%.1f", min_value=0.0)
    },
    use_container_width=True,
    num_rows="dynamic"
)

# --- CALCULATIONS ---
if st.button("🚀 Calculate Voltage Drop", type="primary"):
    df = edited_df.copy()
    
    # Logic: Tail to Source Cumulative Load
    loads = df["SECTION LOAD (kVA)"].fillna(0).tolist()
    upto_loads = [0] * len(loads)
    temp_sum = 0
    for i in range(len(loads)-1, -1, -1):
        temp_sum += loads[i]
        upto_loads[i] = temp_sum
    
    df["UPTO LOAD (kVA)"] = upto_loads
    df["VD FACTOR"] = df["CONDUCTOR SIZE"].map(VD_FACTORS).fillna(0)
    df["VD (VOLTS)"] = df["DISTANCE (KM)"] * df["UPTO LOAD (kVA)"] * df["VD FACTOR"]
    
    total_vd_v = df["VD (VOLTS)"].sum()
    total_dist = df["DISTANCE (KM)"].sum()
    total_sec_load = df["SECTION LOAD (kVA)"].sum()
    total_load_at_source = upto_loads[0] if len(upto_loads) > 0 else 0
    
    # Formula Calculations
    df_val = mdi_kva / total_load_at_source if total_load_at_source > 0 else 0
    actual_vd_v = total_vd_v * df_val
    denom = (11000 - actual_vd_v)
    vd_percent = (actual_vd_v / denom * 100) if denom > 0 else 0

    # --- TABLE ENHANCEMENT: ADD TOTAL ROW ---
    summary_row = pd.DataFrame({
        "POINT": ["**TOTAL**"],
        "CONDUCTOR SIZE": ["-"],
        "DISTANCE (KM)": [total_dist],
        "SECTION LOAD (kVA)": [total_sec_load],
        "UPTO LOAD (kVA)": [0.0],
        "VD FACTOR": [0.0],
        "VD (VOLTS)": [total_vd_v]
    })
    df_with_total = pd.concat([df, summary_row], ignore_index=True)

    # --- DISPLAY CALCULATION TABLE ---
    st.divider()
    st.subheader("📊 Step 2: Voltage Drop Analysis Table")
    st.dataframe(df_with_total.style.format({
        "DISTANCE (KM)": "{:.3f}", 
        "VD (VOLTS)": "{:.4f}", 
        "UPTO LOAD (kVA)": "{:.2f}",
        "SECTION LOAD (kVA)": "{:.1f}"
    }), use_container_width=True)

    # --- FORMULAS & FINAL RESULTS ---
    st.markdown('<div class="formula-section">', unsafe_allow_html=True)
    st.subheader("🧮 Applied Formulas & Final Summary")
    
    c1, c2, c3 = st.columns(3)
    
    with c1:
        st.info("1. Demand Factor (D.F.)")
        st.latex(r"D.F. = \frac{\sqrt{3} \times 11 \times MDI(A)}{Total\ kVA}")
        st.markdown(f"**Calculation:** {mdi_kva} / {total_load_at_source}")
        st.metric("Result (D.F.)", f"{df_val:.4f}")

    with c2:
        st.info("2. Actual Voltage Drop")
        st.latex(r"Actual\ V.D. = Total\ V.D. \times D.F.")
        st.markdown(f"**Calculation:** {total_vd_v:.2f} × {df_val:.4f}")
        st.metric("Actual VD", f"{actual_vd_v:.2f} Volts")

    with c3:
        st.info("3. Percentage Voltage Drop")
        st.latex(r"\% V.D. = \frac{Actual\ V.D.}{11000 - Actual\ V.D.} \times 100")
        color = "normal" if vd_percent < 9 else "inverse"
        st.metric("Final % VD", f"{vd_percent:.3f}%", delta_color=color)

    st.markdown('</div>', unsafe_allow_html=True)

    # --- EXPORT REPORT ---
    def get_csv():
        output = io.StringIO()
        output.write(f"OFFICIAL VOLTAGE DROP REPORT: {feeder_name.upper()}\n")
        output.write(f"SUB-DIVISION: {sub_div.upper()}, DIVISION: {div.upper()}\n\n")
        df_with_total.to_csv(output, index=False)
        output.write(f"\nTOTAL VD (VOLTS),{total_vd_v:.4f}\n")
        output.write(f"DEMAND FACTOR,{df_val:.4f}\n")
        output.write(f"ACTUAL VD (VOLTS),{actual_vd_v:.4f}\n")
        output.write(f"PERCENTAGE VD (%),{vd_percent:.4f}%\n")
        output.write(f"\n\nSDO {sub_div.upper()}\nStamp & Sign\n")
        return output.getvalue()

    st.download_button("📥 Download Official CSV Report", get_csv(), f"{feeder_name}_VD_Report.csv", "text/csv")

else:
    st.warning("Please fill the data and click 'Calculate Voltage Drop' to see the results.")

# --- UPDATED FOOTER ---
st.markdown(f"""
<div class="footer-container">
    <p style="font-size:1.2em; font-weight:bold; color:#333;">Made with ❤️ by Anuj Narang</p>
    <div style="margin: 25px 0;">
        <a href="https://instagram.com/iamanujnarang" target="_blank"><img src="{INSTA_ICON}" class="social-logo" title="Instagram"></a>
        <a href="https://facebook.com/iamanujnarang" target="_blank"><img src="{FB_ICON}" class="social-logo" title="Facebook"></a>
        <a href="https://x.com/iamanujnarang" target="_blank"><img src="{X_ICON}" class="social-logo" title="X (Twitter)"></a>
        <a href="https://linkedin.com/in/iamanujnarang" target="_blank"><img src="{LINKEDIN_ICON}" class="social-logo" title="LinkedIn"></a>
    </div>
    <p style="color:#666;">Powered by <a href="https://beeclue.com" target="_blank" style="color:#004a99; text-decoration:none; font-weight:bold;">Beeclue Tech</a></p>
</div>
""", unsafe_allow_html=True)
