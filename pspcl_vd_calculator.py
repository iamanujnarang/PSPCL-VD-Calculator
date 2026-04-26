import streamlit as st
import pandas as pd
import math

st.set_page_config(page_title="PSPCL VD Calculator", page_icon="⚡", layout="wide")

# ------------------ STYLE ------------------
st.markdown("""
<style>
.main {background: linear-gradient(135deg, #0f172a, #1e40af);}
h1 {color: #60a5fa; text-align: center;}
.footer {text-align: center; margin-top: 50px; color: #94a3b8;}
.made-with {font-size: 1.5rem; margin: 25px 0;}
</style>
""", unsafe_allow_html=True)

st.title("⚡ PSPCL 11kV Voltage Drop Calculator")

# ------------------ INPUT ------------------
col1, col2 = st.columns([3,1])

with col1:
    feeder_name = st.text_input("Feeder Name", "11kV Feeder")

with col2:
    md_kva = st.number_input("Maximum Demand (kVA)", value=1000.0, step=50.0)

# ------------------ CONDUCTOR DATA ------------------
conductors = {
    "ACSR Weasel": {"R": 1.0209, "X": 0.382},
    "ACSR Rabbit": {"R": 0.6103, "X": 0.372},
    "ACSR Raccoon": {"R": 0.3712, "X": 0.30},
    "ACSR Dog": {"R": 0.2792, "X": 0.29},
    "XLPE 300 Sqmm": {"R": 0.126, "X": 0.10},
    "XLPE 400 Sqmm": {"R": 0.0997, "X": 0.0977}
}

# ------------------ BRANCH INPUT ------------------
num = st.number_input("Number of Sections", min_value=1, max_value=20, value=1)

st.subheader("Section-wise Input")

sections = []
total_load = 0

for i in range(num):
    st.markdown(f"### Section {chr(65+i)} → {chr(66+i)}")
    
    c1, c2, c3 = st.columns(3)

    with c1:
        cond = st.selectbox("Conductor", list(conductors.keys()), key=i)

    with c2:
        length = st.number_input("Length (km)", value=0.5, step=0.1, key=f"l{i}")

    with c3:
        load = st.number_input("Load at this point (kVA)", value=100.0, step=10.0, key=f"ld{i}")

    sections.append({
        "cond": cond,
        "length": length,
        "load": load
    })

# ------------------ CALCULATION ------------------
pf = 0.85
sin_phi = math.sin(math.acos(pf))

remaining_load = md_kva
data = []
total_vd = 0

for i, sec in enumerate(sections):

    r = conductors[sec["cond"]]["R"]
    x = conductors[sec["cond"]]["X"]

    current = (remaining_load * 1000) / (math.sqrt(3) * 11000)

    vd = (math.sqrt(3) * current * sec["length"] * (r * pf + x * sin_phi) * 100) / 11000

    total_vd += vd

    data.append({
        "Section": f"{chr(65+i)}-{chr(66+i)}",
        "Conductor": sec["cond"],
        "Length (km)": sec["length"],
        "Load Flow (kVA)": round(remaining_load,2),
        "R": r,
        "X": x,
        "Current (A)": round(current,2),
        "VD %": round(vd,3),
        "Formula Used": f"√3×{round(current,1)}×{sec['length']}×({r}×0.85 + {x}×{round(sin_phi,2)})"
    })

    # Reduce load for next branch
    remaining_load -= sec["load"]

# ------------------ OUTPUT ------------------
df = pd.DataFrame(data)
st.dataframe(df, use_container_width=True)

st.success(f"Total Voltage Drop = {total_vd:.2f} %")

if total_vd <= 5:
    st.success("✅ Within Limit")
elif total_vd <= 9:
    st.warning("⚠️ Acceptable")
else:
    st.error("❌ Exceeds Limit")

# ------------------ SKETCH ------------------
st.subheader("📍 Feeder Sketch")

sketch = "Substation (11kV)"
for i, row in df.iterrows():
    sketch += f" → [{row['Section']} | {row['Load Flow (kVA)']} kVA]"
sketch += " → End"

st.code(sketch)

# ------------------ FOOTER ------------------
st.markdown("---")
st.markdown("""
<div class="footer">
    <div class="made-with">
        Made with ❤️ by <strong>@iamanujnarang</strong>
    </div>
    <p>
        <a href="https://facebook.com/iamanujnarang" target="_blank">Facebook</a> |
        <a href="https://instagram.com/iamanujnarang" target="_blank">Instagram</a> |
        <a href="https://x.com/iamanujnarang" target="_blank">X</a> |
        <a href="https://linkedin.com/in/iamanujnarang" target="_blank">LinkedIn</a>
    </p>
    <p>
        Powered by <a href="https://beeclue.com/" target="_blank">Beeclue Tech</a>
    </p>
</div>
""", unsafe_allow_html=True)
