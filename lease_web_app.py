from fpdf import FPDF
from PIL import Image
import tempfile
import streamlit as st
import pandas as pd
import numpy_financial as npf
import io
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
import plotly.graph_objects as go
from PIL import Image

def explain(label, tooltip):
    return f'{label} <span title="{tooltip}">ℹ️</span>'

# --- Analysis Function ---
def analyze_lease(p):
    term_mos    = max(p["term_mos"], 1)
    start_date  = p["start_date"]
    sqft        = max(p["sqft"], 1)
    base        = p["base"]
    lease_type = p.get("lease_type", "Triple Net (NNN)")
    opex_base = p.get("opex_base", 0.0)
    opex        = p["opex"]
    opexinc     = p["opexinc"]
    park_cost   = p["park_cost"]
    park_spaces = p["park_spaces"]
    free_mo     = p["free"]
    ti_sf       = p["ti"]
    add_cred    = p["add_cred"]
    move_sf     = p["move_exp"]
    const_sf    = p.get("construction", 0.0)
    disc_pct    = p["disc"]
    inc_list    = p.get("rent_incs")
    custom_ab   = p["custom_abate"]
    abates      = p.get("abates")

    # determine number of periods
    full_years = term_mos // 12
    extra_mos  = term_mos % 12
    periods    = full_years + (1 if extra_mos else 0)

    # one-time credits & annual parking cost/SF
    ti_credit_full   = ti_sf * sqft
    add_credit_full  = add_cred * sqft
    move_credit_full = move_sf * sqft
    p_year           = park_cost * park_spaces * 12 / sqft
    construction_full = const_sf * sqft

    cfs, rows = [], []
    for i in range(periods):
        # pick rent increase
        inc_pct = inc_list[i] if inc_list and i < len(inc_list) else p["inc"]
        # dates
        period_start = start_date + relativedelta(months=12*i)
        if i < full_years:
            period_end = period_start + relativedelta(years=1) - timedelta(days=1)
            frac = 1.0
        else:
            period_end = start_date + relativedelta(months=term_mos) - timedelta(days=1)
            frac = extra_mos / 12.0

        # build rates
        b_year = base * (1 + inc_pct/100)**i
        raw_opex = opex * (1 + opexinc / 100) ** i

        if lease_type == "Full Service (Gross)":
            base = opex_base or opex
            o_year = max(0, raw_opex - base)  # tenant pays only the increase
        else:
            o_year = raw_opex  # NNN tenant pays full OPEX

        gross_full = (b_year + o_year + p_year) * sqft
        gross      = gross_full * frac
        move_exp   = move_sf * sqft if i == 0 else 0

        # abatement credit
        if custom_ab and abates:
            abate_credit = abates[i]/12 * base * sqft
        else:
            abate_credit = free_mo/12 * base * sqft if i == 0 else 0

        # total credit (only abatement and additional credit)
        total_credit = abate_credit + (add_credit_full if i==0 else 0)

        # Net Rent calculation (as requested)
        net_rent = gross + move_exp - total_credit

        rows.append({
            "Year":           i+1,
            "Period":         f"{period_start:%m/%d/%Y} – {period_end:%m/%d/%Y}",
            "Base Rent":      round(b_year * sqft * frac),
            "Opex":           round(o_year * sqft * frac),
            "Parking Exp":    round(p_year * sqft * frac),
            "Moving Expense": round(move_exp),
            "Rent Abatement": -round(abate_credit) if abate_credit else 0,
            "Additional Credit": -round(add_credit_full) if i==0 else 0,
            "Net Rent":       round(abs(net_rent)),
        })
        cfs.append(-gross + abate_credit + ti_credit_full + add_credit_full + move_credit_full if i==0 else -gross + abate_credit)

    # metrics
    npv_raw = npf.npv(disc_pct/100, cfs)
    npv     = abs(npv_raw)
    occ     = sum(row["Net Rent"] for row in rows)

    # payback in months
    monthly_base = (base * sqft)/12 if base>0 else 0
    if monthly_base>0:
        total_abate_months = sum(abates) if custom_ab and abates else free_mo
        payback_mos = total_abate_months + (ti_credit_full)/monthly_base
        payback_lbl = f"{int(round(payback_mos))} mo"
    else:
        payback_lbl = "N/A"

    # average effective rent — un-prorated full years basis
    avg = occ/((full_years + (1 if extra_mos else 0))*sqft) if sqft>0 else 0

    summary = {
        "Option":            p["name"],
        "Start Date":        start_date.strftime("%m/%d/%Y"),
        "Term (mos)":        term_mos,
        "RSF":               sqft,
        "Total Cost":        f"${occ:,.0f}",
        "Avg Eff. Rent":     f"${avg:,.2f} /SF/yr",
        "Payback":           payback_lbl,
        f"NPV ({disc_pct:.2f}%):": f"${npv:,.0f}",
        "TI Allowance":      f"${ti_credit_full:,.0f}",
        "Moving Exp":        f"${move_credit_full:,.0f}",
        "Construction Cost": f"${construction_full:,.0f}",
        "Additional Credit": f"${add_credit_full:,.0f}"
    }

    # Set Total Cost to sum of Net Rent
    if 'Net Rent' in rows:
        total_cost = sum(abs(net_rent) for net_rent in cfs)
        summary['Total Cost'] = f"${total_cost:,.0f}"

    return summary, pd.DataFrame(rows)


# -- Streamlit UI Setup --
st.set_page_config(page_title="Savills Lease Analyzer", layout="wide")

# Initialize session state for saved scenarios if not exists
if 'saved_scenarios' not in st.session_state:
    st.session_state.saved_scenarios = {}

# Global styling
st.markdown("""
    <style>
    .header-container {
        display: flex;
        justify-content: space-between;
        align-items: center;
        width: 100%;
    }
    .logo-container {
        text-align: right;
    }
    .save-load-container {
        background-color: #f0f2f6;
        padding: 1.5rem;
        border-radius: 0.5rem;
        margin: 1rem 0;
        border: 1px solid #e0e0e0;
    }
    .stButton button {
        width: 100%;
        margin-top: 0.5rem;
        background-color: #0066cc;
        color: white;
    }
    .stButton button:hover {
        background-color: #0052a3;
    }
    div[data-testid="stVerticalBlock"] > div:nth-of-type(1) {
        padding-top: 1rem;
    }
    </style>
    """, unsafe_allow_html=True)

# Create header container
with st.container():
    col1, col2 = st.columns([0.85, 0.15])
    with col1:
        st.title("Savills | Lease Analyzer")
    with col2:
        logo = Image.open("savills_logo.png")
        st.image(logo, width=180)

st.caption("Created by Peyton Dowd")
st.markdown("---")

tab_inputs, tab_analysis, tab_comparison = st.tabs(["Inputs","Analysis","Comparison"])

# ---- Inputs Tab ----
with tab_inputs:
    st.header("Configure & Compare Scenarios")
    
    # Save/Load Section
    with st.container():
        st.markdown('<div class="save-load-container">', unsafe_allow_html=True)
        
        save_col, load_col = st.columns([1, 1])
        
        with save_col:
            st.markdown("##### 💾 Save Current Scenario")
            save_name = st.text_input("Enter name to save scenario", key="save_name")
            if st.button("Save Scenario", use_container_width=True):
                if save_name:
                    # Collect all current inputs
                    current_scenario = {
                        "name": st.session_state.get("name0", "Option 1"),
                        "start_date": st.session_state.get("sd0", date.today()),
                        "term_mos": st.session_state.get("tm0", 0),
                        "sqft": st.session_state.get("sq0", 0),
                        "base": st.session_state.get("b0", 46.0),
                        "custom_inc": st.session_state.get("ci0", False),
                        "inc": st.session_state.get("r0", 3.0),
                        "lease_type": st.session_state.get("lt0", "Triple Net (NNN)"),
                        "opex": st.session_state.get("ox0", 12.0),
                        "opexinc": st.session_state.get("oi0", 3.0),
                        "park_cost": st.session_state.get("pc0", 150.0),
                        "park_spaces": st.session_state.get("ps0", 0),
                        "move_exp": st.session_state.get("mv0", 10.0),
                        "construction": st.session_state.get("cc0", 0.0),
                        "free": st.session_state.get("fr0", 3),
                        "ti": st.session_state.get("ti0", 50.0),
                        "add_cred": st.session_state.get("ac0", 0.0),
                        "disc": st.session_state.get("dr0", 0.0)
                    }
                    st.session_state.saved_scenarios[save_name] = current_scenario
                    st.success(f"Scenario '{save_name}' saved successfully!")
                else:
                    st.warning("Please enter a name for the scenario")
        
        with load_col:
            st.markdown("##### 📂 Load Saved Scenario")
            if st.session_state.saved_scenarios:
                scenario_names = list(st.session_state.saved_scenarios.keys())
                selected_scenario = st.selectbox("Select scenario to load", scenario_names, key="load_scenario")
                
                col1, col2 = st.columns([1, 1])
                with col1:
                    if st.button("Load", use_container_width=True):
                        scenario = st.session_state.saved_scenarios[selected_scenario]
                        # Update all session state variables
                        for key, value in scenario.items():
                            st.session_state[key + "0"] = value
                        st.success(f"Loaded scenario: {selected_scenario}")
                
                with col2:
                    if st.button("Delete", use_container_width=True):
                        del st.session_state.saved_scenarios[selected_scenario]
                        st.success(f"Deleted scenario: {selected_scenario}")
                        st.rerun()
            else:
                st.info("No saved scenarios available")
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Main configuration section
    st.markdown("### Configuration")
    compare = st.checkbox("🔁 Compare Multiple Options")
    count   = st.number_input("Number of Options", 1, 10, 1) if compare else 1

    inputs = []
    for i in range(int(count)):
        with st.expander(f"Scenario {i+1}", expanded=(i==0)):
            # Basic Information
            name      = st.text_input("Name", f"Option {i+1}", key=f"name{i}")
            start_dt  = st.date_input("Lease Commencement", date.today(), key=f"sd{i}")
            term_mos  = st.number_input("Lease Term (months)", 0, 600, 0, 1, key=f"tm{i}")
            sqft      = st.number_input("Rentable SF", 0, 200000, 0, 1, key=f"sq{i}")
            st.markdown("---")

            # Rent and Operating Expenses Section
            rent_col, opex_col = st.columns(2)
            
            with rent_col:
                st.markdown("#### Base Rent")
                base = st.number_input("Base Rent ($/SF/yr)", 0.0, 1000.0, 46.0, 0.01, key=f"b{i}")
                custom_inc = st.checkbox("Custom Rent ↑ per Year", key=f"ci{i}")
                if custom_inc:
                    yrs = term_mos//12 + (1 if term_mos%12 else 0)
                    rent_incs = [st.number_input(f"Year {y} ↑ (%)", 0.0, 100.0, 0.0, 0.1, key=f"yrinc_{i}_{y}") for y in range(1,yrs+1)]
                else:
                    rent_incs = None
                    inc = st.number_input("Default Rent ↑ (%)", 0.0, 100.0, 3.0, 0.1, key=f"r{i}")
            
            with opex_col:
                st.markdown("#### Operating Expenses")
                lease_type = st.selectbox(
                    "Lease Type",
                    ["Full Service (Gross)", "Triple Net (NNN)"],
                    key=f"lt{i}"
                )

                if lease_type == "Triple Net (NNN)":
                    opex = st.number_input("OPEX ($/SF/yr)", 0.0, 500.0, 12.0, 0.01, key=f"ox{i}")
                    opexinc = st.number_input("OPEX ↑ (%)", 0.0, 100.0, 3.0, 0.1, key=f"oi{i}")
                    opex_base = None  # NNN pays everything
                else:
                    opex = 0.0  # Full Service doesn't pay OPEX
                    opexinc = 0.0  # No OPEX increase for Full Service
                    opex_base = None  # No base year for Full Service

            st.markdown("---")

            # Parking Section
            st.markdown("#### Parking")
            fxp = st.checkbox("Fixed Parking Spaces", key=f"fxp{i}")
            if fxp:
                park_spaces = st.number_input("Spaces", 0,500,0,1, key=f"ps{i}")
            else:
                ratio = st.number_input("Ratio (spaces/1k SF)", 0.0,100.0,0.0,0.1, key=f"rt{i}")
                park_spaces = int(round(ratio*(sqft or 0)/1000))
                st.caption(f"→ {park_spaces} spaces")
            park_cost = st.number_input("Parking $/space/mo", 0.0,500.0,150.0,0.01, key=f"pc{i}")
            st.markdown("---")

            # Additional Costs Section
            st.markdown("#### Additional Costs")
            mv_sf = st.number_input("Moving Exp ($/SF)", 0.0,500.0,10.0,0.01, key=f"mv{i}")
            const_sf = st.number_input("Construction Exp ($/SF)", 0.0,1000.0,0.0,0.01, key=f"cc{i}")

            # Abatement Section
            st.markdown("#### Abatement")
            cust_ab = st.checkbox("Custom Abatement per Year", key=f"cab{i}")
            if cust_ab:
                yrs = term_mos//12 + (1 if term_mos%12 else 0)
                abates = [st.number_input(f"Year {y} Abate (mo)", 0, term_mos, 0,1, key=f"abate_{i}_{y}") for y in range(1,yrs+1)]
                free_mo = 0
            else:
                abates = None
                free_mo = st.number_input("Rent Abatement (mo)", 0,24,3,1, key=f"fr{i}")

            # TI Allowance Section
            st.markdown("#### TI Allowance")
            ti_fx = st.checkbox("Fixed TI Allowance (total $)", key=f"tifx{i}")
            if ti_fx:
                tot = st.number_input("TI Allowance (total $)",0.0,1e7,0.0,1.0, key=f"titot{i}")
                ti_sf = tot/(sqft or 1)
            else:
                ti_sf = st.number_input("TI Allowance ($/SF)",0.0,500.0,50.0,1.0, key=f"ti{i}")

            # Additional Credits Section
            st.markdown("#### Additional Credits")
            ac_fx = st.checkbox("Fixed Additional Credits (total $)", key=f"acfx{i}")
            if ac_fx:
                ac_tot = st.number_input("Additional Credits (total $)",0.0,1e7,0.0,1.0, key=f"ac_tot{i}")
                add_cred = ac_tot/(sqft or 1)
            else:
                add_cred = st.number_input("Additional Credits ($/SF)",0.0,500.0,0.0,0.01, key=f"ac{i}")

            # Discount Rate
            st.markdown("#### Financial Parameters")
            disc_pct = st.number_input("Discount Rate (%)",0.0,100.0,0.0,0.01, key=f"dr{i}")

            inputs.append({
                "name":          name,
                "start_date":    start_dt,
                "term_mos":      term_mos,
                "sqft":          sqft,
                "base":          base,
                "inc":           inc if not custom_inc else None,
                "rent_incs":     rent_incs,
                "lease_type":    lease_type,
                "opex_base":     opex_base,
                "opex":          opex,
                "opexinc":       opexinc,
                "park_cost":     park_cost,
                "park_spaces":   park_spaces,
                "move_exp":      mv_sf,
                "construction":  const_sf,
                "free":          free_mo,
                "ti":            ti_sf,
                "add_cred":      add_cred,
                "disc":          disc_pct,
                "custom_abate":  cust_ab,
                "abates":        abates,
            })

    st.markdown("<p style='font-size: 0.8em; color: gray;'>© 2025 Savills. All rights reserved.</p>", unsafe_allow_html=True)

    if st.button("Run Analysis"):
        st.session_state["results"] = [(p, *analyze_lease(p)) for p in inputs]
        st.query_params.update({"tab": "analysis"})


# ---- Analysis Tab ----
with tab_analysis:
    results = st.session_state.get("results", [])
    if not results:
        st.warning("Run analysis first in Inputs.")
    else:
        # Find the lowest total rent for highlighting
        total_rents = [float(r[1]["Total Cost"].replace("$", "").replace(",", "")) for r in results]
        min_total_rent = min(total_rents) if total_rents else None
        for idx, (p, s, wf) in enumerate(results):
            st.subheader(f"Scenario {idx+1}: {s['Option']}")

            # Highlight Total Rent: green for lowest, red for others
            is_lowest = float(s["Total Cost"].replace("$", "").replace(",", "")) == min_total_rent
            total_rent_color = "#008000" if is_lowest else "#d90429"
            st.markdown('#### Key Metrics')
            k1, k2, k3 = st.columns(3)
            with k1:
                st.markdown(f'<div style="font-size:1.1em;font-weight:bold;">Total Rent</div>', unsafe_allow_html=True)
                st.markdown(f'<div style="font-size:1.7em;font-weight:bold;color:{total_rent_color}">{s["Total Cost"]}</div>', unsafe_allow_html=True)
            k2.metric("Avg Eff. Rent", s["Avg Eff. Rent"], help="Effective gross rent per SF per year, averaged across full years.")
            k3.metric("Net Present Value", s[next(k for k in s if k.startswith("NPV"))], help="Net present value of net cash flows using the given discount rate.")

            k4, k5, k6 = st.columns(3)
            k4.metric("Payback", s["Payback"], help="Months to recoup TI allowance and abatement via rent.")
            k5.metric("Moving Exp", s["Moving Exp"], help="Moving cost calculated as $/SF × SF.")
            k6.metric("Additional Credit", s["Additional Credit"], help="Other landlord incentives such as cash allowances or early occupancy.")

            st.markdown('#### Construction')
            c1, c2, c3 = st.columns(3)
            c1.metric("Tenant Improvement Allowance", s["TI Allowance"], help="Total tenant improvement allowance (TI $/SF × SF).")
            c2.metric("Construction Cost", s["Construction Cost"], help="Total construction cost based on $/SF input.")
            ti_allowance = float(s["TI Allowance"].replace("$", "").replace(",", ""))
            construction_cost = float(s["Construction Cost"].replace("$", "").replace(",", ""))
            tenant_expense = construction_cost - ti_allowance
            c3.metric("Tenant's Construction Expense", f"${tenant_expense:,.0f}", help="Construction Cost minus TI Allowance.")

            st.markdown('---')

            # Annual Cost Breakdown Chart
            st.markdown("### 📈 Annual Cost Breakdown")
            cost_fig = go.Figure()
            for name in ["Base Rent", "Opex", "Parking Exp", "Moving Expense"]:
                cost_fig.add_trace(go.Bar(name=name, x=wf["Year"], y=wf[name]))
            cost_fig.update_layout(
                barmode="stack",
                title="Annual Cost Breakdown",
                xaxis_title="Year",
                yaxis_title="Cost ($)",
                margin=dict(t=30, b=30),
                legend_title_text="Category"
            )
            st.plotly_chart(cost_fig, use_container_width=True)

            # Rent Schedule Table
            with st.expander("📋 Rent Schedule"):
                disp = wf.copy()
                # Format all numeric columns as currency
                for col in disp.columns:
                    if col not in ['Period', 'Year']:
                        disp[col] = disp[col].map(lambda x: f"${int(x):,}" if isinstance(x, (int, float)) else x)
                # Ensure Net Rent is positive and formatted as currency
                if 'Net Rent' in disp.columns:
                    disp['Net Rent'] = disp['Net Rent'].apply(lambda x: f"${abs(int(str(x).replace('$','').replace(',','').replace('-',''))):,}" if isinstance(x, str) and any(c.isdigit() for c in x) else x)
                # Styling for yellow highlight, green font, and thick black borders
                def style_table(row):
                    styles = [''] * len(row)
                    if row.name == 'Net Rent':
                        styles = ['background-color: #ffffcc'] * len(row)
                    if row.name in ['Rent Abatement', 'Additional Credit']:
                        styles = ['color: #008000; font-weight: bold;'] * len(row)
                    if row.name in ['Parking Exp', 'Rent Abatement']:
                        styles = [s + ';border-bottom: 4px solid #000' for s in styles]
                    return styles
                disp = disp.set_index('Year').T
                st.dataframe(disp.style.apply(style_table, axis=1), use_container_width=True)
            st.markdown("---")

# ---- Comparison Tab ----
with tab_comparison:
    results = st.session_state.get("results", [])
    if len(results) < 2:
        st.info("Enable compare & run ≥2 scenarios.")
    else:
        # Build comparison DataFrame with Lease Type
        df = pd.DataFrame([{
            **r[1],  # summary
            "Lease Type": r[0].get("lease_type", "")
        } for r in results])

        st.markdown("## Comparison Summary")
        st.dataframe(df, use_container_width=True)

        # Excel export
        if not df.empty:
            excel_buf = io.BytesIO()
            with pd.ExcelWriter(excel_buf, engine="openpyxl") as writer:
                df.to_excel(writer, sheet_name="Summary", index=False)
            st.download_button("📥 Download Comparison Excel", excel_buf.getvalue(),
                               file_name="comparison.xlsx",
                               mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

            # PDF export
            if st.button("📄 Generate PDF Summary"):
                pdf = FPDF()
                pdf.set_auto_page_break(auto=True, margin=15)
                pdf.add_page()
                pdf.image("savills_logo.png", x=10, y=10, w=40)
                pdf.ln(20)  # space below the logo


                pdf.set_font("Arial", 'B', 16)
                pdf.cell(0, 10, "Lease Scenario Comparison Summary", ln=True)

                pdf.set_font("Arial", '', 10)
                col_width = pdf.w / (len(df.columns) + 1)
                pdf.ln(5)
                for col in df.columns:
                    pdf.cell(col_width, 8, str(col), border=1)
                pdf.ln()
                for _, row in df.iterrows():
                    for val in row:
                        pdf.cell(col_width, 8, str(val), border=1)
                    pdf.ln()

                # Add individual scenario summaries
                for idx, result in enumerate(results):
                    p, s, wf = result

                    pdf.add_page()
                    pdf.image("savills_logo.png", x=10, y=10, w=40)
                    pdf.ln(20)  # space below the logo

                    pdf.set_font("Arial", 'B', 14)
                    pdf.cell(0, 10, f"Scenario {idx+1}: {s['Option']}", ln=True)

                    pdf.set_font("Arial", '', 11)
                    for k, v in s.items():
                        pdf.cell(0, 8, f"{k}: {v}", ln=True)

                    import tempfile
                    from PIL import Image

                    # --- Create and save charts as images ---

                    # Annual Cost Breakdown Chart
                    cost_fig = go.Figure()
                    for name in ["Base Rent", "Opex", "Parking Exp"]:
                        cost_fig.add_trace(go.Bar(name=name, x=wf["Year"], y=wf[name]))
                    cost_fig.update_layout(
                        barmode="stack",
                        title="Annual Cost Breakdown",
                        xaxis_title="Year",
                        yaxis_title="Cost ($)",
                        margin=dict(t=30, b=30),
                        legend_title_text="Category"
                    )

                    # Net CF Breakdown Chart
                    netcf_fig = go.Figure()
                    netcf_fig.add_trace(go.Bar(name="Rent Abatement", x=wf["Year"], y=wf["Rent Abatement"]))
                    netcf_fig.add_trace(go.Bar(name="Net CF", x=wf["Year"], y=wf["Net CF"]))
                    netcf_fig.update_layout(
                        barmode="relative",
                        title="Net Cash Flow",
                        xaxis_title="Year",
                        yaxis_title="Net Impact ($)",
                        margin=dict(t=30, b=30),
                        legend_title_text="Component"
                    )

                    # Save both charts to temporary files
                    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as cost_tmp:
                        cost_fig.write_image(cost_tmp.name, format="png", width=700, height=400)
                        cost_img_path = cost_tmp.name

                    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as netcf_tmp:
                        netcf_fig.write_image(netcf_tmp.name, format="png", width=700, height=400)
                        netcf_img_path = netcf_tmp.name

                    # Insert into PDF
                    pdf.ln(5)
                    pdf.set_font("Arial", 'B', 12)
                    pdf.cell(0, 10, "Annual Cost Breakdown", ln=True)
                    pdf.image(cost_img_path, w=pdf.w - 30)

                    pdf.ln(5)
                    pdf.set_font("Arial", 'B', 12)
                    pdf.cell(0, 10, "Net Cash Flow Breakdown", ln=True)
                    pdf.image(netcf_img_path, w=pdf.w - 30)

                    # Cash-Flow Table
                    pdf.ln(5)
                    pdf.set_font("Arial", 'B', 12)
                    pdf.cell(0, 10, "Annual Cash Flow Table", ln=True)
                    pdf.set_font("Arial", '', 8)
                    cols = wf.columns.tolist()
                    for col in cols:
                        pdf.cell(25, 6, col[:15], border=1)
                    pdf.ln()
                    for _, row in wf.iterrows():
                        for val in row:
                            v = f"${int(val):,}" if isinstance(val, (int, float)) else str(val)
                            pdf.cell(25, 6, v[:15], border=1)
                        pdf.ln()

                # Stream to download
                pdf_output = io.BytesIO()
                pdf.output(pdf_output)
                st.download_button("📥 Download PDF Summary", data=pdf_output.getvalue(),
                                   file_name="Lease_Summary.pdf", mime="application/pdf")
        else:
            st.info("No data available for export.")
