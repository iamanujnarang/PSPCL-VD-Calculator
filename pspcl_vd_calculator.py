import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import math

st.set_page_config(page_title="PSPCL VD Calculator", page_icon="⚡", layout="centered")

# Custom CSS for modern look
st.markdown("""
<style>
    .main {background: linear-gradient(135deg, #0f172a, #1e3a8a);}
    .stApp {background: transparent;}
    h1 {color: #60a5fa; text-align: center;}
    .footer {text-align: center; margin-top: 50px; padding: 20px; color: #94a3b8;}
    .made-with {font-size: 1.3rem; margin: 25px 0;}
</style>
""", unsafe_allow_html=True)

st.title("⚡ PSPCL 11kV Voltage Drop Calculator")
st.markdown("### Accurate Calculation with Reactance | As per PSPCL Guidelines")

# Input Section
col1, col2 = st.columns(2)

with col1:
    feeder_name = st.text_input("Feeder Name", placeholder="e.g. Ludhiana Industrial Feeder")
    demand_kva = st.number_input("Maximum Demand on Feeder (kVA)", min_value=10.0, value=500.0, step=10.0)
    length_km = st.number_input("Length of Feeder (km)", min_value=0.1, value=5.0, step=0.1)

with col2:
    pf = st.slider("Power Factor (cosφ)", min_value=0.70, max_value=0.99, value=0.85, step=0.01)
    conductor = st.selectbox("Conductor Type", 
                             ["Weasel", "Rabbit", "Raccoon", "Dog"])

# Conductor Data (R + X values at 50Hz typical for 11kV)
conductor_data = {
    "Weasel":  {"R": 0.9289, "X": 0.35},
    "Rabbit":  {"R": 0.5524, "X": 0.32},
    "Raccoon": {"R": 0.3712, "X": 0.30},
    "Dog":     {"R": 0.2792, "X": 0.29}
}

data = conductor_data[conductor]
R = data["R"]   # ohm/km
X = data["X"]   # ohm/km (approximate inductive reactance)

# Calculation
current = (demand_kva * 1000) / (math.sqrt(3) * 11000)
z_eff = math.sqrt(R**2 + X**2)                     # impedance
vd_volts = math.sqrt(3) * current * length_km * (R * pf + X * math.sin(math.acos(pf)))
vd_percent = (vd_volts / 11000) * 100

# Status
if vd_percent <= 5.0:
    status = "✅ Excellent - Well within limit"
    color = "green"
elif vd_percent <= 9.0:
    status = "⚠️ Acceptable but monitor"
    color = "orange"
else:
    status = "❌ High Voltage Drop - Feeder augmentation recommended"
    color = "red"

# Display Results
st.success(f"**Voltage Drop = {vd_percent:.2f} %**")

st.markdown(f"<h3 style='color:{color}; text-align:center;'>{status}</h3>", unsafe_allow_html=True)

col_a, col_b, col_c = st.columns(3)
with col_a:
    st.metric("Current", f"{current:.1f} A")
with col_b:
    st.metric("Resistance", f"{R:.4f} Ω/km")
with col_c:
    st.metric("Reactance", f"{X:.2f} Ω/km")

# Graphs
st.subheader("📊 Visual Analysis")

fig1 = go.Figure(go.Bar(
    x=["Voltage Drop %"],
    y=[vd_percent],
    marker_color=color,
    text=[f"{vd_percent:.2f}%"],
    textposition="auto"
))
fig1.update_layout(title="Voltage Drop Percentage", yaxis_range=[0, max(12, vd_percent+2)], height=300)
st.plotly_chart(fig1, use_container_width=True)

# Pie Chart
fig2 = px.pie(values=[vd_percent, 100-vd_percent], 
              names=["Drop", "Remaining"], 
              title="Voltage Drop vs Available Voltage",
              color_discrete_sequence=[color, "#64748b"])
st.plotly_chart(fig2, use_container_width=True)

# Rough Feeder Sketch
st.subheader("📍 Rough Feeder Sketch")
st.markdown(f"""
Substation (11kV) ───────────────────────────────► Consumer End
{conductor} Conductor   ({length_km} km)
⚡ Source Voltage: 11,000 V
📉 Voltage at End : {11000 - vd_volts:.0f} V   ({vd_percent:.1f}% Drop)
""")

# AI Insight
st.subheader("🤖 AI Insight & Recommendation")
if vd_percent > 9:
    st.error("This feeder may cause low voltage complaints. PSPCL usually recommends augmentation if drop >9%.")
elif vd_percent > 5:
    st.warning("Voltage is acceptable but on the higher side. Consider load management or future augmentation.")
else:
    st.success("Voltage profile is good. No immediate action required.")

st.info(f"**Tip:** For more accurate results in official submissions, use PSPCL's official tool along with this calculator.")

# Footer
st.markdown("---")
st.markdown("""
<div class="footer">
    <div class="made-with">
        Made with ❤️ by <strong>@iamanujnarang</strong>
    </div>
    <p>
        <a href="https://facebook.com/iamanujnarang" target="_blank">Facebook</a> |
        <a href="https://instagram.com/iamanujnarang" target="_blank">Instagram</a> |
        <a href="https://x.com/iamanujnarang" target="_blank">X (Twitter)</a> |
        <a href="https://linkedin.com/in/iamanujnarang" target="_blank">LinkedIn</a>
    </p>
    <p>
        Powered by <a href="https://beeclue.com/" target="_blank" style="color:#60a5fa;">Beeclue Tech</a>
    </p>
</div>
""", unsafe_allow_html=True)
