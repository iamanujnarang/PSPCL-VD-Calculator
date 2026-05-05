import streamlit as st
import pandas as pd
import numpy as np
import io
import graphviz
from fpdf import FPDF
from datetime import datetime
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils.dataframe import dataframe_to_rows

# --- PAGE CONFIG ---
st.set_page_config(page_title="PSPCL VD Calculator Pro", page_icon="⚡", layout="wide")

# --- CONSTANTS & ASSETS ---
PSPCL_LOGO = "https://pspcl.in/assets/images/logo.png"
INSTA_ICON = "https://upload.wikimedia.org/wikipedia/commons/a/a5/Instagram_icon.png"
FB_ICON = "https://upload.wikimedia.org/wikipedia/commons/1/1b/Facebook_icon.svg"
X_LOGO_FINAL = "https://upload.wikimedia.org/wikipedia/commons/b/b7/X_logo.jpg"
LINKEDIN_ICON = "https://upload.wikimedia.org/wikipedia/commons/c/ca/LinkedIn_logo_initials.png"
BEECLUE_LOGO = "https://raw.githubusercontent.com/iamanujnarang/LDHF/e5748e037b76a52a47d610a88c3a3c70f72f1c9a/BEECLUE.png"

VD_FACTORS = {
    "ACSR 100 SQMM": 0.0415, "ACSR 80 SQMM": 0.0512, "ACSR 50 SQMM": 0.0910,
    "ACSR 30 SQMM": 0.1520, "ACSR 20 SQMM": 0.2250, "XLPE CABLE 300 SQMM": 0.0146,
    "XLPE CABLE 150 SQMM": 0.0285, "XLPE CABLE 35 SQMM": 0.1150
}

# --- CUSTOM CSS ---
st.markdown("""
<style>
    .header-box { text-align: center; padding: 25px; background: white; border-radius: 15px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); margin-bottom: 25px; border-top: 8px solid #ffcc00; }
    .pspcl-main-logo { height: 130px; margin-bottom: 15px; }
    .formula-section { background: #ffffff; padding: 30px; border-radius: 15px; border: 1px solid #dee2e6; margin-top: 30px; box-shadow: 0 10px 25px rgba(0,0,0,0.05); }
    .footer-container { text-align: center; margin-top: 60px; padding: 50px; border-top: 1px solid #eee; background: #fdfdfd; }
    .social-logo { width: 40px; margin: 0 12px; transition: 0.3s; cursor: pointer; border-radius: 5px; }
    .social-logo:hover { transform: scale(1.3); }
    .beeclue-footer-logo { width: 140px; margin-top: 15px; }
    .metric-box { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 10px; text-align: center; }
    .success-box { background: #d4edda; border: 2px solid #28a745; padding: 15px; border-radius: 8px; margin: 10px 0; }
    .warning-box { background: #fff3cd; border: 2px solid #ffc107; padding: 15px; border-radius: 8px; margin: 10px 0; }
</style>
""", unsafe_allow_html=True)

# --- HEADER ---
st.markdown(f"""
<div class="header-box">
    <img src="{PSPCL_LOGO}" class="pspcl-main-logo">
    <h1 style="color: #1a237e; margin: 0;">PUNJAB STATE POWER CORPORATION LIMITED</h1>
    <h2 style="color: #444; margin: 5px;">11kV Voltage Drop Calculator</h2>
    <p style="color: #666; margin: 5px;">Advanced Analysis & Reporting System</p>
</div>
""", unsafe_allow_html=True)

# --- SESSION STATE ---
if 'final_df' not in st.session_state: st.session_state.final_df = None
if 'metrics' not in st.session_state: st.session_state.metrics = {}
if 'feeder_info' not in st.session_state: st.session_state.feeder_info = {}

# --- SIDEBAR (Feeder Information) ---
with st.sidebar:
    st.header("📋 Feeder Information")
    f_name = st.text_input("Feeder Name", value="FEEDER-01", key="f_name")
    ss_name = st.text_input("Feeding Substation", value="MAIN SUBSTATION", key="ss_name")
    s_div = st.text_input("Sub-Division", value="SUBDIVISION-01", key="s_div")
    division = st.text_input("Division", value="DIVISION-01", key="division")
    
    st.session_state.feeder_info = {
        "feeder_name": f_name,
        "substation": ss_name,
        "subdivision": s_div,
        "division": division
    }
    
    st.divider()
    st.header("⚡ Parameter Settings")
    mdi_a = st.number_input("Max Demand (MDI Amps)", min_value=0.0, step=0.1, value=100.0, key="mdi_a")
    n_sec = st.number_input("Number of Sections", min_value=1, max_value=100, value=5, key="n_sec")
    mdi_k = round(np.sqrt(3) * 11 * mdi_a, 4)
    st.success(f"✓ MDI: {mdi_k} kVA")
    
    st.divider()
    st.header("📊 Voltage Limits")
    vd_limit = st.number_input("Acceptable VD Limit (%)", min_value=0.0, max_value=10.0, value=5.0, step=0.1)

# --- DATA INPUT TABLE ---
st.subheader("📍 Section-wise Network Input")
sec_labels = [f"{chr(65+i)}-{chr(66+i)}" for i in range(int(n_sec))]
df_template = pd.DataFrame({
    "SECTION": sec_labels,
    "CONDUCTOR SIZE": [None] * int(n_sec),
    "LENGTH (KM)": [0.0] * int(n_sec),
    "NET LOAD (kVA)": [0.0] * int(n_sec)
})

user_input_df = st.data_editor(
    df_template,
    column_config={
        "SECTION": st.column_config.TextColumn("Span", disabled=True),
        "CONDUCTOR SIZE": st.column_config.SelectboxColumn("Conductor/Cable", options=list(VD_FACTORS.keys()), required=True),
        "LENGTH (KM)": st.column_config.NumberColumn("Length (km)", min_value=0.0, format="%.3f"),
        "NET LOAD (kVA)": st.column_config.NumberColumn("Node Load (kVA)", min_value=0.0, format="%.1f")
    },
    use_container_width=True, num_rows="fixed", key="data_editor"
)

# --- CALCULATION LOGIC ---
col_btn1, col_btn2, col_btn3, col_btn4 = st.columns(4)

if col_btn1.button("🚀 Calculate Results", type="primary", use_container_width=True):
    if user_input_df["CONDUCTOR SIZE"].isnull().any():
        st.error("❌ Error: Please select conductor type for all sections.")
    else:
        calc_df = user_input_df.copy()
        
        # Cumulative Load Calculation (Tail to Source)
        node_loads = calc_df["NET LOAD (kVA)"].tolist()
        cum_loads = [0] * len(node_loads)
        running_total = 0
        for i in range(len(node_loads)-1, -1, -1):
            running_total += node_loads[i]
            cum_loads[i] = running_total
            
        calc_df["CUMULATIVE LOAD (kVA)"] = cum_loads
        calc_df["FACTOR"] = calc_df["CONDUCTOR SIZE"].map(VD_FACTORS)
        calc_df["SECTION VD (V)"] = calc_df["LENGTH (KM)"] * calc_df["CUMULATIVE LOAD (kVA)"] * calc_df["FACTOR"]
        
        sum_vd = calc_df["SECTION VD (V)"].sum()
        max_ld_kva = cum_loads[0] if cum_loads else 0
        demand_f = mdi_k / max_ld_kva if max_ld_kva > 0 else 0
        act_vd_volts = sum_vd * demand_f
        vd_percentage = (act_vd_volts / (11000 - act_vd_volts) * 100) if (11000 - act_vd_volts) > 0 else 0
        
        st.session_state.final_df = calc_df
        st.session_state.metrics = {
            "sum_vd": sum_vd, "max_ld_kva": max_ld_kva, "demand_f": demand_f,
            "act_vd_volts": act_vd_volts, "vd_percentage": vd_percentage, "mdi_kva": mdi_k
        }
        
        st.success("✓ Calculation completed successfully!")

# --- DISPLAY RESULTS ---
if st.session_state.final_df is not None:
    res = st.session_state.final_df
    m = st.session_state.metrics
    
    # --- RESULTS TABLE ---
    st.subheader("📊 Final Calculation Table")
    st.dataframe(
        res.style.format({
            "LENGTH (KM)": "{:.3f}",
            "NET LOAD (kVA)": "{:.1f}",
            "CUMULATIVE LOAD (kVA)": "{:.1f}",
            "FACTOR": "{:.6f}",
            "SECTION VD (V)": "{:.4f}"
        }),
        use_container_width=True,
        hide_index=True
    )
    
    # --- METRICS VISUALIZATION ---
    st.markdown('<div class="formula-section">', unsafe_allow_html=True)
    st.subheader("🧮 Mathematical Verification & Metrics")
    
    mc1, mc2, mc3, mc4 = st.columns(4)
    
    with mc1:
        st.latex(r"D.F. = \frac{MDI_{kVA}}{Total_{kVA}}")
        st.metric("Demand Factor", f"{m['demand_f']:.4f}")
    
    with mc2:
        st.latex(r"Sum\ VD(V) = \sum (L \times CL \times F)")
        st.metric("Sum of Section VD (V)", f"{m['sum_vd']:.2f}")
    
    with mc3:
        st.latex(r"Actual\ VD(V) = Sum\ VD \times D.F.")
        st.metric("Actual VD (Volts)", f"{m['act_vd_volts']:.2f}")
    
    with mc4:
        st.latex(r"\% VD = \frac{VD}{11000-VD} \times 100")
        color = "🔴" if m['vd_percentage'] > vd_limit else "🟢"
        st.metric("Final VD (%)", f"{color} {m['vd_percentage']:.3f} %")
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # --- VD STATUS ---
    if m['vd_percentage'] > vd_limit:
        st.markdown(f"""<div class="warning-box"><strong>⚠️ WARNING:</strong> Voltage Drop ({m['vd_percentage']:.3f}%) exceeds the acceptable limit ({vd_limit}%)</div>""", unsafe_allow_html=True)
    else:
        st.markdown(f"""<div class="success-box"><strong>✓ OK:</strong> Voltage Drop ({m['vd_percentage']:.3f}%) is within acceptable limits ({vd_limit}%)</div>""", unsafe_allow_html=True)
    
    # --- EXPORT BUTTONS ---
    st.subheader("📥 Export Options")
    
    exp_col1, exp_col2, exp_col3 = st.columns(3)
    
    # --- EXCEL EXPORT ---
    with exp_col1:
        if st.button("📊 Export to Excel", use_container_width=True):
            wb = Workbook()
            
            # Sheet 1: Summary
            ws_summary = wb.active
            ws_summary.title = "Summary"
            ws_summary["A1"] = "PSPCL VOLTAGE DROP CALCULATION REPORT"
            ws_summary["A1"].font = Font(bold=True, size=14)
            ws_summary.merge_cells("A1:F1")
            
            ws_summary["A3"] = "Report Generated:"
            ws_summary["B3"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            ws_summary["A5"] = "Feeder Information"
            ws_summary["A5"].font = Font(bold=True, size=12)
            ws_summary["A6"] = "Feeder Name:"
            ws_summary["B6"] = st.session_state.feeder_info.get("feeder_name", "")
            ws_summary["A7"] = "Substation:"
            ws_summary["B7"] = st.session_state.feeder_info.get("substation", "")
            ws_summary["A8"] = "Sub-Division:"
            ws_summary["B8"] = st.session_state.feeder_info.get("subdivision", "")
            ws_summary["A9"] = "Division:"
            ws_summary["B9"] = st.session_state.feeder_info.get("division", "")
            
            ws_summary["A11"] = "Calculation Parameters"
            ws_summary["A11"].font = Font(bold=True, size=12)
            ws_summary["A12"] = "MDI (kVA):"
            ws_summary["B12"] = m['mdi_kva']
            ws_summary["A13"] = "Total Load (kVA):"
            ws_summary["B13"] = m['max_ld_kva']
            ws_summary["A14"] = "Demand Factor:"
            ws_summary["B14"] = m['demand_f']
            ws_summary["A15"] = "Sum of Section VD (V):"
            ws_summary["B15"] = m['sum_vd']
            ws_summary["A16"] = "Actual VD (Volts):"
            ws_summary["B16"] = m['act_vd_volts']
            ws_summary["A17"] = "Voltage Drop (%):"
            ws_summary["B17"] = m['vd_percentage']
            ws_summary["A18"] = "Acceptable Limit (%):"
            ws_summary["B18"] = vd_limit
            
            ws_summary["A20"] = "Status:"
            status = "✓ PASS" if m['vd_percentage'] <= vd_limit else "✗ FAIL"
            ws_summary["B20"] = status
            ws_summary["B20"].font = Font(bold=True, color="00B050" if m['vd_percentage'] <= vd_limit else "FF0000")
            
            # Format columns
            for col in ["A", "B", "C", "D", "E", "F"]:
                ws_summary.column_dimensions[col].width = 20
            
            # Sheet 2: Detailed Calculations
            ws_detail = wb.create_sheet("Detailed Calculations")
            
            # Write headers
            headers = ["SECTION", "CONDUCTOR SIZE", "LENGTH (KM)", "NET LOAD (kVA)", 
                      "CUMULATIVE LOAD (kVA)", "FACTOR", "SECTION VD (V)"]
            
            for col_num, header in enumerate(headers, 1):
                cell = ws_detail.cell(row=1, column=col_num)
                cell.value = header
                cell.font = Font(bold=True, color="FFFFFF")
                cell.fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
                cell.alignment = Alignment(horizontal="center", vertical="center")
            
            # Write data
            for row_num, (idx, row) in enumerate(res.iterrows(), 2):
                ws_detail.cell(row=row_num, column=1).value = row['SECTION']
                ws_detail.cell(row=row_num, column=2).value = row['CONDUCTOR SIZE']
                ws_detail.cell(row=row_num, column=3).value = round(row['LENGTH (KM)'], 4)
                ws_detail.cell(row=row_num, column=4).value = round(row['NET LOAD (kVA)'], 2)
                ws_detail.cell(row=row_num, column=5).value = round(row['CUMULATIVE LOAD (kVA)'], 2)
                ws_detail.cell(row=row_num, column=6).value = round(row['FACTOR'], 6)
                ws_detail.cell(row=row_num, column=7).value = round(row['SECTION VD (V)'], 4)
            
            # Set column widths and format
            for col_num in range(1, len(headers) + 1):
                ws_detail.column_dimensions[chr(64 + col_num)].width = 22
            
            # Total row
            total_row = len(res) + 2
            ws_detail.cell(row=total_row, column=1).value = "TOTAL"
            ws_detail.cell(row=total_row, column=1).font = Font(bold=True)
            ws_detail.cell(row=total_row, column=7).value = round(m['sum_vd'], 4)
            ws_detail.cell(row=total_row, column=7).font = Font(bold=True)
            
            # Save to bytes
            excel_buffer = io.BytesIO()
            wb.save(excel_buffer)
            excel_buffer.seek(0)
            
            st.download_button(
                label="⬇️ Download Excel Report",
                data=excel_buffer.getvalue(),
                file_name=f"PSPCL_VD_Report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
    
    # --- CSV EXPORT ---
    with exp_col2:
        if st.button("📄 Export to CSV", use_container_width=True):
            csv_data = res.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="⬇️ Download CSV",
                data=csv_data,
                file_name=f"PSPCL_VD_Table_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
                use_container_width=True
            )
    
    # --- PDF EXPORT ---
    with exp_col3:
        if st.button("📋 Export to PDF", use_container_width=True):
            pdf = FPDF(orientation='L', unit='mm', format='A4')
            pdf.add_page()
            pdf.set_font("helvetica", 'B', 16)
            pdf.cell(0, 10, "PSPCL OFFICIAL VOLTAGE DROP REPORT", ln=True, align='C')
            pdf.ln(5)
            
            pdf.set_font("helvetica", 'B', 12)
            pdf.cell(0, 8, "Feeder Information", ln=True)
            pdf.set_font("helvetica", '', 11)
            pdf.cell(95, 7, f"Feeder: {st.session_state.feeder_info.get('feeder_name', '')}")
            pdf.cell(0, 7, f"Sub-Division: {st.session_state.feeder_info.get('subdivision', '')}", ln=True)
            pdf.cell(95, 7, f"Substation: {st.session_state.feeder_info.get('substation', '')}")
            pdf.cell(0, 7, f"Division: {st.session_state.feeder_info.get('division', '')}", ln=True)
            pdf.ln(3)
            
            # Calculation Summary
            pdf.set_font("helvetica", 'B', 11)
            pdf.cell(0, 7, "Calculation Summary", ln=True)
            pdf.set_font("helvetica", '', 10)
            pdf.cell(95, 6, f"MDI (kVA): {m['mdi_kva']:.2f}")
            pdf.cell(0, 6, f"Total Load (kVA): {m['max_ld_kva']:.2f}", ln=True)
            pdf.cell(95, 6, f"Demand Factor: {m['demand_f']:.4f}")
            pdf.cell(0, 6, f"Sum VD (V): {m['sum_vd']:.2f}", ln=True)
            pdf.cell(95, 6, f"Actual VD (Volts): {m['act_vd_volts']:.2f}")
            pdf.cell(0, 6, f"Voltage Drop (%): {m['vd_percentage']:.3f}%", ln=True)
            pdf.ln(5)
            
            # Table Header
            pdf.set_font("helvetica", 'B', 9)
            pdf.set_fill_color(54, 96, 146)
            pdf.set_text_color(255, 255, 255)
            pdf.cell(20, 8, "Section", 1, 0, 'C', True)
            pdf.cell(35, 8, "Conductor", 1, 0, 'C', True)
            pdf.cell(20, 8, "Length(km)", 1, 0, 'C', True)
            pdf.cell(25, 8, "Load(kVA)", 1, 0, 'C', True)
            pdf.cell(30, 8, "Cum.Load(kVA)", 1, 0, 'C', True)
            pdf.cell(20, 8, "Factor", 1, 0, 'C', True)
            pdf.cell(25, 8, "Sec VD(V)", 1, 1, 'C', True)
            
            # Table Body
            pdf.set_font("helvetica", '', 8)
            pdf.set_text_color(0, 0, 0)
            for _, row in res.iterrows():
                pdf.cell(20, 7, str(row['SECTION']), 1)
                pdf.cell(35, 7, str(row['CONDUCTOR SIZE'])[:18], 1)
                pdf.cell(20, 7, f"{row['LENGTH (KM)']:.3f}", 1)
                pdf.cell(25, 7, f"{row['NET LOAD (kVA)']:.1f}", 1)
                pdf.cell(30, 7, f"{row['CUMULATIVE LOAD (kVA)']:.1f}", 1)
                pdf.cell(20, 7, f"{row['FACTOR']:.6f}", 1)
                pdf.cell(25, 7, f"{row['SECTION VD (V)']:.4f}", 1, 1)
            
            pdf.ln(5)
            pdf.set_font("helvetica", 'B', 11)
            pdf.set_text_color(200, 0, 0)
            pdf.cell(0, 8, f"FINAL VOLTAGE DROP: {m['vd_percentage']:.3f}% | Status: {'✓ PASS' if m['vd_percentage'] <= vd_limit else '✗ FAIL'}", ln=True)
            
            # SDO Stamp Area
            pdf.ln(20)
            pdf.set_text_color(0, 0, 0)
            pdf.set_font("helvetica", '', 9)
            pdf.cell(130)
            pdf.multi_cell(60, 5, f"__________________\nSDO OP SUB-DIVISION\nPSPCL {st.session_state.feeder_info.get('subdivision', '').upper()}", align='C')
            
            pdf_bytes = pdf.output()
            st.download_button(
                label="⬇️ Download PDF Report",
                data=pdf_bytes,
                file_name=f"PSPCL_VD_Report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                mime="application/pdf",
                use_container_width=True
            )

# --- SKETCH & NETWORK DIAGRAM ---
if st.session_state.final_df is not None:
    st.subheader("🎨 Network Single Line Diagram")
    
    if col_btn2.button("🎨 Generate Sketch", use_container_width=True):
        res_data = st.session_state.final_df
        m_data = st.session_state.metrics
        
        # --- Graphviz Logic ---
        dot = graphviz.Digraph(comment='PSPCL Network', engine='dot')
        dot.attr(rankdir='TB', bgcolor='transparent')
        dot.attr('node', shape='box', style='filled', fillcolor='#e8f4f8', fontname='Arial')
        dot.attr('edge', fontname='Arial', fontsize='9')
        
        # Source Node
        source_load = m_data["max_ld_kva"]
        dot.node('SOURCE', 
                f'{st.session_state.feeder_info.get("substation", "SOURCE")}\n(11 kV Source)\n{source_load:.1f} kVA',
                shape='box', style='filled', fillcolor='gold', fontcolor='black', fontsize='10')
        
        last_n = 'SOURCE'
        for idx, row in res_data.iterrows():
            curr_n = f"NODE_{idx}"
            is_cable = "CABLE" in row['CONDUCTOR SIZE'].upper()
            
            # Determine node shape and color
            node_shape = 'box' if is_cable else 'circle'
            node_color = '#ff9999' if is_cable else '#99ccff'
            
            node_label = (f"{row['SECTION'].split('-')[-1]}\n"
                         f"{row['NET LOAD (kVA)']:.1f} kVA\n"
                         f"VD: {row['SECTION VD (V)']:.2f}V")
            
            dot.node(curr_n, node_label, shape=node_shape, fillcolor=node_color, fontsize='8')
            
            edge_label = (f"{row['CONDUCTOR SIZE']}\n"
                         f"{row['LENGTH (KM)']:.2f}km\n"
                         f"CL: {row['CUMULATIVE LOAD (kVA)']:.1f}kVA")
            
            dot.edge(last_n, curr_n, label=edge_label, color='red' if is_cable else 'black', penwidth='2' if is_cable else '1')
            last_n = curr_n
        
        st.graphviz_chart(dot, use_container_width=True)
        
        # Export Sketch
        sketch_col1, sketch_col2 = st.columns(2)
        
        with sketch_col1:
            if st.button("💾 Download Sketch (SVG)", use_container_width=True):
                svg_data = dot.pipe(format='svg').decode('utf-8')
                st.download_button(
                    label="⬇️ SVG Format",
                    data=svg_data,
                    file_name=f"PSPCL_Network_Diagram_{datetime.now().strftime('%Y%m%d_%H%M%S')}.svg",
                    mime="image/svg+xml",
                    use_container_width=True
                )
        
        with sketch_col2:
            if st.button("💾 Download Sketch (PNG)", use_container_width=True):
                png_data = dot.pipe(format='png')
                st.download_button(
                    label="⬇️ PNG Format",
                    data=png_data,
                    file_name=f"PSPCL_Network_Diagram_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png",
                    mime="image/png",
                    use_container_width=True
                )

# --- LEGEND & INFORMATION ---
with st.expander("📚 Help & Information"):
    st.markdown("""
    ### 📋 How to Use This Calculator
    
    1. **Enter Feeder Information** in the sidebar
    2. **Set Parameters** (MDI in Amps, Number of Sections)
    3. **Input Section Data** in the table (Conductor, Length, Load)
    4. **Click Calculate** to get results
    5. **View Results** and export in desired format
    
    ### 🧮 Formulas Used
    
    - **Demand Factor (DF)** = MDI (kVA) / Total Load (kVA)
    - **Section VD** = Length × Cumulative Load × Resistance Factor
    - **Actual VD** = Sum of Section VD × Demand Factor
    - **VD %** = (VD / (11000 - VD)) × 100
    
    ### 📊 Conductor/Cable VD Factors
    """)
    
    factor_df = pd.DataFrame([
        {"Conductor": k, "VD Factor": v} for k, v in VD_FACTORS.items()
    ])
    st.dataframe(factor_df, use_container_width=True, hide_index=True)
    
    st.markdown("""
    ### 🎯 Acceptable Voltage Drop Limits
    - **Distribution Feeder**: < 5% (Standard)
    - **Primary Distribution**: < 3%
    - **Secondary Distribution**: < 2%
    """)

# --- FOOTER ---
footer_html = f"""
<div class="footer-container">
<div class="made-with-love">Made with <span class="heart-symbol">❤️</span> by <b>Er. Anuj Narang, JE PSPCL</b></div>
<div style="margin-bottom: 25px;">
<a href="https://instagram.com/iamanujnarang" target="_blank"><img src="{INSTA_ICON}" class="social-icon"></a>
<a href="https://facebook.com/iamanujnarang" target="_blank"><img src="{FB_ICON}" class="social-icon"></a>
<a href="https://x.com/iamanujnarang" target="_blank"><img src="{X_ICON}" class="social-icon"></a>
<a href="https://linkedin.com/in/iamanujnarang" target="_blank"><img src="{LINKEDIN_ICON}" class="social-icon"></a>
</div>

<!-- Beeclue without box -->
<div style="margin-top: 25px;">
    <div class="powered-text">In Strategic Collaboration with</div>
    <a href="https://beeclue.com" target="_blank">
        <img src="{BEECLUE_LOGO}" class="beeclue-img">
    </a>
</div>

<div style="color: #94a3b8; font-size: 0.85rem; margin-top: 25px;">© 2026 | PSPCL Guidelines</div>
</div>
"""
st.markdown(footer_html, unsafe_allow_html=True)
