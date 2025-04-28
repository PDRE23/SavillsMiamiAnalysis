import streamlit as st
import pandas as pd
import numpy_financial as npf
import plotly.graph_objects as go
import plotly.io as pio
import json, io, base64, os
from fpdf import FPDF

# ---- Savills Plotly Template ----
pio.templates["savills"] = go.layout.Template(
    layout=go.Layout(
        colorway=["#E60000", "#FFD700"],
        font=dict(family="Segoe UI", color="#FFFFFF"),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        legend=dict(font=dict(color="#FFFFFF")),
        xaxis=dict(gridcolor="rgba(255,255,255,0.1)", zerolinecolor="rgba(255,255,255,0.2)", color="#FFFFFF"),
        yaxis=dict(gridcolor="rgba(255,255,255,0.1)", zerolinecolor="rgba(255,255,255,0.2)", color="#FFFFFF"),
        margin=dict(t=20,b=20,l=20,r=20)
    )
)
pio.templates.default = "savills"

# ---- Scenario Persistence ----
SCENARIO_FILE = "scenarios.json"

def load_scenarios():
    return json.load(open(SCENARIO_FILE, "r")) if os.path.exists(SCENARIO_FILE) else {}

def save_scenarios(scen):
    with open(SCENARIO_FILE, "w") as f:
        json.dump(scen, f, indent=2)

scenarios = load_scenarios()

# ---- Embed Logo ----
logo_data = base64.b64encode(open("savills_logo.png", "rb").read()).decode()

# ---- Page Config & CSS ----
st.set_page_config(page_title="Savills Lease Analyzer", layout="wide")
st.markdown("""
<style>
  header, div[role=\"banner\"] { display: none !important; }
  body::before { content: ''; position: fixed; top: 0; left: 0; width: 100%; height: 6px;
                  background: linear-gradient(90deg,#FFD700,#E60000); z-index: 9999; }
  [data-testid=\"stAppViewContainer\"] { padding-top: 12px !important; background: #505050 !important; color: #FFF !important; }
  [data-testid=\"stSidebar\"] { background: #333 !important; color: #FFF !important; }
  input, textarea { color: #000 !important; background: #FFF !important; }
  .stButton > button { background: #FFF !important; color: #000 !important; border: none !important; }
  [data-testid=\"stDataFrame\"] td, th { color: #000 !important; background: #FFF !important; }
  h1, h2, h3, h4 { color: #000 !important; }
  p, label { color: #DDD !important; }
</style>
""", unsafe_allow_html=True)

# ---- Header ----
st.markdown(f"""
<div style='display:flex; align-items:center; margin-bottom:1rem;'>
  <img src='data:image/png;base64,{logo_data}' width='80'>
  <div style='margin-left:1rem;'>
    <h1 style='margin:0; font-family:Segoe UI;'>Savills | Lease Analyzer</h1>
    <p style='margin:0; font-size:14px;'>Created by Peyton Dowd</p>
  </div>
</div>
""", unsafe_allow_html=True)
st.markdown("---")

# ---- Sidebar: Load/Save ----
with st.sidebar:
    st.header("Scenarios")
    load_name = st.selectbox("🔄 Load Scenario", [""] + list(scenarios.keys()))
    if load_name:
        for k,v in scenarios[load_name].items(): st.session_state[k] = v
        st.success(f"Loaded '{load_name}'")
    save_name = st.text_input("💾 Save Current As")
    if st.button("Save Scenario"):
        to_save = {k: st.session_state[k] for k in st.session_state if any(k.startswith(prefix) for prefix in (
            'name','term','sqft','base','inc','opex','opexinc','park_cost','park_ratio','park_spaces','free','ti','move','disc','pdfs'
        ))}
        scenarios[save_name] = to_save
        save_scenarios(scenarios)
        st.success(f"Saved '{save_name}'")

# ---- Tabs ----
tab_inputs, tab_analysis, tab_comparison = st.tabs(["Inputs", "Analysis", "Comparison"])

# ---- Analysis Function ----
def analyze_lease(params):
    term, sqft = max(params['term'],1), max(params['sqft'],1)
    yrs, br, opx, prk, gr = [], [], [], [], []
    for y in range(1, term+1):
        yrs.append(y)
        b = params['base'] * (1 + params['inc']/100)**(y-1)
        o = params['opex'] * (1 + params['opexinc']/100)**(y-1)
        p = (params['park_cost'] * params['park_spaces']) * 12 / sqft
        g = (b + o + p) * sqft
        br.append(b); opx.append(o); prk.append(p); gr.append(g)
    free_cr = params['free']/12 * params['base'] * sqft
    ti_cr = params['ti'] * sqft
    cfs, wf = [], []
    for idx,g in enumerate(gr):
        net = -g + (free_cr if idx==0 else 0) + (ti_cr if idx==0 else 0) + (params['move']*sqft if idx==0 else 0)
        cfs.append(net)
        wf.append({
            'Year': idx+1,
            'Gross Cost': round(g,2),
            'Free Rent Credit': round(free_cr if idx==0 else 0,2),
            'TI Allowance': round(ti_cr if idx==0 else 0,2),
            'Moving Allowance': round(params['move']*sqft if idx==0 else 0,2),
            'Net Cash Flow': round(net,2)
        })
    irr = npf.irr(cfs) if len(cfs)>1 else None
    cum, payback = 0, "Never"
    for rec in wf:
        cum += rec['Net Cash Flow']
        if cum >= 0 and payback == "Never": payback = rec['Year']
    occ = sum(-x for x in cfs)
    avg = occ/(term*sqft) if term*sqft>0 else 0
    npv = npf.npv(params['disc']/100, cfs)
    summary = {
        'Option': params['name'],
        'Term (yrs)': params['term'],
        'RSF': params['sqft'],
        'Occupancy Cost': f"${occ:,.0f}",
        'Avg Eff. Rent': f"${avg:,.2f}",
        'NPV': f"${npv:,.0f}",
        'IRR': f"{irr*100:.2f}%" if irr else 'N/A',
        'Payback': f"{payback} yrs"
    }
    ann_df = pd.DataFrame({'Year':yrs,'Base':br,'Opex':opx,'Parking':prk,'Gross':gr})
    return summary, ann_df, pd.DataFrame(wf)

# ---- Inputs Tab ----
with tab_inputs:
    st.header("Configure Lease Scenario")
    compare = st.checkbox("🔁 Compare Multiple Lease Options")
    count = st.slider("Number of Options",1,10,1) if compare else 1
    inputs = []
    for i in range(count):
        st.subheader(f"Scenario {i+1}")
        left, right = st.columns(2)
        with left:
            name = st.text_input("Option Name", f"Option {i+1}", key=f"name_{i}")
            term = st.number_input("Lease Term (yrs)", min_value=0, step=1, key=f"term_{i}")
            sqft = st.number_input("RSF", min_value=0, step=1, key=f"sqft_{i}")
            base = st.number_input("Starting Base Rent ($/SF/yr)", min_value=0.0, step=0.01, key=f"base_{i}")
            inc  = st.slider("Base Rent Increase (%)",0.0,10.0,3.0,0.1, key=f"inc_{i}")
        with right:
            rt = st.radio("Rate Type", ["Full Service","Triple Net"], key=f"rt_{i}")
            if rt == "Triple Net":
                opex = st.number_input("Starting OPEX ($/SF/yr)", min_value=0.0, step=0.01, key=f"opex_{i}")
                oinc = st.slider("OPEX Increase (%)",0.0,10.0,3.0,0.1, key=f"opexinc_{i}")
            else:
                opex, oinc = 0.0, 0.0
            park_cost = st.number_input("Parking Cost per Space ($/mo)", min_value=0.0, step=0.01, key=f"park_cost_{i}")
            park_ratio = st.number_input("Parking Ratio (spaces/1k SF)", min_value=0.0, step=0.1, key=f"park_ratio_{i}")
            park_spaces = round(park_ratio * sqft / 1000)
            st.write(f"#### Calculated Parking Spaces: {park_spaces}")
            override = st.checkbox("Override with Fixed Parking Spaces", key=f"override_{i}")
            if override:
                park_spaces = st.number_input("Fixed Parking Spaces", min_value=0, step=1, key=f"park_spaces_{i}")
        st.markdown("**Landlord Concessions**")
        free = st.slider("Free Rent (months)",0,24,0,1, key=f"free_{i}")
        ti_allow = st.slider("TI Allowance ($/SF)",0.0,200.0,0.0,1.0, key=f"ti_{i}")
        move = st.slider("Moving Allowance ($/SF)",0.0,200.0,0.0,1.0, key=f"move_{i}")

        st.markdown("#### Net Present Value Calculation")
        disc = st.slider("Discount Rate (%)",0.0,20.0,7.0,0.1, key=f"disc_{i}")

        pdfs = st.file_uploader("🔖 Attach Lease Documents (PDF)", type="pdf", accept_multiple_files=True, key=f"pdfs_{i}")
        inputs.append({
            'name':name,'term':term,'sqft':sqft,'base':base,'inc':inc,
            'opex':opex,'opexinc':oinc,'park_cost':park_cost,'park_spaces':park_spaces,
            'free':free,'ti':ti_allow,'move':move,'disc':disc,'pdfs':pdfs
        })
    if st.button("▶️ Run Analysis"): results = [analyze_lease(inp) for inp in inputs]

# ---- Analysis Tab ----
with tab_analysis:
    if 'results' not in locals() or not results:
        st.warning("Run analysis in Inputs first.")
    else:
        for idx, (summ, ann_df, wf_df) in enumerate(results):
            st.subheader(f"Scenario {idx+1}: {summ['Option']}")
            pdf_list = inputs[idx]['pdfs']
            if pdf_list:
                for pdf in pdf_list:
                    raw = pdf.read()
                    b64 = base64.b64encode(raw).decode('utf-8')
                    iframe = f"<iframe src='data:application/pdf;base64,{b64}' width='100%' height='400px' style='border:1px solid #ccc;'></iframe>"
                    st.markdown(iframe, unsafe_allow_html=True)
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("💰 Occupancy Cost", summ['Occupancy Cost'])
            c2.metric("📈 Avg Eff. Rent", summ['Avg Eff. Rent'])
            c3.metric("🔮 NPV", summ['NPV'])
            c4.metric("⏱️ Payback", summ['Payback'])
            with st.spinner("Rendering chart..."):
                fig = go.Figure()
                yrs = ann_df['Year']
                fig.add_trace(go.Bar(name='Base Rent', x=yrs, y=ann_df['Base']))
                fig.add_trace(go.Bar(name='Opex', x=yrs, y=ann_df['Opex']))
                fig.add_trace(go.Bar(name='Parking', x=yrs, y=ann_df['Parking']))
                fig.update_layout(barmode='stack', xaxis_title='Year', yaxis_title='$/SF')
                st.plotly_chart(fig, use_container_width=True)

# ---- Comparison Tab ----
with tab_comparison:
    if 'results' not in locals() or len(results) < 2:
        st.info("Enable multiple options in Inputs first.")
    else:
        comp = pd.DataFrame([r[0] for r in results])
        st.markdown("## Comparison Summary")
        st.dataframe(comp, use_container_width=True)
