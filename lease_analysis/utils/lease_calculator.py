import pandas as pd
import numpy as np
import numpy_financial as npf
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta

def analyze_lease(p):
    """Analyze lease parameters and return summary and cash flow data."""
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

        # abatement credit
        if custom_ab and abates:
            abate_credit = abates[i]/12 * base * sqft
        else:
            abate_credit = free_mo/12 * base * sqft if i == 0 else 0

        # total credit
        credit = abate_credit + (ti_credit_full if i==0 else 0)
        credit += (add_credit_full if i==0 else 0) + (move_credit_full if i==0 else 0)

        net = -gross + credit
        cfs.append(net)

        rows.append({
            "Year":           i+1,
            "Period":         f"{period_start:%m/%d/%Y} – {period_end:%m/%d/%Y}",
            "Base Cost":      round(b_year * sqft * frac),
            "Opex Cost":      round(o_year * sqft * frac),
            "Parking Exp":    round(p_year * sqft * frac),
            "Rent Abatement": -round(abate_credit) if abate_credit else 0,
            "Net CF":         round(net),
        })

    # metrics
    npv_raw = npf.npv(disc_pct/100, cfs)
    npv     = abs(npv_raw)
    occ     = sum(-cf for cf in cfs)

    # payback in months
    monthly_base = (base * sqft)/12 if base>0 else 0
    if monthly_base>0:
        total_abate_months = sum(abates) if custom_ab and abates else free_mo
        payback_mos = total_abate_months + (ti_credit_full + add_credit_full)/monthly_base
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

    return summary, pd.DataFrame(rows)

def calculate_lease_metrics(params):
    """Calculate lease metrics based on input parameters."""
    # Extract parameters
    lease_type = params["lease_type"]
    rent = params["rent"]
    area = params["area"]
    term = params["term"]
    escalations = params["escalations"] / 100
    discount_rate = params["discount_rate"] / 100
    
    # Calculate base costs
    base_rent = rent * area
    total_base_cost = base_rent * term
    
    # Calculate operating expenses for Net and Modified Gross leases
    if lease_type in ["Net", "Modified Gross"]:
        cam = params["cam"] * area
        insurance = params["insurance"] * area
        taxes = params["taxes"] * area
        utilities = params["utilities"] * area
        
        total_opex = (cam + insurance + taxes + utilities) * term
    else:
        total_opex = 0
    
    # Calculate total cost
    total_cost = total_base_cost + total_opex
    
    # Create cash flow DataFrame
    periods = range(1, term + 1)
    cash_flow = pd.DataFrame({
        "Period": periods,
        "Base Rent": [base_rent * (1 + escalations) ** (p-1) for p in periods]
    })
    
    if lease_type in ["Net", "Modified Gross"]:
        cash_flow["CAM"] = [cam * (1 + escalations) ** (p-1) for p in periods]
        cash_flow["Insurance"] = [insurance * (1 + escalations) ** (p-1) for p in periods]
        cash_flow["Taxes"] = [taxes * (1 + escalations) ** (p-1) for p in periods]
        cash_flow["Utilities"] = [utilities * (1 + escalations) ** (p-1) for p in periods]
    
    # Calculate financial metrics
    cash_flows = -cash_flow.drop("Period", axis=1).sum(axis=1).values
    npv = npf.npv(discount_rate, cash_flows)
    irr = npf.irr(cash_flows)
    roi = (total_cost - npv) / npv * 100 if npv != 0 else 0
    
    # Calculate payback period
    cumulative = np.cumsum(cash_flows)
    payback = np.where(cumulative >= 0)[0]
    payback = payback[0] + 1 if len(payback) > 0 else term
    
    # Create summary dictionary
    summary = {
        "Option": f"{lease_type} Lease",
        "Total Cost": total_cost,
        "NPV": npv,
        "IRR": irr * 100,
        "ROI": roi,
        "Payback": payback,
        "Avg. Annual Cost": total_cost / term
    }
    
    return summary, cash_flow 