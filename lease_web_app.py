import os
from fpdf import FPDF
from PIL import Image
import tempfile
import streamlit as st
import pandas as pd
import numpy as np
import numpy_financial as npf
import io
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
import plotly.graph_objects as go
import streamlit.components.v1 as components

# Add cache-control headers
st.set_page_config(
    page_title="Savills Lease Analyzer",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'Get Help': None,
        'Report a bug': None,
        'About': None
    }
)

# Add no-cache headers
components.html(
    """
    <script>
        // Clear browser cache on load
        window.onload = function() {
            if(!window.location.hash) {
                window.location = window.location + '#loaded';
                window.location.reload();
            }
        }
    </script>
    """,
    height=0
)

# Initialize session state
if 'saved_scenarios' not in st.session_state:
    st.session_state.saved_scenarios = {}
if 'count' not in st.session_state:
    st.session_state.count = 1

# Function to get asset path
def get_asset_path(filename):
    try:
        # Check if running on Streamlit Cloud
        if os.getenv('STREAMLIT_SHARING') or os.getenv('STREAMLIT_SERVER_URL'):
            return os.path.join(os.path.dirname(__file__), filename)
        return filename
    except Exception:
        return filename

# Load logo safely
def load_logo():
    try:
        logo_path = get_asset_path("savills_logo.png")
        return Image.open(logo_path)
    except Exception as e:
        return None

def explain(label, tooltip):
    return f'{label} <span title="{tooltip}">ℹ️</span>'

# --- Analysis Function ---
def analyze_lease(p):
    # Get base term and calculate total abatement months
    base_term_mos = max(p["term_mos"], 1)
    total_abate_months = sum(p.get("abates", [])) if p["custom_abate"] else p["free"]
    
    # Extend term by abatement months only if not inside term
    inside_term = p.get("inside_term", False)
    term_mos = base_term_mos if inside_term else base_term_mos + total_abate_months
    
    start_date  = p["start_date"]
    initial_sqft = max(p["sqft"], 1)
    exp_month = p.get("exp_month", 0)
    exp_sqft = p.get("exp_sqft", 0)
    total_sqft = initial_sqft + exp_sqft if exp_month > 0 else initial_sqft
    
    base        = p["base"]
    lease_type = p.get("lease_type", "Triple Net (NNN)")
    opex_base = p.get("opex_base", 0.0)
    opex        = p["opex"]
    opexinc     = p["opexinc"]
    park_cost   = p["park_cost"]
    park_spaces = p["park_spaces"]
    park_detail = p.get("park_detail")
    park_inc    = park_detail.get('park_inc', 0.0) if park_detail else 0.0
    free_mo     = p["free"]
    ti_sf       = p["ti"]
    add_cred    = p["add_cred"]
    move_sf     = p["move_exp"]
    ffe_sf      = p.get("ffe", 0.0)  # Get FF&E cost
    const_sf    = p.get("construction", 0.0)
    disc_pct    = p["disc"]
    inc_list    = p.get("rent_incs")
    custom_ab   = p["custom_abate"]
    abates      = p.get("abates")
    commission_pct = p.get("commission", 0.0)
    include_opex = p.get("include_opex", False)

    # determine number of periods
    full_years = term_mos // 12
    extra_mos  = term_mos % 12
    periods    = int(full_years + (1 if extra_mos else 0))

    # one-time credits & annual parking cost/SF
    ti_credit_full   = ti_sf * total_sqft  # Use total_sqft for TI
    add_credit_full  = add_cred * total_sqft  # Use total_sqft for additional credits
    move_ffe_full = (move_sf + ffe_sf) * initial_sqft  # Combine Moving and FF&E, use initial_sqft
    if park_detail:
        unres_total = park_detail['unres_cost'] * park_detail['unres_spaces'] * 12
        res_total = park_detail['res_cost'] * park_detail['res_spaces'] * 12
        p_year = (unres_total + res_total) / total_sqft
    else:
        p_year = park_cost * park_spaces * 12 / total_sqft
    construction_full = const_sf * total_sqft  # Use total_sqft for construction

    cfs, rows = [], []
    for i in range(periods):
        # Calculate current SF based on expansion timing
        current_month = i * 12 + (extra_mos if i == full_years else 12)
        current_sqft = total_sqft if exp_month > 0 and current_month >= exp_month else initial_sqft
        
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

        # Calculate parking with escalation
        if park_detail:
            unres_cost = park_detail['unres_cost'] * (1 + park_inc/100)**i
            res_cost = park_detail['res_cost'] * (1 + park_inc/100)**i
            unres_total = unres_cost * park_detail['unres_spaces'] * 12
            res_total = res_cost * park_detail['res_spaces'] * 12
            p_year = (unres_total + res_total) / current_sqft
        else:
            p_year = park_cost * park_spaces * 12 / current_sqft * (1 + park_inc/100)**i

        gross_full = (b_year + o_year + p_year) * current_sqft
        gross      = gross_full * frac
        move_ffe_exp = move_ffe_full if i == 0 else 0  # Combined Moving and FF&E expense

        # abatement credit
        if custom_ab and abates:
            if p.get("base_only_abate", False) and lease_type == "Triple Net (NNN)":
                # Only abate base rent for NNN lease
                abate_credit = abates[i]/12 * base * current_sqft if i < len(abates) else 0
            else:
                # Abate both base rent and OpEx
                abate_credit = abates[i]/12 * (base + o_year) * current_sqft if i < len(abates) else 0
        else:
            if p.get("base_only_abate", False) and lease_type == "Triple Net (NNN)":
                # Only abate base rent for NNN lease
                abate_credit = free_mo/12 * base * current_sqft if i == 0 else 0
            else:
                # Abate both base rent and OpEx
                abate_credit = free_mo/12 * (base + o_year) * current_sqft if i == 0 else 0

        # total credit (only abatement and additional credit)
        total_credit = abate_credit + (add_credit_full if i==0 else 0)

        # Net Rent calculation
        net_rent = gross + move_ffe_exp - total_credit

        # Calculate base components for total rent (excluding parking)
        base_components = b_year * current_sqft * frac  # Base rent
        opex_components = o_year * current_sqft * frac  # OpEx
        
        # Net cash flow for NPV should match total rent components (excluding parking)
        net_cf = -(base_components + opex_components) + total_credit
        cfs.append(net_cf)

        rows.append({
            "Year":           i+1,
            "Period":         f"{period_start:%m/%d/%Y} – {period_end:%m/%d/%Y}",
            "SF":            f"{current_sqft:,}",
            "Base Rent":      round(base_components),
            "Opex":           round(opex_components),
            "Parking Exp":    round(p_year * current_sqft * frac),
            "Rent Abatement": -round(abate_credit) if abate_credit else 0,
            "Moving & FF&E":  round(move_ffe_exp),
            "Additional Credit": -round(add_credit_full) if i==0 else 0,
            "Net Rent":       round(abs(net_rent)),
            "Base Components": round(base_components + opex_components),  # Track base components separately
        })

    # Calculate total rent (excluding parking)
    total_base_components = sum(row["Base Components"] for row in rows)
    
    # Add construction cost balance if it's positive (tenant pays extra)
    construction_balance = const_sf - ti_sf
    if construction_balance > 0:
        total_base_components += construction_balance * total_sqft

    # metrics
    npv_raw = npf.npv(disc_pct/100, cfs)
    npv     = abs(npv_raw)
    
    # Calculate total cost as sum of all net rent payments
    total_cost = sum(row["Net Rent"] for row in rows)

    # payback in months
    monthly_base = (base * total_sqft)/12 if base>0 else 0
    if monthly_base>0:
        total_abate_months = sum(abates) if custom_ab and abates else free_mo
        payback_mos = total_abate_months + (ti_credit_full)/monthly_base
        payback_lbl = f"{int(round(payback_mos))} mo"
    else:
        payback_lbl = "N/A"

    # average effective rent — un-prorated full years basis
    avg = total_cost/((full_years + (1 if extra_mos else 0))*total_sqft) if total_sqft>0 else 0

    # Calculate commission
    total_commission_base = 0
    for i in range(periods):
        current_month = i * 12 + (extra_mos if i == full_years else 12)
        current_sqft = total_sqft if exp_month > 0 and current_month >= exp_month else initial_sqft
        
        if custom_ab and abates:
            abate_months = abates[i] if i < len(abates) else 0
        else:
            abate_months = free_mo if i == 0 else 0
            
        if i < full_years:
            effective_months = 12 - abate_months
        else:
            effective_months = extra_mos - abate_months
            
        inc_pct = inc_list[i] if inc_list and i < len(inc_list) else p["inc"]
        base_year = base * (1 + inc_pct/100)**i
        
        if include_opex:
            raw_opex = opex * (1 + opexinc / 100) ** i
            if lease_type == "Full Service (Gross)":
                base_opex = opex_base or opex
                opex_year = max(0, raw_opex - base_opex)
            else:
                opex_year = raw_opex
            base_year += opex_year
            
        total_commission_base += base_year * current_sqft * (effective_months / 12)
        
    commission_amount = total_commission_base * (commission_pct / 100)

    summary = {
        "Option":            p["name"],
        "Start Date":        start_date.strftime("%m/%d/%Y"),
        "Base Term (mos)":   base_term_mos,
        "Total Term (mos)":  term_mos,
        "Abatement Type":    "Inside Term" if inside_term else "Added to Term",
        "Initial SF":        f"{initial_sqft:,}",
        "Size Change":       f"{exp_sqft:+,}" if exp_month > 0 else "-",  # Use + sign to show increase/decrease
        "Total SF":          f"{total_sqft:,}",
        "Total Cost":        f"${total_base_components:,.0f}",
        "Avg Eff. Rent":     f"${avg:,.2f} /SF/yr",
        "Payback":           payback_lbl,
        f"NPV ({disc_pct:.2f}%):": f"${npv:,.0f}",
        "TI Allowance":      f"${ti_credit_full:,.0f}",
        "Moving & FF&E":     f"${move_ffe_full:,.0f}",  # Combined Moving and FF&E
        "Construction Cost": f"${construction_full:,.0f}",
        "Additional Credit": f"${add_credit_full:,.0f}",
        "Commission Amount": commission_amount,
        "Commission Base":   total_commission_base,
        "Commission Rate":   commission_pct,
        "Include OpEx":      include_opex,
    }

    # Set Total Cost to sum of Net Rent
    if 'Net Rent' in rows:
        total_cost = sum(abs(net_rent) for net_rent in cfs)
        summary['Total Cost'] = f"${total_cost:,.0f}"

    return summary, pd.DataFrame(rows)


# -- Streamlit UI Setup --

# Global styling
st.markdown("""
    <style>
    /* Reset for Streamlit elements */
    [data-testid="stMarkdown"] {
        all: unset !important;
    }
    
    /* Remove any list styling */
    [data-testid="stMarkdown"] ul,
    [data-testid="stMarkdown"] ol,
    [data-testid="stMarkdown"] li {
        all: unset !important;
        list-style: none !important;
    }
    
    /* Header styles */
    .stMarkdown p {
        margin: 0 !important;
        padding: 0 !important;
    }
    
    /* Metric card styles */
    .metric-card {
        background-color: white;
        padding: 1.5rem;
        border-radius: 0.75rem;
        margin: 0.75rem 0;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        border: 1px solid #e0e0e0;
    }
    
    .metric-value {
        font-size: 1.5em;
        font-weight: 600;
        color: #0066cc;
        margin: 0.5rem 0;
    }
    
    .metric-description {
        font-size: 0.9em;
        color: #666;
    }
    
    /* Section spacing */
    .section-spacer {
        margin: 2rem 0;
    }

    /* Tab styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 24px;
    }

    .stTabs [data-baseweb="tab"] {
        font-size: 2.4rem !important;
        font-weight: 700;
    }

    .stTabs [data-baseweb="tab-list"] button {
        font-size: 2.4rem !important;
        font-weight: 700;
    }

    .stTabs [data-baseweb="tab-list"] button[aria-selected="true"] {
        font-weight: 900;
    }

    /* Workflow instruction styling */
    .workflow-instruction {
        background: #f8f9fa;
        border-radius: 8px;
        padding: 8px;
        margin-bottom: 16px;
        text-align: center;
        border: 1px solid #e9ecef;
    }
    </style>
""", unsafe_allow_html=True)

# Create header container
with st.container():
    col1, col2 = st.columns([0.85, 0.15])
    with col1:
        st.markdown('<h1 style="font-size: 4rem;">Lease Analyzer</h1>', unsafe_allow_html=True)
    with col2:
        pass  # Logo removed from header

st.caption("Created by Peyton Dowd")
st.markdown("---")

# Try to load the logo, with error handling
try:
    logo = load_logo()
    if logo:
        st.sidebar.image(logo, width=300)
except Exception as e:
    st.sidebar.warning("Logo not available")

tab_inputs, tab_analysis, tab_comparison = st.tabs(["Inputs","Analysis","Comparison"])

# Sidebar for inputs
with st.sidebar:
    st.subheader("Save/Load Analysis")
    
    # Test Data Section in an expander
    with st.expander("🧪 Test Data", expanded=False):
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Single Option", use_container_width=True):
                load_test_data()
                st.success("Single option test data loaded!")
                st.rerun()
        with col2:
            if st.button("Compare Two", use_container_width=True):
                load_comparison_test_data()
                st.success("Comparison test data loaded!")
                st.rerun()
    
    # Save/Load Section in an expander
    with st.expander("💾 Save & Load Scenarios", expanded=False):
        # Save Section
        st.markdown("##### Save Current Scenario")
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
                    "move_exp": st.session_state.get("mv0", 5.0),
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
        
        st.markdown("---")
        
        # Load Section
        st.markdown("##### Load Saved Scenario")
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

# Auto-collapse sidebar on page load
components.html(
    """
    <script>
    window.addEventListener('DOMContentLoaded', (event) => {
        const sidebarCollapseBtn = window.parent.document.querySelector('[data-testid="collapsedControl"]');
        if (sidebarCollapseBtn && !sidebarCollapseBtn.getAttribute('aria-expanded')) {
            sidebarCollapseBtn.click();
        }
    });
    </script>
    """,
    height=0,
    width=0
)

# ---- Inputs Tab ----
with tab_inputs:
    st.header("Configure & Compare Scenarios")
    count = st.number_input("Number of Scenarios", 1, 10, key="count")

    inputs = []
    for i in range(int(count)):
        with st.expander(f"Scenario {i+1}", expanded=(i==0)):
            # Space & Term Section
            st.markdown("#### Space & Term")
            
            # Basic Information
            name = st.text_input("Name", key=f"name{i}")
            if not name:  # If no name is provided, use default
                name = f"Option {i+1}"
            if f"sd{i}" not in st.session_state:
                st.session_state[f"sd{i}"] = date.today()
            start_dt = st.date_input("Lease Commencement", key=f"sd{i}")
            term_mos = st.number_input("Lease Term (months)", min_value=0, max_value=600, step=1, key=f"tm{i}")
            
            initial_sqft = st.number_input("Initial RSF", min_value=0, max_value=200000, step=1, key=f"sq{i}")
            has_size_change = st.checkbox("Include Size Change", key=f"exp{i}")
            
            if has_size_change:
                if term_mos > 0:
                    default_change_month = min(12, term_mos)
                    change_month = st.number_input("Change Month", min_value=1, max_value=term_mos, step=1, key=f"em{i}")
                    # Calculate which year the change occurs in
                    change_year = (change_month - 1) // 12 + 1
                    max_reduction = -initial_sqft if initial_sqft > 0 else 0
                    change_sqft = st.number_input("Size Change (±RSF)", min_value=max_reduction, max_value=200000, step=1, key=f"es{i}")
                    total_sqft = initial_sqft + change_sqft
                    if total_sqft > 0:
                        change_type = "expansion" if change_sqft > 0 else "reduction" if change_sqft < 0 else "no change"
                        if change_sqft != 0:
                            st.caption(f"→ {abs(change_sqft):,} SF {change_type} in month {change_month} (Year {change_year})")
                        st.caption(f"→ Total SF after change: {total_sqft:,}")
                    else:
                        st.error("Total SF cannot be negative or zero")
                        total_sqft = initial_sqft
                        change_sqft = 0
                else:
                    st.warning("Please set lease term before adding size change")
                    change_month = 0
                    change_sqft = 0
                    total_sqft = initial_sqft
            else:
                change_month = 0
                change_sqft = 0
                total_sqft = initial_sqft
            
            st.markdown("---")

            # Rent & Operating Costs Section
            st.markdown("#### Rent & Operating Costs")
            
            # Base Rent Subsection
            st.markdown("##### Base Rent")
            base = st.number_input("Base Rent ($/SF/yr)", min_value=0.0, max_value=1000.0, step=0.01, format="%.2f", key=f"b{i}")
            custom_inc = st.checkbox("Custom Rent ↑ per Year", key=f"ci{i}")
            if custom_inc:
                yrs = term_mos//12 + (1 if term_mos%12 else 0)
                rent_incs = [st.number_input(f"Year {y} ↑ (%)", min_value=0.0, max_value=100.0, step=0.01, format="%.2f", key=f"yrinc_{i}_{y}") for y in range(1, int(yrs)+1)]
            else:
                rent_incs = None
                inc = st.number_input("Base Rent ↑ (%)", min_value=0.0, max_value=100.0, step=0.01, format="%.2f", key=f"r{i}")

            # Operating Expenses Subsection
            st.markdown("##### Operating Expenses")
            lease_type = st.selectbox(
                "Lease Type",
                ["Full Service (Gross)", "Triple Net (NNN)"],
                key=f"lt{i}"
            )

            if lease_type == "Triple Net (NNN)":
                opex = st.number_input("OPEX ($/SF/yr)", min_value=0.0, max_value=500.0, step=0.01, format="%.2f", key=f"ox{i}")
                opexinc = st.number_input("Estimated OpEx ↑ (%)", min_value=0.0, max_value=100.0, step=0.01, format="%.2f", key=f"oi{i}")
                opex_base = None  # NNN pays everything
            else:
                opex = 0.0  # Full Service doesn't pay OPEX
                opexinc = 0.0  # No OPEX increase for Full Service
                opex_base = None  # No base year for Full Service

            # Parking Subsection
            st.markdown("##### Parking")
            fxp = st.checkbox("Fixed Parking Spaces", key=f"fxp{i}")
            if fxp:
                unres_spaces = st.number_input("Unreserved Spaces", min_value=0, max_value=500, step=1, key=f"ps_unres{i}")
                unres_cost = st.number_input("Unreserved $/space/mo", min_value=0.0, max_value=500.0, step=0.01, format="%.2f", key=f"pc_unres{i}")
                res_spaces = st.number_input("Reserved Spaces", min_value=0, max_value=500, step=1, key=f"ps_res{i}")
                res_cost = st.number_input("Reserved $/space/mo", min_value=0.0, max_value=1000.0, step=0.01, format="%.2f", key=f"pc_res{i}")
            else:
                unres_ratio = st.number_input("Unreserved Ratio (spaces/1k SF)", min_value=0.0, max_value=100.0, step=0.01, format="%.2f", key=f"rt_unres{i}")
                total_spaces = unres_ratio * (initial_sqft or 0) / 1000
                res_spaces = st.number_input("Reserved Spaces", min_value=0, max_value=500, step=1, key=f"ps_res{i}")
                unres_spaces = int(round(max(total_spaces - res_spaces, 0)))
                st.caption(f"→ {unres_spaces} unreserved, {res_spaces} reserved spaces")
                unres_cost = st.number_input("Unreserved $/space/mo", min_value=0.0, max_value=500.0, step=0.01, format="%.2f", key=f"pc_unres{i}")
                res_cost = st.number_input("Reserved $/space/mo", min_value=0.0, max_value=1000.0, step=0.01, format="%.2f", key=f"pc_res{i}")
            
            # Add parking escalation input
            park_inc = st.number_input("Estimated Annual Parking Cost ↑ (%)", min_value=0.0, max_value=100.0, step=0.01, format="%.2f", key=f"pi{i}")
            
            park_spaces = unres_spaces + res_spaces
            park_cost = (unres_cost * unres_spaces + res_cost * res_spaces) / (park_spaces if park_spaces else 1)
            park_detail = {
                'unres_spaces': unres_spaces,
                'unres_cost': unres_cost,
                'res_spaces': res_spaces,
                'res_cost': res_cost,
                'park_inc': park_inc
            }

            st.markdown("---")

            # Capital Expenses Section
            st.markdown("#### Capital Expenses")
            
            # Total Construction Cost Subsection
            st.markdown("##### Total Construction Cost")
            cc_fx = st.checkbox("Fixed Total Construction Cost (total $)", key=f"ccfx{i}")
            if cc_fx:
                cc_tot = st.number_input("Total Construction Cost (total $)", min_value=0.0, max_value=10000000.0, step=0.01, format="%.2f", key=f"cc_tot{i}")
                const_sf = cc_tot/(initial_sqft or 1)
                if initial_sqft > 0:
                    st.caption(f"→ ${const_sf:.2f}/SF")
            else:
                const_sf = st.number_input("Total Construction Cost ($/SF)", min_value=0.0, max_value=1000.0, step=0.01, format="%.2f", key=f"cc{i}")

            # Moving Expense Subsection
            st.markdown("##### Moving Cost")
            mv_fx = st.checkbox("Fixed Moving Cost (total $)", key=f"mvfx{i}")
            if mv_fx:
                mv_tot = st.number_input("Moving Cost (total $)", min_value=0.0, max_value=10000000.0, step=0.01, format="%.2f", key=f"mv_tot{i}")
                mv_sf = mv_tot/(initial_sqft or 1)
                if initial_sqft > 0:
                    st.caption(f"→ ${mv_sf:.2f}/SF")
            else:
                mv_sf = st.number_input("Moving Cost ($/SF)", min_value=0.0, max_value=500.0, step=0.01, format="%.2f", key=f"mv{i}")

            # FF&E Subsection
            st.markdown("##### FF&E")
            ffe_fx = st.checkbox("Fixed FF&E Expense (total $)", key=f"ffefx{i}")
            if ffe_fx:
                ffe_tot = st.number_input("FF&E Expense (total $)", min_value=0.0, max_value=10000000.0, step=0.01, format="%.2f", key=f"ffe_tot{i}")
                ffe_sf = ffe_tot/(initial_sqft or 1)
                if initial_sqft > 0:
                    st.caption(f"→ ${ffe_sf:.2f}/SF")
            else:
                ffe_sf = st.number_input("FF&E Exp ($/SF)", min_value=0.0, max_value=500.0, step=0.01, format="%.2f", key=f"ffe{i}")

            st.markdown("---")

            # Concessions Section
            st.markdown("#### Concessions")
            
            # Abatement Subsection
            st.markdown("##### Rent Abatement")
            lease_type = st.session_state.get(f"lt{i}", "Triple Net (NNN)")
            base_only = False  # Initialize base_only
            
            free_mo = st.number_input("Rent Abatement (mo)", min_value=0, max_value=24, step=1, key=f"fr{i}")
            cust_ab = st.checkbox("Custom Abatement per Year", key=f"cab{i}")
            
            if cust_ab:
                yrs = term_mos//12 + (1 if term_mos%12 else 0)
                abates = [st.number_input(f"Year {y} Abate (mo)", min_value=0, max_value=term_mos, step=1, key=f"abate_{i}_{y}") for y in range(1,yrs+1)]
                free_mo = 0
            else:
                abates = None
            
            inside_term = st.checkbox("Abatement inside of the Term", key=f"inside_term{i}", help="If checked, abatement months will not extend the lease term")
            if lease_type == "Triple Net (NNN)":
                base_only = st.checkbox("Abatement applies to Base Rent only", key=f"base_only{i}", help="If checked, tenant will continue to pay OpEx during abatement period")

            # TI Allowance Subsection
            st.markdown("##### TI Allowance")
            ti_fx = st.checkbox("Fixed TI Allowance (total $)", key=f"tifx{i}")
            if ti_fx:
                tot = st.number_input("TI Allowance (total $)", min_value=0.0, max_value=10000000.0, step=0.01, format="%.2f", key=f"titot{i}")
                ti_sf = tot/(initial_sqft or 1)
                if initial_sqft > 0:
                    st.caption(f"→ ${ti_sf:.2f}/SF")
            else:
                ti_sf = st.number_input("TI Allowance ($/SF)", min_value=0.0, max_value=500.0, step=0.01, format="%.2f", key=f"ti{i}")

            # Additional Credits Subsection
            st.markdown("##### Additional Credits")
            ac_fx = st.checkbox("Fixed Additional Credits (total $)", key=f"acfx{i}")
            if ac_fx:
                ac_tot = st.number_input("Additional Credits (total $)", min_value=0.0, max_value=10000000.0, step=0.01, format="%.2f", key=f"ac_tot{i}")
                add_cred = ac_tot/(initial_sqft or 1)
                if initial_sqft > 0:
                    st.caption(f"→ ${add_cred:.2f}/SF")
            else:
                add_cred = st.number_input("Additional Credits ($/SF)", min_value=0.0, max_value=500.0, step=0.01, format="%.2f", key=f"ac{i}")

            st.markdown("---")

            # Financial Parameters
            st.markdown("#### Financial Parameters")
            disc_pct = st.number_input("Discount Rate (%)", min_value=0.0, max_value=100.0, step=0.01, format="%.2f", key=f"dr{i}")
            
            # Commission Parameters (Internal Use)
            st.markdown("#### Commission (Internal)")
            st.caption("Internal use only - not shown in client-facing outputs")
            comm_pct = st.number_input("Commission Rate (%)", min_value=0.0, max_value=100.0, step=0.01, format="%.2f", key=f"cm{i}")
            include_opex = st.checkbox("Include OpEx in Commission Calculation", key=f"io{i}")

            inputs.append({
                "name":          name,
                "start_date":    start_dt,
                "term_mos":      term_mos,
                "sqft":          initial_sqft,
                "exp_month":     change_month,
                "exp_sqft":      change_sqft,
                "total_sqft":    total_sqft,
                "base":          base,
                "inc":           inc if not custom_inc else None,
                "rent_incs":     rent_incs,
                "lease_type":    lease_type,
                "opex_base":     opex_base,
                "opex":          opex,
                "opexinc":       opexinc,
                "park_cost":     park_cost,
                "park_spaces":   park_spaces,
                "park_detail":   park_detail,
                "move_exp":      mv_sf,
                "construction":  const_sf,
                "ffe":           ffe_sf,
                "free":          free_mo,
                "ti":            ti_sf,
                "add_cred":      add_cred,
                "disc":          disc_pct,
                "custom_abate":  cust_ab,
                "abates":        abates,
                "inside_term":   inside_term,
                "base_only_abate": base_only if lease_type == "Triple Net (NNN)" else False,
                "commission":    comm_pct,
                "include_opex":  include_opex,
            })

    # Run Analysis Button after inputs are created
    st.markdown("---")
    st.markdown("""
        <style>
        /* Main button styling */
        .stButton > button {
            background-color: #0066cc !important;
            color: white !important;
            font-size: 1.2em !important;
            font-weight: 500 !important;
            padding: 0.7em 1em !important;
            border-radius: 6px !important;
            border: none !important;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1) !important;
            transition: all 0.2s ease !important;
            width: 100% !important;
            margin: 0.5em 0 !important;
        }

        /* Hover state */
        .stButton > button:hover {
            background-color: #0052a3 !important;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.15) !important;
            transform: translateY(-1px) !important;
        }

        /* Active/Click state */
        .stButton > button:active {
            transform: translateY(0px) !important;
            box-shadow: 0 1px 2px rgba(0, 0, 0, 0.1) !important;
            background-color: #004080 !important;
        }
        </style>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        if st.button("🚀 Run Analysis", use_container_width=True):
            if len(inputs) > 0:
                st.session_state["results"] = [(p, *analyze_lease(p)) for p in inputs]
                st.query_params.update({"tab": "analysis"})
                st.success("Analysis complete! Switch to the Analysis tab to view results.")
            else:
                st.error("Please configure at least one scenario before running analysis.")

    st.markdown("---")
    st.markdown("<p style='font-size: 0.8em; color: gray;'>© 2025 Savills. All rights reserved.</p>", unsafe_allow_html=True)

# ---- Analysis Tab ----
with tab_analysis:
    results = st.session_state.get("results", [])
    if not results:
        st.warning("Run analysis first in Inputs.")
    else:
        for idx, (p, s, wf) in enumerate(results):
            st.header(f"Scenario {idx+1}: {s['Option']}")

            # Lease Summary Section
            st.markdown("### Lease Summary")
            
            # Create a container for the summary
            with st.container():
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    # Lease Term Section
                    with st.container():
                        st.markdown("#### Lease Term")
                        
                        # Get abatement details
                        abate_details = ""
                        if p.get("custom_abate") and p.get("abates"):
                            # For custom abatement, show which years have abatement
                            abate_years = [f"Year {i+1}: {months}mo" 
                                         for i, months in enumerate(p.get("abates")) 
                                         if months > 0]
                            if abate_years:
                                abate_details = f" ({', '.join(abate_years)})"
                        elif p.get("free", 0) > 0:
                            # For standard abatement, it's always in Year 1
                            abate_details = " (Year 1)"
                        
                        # Calculate total abatement
                        total_abate = sum(p.get("abates", [])) if p.get("custom_abate") else p.get("free", 0)
                        
                        # Determine abatement type label
                        if total_abate > 0:
                            if p.get("lease_type") == "Triple Net (NNN)":
                                if p.get("base_only_abate"):
                                    abate_type = "Base Rent Only"
                                else:
                                    abate_type = "Base Rent & OpEx"
                                abate_text = f"{total_abate} months{abate_details} ({abate_type})"
                            else:
                                abate_text = f"{total_abate} months{abate_details}"
                        else:
                            abate_text = "None"
                        
                        lease_term_df = pd.DataFrame([
                            ["Commencement", p.get("start_date", "").strftime("%m/%d/%Y") if p.get("start_date") else ""],
                            ["Base Term", f"{p.get('term_mos', '')} months"],
                            ["Months Abated", abate_text],
                            ["Total Term", f"{s.get('Total Term (mos)', '')} months"],
                            ["Expiration", (p.get("start_date") + relativedelta(months=s.get("Total Term (mos)", 0))).strftime("%m/%d/%Y") if p.get("start_date") else ""]
                        ], columns=['Label', 'Value'])
                        
                        styled_lease_term_df = lease_term_df.style\
                            .set_properties(**{'text-align': 'left'})\
                            .hide(axis=0)\
                            .hide(axis=1)
                        
                        st.dataframe(styled_lease_term_df, hide_index=True)
                    
                    # Square Footage Section
                    with st.container():
                        st.markdown("#### Square Footage")
                        # Calculate which year the change occurs in
                        if p.get('exp_month', 0) > 0:
                            change_year = (p.get('exp_month', 0) - 1) // 12 + 1
                            size_change_text = f"{p.get('exp_sqft', 0):+,} (Year {change_year})"
                        else:
                            size_change_text = "-"
                            
                        square_footage_df = pd.DataFrame([
                            ["Initial SF", f"{p.get('sqft', ''):,}"],
                            ["Size Change", size_change_text],
                            ["Total SF", f"{p.get('total_sqft', ''):,}"]
                        ], columns=['Label', 'Value'])
                        
                        styled_square_footage_df = square_footage_df.style\
                            .set_properties(**{'text-align': 'left'})\
                            .hide(axis=0)\
                            .hide(axis=1)
                        
                        st.dataframe(styled_square_footage_df, hide_index=True)
                    
                    # Capital Costs Section
                    with st.container():
                        st.markdown("#### Capital Costs")
                        construction_balance = p.get('construction', 0) - p.get('ti', 0)
                        balance_color = "red" if construction_balance > 0 else "green"
                        
                        # Create DataFrame for capital costs
                        capital_costs_df = pd.DataFrame([
                            ["Total Construction Cost", f"${p.get('construction', 0):,.2f} /SF"],
                            ["TI Allowance", f"${p.get('ti', 0):,.2f} /SF"],
                            ["Construction Cost Balance", f"${construction_balance:,.2f} /SF"],
                            ["Moving Cost", f"${p.get('move_exp', 0):,.2f} /SF"],
                            ["FF&E", f"${p.get('ffe', 0):,.2f} /SF"]
                        ], columns=['Label', 'Value'])
                        
                        # Apply styling
                        def style_df(df):
                            return pd.DataFrame(
                                [[''] * len(df.columns) if 'Construction Cost Balance' not in row['Label'] 
                                 else ['', f'color: {balance_color}'] for _, row in df.iterrows()],
                                index=df.index, columns=df.columns
                            )
                        
                        styled_df = capital_costs_df.style\
                            .set_properties(**{'text-align': 'left'})\
                            .apply(style_df, axis=None)\
                            .hide(axis=0)\
                            .hide(axis=1)
                        
                        st.dataframe(styled_df, hide_index=True)
                        st.caption("Note: A positive Construction Cost Balance (red) means additional tenant cost; negative (green) means tenant credit.")
                
                with col2:
                    # Base Rent Section
                    with st.container():
                        st.markdown("#### Base Rent")
                        base_rent_df = pd.DataFrame([
                            ["Base Rent", f"${p.get('base', 0):,.2f}"],
                            ["Type", p.get('lease_type', '')],
                            ["Escalation", f"{p.get('inc', 0)}%"]
                        ], columns=['Label', 'Value'])
                        styled_base_df = base_rent_df.style\
                            .set_properties(**{'text-align': 'left'})\
                            .hide(axis=0)\
                            .hide(axis=1)
                        st.dataframe(styled_base_df, hide_index=True)
                    
                    # Operating Expenses Section
                    with st.container():
                        st.markdown("#### Operating Expenses")
                        operating_expenses_df = pd.DataFrame([
                            ["OpEx Base Year", f"${p.get('opex', 0):,.2f}"],
                            ["Escalation", f"{p.get('opexinc', 0)}%"]
                        ], columns=['Label', 'Value'])
                        styled_opex_df = operating_expenses_df.style\
                            .set_properties(**{'text-align': 'left'})\
                            .hide(axis=0)\
                            .hide(axis=1)
                        st.dataframe(styled_opex_df, hide_index=True)
                        st.caption("*Estimated OpEx escalation")
                    
                    # Parking Section
                    with st.container():
                        st.markdown("#### Parking")
                        
                        # Create parking table with clean layout
                        parking_df = pd.DataFrame([
                            ["Ratio/1,000 SF", f"{p.get('park_spaces', 0)/(p.get('sqft', 1))*1000 if p.get('sqft', 1) else 0:.2f}"],
                            ["Unreserved Spaces", str(p.get('park_detail', {}).get('unres_spaces', 0))],
                            ["Unreserved Rate", f"${p.get('park_detail', {}).get('unres_cost', 0):,.2f}"],
                            ["Reserved Spaces", str(p.get('park_detail', {}).get('res_spaces', 0))],
                            ["Reserved Rate", f"${p.get('park_detail', {}).get('res_cost', 0):,.2f}"],
                            ["Escalation", f"{p.get('park_detail', {}).get('park_inc', 0)}%"]
                        ], columns=['Label', 'Value'])
                        
                        styled_parking_df = parking_df.style\
                            .set_properties(**{'text-align': 'left'})\
                            .hide(axis=0)\
                            .hide(axis=1)
                        
                        st.dataframe(styled_parking_df, hide_index=True)
                        
                        # Show escalation caption
                        st.caption("*Estimated parking escalation")

            st.divider()

            # Primary Financial Metrics
            st.markdown("### Primary Financial Metrics")
            
            k1, k2, k3 = st.columns(3)
            with k1:
                st.markdown("#### Total Rent Obligation")
                st.markdown(f'<div class="metric-value">{s["Total Cost"]}</div>', unsafe_allow_html=True)
                st.caption("(Excluding parking, including construction cost balance and additional credits)")
            
            with k2:
                st.markdown("#### Avg Eff. Rent")
                st.markdown(f'<div class="metric-value">{s["Avg Eff. Rent"]}</div>', unsafe_allow_html=True)
                st.caption("Average effective rent per SF per year")
            
            with k3:
                npv_key = next(k for k in s if k.startswith("NPV"))
                st.markdown(f"#### {npv_key}")
                st.markdown(f'<div class="metric-value">{s[npv_key]}</div>', unsafe_allow_html=True)
                st.caption("Present value of all lease payments and concessions using the given discount rate, excluding parking costs")

            st.divider()

            # Second row of metrics (without title)
            k4, k5, k6 = st.columns(3)
            with k4:
                st.markdown("#### Moving Cost")
                st.markdown(f'<div class="metric-value">${p.get("move_exp", 0)*initial_sqft:,.0f}</div>', unsafe_allow_html=True)
                st.caption("Total moving cost")
            
            with k5:
                st.markdown("#### FF&E")
                st.markdown(f'<div class="metric-value">${p.get("ffe", 0)*initial_sqft:,.0f}</div>', unsafe_allow_html=True)
                st.caption("Total FF&E cost")
            
            with k6:
                st.markdown("#### Additional Credit")
                st.markdown(f'<div class="metric-value">{s["Additional Credit"]}</div>', unsafe_allow_html=True)
                st.caption("Other landlord incentives")

            st.divider()

            # Third row of metrics (without title)
            c1, c2, c3 = st.columns(3)
            with c1:
                st.markdown("#### Construction Cost")
                st.markdown(f'<div class="metric-value">{s["Construction Cost"]}</div>', unsafe_allow_html=True)
                st.caption("Total construction cost")
            
            with c2:
                st.markdown("#### TI Allowance")
                st.markdown(f'<div class="metric-value">{s["TI Allowance"]}</div>', unsafe_allow_html=True)
                st.caption("Total tenant improvement allowance")
            
            with c3:
                def parse_currency(val):
                    return float(str(val).replace('$', '').replace(',', '').replace(' ', ''))
                tenant_expense = parse_currency(s["Construction Cost"]) - parse_currency(s["TI Allowance"])
                expense_color = "red" if tenant_expense > 0 else "green"
                st.markdown("#### Construction Cost Balance")
                st.markdown(f'<div class="metric-value" style="color: {expense_color}">${tenant_expense:,.0f}</div>', unsafe_allow_html=True)
                st.caption("Red: additional tenant cost; green: tenant credit")

            st.divider()

            # Annual Cost Breakdown Chart
            st.markdown("### Annual Cost Breakdown")
            
            # Chart without header
            cost_fig = go.Figure()
            for name in ["Base Rent", "Opex", "Parking Exp"]:
                if name in wf.columns:
                    cost_fig.add_trace(go.Bar(
                        name=name,
                        x=wf["Year"],
                        y=wf[name],
                    ))
            cost_fig.update_layout(
                barmode="stack",
                xaxis_title="Year",
                yaxis_title="Cost ($)",
                margin=dict(t=30, b=30, l=50, r=30),
                legend_title_text="",
                hovermode="x unified",
                template="plotly_white",
                showlegend=True,
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.02,
                    xanchor="center",
                    x=0.5
                )
            )
            st.plotly_chart(cost_fig, use_container_width=True)

            # Rent Schedule
            st.markdown("### Rent Schedule")
            
            # Create the rent schedule DataFrame (not transposed)
            rent_schedule = pd.DataFrame({
                "Period": wf["Period"].tolist(),
                "SF": wf["SF"].tolist(),
                # Base Rent and OpEx as PSF - divide total by SF
                "Base Rent PSF": [base / float(rsf.replace(',', '')) 
                                  for base, rsf in zip(wf["Base Rent"].tolist(), wf["SF"].tolist())],
                "OpEx PSF": [opex / float(rsf.replace(',', '')) 
                             for opex, rsf in zip(wf["Opex"].tolist(), wf["SF"].tolist())],
                # Total costs for other columns
                "Gross Rent": [base + opex for base, opex in zip(wf["Base Rent"].tolist(), wf["Opex"].tolist())],
                "Rent Abatement": wf["Rent Abatement"].tolist() if "Rent Abatement" in wf.columns else [0] * len(wf),
            })

            # Add Net Rent column
            rent_schedule["Net Rent"] = rent_schedule["Gross Rent"] + rent_schedule["Rent Abatement"]

            # Calculate full years and extra months
            full_years = p["term_mos"] // 12
            extra_mos = p["term_mos"] % 12

            # Create Year and Months columns
            year_labels = [f"Year {i+1}" for i in range(len(wf))]
            month_values = [12 if i < len(wf)-1 else (extra_mos if extra_mos > 0 else 12) for i in range(len(wf))]
            
            # Add Year and Months columns at the start
            rent_schedule.insert(0, "Year", year_labels)
            rent_schedule.insert(1, "Months", month_values)

            # Format currency columns
            psf_columns = ["Base Rent PSF", "OpEx PSF"]
            total_columns = ["Gross Rent", "Rent Abatement", "Net Rent"]

            # Format PSF columns
            for col in psf_columns:
                rent_schedule[col] = rent_schedule[col].apply(lambda x: f"${x:,.2f}")

            # Format total cost columns
            for col in total_columns:
                rent_schedule[col] = rent_schedule[col].apply(lambda x: f"${abs(x):,.0f}" if col != "Rent Abatement" else f"${x:,.0f}")

            # Create the style
            styled_schedule = rent_schedule.style

            # Apply base styling
            styled_schedule = styled_schedule.set_properties(**{
                'text-align': 'center',
                'padding': '8px',
                'white-space': 'nowrap'
            })

            # Apply specific column styles
            styled_schedule = styled_schedule.set_properties(**{
                'color': 'green'
            }, subset=['Rent Abatement'])

            styled_schedule = styled_schedule.set_properties(**{
                'background-color': '#FFEB9C'
            }, subset=['Net Rent'])

            # Style the first four columns
            styled_schedule = styled_schedule.set_properties(**{
                'color': '#666666',
                'font-size': '0.95em'
            }, subset=pd.IndexSlice[:, ['Year', 'Months', 'Period', 'SF']])

            # Add table styles
            styled_schedule = styled_schedule.set_table_styles([
                # Style for column headers
                {'selector': 'th', 'props': [
                    ('text-align', 'center'),
                    ('font-weight', 'bold'),
                    ('padding', '8px'),
                    ('white-space', 'nowrap'),
                    ('background-color', '#f8f9fa')
                ]},
                # Add borders between sections
                {'selector': 'td:nth-child(6)', 'props': [  # After OpEx (adjusted for new Months column)
                    ('border-right', '2px solid #e0e0e0')
                ]},
                {'selector': 'td:nth-child(8)', 'props': [  # After Gross Rent (adjusted for new Months column)
                    ('border-right', '2px solid #e0e0e0')
                ]},
                {'selector': 'th:nth-child(6)', 'props': [  # Header after OpEx (adjusted for new Months column)
                    ('border-right', '2px solid #e0e0e0')
                ]},
                {'selector': 'th:nth-child(8)', 'props': [  # Header after Gross Rent (adjusted for new Months column)
                    ('border-right', '2px solid #e0e0e0')
                ]}
            ])

            st.dataframe(styled_schedule, use_container_width=True)

            # Commission Section (Internal Only)
            if s["Commission Rate"] > 0:
                with st.expander("💰 Commission Details (Internal)", expanded=False):
                    st.markdown("#### Commission Calculation")
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.metric(
                            "Commission Amount",
                            f"${s['Commission Amount']:,.2f}",
                            help="Total commission based on selected rate and base"
                        )
                        st.caption(f"Rate: {s['Commission Rate']}%")
                    
                    with col2:
                        st.metric(
                            "Commission Base",
                            f"${s['Commission Base']:,.2f}",
                            help="Total amount commission is calculated on"
                        )
                        st.caption(f"Including OpEx: {'Yes' if s['Include OpEx'] else 'No'}")
                    
                    st.markdown("---")
                    st.markdown("##### Calculation Details")
                    st.markdown("""
                    - Base: {'Base Rent + OpEx' if s['Include OpEx'] else 'Base Rent Only'}
                    - Excludes: Abatement Months
                    - Calculation: Commission Base × Rate%
                    """)

            st.markdown("<p style='font-size: 0.8em; color: gray;'>© 2025 Savills. All rights reserved.</p>", unsafe_allow_html=True)

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
                
                # Try to add logo to PDF using the asset path function
                try:
                    logo_path = get_asset_path("savills_logo.png")
                    pdf.image(logo_path, x=10, y=10, w=40)
                except Exception:
                    # Continue without logo if not available
                    pass
                    
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
                        if name in wf.columns:
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
