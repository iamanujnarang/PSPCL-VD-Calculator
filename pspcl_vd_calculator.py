import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import math

st.set_page_config(page_title="PSPCL VD Calculator", page_icon="⚡", layout="centered")

# Modern Custom Styling
st.markdown("""
<style>
    .main {background: linear-gradient(135deg, #0f172a 0%, #1e40af 100%);}
    h1 {color: #60a5fa; text-align: center;}
    .footer {text-align: center; margin-top: 60px; color: #94a3b8;}
    .made-with {font-size: 1.4rem; margin: 25px 0 15px 0;}
</style>
""", unsafe_allow_html=True)

st.title("⚡ PSPCL 11kV Voltage Drop Calculator")
st.markdown("**Accurate Calculation with Reactance + Graphs + AI Insight**")

# Input Section
col1, col2 = st.columns(2)

with col1:
    feeder_name = st.text_input("Feeder Name", placeholder="e.g. Ludhiana Industrial Feeder")
    demand_kva = st.number_input("Maximum Demand (kVA)", min_value=10.0, value=500.0, step=10.0)
    length_km = st.number_input("Feeder Length (km)", min_value=0.1, value=5.0, step=0.1)

with col2:
    pf = st.slider("Power Factor", 0.70, 0.99, 0.85, 0.01)
    conductor = st.selectbox("Conductor Type", ["Weasel", "Rabbit", "Raccoon", "Dog"])

# Conductor Data (R + X in Ω/km)
conductor_data = {
    "Weasel":  {"R": 0.9289, "X": 0.35},
    "Rabbit":  {"R": 0.5524, "X": 0.32},
    "Raccoon": {"R": 0.3712, "X": 0.30},
    "Dog":     {"R": 0.2792, "X": 0.29}
}

data = conductor_data[conductor]
R, X = data["R"], data["X"]

# Calculation
current = (demand_kva * 1000) / (math.sqrt(3) * 11000)
vd_volts = math.sqrt(3) * current * length_km * (R * pf + X * math.sin(math.acos(pf)))
vd_percent = (vd_volts / 11000) * 100

# Status
if vd_percent <= 5.0:
    status_color = "green"
    status = "✅ Excellent - Well within PSPCL Limit"
elif vd_percent <= 9.0:
    status_color = "orange"
    status = "⚠️ Acceptable but High"
else:
    status_color = "red"
    status = "❌ High Voltage Drop - Feeder Augmentation Recommended"

# Results
st.success(f"**Voltage Drop = {vd_percent:.2f} %**")
st.markdown(f"<h3 style='color:{status_color}; text-align:center;'>{status}</h3>", unsafe_allow_html=True)

# Metrics
c1, c2, c3 = st.columns(3)
c1.metric("Current", f"{current:.1f} A")
c2.metric("Resistance", f"{R:.4f} Ω/km")
c3.metric("Reactance", f"{X:.2f} Ω/km")

# Graphs
st.subheader("📊 Voltage Drop Analysis")

fig1 = go.Figure(go.Bar(x=["Voltage Drop"], y=[vd_percent], marker_color=status_color))
fig1.update_layout(yaxis_range=[0, max(12, vd_percent + 3)], height=350)
st.plotly_chart(fig1, use_container_width=True)

fig2 = px.pie(values=[vd_percent, 100 - vd_percent], names=["Drop", "Remaining Voltage"],
              title="Voltage Drop Distribution", color_discrete_sequence=[status_color, "#64748b"])
st.plotly_chart(fig2, use_container_width=True)

# Rough Sketch
st.subheader("📍 Rough Feeder Sketch")
st.markdown(f"""
Substation (11 kV) ───────────────────────────────► Consumer End
{conductor} Conductor   ({length_km} km)
Voltage at Consumer End ≈ {11000 - vd_volts:.0f} V
text""")

# AI Insight
st.subheader("🤖 AI Recommendation")
if vd_percent > 9:
    st.error("This level of voltage drop usually causes complaints. PSPCL may ask for feeder augmentation or new substation.")
elif vd_percent > 5:
    st.warning("Voltage is acceptable but on the higher side. Plan for future load growth.")
else:
    st.success("Voltage profile is good. No immediate action needed.")

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
        <a href="https://x.com/iamanujnarang" target="_blank">X</a> |
        <a href="https://linkedin.com/in/iamanujnarang" target="_blank">LinkedIn</a>
    </p>
    <p>
        Powered by <a href="https://beeclue.com/" target="_blank" style="color:#60a5fa;">Beeclue Tech</a>
    </p>
</div>
""", unsafe_allow_html=True)
