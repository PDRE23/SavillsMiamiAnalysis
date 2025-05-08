import streamlit as st
import pandas as pd
import numpy_financial as npf
import io
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta

# --- Analysis Function ---
def analyze_lease(p):
    # unpack inputs
    term_mos    = max(p["term_mos"], 1)
    start_date  = p["start_date"]
    sqft        = max(p["sqft"], 1)
    base        = p["base"]
    inc         = p["inc"]
    opex        = p["opex"]
    opexinc     = p["opexinc"]
    park_cost   = p["park_cost"]
    park_spaces = p["park_spaces"]
    free_mo     = p["free"]
    ti_sf       = p["ti"]
    add_cred    = p["add_cred"]
    move_sf     = p["move_exp"]
    disc_pct    = p["disc"]

    # calculate periods
    full_years = term_mos // 12
    extra_mos  = term_mos % 12
    periods    = full_years + (1 if extra_mos else 0)

    # credits & cost
    abate_credit_full = free_mo/12 * base * sqft
    ti_credit_full    = ti_sf   * sqft
    add_credit_full   = add_cred * sqft
    move_credit_full  = move_sf * sqft
    p_year            = park_cost * park_spaces * 12 / sqft

    cfs, rows = [], []
    for i in range(periods):
        # period dates
        period_start = start_date + relativedelta(months=12*i)
        if i < full_years:
            period_end = period_start + relativedelta(years=1) - timedelta(days=1)
            frac = 1.0
        else:
            period_end = start_date + relativedelta(months=term_mos) - timedelta(days=1)
            frac = extra_mos / 12.0

        b_year = base * (1 + inc/100)**i
        o_year = opex * (1 + opexinc/100)**i

        gross_full = (b_year + o_year + p_year) * sqft
        gross      = gross_full * frac

        net = -gross
        if i == 0:
            net += abate_credit_full

        cfs.append(net)
        rows.append({
            "Year":           i+1,
            "Period":         f"{period_start:%m/%d/%Y} – {period_end:%m/%d/%Y}",
            "Base Cost":      round(b_year * sqft * frac),
            "Opex Cost":      round(o_year * sqft * frac),
            "Parking Exp":    round(p_year * sqft * frac),
            "Rent Abatement": -round(abate_credit_full) if i==0 else 0,
            "Net CF":         round(net),
        })

    # metrics
    irr      = npf.irr(cfs) if len(cfs) > 1 else None
    npv_raw  = npf.npv(disc_pct/100, cfs)
    npv      = abs(npv_raw)
    occ      = sum(-cf for cf in cfs)

    monthly_base = (base * sqft) / 12 if base > 0 else 0
    if monthly_base > 0:
        payback_mos = free_mo + (ti_credit_full + add_credit_full) / monthly_base
        payback_lbl = f"{int(round(payback_mos))} mo"
    else:
        payback_lbl = "N/A"

    avg = occ / (term_mos * sqft) if term_mos * sqft > 0 else 0

    summary = {
        "Option":            p["name"],
        "Start Date":        start_date.strftime("%m/%d/%Y"),
        "Term (mos)":        term_mos,
        "RSF":               sqft,
        "Total Cost":        f"${occ:,.0f}",
        "Avg Eff. Rent":     f"${avg:,.0f}",
        f"NPV ({disc_pct:.2f}%):": f"${npv:,.0f}",
        "TI Allowance":      f"${ti_credit_full:,.0f}",
        "Moving Exp":        f"${move_credit_full:,.0f}",
        "Additional Credit": f"${add_credit_full:,.0f}",
        "IRR":               f"{irr*100:.2f}%" if irr else "N/A",
        "Payback":           payback_lbl,
    }

    return summary, pd.DataFrame(rows)

# -- Streamlit UI --
st.set_page_config(page_title="Savills Lease Analyzer", layout="wide")
st.title("Savills | Lease Analyzer")
st.caption("Created by Peyton Dowd")
st.markdown("---")

tab_inputs, tab_analysis, tab_comparison = st.tabs(["Inputs","Analysis","Comparison"])

with tab_inputs:
    st.header("Configure & Compare Scenarios")
    compare = st.checkbox("🔁 Compare Multiple Options")
    count   = st.number_input("Number of Options", 1, 10, 1, step=1) if compare else 1

    inputs = []
    for i in range(int(count)):
        with st.expander(f"Scenario {i+1}", expanded=(i==0)):
            name     = st.text_input("Name", f"Option {i+1}", key=f"name{i}")
            start_dt = st.date_input("Lease Commencement", date.today(), key=f"sd{i}")
            term_mos = st.number_input("Lease Term (months)", 0, 600, 0, 1, key=f"tm{i}")
            sqft     = st.number_input("Rentable SF", 0, 200000, 0, 1, key=f"sq{i}")
            st.markdown("---")

            base    = st.number_input("Base Rent ($/SF/yr)",    0.0,1000.0,0.0,0.01, key=f"b{i}")
            inc     = st.number_input("Rent ↑ (%)",             0.0,100.0,0.0,0.01, key=f"r{i}")
            opex    = st.number_input("OPEX ($/SF/yr)",         0.0,500.0,0.0,0.01, key=f"ox{i}")
            opex_i  = st.number_input("OPEX ↑ (%)",             0.0,100.0,0.0,0.01, key=f"oi{i}")
            st.markdown("---")

            fixed   = st.checkbox("Fixed Parking Spaces", key=f"fx{i}")
            if fixed:
                park_spaces = st.number_input("Spaces", 0,500,0,1, key=f"ps{i}")
            else:
                ratio       = st.number_input("Ratio (spaces/1k SF)",0.0,100.0,0.0,0.01, key=f"rt{i}")
                park_spaces = int(round(ratio * (sqft or 0)/1000))
                st.caption(f"→ {park_spaces} spaces")
            park_cost= st.number_input("Parking $/space/mo",   0.0,500.0,0.0,0.01, key=f"pc{i}")
            st.markdown("---")

            mv_fixed = st.checkbox("Fixed Moving Expense (total $)", key=f"mv_fx{i}")
            if mv_fixed:
                mv_total  = st.number_input("Moving Expense (total $)", 0.0,1e7,0.0,1.0, key=f"mv_tot{i}")
                move_sf   = mv_total / (sqft or 1)
            else:
                move_sf   = st.number_input("Moving Expense ($/SF)", 0.0,500.0,0.0,0.01, key=f"mv{i}")
            st.markdown("---")

            free_mo   = st.number_input("Rent Abatement (mo)",   0,24,0,1,    key=f"fr{i}")

            ti_fixed  = st.checkbox("Fixed TI Allowance (total $)", key=f"ti_fx{i}")
            if ti_fixed:
                ti_total = st.number_input("TI Allowance (total $)",0.0,1e7,0.0,1.0,key=f"ti_tot{i}")
                ti_sf     = ti_total / (sqft or 1)
            else:
                ti_sf     = st.number_input("TI Allowance ($/SF)", 0.0,500.0,0.0,0.01, key=f"ti{i}")

            ac_fixed  = st.checkbox("Fixed Additional Credits (total $)", key=f"ac_fx{i}")
            if ac_fixed:
                ac_total = st.number_input("Additional Credits (total $)",0.0,1e7,0.0,1.0,key=f"ac_tot{i}")
                add_cred = ac_total / (sqft or 1)
            else:
                add_cred = st.number_input("Additional Credits ($/SF)", 0.0,500.0,0.0,0.01, key=f"ac{i}")

            st.markdown("---")
            disc_pct  = st.number_input("Discount Rate (%)",0.0,100.0,0.0,0.01, key=f"dr{i}")

        inputs.append({
            "name":        name,
            "start_date":  start_dt,
            "term_mos":    term_mos,
            "sqft":        sqft,
            "base":        base,
            "inc":         inc,
            "opex":        opex,
            "opexinc":     opex_i,
            "park_cost":   park_cost,
            "park_spaces": park_spaces,
            "move_exp":    move_sf,
            "free":        free_mo,
            "ti":          ti_sf,
            "add_cred":    add_cred,
            "disc":        disc_pct
        })

    if st.button("Run Analysis"):
        st.session_state["results"] = [analyze_lease(p) for p in inputs]

with tab_analysis:
    results = st.session_state.get("results", [])
    if not results:
        st.warning("Run analysis first.")
    else:
        for idx, (s, wf) in enumerate(results):
            st.subheader(f"Scenario {idx+1}: {s['Option']}")

            # summary metrics
            metric_items = [(k, v) for k, v in s.items()
                            if k not in ("Option","Start Date","Term (mos)","RSF","IRR")]
            # reorder to place NPV after Payback
            payback_idx = next((i for i, (k,_) in enumerate(metric_items) if k == "Payback"), None)
            npv_idx = next((i for i, (k,_) in enumerate(metric_items) if k.startswith("NPV")), None)
            if payback_idx is not None and npv_idx is not None:
                npv_item = metric_items.pop(npv_idx)
                if npv_idx < payback_idx:
                    payback_idx -= 1
                metric_items.insert(payback_idx+1, npv_item)
            cols = st.columns(len(metric_items))
            for col_obj, (k, v) in zip(cols, metric_items):
                col_obj.metric(k, v)

            st.markdown("#### Cash-Flow Waterfall")
            disp = wf.copy()
            for col in disp.columns:
                if col not in ("Period",):
                    disp[col] = disp[col].map(lambda x: f"${int(x):,}")
            st.dataframe(disp, use_container_width=True)

with tab_comparison:
    results = st.session_state.get("results", [])
    if len(results) < 2:
        st.info("Enable compare & run ≥2 scenarios.")
    else:
        df = pd.DataFrame([r[0] for r in results])
        st.markdown("## Comparison Summary")
        st.dataframe(df)

        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine="openpyxl") as w:
            df.to_excel(w, "Summary", index=False)
        st.download_button(
            "Download Comparison Excel",
            buf.getvalue(),
            file_name="comparison.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
