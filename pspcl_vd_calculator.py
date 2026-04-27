import streamlit as st
import pandas as pd
import math
import matplotlib.pyplot as plt
from io import BytesIO

st.set_page_config(page_title="PSPCL VD Tool FINAL", page_icon="⚡", layout="wide")

st.title("⚡ PSPCL 11kV Voltage Drop Calculator – FINAL TOOL")

# ---------------- VD FACTORS ----------------
vd_factors = {
    "ACSR 13": 0.1333,
    "ACSR 20/30": 0.0991,
    "ACSR 30/50": 0.0662,
    "ACSR 48/80": 0.0499,
    "ACSR 65/100": 0.0415,
    "XLPE 300": 0.0142,
    "XLPE 150": 0.0257,
    "XLPE 35": 0.0948
}

# ---------------- FUNCTION ----------------
def calculate_vd(df, md_amp, total_kva):
    total_vd = 0
    vd_list = []
    dist_cum = []

    cum_dist = 0

    for i, row in df.iterrows():
        vd = row["Length"] * row["Load"] * row["VD Factor"]
        total_vd += vd
        cum_dist += row["Length"]

        vd_list.append(total_vd)
        dist_cum.append(cum_dist)

    df_val = (math.sqrt(3) * 11 * md_amp) / total_kva
    actual_vd = total_vd * df_val
    percent_vd = (actual_vd / (11000 - actual_vd)) * 100

    return total_vd, actual_vd, percent_vd, vd_list, dist_cum

# ---------------- FILE UPLOAD ----------------
st.header("📂 Upload Feeder Data")

file = st.file_uploader("Upload Excel (Your Format)", type=["xlsx"])

md_amp = st.number_input("Maximum Demand (Amp)", value=100.0)
total_kva = st.number_input("Total Connected Load (kVA)", value=1000.0)

if file:
    df = pd.read_excel(file)

    st.subheader("📊 Raw Data")
    st.dataframe(df)

    # Auto column detection
    cols = df.columns.str.lower()

    length_col = [c for c in df.columns if "length" in c.lower()][0]
    load_col = [c for c in df.columns if "load" in c.lower()][0]
    vd_col = [c for c in df.columns if "vd" in c.lower()][0]

    df_calc = pd.DataFrame({
        "Length": df[length_col],
        "Load": df[load_col],
        "VD Factor": df[vd_col]
    })

    # ---------------- CALCULATE ----------------
    total_vd, actual_vd, percent_vd, vd_list, dist = calculate_vd(df_calc, md_amp, total_kva)

    st.success(f"Actual VD = {actual_vd:.2f} V")
    st.success(f"% Voltage Drop = {percent_vd:.2f}%")

    # ---------------- GRAPH ----------------
    st.subheader("📈 Voltage Profile")

    fig, ax = plt.subplots()
    ax.plot(dist, vd_list)
    ax.set_xlabel("Distance (km)")
    ax.set_ylabel("Voltage Drop (Volts)")
    ax.set_title("VD Profile")
    st.pyplot(fig)

    # ---------------- SUGGESTION ----------------
    st.subheader("🧠 Smart Suggestion")

    if percent_vd > 5:
        st.error("❌ VD High → Suggest Bifurcation / Conductor Upgrade")
    else:
        st.success("✅ System within limits")

    # ---------------- REPORT ----------------
    output = BytesIO()
    report = pd.DataFrame({
        "Total VD": [total_vd],
        "Actual VD": [actual_vd],
        "%VD": [percent_vd]
    })

    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, sheet_name="Input")
        report.to_excel(writer, sheet_name="Result")

    st.download_button("📥 Download Report", output.getvalue(), "PSPCL_VD_Report.xlsx")

# ---------------- COMPARISON TOOL ----------------
st.header("🔁 Before vs After Comparison")

file1 = st.file_uploader("Upload BEFORE Excel", type=["xlsx"], key="b")
file2 = st.file_uploader("Upload AFTER Excel", type=["xlsx"], key="a")

if file1 and file2:
    df1 = pd.read_excel(file1)
    df2 = pd.read_excel(file2)

    # simple VD compare (assumes same format)
    vd1 = df1.iloc[:, -1].sum()
    vd2 = df2.iloc[:, -1].sum()

    st.write(f"Before VD: {vd1}")
    st.write(f"After VD: {vd2}")

    fig, ax = plt.subplots()
    ax.bar(["Before", "After"], [vd1, vd2])
    st.pyplot(fig)

# ---------------- SKETCH ----------------
st.header("🗺️ Auto Feeder Sketch")

if st.button("Generate Sketch"):
    sketch = "🔌 Substation"
    for i in range(10):
        sketch += f" → {chr(65+i)}"
    sketch += " → End"
    st.code(sketch)

# ---------------- FOOTER ----------------
st.markdown("---")
st.markdown("""
<div style="text-align:center;">
Made with ❤️ by <b>@iamanujnarang</b><br>
Powered by Beeclue Tech
</div>
""", unsafe_allow_html=True)
