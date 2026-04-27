import streamlit as st
import pandas as pd
import numpy as np
import io
import graphviz

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
    .header-box {{ text-align: center; padding: 25px; background: white; border-radius: 15px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); margin-bottom: 25px; border-top: 6px solid #ffcc00; }}
    .formula-section {{ background: #ffffff; padding: 30px; border-radius: 15px; border: 1px solid #dee2e6; margin-top: 30px; box-shadow: 0 10px 25px rgba(0,0,0,0.05); }}
    .sketch-section {{ background: #fdfdfd; padding: 20px; border-radius: 15px; border: 2px solid #eee; margin-top: 20px; text-align: center; }}
    .footer-container {{ text-align: center; margin-top: 60px; padding: 40px; border-top: 1px solid #eee; background: #fdfdfd; }}
    .social-logo {{ width: 35px; margin: 0 15px; transition: transform 0.3s ease-in-out; cursor: pointer; }}
    .social-logo:hover {{ transform: scale(1.3); }}
    .stMetric {{ background: #f8f9fa; padding: 15px; border-radius: 10px; border: 1px solid #eee; }}
</style>
""", unsafe_allow_html=True)

# --- HEADER ---
st.markdown(f'<div class="header-box"><img src="{PSPCL_LOGO}" width="100"><h1>PUNJAB STATE POWER CORPORATION LIMITED</h1><h3>11kV Voltage Drop Calculation Tool</h3></div>', unsafe_allow_html=True)

# --- SIDEBAR ---
with st.sidebar:
    st.header("📝 Feeder Details")
    feeder_name = st.text_input("Feeder Name", placeholder="e.g. 11kV Mall Mandi")
    substation_name = st.text_input("Feeding Substation", placeholder="e.g. 66kV Mall Mandi")
    sub_div = st.text_input("Sub-Division", placeholder="e.g. Mall Mandi")
    div = st.text_input("Division", placeholder="e.g. City Center")
    
    st.divider()
    st.header("⚡ Load & Sections")
    mdi_amps = st.number_input("Max Demand (MDI Amps)", min_value=0.0, value=0.0, step=0.1, format="%.1f")
    num_sections = st.number_input("Number of Sections", min_value=1, max_value=100, value=2)
    
    mdi_kva = round(np.sqrt(3) * 11 * mdi_amps, 4)
    st.success(f"MDI in kVA: {mdi_kva}")

# --- DATA EDITOR (FIXED SECTION LOGIC) ---
st.subheader("📍 Step 1: Sectional Data Entry")
# Generate labels A-B, B-C, etc. based strictly on num_sections
points = [f"{chr(65+i)}-{chr(66+i)}" for i in range(num_sections)]

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
    num_rows="fixed" # Prevents extra ghost rows
)

# Initialize Session State for dataframe to persist between button clicks
if 'calculated_df' not in st.session_state:
    st.session_state.calculated_df = None

# --- CALCULATIONS ---
col_calc, col_sketch = st.columns([1, 1])

with col_calc:
    calc_trigger = st.button("🚀 Calculate Voltage Drop", type="primary", use_container_width=True)

with col_sketch:
    sketch_trigger = st.button("🎨 Generate Feeder Sketch", use_container_width=True)

if calc_trigger:
    df = edited_df.copy()
    loads = df["SECTION LOAD (kVA)"].fillna(0).tolist()
    upto_loads = [0] * len(loads)
    temp_sum = 0
    for i in range(len(loads)-1, -1, -1):
        temp_sum += loads[i]
        upto_loads[i] = temp_sum
    
    df["UPTO LOAD (kVA)"] = upto_loads
    df["VD FACTOR"] = df["CONDUCTOR SIZE"].map(VD_FACTORS).fillna(0)
    df["VD (VOLTS)"] = df["DISTANCE (KM)"] * df["UPTO LOAD (kVA)"] * df["VD FACTOR"]
    
    st.session_state.calculated_df = df
    st.session_state.totals = {
        "len": df["DISTANCE (KM)"].sum(),
        "load": df["SECTION LOAD (kVA)"].sum(),
        "vd": df["VD (VOLTS)"].sum(),
        "source_kva": upto_loads[0] if upto_loads else 0
    }

# --- DISPLAY RESULTS ---
if st.session_state.calculated_df is not None:
    df = st.session_state.calculated_df
    totals = st.session_state.totals
    
    # 1. Calculation Table
    summary_row = pd.DataFrame({
        "POINT": ["**GRAND TOTAL**"], "CONDUCTOR SIZE": ["-"], "DISTANCE (KM)": [totals['len']],
        "SECTION LOAD (kVA)": [totals['load']], "UPTO LOAD (kVA)": [0.0], "VD (VOLTS)": [totals['vd']]
    })
    st.dataframe(pd.concat([df, summary_row], ignore_index=True), use_container_width=True)

    # 2. Formula Summary
    df_val = mdi_kva / totals['source_kva'] if totals['source_kva'] > 0 else 0
    actual_vd_v = totals['vd'] * df_val
    vd_percent = (actual_vd_v / (11000 - actual_vd_v) * 100) if (11000 - actual_vd_v) > 0 else 0

    st.markdown('<div class="formula-section">', unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    c1.metric("Demand Factor", f"{df_val:.4f}")
    c2.metric("Actual VD", f"{actual_vd_v:.2f} Volts")
    c3.metric("Final % VD", f"{vd_percent:.3f}%")
    st.markdown('</div>', unsafe_allow_html=True)

# --- SKETCH LOGIC ---
if sketch_trigger:
    if st.session_state.calculated_df is None:
        st.warning("Pehle 'Calculate Voltage Drop' par click karein!")
    else:
        df = st.session_state.calculated_df
        st.subheader("🎨 Dynamic Feeder Sketch")
        st.markdown('<div class="sketch-section">', unsafe_allow_html=True)
        
        dot = graphviz.Digraph(comment='Feeder Sketch')
        dot.attr(rankdir='BT') 
        
        # Substation Node
        ss_name = substation_name if substation_name else "SUBSTATION"
        dot.node('SS', f' {ss_name} \n (Source) ', shape='house', style='filled', fillcolor='gold')
        
        previous_node = 'SS'
        for i, row in df.iterrows():
            node_id = f"P{i}"
            point_name = row['POINT'].split('-')[-1]
            cond_size = row['CONDUCTOR SIZE']
            
            # Identify if Cable or Conductor
            is_cable = "CABLE" in cond_size.upper()
            
            # Label for the arrow/line
            edge_label = (f"{row['DISTANCE (KM)']} km\n"
                          f"{cond_size}\n"
                          f"Sec VD: {row['VD (VOLTS)']:.2f} V\n"
                          f"Cum Load: {row['UPTO LOAD (kVA)']} kVA")
            
            # Styling: Cable = Double Circle Node or Coil-like feel, Conductor = Single
            node_shape = 'doublecircle' if is_cable else 'circle'
            dot.node(node_id, point_name, shape=node_shape, style='filled', fillcolor='aliceblue')
            
            # Line style: Cables can be dashed to look different
            line_style = 'solid' if not is_cable else 'dashed'
            dot.edge(node_id, previous_node, label=edge_label, color='red', style=line_style, penwidth='2.0')
            
            previous_node = node_id
            
        st.graphviz_chart(dot)
        st.caption("Note: Dashed lines represent Cables, Solid lines represent ACSR Conductors.")
        st.markdown('</div>', unsafe_allow_html=True)

# --- FOOTER ---
st.markdown(f"""
<div class="footer-container">
    <p style="font-size:1.2em; font-weight:bold;">Made with ❤️ by Anuj Narang</p>
    <div style="margin: 25px 0;">
        <a href="https://instagram.com/iamanujnarang"><img src="{INSTA_ICON}" class="social-logo"></a>
        <a href="https://facebook.com/iamanujnarang"><img src="{FB_ICON}" class="social-logo"></a>
        <a href="https://x.com/iamanujnarang"><img src="{X_ICON}" class="social-logo"></a>
        <a href="https://linkedin.com/in/iamanujnarang"><img src="{LINKEDIN_ICON}" class="social-logo"></a>
    </div>
    <p>Powered by <b>Beeclue Tech</b></p>
</div>
""", unsafe_allow_html=True)
