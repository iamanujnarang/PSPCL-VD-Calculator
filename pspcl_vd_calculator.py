import streamlit as st
import pandas as pd
import numpy as np
import io

# --- PAGE CONFIG ---
st.set_page_config(
    page_title="PSPCL 11kV VD Calculator Pro",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CUSTOM CSS FOR BEST GUI ---
st.markdown("""
<style>
    /* Main Background */
    .stApp {
        background-color: #f4f7f6;
    }
    
    /* Headers */
    h1, h2, h3 {
        color: #003366 !important;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }
    
    /* Branding Header */
    .header-box {
        background-color: #ffffff;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        text-align: center;
        margin-bottom: 25px;
        border-top: 5px solid #ffcc00;
    }
    
    /* Footer Styling */
    .footer {
        text-align: center;
        padding: 40px 20px;
        margin-top: 50px;
        background-color: #ffffff;
        border-top: 1px solid #e0e0e0;
    }
    .footer a {
        text-decoration: none;
        color: #007bff;
        font-weight: bold;
        margin: 0 10px;
    }
    .social-icons {
        font-size: 24px;
        margin-bottom: 10px;
    }

    /* Table Styling */
    .stDataFrame {
        border-radius: 10px;
    }
    
    /* Sidebar Input Styling */
    .css-1d391kg {
        background-color: #003366;
    }
</style>
""", unsafe_allow_html=True)

# --- CONDUCTOR DATA & VD FACTORS ---
# Based on your shared files and standard PSPCL 11kV data
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

# --- HEADER SECTION ---
st.markdown("""
    <div class="header-box">
        <img src="https://upload.wikimedia.org/wikipedia/en/b/b3/PSPCL_Logo.png" width="80">
        <h1>PUNJAB STATE POWER CORPORATION LIMITED</h1>
        <h3>11kV Voltage Drop Calculator - Pro Version</h3>
    </div>
""", unsafe_allow_html=True)

# --- INPUT PANEL ---
with st.sidebar:
    st.header("📋 General Information")
    feeder_name = st.text_input("Feeder Name", "11kV NEW AMRITSAR")
    sub_division = st.text_input("Sub-Division Name", "MALL MANDI")
    
    st.divider()
    st.header("⚡ Load Parameters")
    load_unit = st.radio("Input Maximum Demand in:", ["Amperes (A)", "kVA"])
    
    if load_unit == "Amperes (A)":
        md_amps = st.number_input("Maximum Demand (Amps)", min_value=0.0, value=126.0, step=1.0)
        md_kva = round(np.sqrt(3) * 11 * md_amps, 2)
        st.info(f"Calculated MD: **{md_kva} kVA**")
    else:
        md_kva = st.number_input("Maximum Demand (kVA)", min_value=0.0, value=2400.0, step=10.0)

    num_sections = st.slider("Number of Sections", 1, 100, 10)

# --- MAIN CONTENT ---
col_main, col_sketch = st.columns([3, 1])

with col_main:
    st.subheader("📍 Section-Wise Data Entry")
    
    # Initialize empty lists for data entry
    # Automatically generate point labels like A-B, B-C...
    labels = []
    for i in range(num_sections):
        start = chr(65 + (i % 26))
        end = chr(66 + (i % 26))
        # Handle cases beyond Z if needed, but for now simple alphabets
        labels.append(f"{start}-{end}")

    # Initial data for the editor
    init_df = pd.DataFrame({
        "POINT": labels,
        "CONDUCTOR SIZE": ["XLPE CABLE 300 SQMM"] * num_sections,
        "DISTANCE (KM)": [0.1] * num_sections,
        "SECTION WISE LOAD (kVA)": [0.0] * num_sections
    })

    # Data Editor for User Input
    edited_df = st.data_editor(
        init_df,
        column_config={
            "CONDUCTOR SIZE": st.column_config.SelectboxColumn(
                "CONDUCTOR SIZE",
                options=list(VD_FACTORS.keys()),
                required=True,
            ),
            "DISTANCE (KM)": st.column_config.NumberColumn(format="%.3f"),
            "SECTION WISE LOAD (kVA)": st.column_config.NumberColumn(format="%.1f")
        },
        num_rows="dynamic",
        use_container_width=True
    )

    # --- CALCULATIONS ---
    # Logic: Upto Load = Total MD - Cumulative sum of previous section loads
    df_calc = edited_df.copy()
    
    upto_loads = []
    current_upto = md_kva
    
    for i in range(len(df_calc)):
        upto_loads.append(current_upto)
        # For the next section, subtract the current section's tapping load
        current_upto -= df_calc.iloc[i]["SECTION WISE LOAD (kVA)"]
    
    df_calc["UPTO LOAD (kVA)"] = upto_loads
    df_calc["VD FACTOR"] = df_calc["CONDUCTOR SIZE"].map(VD_FACTORS)
    df_calc["TOTAL VOLTAGE DROP (VOLTS)"] = (
        df_calc["DISTANCE (KM)"] * df_calc["UPTO LOAD (kVA)"] * df_calc["VD FACTOR"]
    )
    
    total_vd_volts = df_calc["TOTAL VOLTAGE DROP (VOLTS)"].sum()
    vd_percentage = (total_vd_volts / 11000) * 100

    # Summary Display
    c1, c2, c3 = st.columns(3)
    c1.metric("Total VD (Volts)", f"{total_vd_volts:.2f} V")
    
    # Status color logic
    status_color = "green" if vd_percentage < 5 else "orange" if vd_percentage < 9 else "red"
    c2.markdown(f"### % Voltage Drop: <span style='color:{status_color}'>{vd_percentage:.3f}%</span>", unsafe_allow_html=True)
    
    if vd_percentage > 9:
        st.error("❌ Voltage drop exceeds permissible limits (9%)!")
    elif vd_percentage > 5:
        st.warning("⚠️ Voltage drop is acceptable but high (>5%).")
    else:
        st.success("✅ Voltage drop is within excellent limits.")

with col_sketch:
    st.subheader("🎨 Live Sketch")
    # Generate simple text-based sketch with arrows
    sketch_lines = ["Substation"]
    for p in df_calc["POINT"]:
        sketch_lines.append(f"   |  ")
        sketch_lines.append(f"   ↓")
        sketch_lines.append(f"({p})")
    sketch_lines.append("   End")
    
    st.code("\n".join(sketch_lines))

# --- REPORT GENERATION ---
st.divider()
st.subheader("📊 Final Calculation Table")
st.dataframe(df_calc, use_container_width=True)

# Export Functionality
def get_csv_report():
    output = io.StringIO()
    # Header logic as per user image
    output.write(f"VOLTAGE DROP OF {feeder_name} FEEDER UNDER {sub_division} SUB DIVISION\n\n")
    df_calc.to_csv(output, index=False)
    output.write(f"\nTOTAL VD (VOLTS),,,,,, {total_vd_volts:.4f}\n")
    output.write(f"ACTUAL VD %,,,,,, {vd_percentage:.4f}%\n\n")
    output.write(f"SDO ________,,,,,, Stamp/Sign\n")
    return output.getvalue()

st.download_button(
    label="📥 Download Pro CSV Report",
    data=get_csv_report(),
    file_name=f"VD_Report_{feeder_name}.csv",
    mime="text/csv",
)

# --- FOOTER ---
st.markdown(f"""
<div class="footer">
    <div class="social-icons">
        <a href="https://instagram.com/iamanujnarang" target="_blank">📸</a>
        <a href="https://facebook.com/iamanujnarang" target="_blank">📘</a>
        <a href="https://x.com/iamanujnarang" target="_blank">🐦</a>
        <a href="https://linkedin.com/in/iamanujnarang" target="_blank">🔗</a>
    </div>
    <p>Made with ❤️ by <strong>Anuj Narang</strong> (@iamanujnarang)</p>
    <p>Powered by <a href="https://beeclue.com/" target="_blank">Beeclue Tech</a></p>
    <p style="font-size: 12px; color: #999;">PSPCL Official Standard Voltage Drop Calculator v2.0</p>
    <br>
    <p><strong>Sub-Division: {sub_division}</strong></p>
    <p><strong>SDO ________________</strong></p>
</div>
""", unsafe_allow_html=True)
