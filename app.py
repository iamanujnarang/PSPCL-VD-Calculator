import streamlit as st
import pandas as pd
import numpy as np
import graphviz
from fpdf import FPDF
import tempfile
import os
from io import BytesIO

# ---------------- CONFIG & ASSETS ----------------
st.set_page_config(page_title="PSPCL VD & Sketch Pro", page_icon="⚡", layout="wide")

# Assets
PSPCL_LOGO_UI = "https://pspcl.in/assets/images/logo.png"
PSPCL_SKETCH_LOGO = "https://raw.githubusercontent.com/iamanujnarang/SketchMaker/refs/heads/main/PSPCLLogo.png"
BEECLUE_LOGO = "https://raw.githubusercontent.com/iamanujnarang/LDHF/e5748e037b76a52a47d610a88c3a3c70f72f1c9a/BEECLUE.png"
INSTA_ICON = "https://upload.wikimedia.org/wikipedia/commons/a/a5/Instagram_icon.png"
FB_ICON = "https://upload.wikimedia.org/wikipedia/commons/1/1b/Facebook_icon.svg"
X_ICON = "https://upload.wikimedia.org/wikipedia/commons/b/b7/X_logo.jpg"
LINKEDIN_ICON = "https://upload.wikimedia.org/wikipedia/commons/c/ca/LinkedIn_logo_initials.png"

# HV LIMITS & FACTORS
HV_UPPER_LIMIT = 6.0
HV_LOWER_LIMIT = -9.0
VD_FACTORS = {
    "ACSR 100 SQMM": 0.0415, "ACSR 80 SQMM": 0.0512, "ACSR 50 SQMM": 0.0910,
    "XLPE 300 SQMM": 0.0146, "XLPE 150 SQMM": 0.0285, "XLPE 35 SQMM": 0.1150
}

# ---------------- CSS ----------------
st.markdown(f"""
<style>
    .main-header {{ text-align: center; padding: 20px; background: white; border-radius: 15px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }}
    .footer-container {{ text-align: center; margin-top: 80px; padding: 40px 20px; border-top: 1px solid #ddd; }}
    .social-icon {{ width: 35px; margin: 0 10px; transition: 0.3s; }}
    .social-icon:hover {{ transform: scale(1.2); }}
    .beeclue-img {{ width: 180px; height: auto; }}
</style>
""", unsafe_allow_html=True)

# ---------------- HEADER ----------------
st.markdown(f'<div class="main-header"><img src="{PSPCL_LOGO_UI}" height="100"><h1>11kV Feeder VD Calculator & Sketch Master</h1></div>', unsafe_allow_html=True)

# ---------------- SIDEBAR ----------------
with st.sidebar:
    st.header("⚙️ Feeder Identity")
    feeder_name = st.text_input("Feeder Name", "New Amritsar Feeder")
    substation = st.text_input("Substation Name", "132kV MALL MANDI")
    mdi_a = st.number_input("Max Demand (Amps)", value=170.0)
    mdi_kva = round(np.sqrt(3) * 11 * mdi_a, 2)
    st.success(f"MDI = {mdi_kva} kVA")
    st.info("HV Limits: +6% to -9%")

# ---------------- INPUT TABLES ----------------
col_left, col_right = st.columns(2)

with col_left:
    st.subheader("🚠 Main Backbone (Sections)")
    n_sec = st.number_input("Number of Sections", min_value=1, value=3, step=1)
    main_sections = [f"{chr(65+i)}-{chr(66+i)}" for i in range(int(n_sec))]
    main_df = pd.DataFrame({
        "SECTION": main_sections,
        "CONDUCTOR": ["ACSR 100 SQMM"] * len(main_sections),
        "LENGTH_KM": [0.500] * len(main_sections),
        "NET LOAD (kVA)": [100.0] * len(main_sections)
    })
    edited_main_df = st.data_editor(main_df, use_container_width=True, key="main_tbl",
                                    column_config={"CONDUCTOR": st.column_config.SelectboxColumn(options=list(VD_FACTORS.keys()))})

with col_right:
    st.subheader("🌿 Sub-Branches / T-Offs")
    node_options = [s.split('-')[1] for s in main_sections]
    branch_df = pd.DataFrame({
        "CONNECT_AT": [node_options[0]] if node_options else [None],
        "BRANCH_NAME": ["Branch 1"],
        "CONDUCTOR": ["ACSR 50 SQMM"],
        "LENGTH_KM": [0.200],
        "LOAD_KVA": [50.0]
    })
    edited_branch_df = st.data_editor(branch_df, num_rows="dynamic", use_container_width=True, 
                                     column_config={
                                         "CONNECT_AT": st.column_config.SelectboxColumn(options=node_options),
                                         "CONDUCTOR": st.column_config.SelectboxColumn(options=list(VD_FACTORS.keys()))
                                     }, key="br_tbl")

# ---------------- CALCULATION ENGINE ----------------
def run_calculations(df, mdi_kva):
    df["FACTOR"] = df["CONDUCTOR"].map(VD_FACTORS)
    loads = df["NET LOAD (kVA)"].tolist()
    cum = []
    running = 0
    for val in loads[::-1]:
        running += val
        cum.append(running)
    df["CUM LOAD"] = cum[::-1]
    df["SECTION VD"] = df["LENGTH_KM"] * df["CUM LOAD"] * df["FACTOR"]
    
    sum_vd = df["SECTION VD"].sum()
    max_load = df["CUM LOAD"].iloc[0]
    demand_factor = mdi_kva / max_load if max_load > 0 else 0
    actual_vd = sum_vd * demand_factor
    vd_percent = (actual_vd / (11000 - actual_vd)) * 100 if (11000 - actual_vd) > 0 else 0
    return df, demand_factor, actual_vd, vd_percent

# ---------------- SKETCH ENGINE ----------------
def create_feeder_graph(m_df, b_df, ss_name):
    dot = graphviz.Digraph()
    dot.attr(rankdir='LR', size='24,14!', ratio='fill', dpi='300', nodesep='0.6', ranksep='1.2')
    dot.node("SOURCE", str(ss_name), shape="box3d", style="filled", fillcolor="#f8f9fa", fontname="Arial-Bold", fontsize="16")
    
    prev_node = "SOURCE"
    for _, row in m_df.iterrows():
        current_node = str(row['SECTION'].split('-')[1])
        node_label = f"Node {current_node}\nLoad: {row['NET LOAD (kVA)']} kVA"
        dot.node(current_node, node_label, shape="circle", style="filled", fillcolor="#e7f3ff", fontsize="12")
        
        edge_label = f"{row['CONDUCTOR']}\nDist: {row['LENGTH_KM']} km"
        is_cable = "XLPE" in str(row['CONDUCTOR']).upper()
        p_width = "5.0" if is_cable else "2.5"
        p_color = "#003366" if is_cable else "black"
        
        dot.edge(prev_node, current_node, label=edge_label, penwidth=p_width, color=p_color, fontsize="11")
        prev_node = current_node

    for _, row in b_df.iterrows():
        if row['CONNECT_AT'] and str(row['CONNECT_AT']) != "None":
            target = str(row['CONNECT_AT'])
            br_id = f"BRANCH_{row['BRANCH_NAME']}"
            dot.node(br_id, f"{row['BRANCH_NAME']}\nLoad: {row['LOAD_KVA']} kVA", shape="plaintext", fontcolor="#a52a2a", fontsize="11")
            br_label = f"{row['CONDUCTOR']}\n{row['LENGTH_KM']} km"
            dot.edge(target, br_id, label=br_label, style="dashed", color="#cc0000", arrowhead="vee", fontsize="10")
    return dot

# ---------------- MAIN EXECUTION ----------------
if st.button("🚀 Calculate VD & Generate High-Detail Sketch", use_container_width=True):
    # Calculations
    calc_df, d_factor, a_vd, v_perc = run_calculations(edited_main_df, mdi_kva)
    
    st.subheader("📊 Voltage Drop Results")
    st.dataframe(calc_df, use_container_width=True)
    
    res_c1, res_c2, res_c3 = st.columns(3)
    res_c1.metric("Demand Factor", f"{d_factor:.4f}")
    res_c2.metric("Actual VD (V)", f"{a_vd:.2f}")
    res_c3.metric("VD %", f"{v_perc:.3f}%")
    
    if v_perc > HV_UPPER_LIMIT or v_perc < HV_LOWER_LIMIT:
        st.error(f"⚠️ Voltage {v_perc:.3f}% OUTSIDE permissible limits (+6% to -9%)")
    else:
        st.success(f"✅ Voltage {v_perc:.3f}% WITHIN permissible limits (+6% to -9%)")

    # Sketching
    st.subheader("🔌 Network Diagram")
    try:
        sketch = create_feeder_graph(calc_df, edited_branch_df, substation)
        st.graphviz_chart(sketch, use_container_width=True)

        with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as tmp:
            sketch.render(tmp.name.replace('.png', ''), format='png', cleanup=True)
            img_path = tmp.name

        # PDF Report
        pdf = FPDF(orientation='L', unit='mm', format='A4')
        pdf.add_page()
        pdf.image(PSPCL_SKETCH_LOGO, x=10, y=10, w=40)
        pdf.set_font("Arial", 'B', 20)
        pdf.cell(0, 15, f"{feeder_name.upper()} - VD REPORT & SLD", ln=True, align='C')
        pdf.set_font("Arial", size=10)
        pdf.cell(0, 5, f"Substation: {substation} | MDI: {mdi_kva} kVA | VD: {v_perc:.3f}%", ln=True, align='C')
        pdf.image(img_path, x=10, y=42, w=275)
        
        pdf_bytes = pdf.output(dest='S').encode('latin1')
        st.download_button("📥 Download Official Report (PDF)", pdf_bytes, f"{feeder_name}_Report.pdf")
        
        if os.path.exists(img_path): os.remove(img_path)
    except Exception as e:
        st.error(f"Sketch Error: {e}")

# ---------------- FOOTER ----------------
st.markdown(f"""
<div class="footer-container">
<div class="made-with-love">Made with <span class="heart-symbol">❤️</span> by <b>Er. Anuj Narang, JE PSPCL</b></div>
<div style="margin-bottom: 25px;">
<a href="https://instagram.com/iamanujnarang" target="_blank"><img src="{INSTA_ICON}" class="social-icon"></a>
<a href="https://facebook.com/iamanujnarang" target="_blank"><img src="{FB_ICON}" class="social-icon"></a>
<a href="https://x.com/iamanujnarang" target="_blank"><img src="{X_ICON}" class="social-icon"></a>
<a href="https://linkedin.com/in/iamanujnarang" target="_blank"><img src="{LINKEDIN_ICON}" class="social-icon"></a>
</div>
<div style="margin-top: 25px;">
    <div class="powered-text">In Strategic Collaboration with</div>
    <a href="https://beeclue.com" target="_blank"><img src="{BEECLUE_LOGO}" class="beeclue-img"></a>
</div>
<div style="color: #94a3b8; font-size: 0.85rem; margin-top: 25px;">© 2026 | PSPCL Guidelines | CC 45/2024</div>
</div>
""", unsafe_allow_html=True)
