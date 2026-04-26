import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import math

st.set_page_config(page_title="PSPCL VD Calculator", page_icon="⚡", layout="wide")

st.markdown("""
<style>
    .main {background: linear-gradient(135deg, #0f172a, #1e40af);}
    h1 {color: #60a5fa; text-align: center;}
    .footer {text-align: center; margin-top: 40px; color: #94a3b8;}
    .made-with {font-size: 1.45rem; margin: 20px 0;}
</style>
""", unsafe_allow_html=True)

st.title("⚡ PSPCL Voltage Drop Calculator")
st.subheader("HT 11kV + LT Cables | Branch-wise | Automated Sketch")

tab1, tab2 = st.tabs(["11kV HT Calculation", "LT Cable Calculation"])

# ====================== HT 11kV TAB ======================
with tab1:
    st.markdown("### 11kV Feeder Voltage Drop (Branch-wise)")
    
    col1, col2 = st.columns([2, 1])
    with col1:
        feeder_name = st.text_input("Feeder Name", "Diamond Estate Feeder")
    
    # Predefined Conductor Data from your Excel
    ht_conductors = {
        "ACSR Squirrel": {"R": 1.5388, "X": 0.3915},
        "ACSR Weasel": {"R": 1.0209, "X": 0.382},
        "ACSR Rabbit": {"R": 0.6103, "X": 0.372},
        "ACSR Raccoon": {"R": 0.3712, "X": 0.30},
        "ACSR Dog": {"R": 0.2792, "X": 0.29},
        "XLPE 300 Sqmm": {"R": 0.126, "X": 0.10},
        "XLPE 400 Sqmm": {"R": 0.0997, "X": 0.0977}
    }

    branches = st.number_input("Number of Sections (Branches)", min_value=1, max_value=15, value=8)

    data = []
    total_load = 0.0

    for i in range(branches):
        st.markdown(f"**Section {chr(65+i)}-{chr(66+i)}**")
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            conductor = st.selectbox(f"Conductor", list(ht_conductors.keys()), key=f"cond_{i}")
        with c2:
            length = st.number_input(f"Length (km)", min_value=0.01, value=0.5, step=0.01, key=f"len_{i}")
        with c3:
            section_load = st.number_input(f"Section Load (kVA)", min_value=0.0, value=200.0, step=10.0, key=f"load_{i}")
        with c4:
            dt_size = st.selectbox("DT Size", ["None", "10kVA", "25kVA", "63kVA", "100kVA", "200kVA", "300kVA", "500kVA", "800kVA", "1000kVA"], key=f"dt_{i}")

        r = ht_conductors[conductor]["R"]
        x = ht_conductors[conductor]["X"]
        pf = 0.85
        sin_phi = 0.52

        # Cumulative load from this point onwards
        cum_load = total_load + section_load
        total_load += section_load

        current = (cum_load * 1000) / (math.sqrt(3) * 11000)
        vd_percent = (math.sqrt(3) * current * length * (r * pf + x * sin_phi) * 100) / 11000

        data.append({
            "Section": f"{chr(65+i)}-{chr(66+i)}",
            "Conductor": conductor,
            "Length_km": length,
            "Section_Load_kVA": section_load,
            "Cumulative_kVA": cum_load,
            "VD_%": round(vd_percent, 3)
        })

    df = pd.DataFrame(data)
    st.dataframe(df, use_container_width=True)

    total_vd = df["VD_%"].sum()
    st.success(f"**Total Voltage Drop = {total_vd:.2f} %**")

    if total_vd <= 5:
        st.success("✅ Within Limit")
    elif total_vd <= 9:
        st.warning("⚠️ Acceptable but High")
    else:
        st.error("❌ Exceeds Limit - Augmentation Recommended")

    # Automated Rough Sketch
    st.subheader("📍 Automated Single Line Sketch")
    sketch = "Substation → "
    for row in data:
        sketch += f"[{row['Section']} {row['Conductor'][:8]} ({row['Length_km']}km) "
        if row['Section_Load_kVA'] > 0:
            sketch += f"{int(row['Section_Load_kVA'])}kVA] → "
    sketch += "Tail End"
    st.code(sketch)

# ====================== LT TAB ======================
with tab2:
    st.markdown("### LT Cable Voltage Drop")
    st.info("LT calculation coming in next update (using your LT sheet data). Currently focused on HT.")

# Footer
st.markdown("---")
st.markdown("""
<div class="footer">
    <div class="made-with">
        Made with ❤️ by <strong>@iamanujnarang</strong>
    </div>
    <p>
        Facebook | Instagram | X | LinkedIn → <strong>iamanujnarang</strong>
    </p>
    <p>
        Powered by <a href="https://beeclue.com/" target="_blank" style="color:#60a5fa;">Beeclue Tech</a>
    </p>
</div>
""", unsafe_allow_html=True)
