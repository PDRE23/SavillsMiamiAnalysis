import streamlit as st
import pandas as pd
import numpy as np
import numpy_financial as npf
from datetime import date, timedelta, datetime
from dateutil.relativedelta import relativedelta
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import io
import base64
from fpdf import FPDF
import tempfile
import os
from PIL import Image
import json
import warnings
import requests
import yfinance as yf
from scipy import stats
from scipy.optimize import minimize
import xlsxwriter
warnings.filterwarnings('ignore')

# --- Page Configuration and CSS ---
st.set_page_config(
    page_title="Client Advisory Tool",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=Montserrat:wght@400;500;600;700&display=swap');
:root {
    --primary-blue: #002B5B;
    --secondary-blue: #007BFF;
    --light-blue: #E7F1FF;
    --dark-gray: #343A40;
    --medium-gray: #6C757D;
    --light-gray: #F8F9FA;
    --border-color: #DEE2E6;
}
.stApp {
    font-family: 'Inter', sans-serif !important;
    background-color: var(--light-gray);
}
h1, h2, h3, h4, h5, h6 {
    font-family: 'Montserrat', sans-serif !important;
    color: var(--primary-blue) !important;
}
.stButton>button {
    border-radius: 8px !important;
    font-weight: 600 !important;
}
.stMetric {
    background-color: #FFFFFF;
    border-left: 5px solid var(--primary-blue);
    border-radius: 8px;
    padding: 1rem;
    box-shadow: 0 2px 4px rgba(0,0,0,0.04);
}
</style>
""", unsafe_allow_html=True)

# --- State Management ---
def initialize_session_state():
    defaults = {
        'analysis_mode': 'Lease Analysis',
        'current_scenario': None,
        'purchase_results': None,
        'monte_carlo_results': None,
        'show_education': True,
        'show_advanced': False,
        'include_parking_in_eff_rent': True,
        'include_parking_in_npv': True,
        'use_base_year_stop': False
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

# --- Helper Functions ---
def get_image_as_base64(path):
    try:
        with open(path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode()
    except FileNotFoundError:
        return None
    except Exception as e:
        st.error(f"An error occurred while loading the logo: {e}")
        return None

# --- Main Application Logic ---
def main():
    initialize_session_state()

    # --- Header ---
    logo_base64 = get_image_as_base64("savills_logo.png")
    header_html = f"""
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 30px; padding: 1rem; background-color: #FFFFFF; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.05);">
        <div>
            <h1 style='font-family: "Montserrat", sans-serif; font-weight: 700; font-size: 36px; color: #002B5B; margin: 0;'>
                Client Advisory Tool
            </h1>
            <p style='font-family: "Inter", sans-serif; font-size: 16px; color: #575757; margin-top: 5px;'>
                Created by Peyton Dowd
            </p>
        </div>
        {'<img src="data:image/png;base64,{}" style="width: 200px; height: auto;">'.format(logo_base64) if logo_base64 else ''}
    </div>
    """
    st.markdown(header_html, unsafe_allow_html=True)

    # --- Sidebar ---
    with st.sidebar:
        st.markdown("### Analysis Mode")
        analysis_options = {
            "🚀 Lease Analysis": "Lease Analysis",
            "🏢 Purchase Analysis": "Purchase Analysis"
        }
        analysis_mode_label = st.radio(
            "Select Analysis Type",
            list(analysis_options.keys()),
            key="analysis_mode_radio"
        )
        st.session_state.analysis_mode = analysis_options[analysis_mode_label]

        st.markdown("### Settings")
        st.session_state.show_education = st.checkbox("📚 Show Educational Tips", value=st.session_state.show_education)

    # --- Page Routing ---
    if st.session_state.analysis_mode == "Lease Analysis":
        render_lease_analysis()
    elif st.session_state.analysis_mode == "Purchase Analysis":
        render_purchase_analysis()

# --- Lease Analysis Page ---
def render_lease_analysis():
    st.markdown("## 🚀 Lease Analysis")
    if st.session_state.show_education:
        with st.expander("📚 Understanding Lease Analysis", expanded=False):
            st.markdown("""
            Evaluates the total cost of a lease, accounting for all expenses and concessions over time.
            - **Base Year Stop:** In many gross or modified gross leases, the landlord covers operating expenses up to a "base year" amount. The tenant only pays for their share of any increases in subsequent years. You can enable this common structure with the checkbox below.
            """)

    # --- Inputs ---
    with st.container(border=True):
        st.markdown("#### Lease Structure")
        use_base_year_stop = st.checkbox("Enable Base Year Stop for Operating Expenses", value=st.session_state.use_base_year_stop, help="Changes the calculation from NNN to a modified gross structure with a base year stop.")
        st.session_state.use_base_year_stop = use_base_year_stop
        
        st.markdown("#### Key Lease Terms")
        c1, c2 = st.columns(2)
        term_mos = c1.number_input("Lease Term (Months)", 1, 600, 60, 1)
        sqft = c2.number_input("Square Footage (SF)", 1000, 1_000_000, 10000, 1000)

        rent_label = "Gross Rent ($/SF/yr)" if use_base_year_stop else "Base Rent ($/SF/yr)"
        base_rent = c1.number_input(rent_label, 10.0, 200.0, 45.0, 0.5)
        
        rent_escalation = c2.number_input("Annual Rent Escalation (%)", 0.0, 20.0, 3.0, 0.1)

        opex_label = "Base Year Opex ($/SF/yr)" if use_base_year_stop else "Operating Expenses ($/SF/yr)"
        opex = c1.number_input(opex_label, 0.0, 50.0, 20.0, 0.5)

        opex_escalation = c2.number_input("Annual OPEX Escalation (%)", 0.0, 20.0, 3.0, 0.1)
        
        st.markdown("#### Concessions & Initial Costs")
        c3, c4 = st.columns(2)
        free_rent_months = c3.number_input("Free Rent (Months)", 0, 24, 6, 1)
        ti_allowance = c4.number_input("TI Allowance ($/SF)", 0.0, 200.0, 75.0, 1.0)
        moving_expense = c3.number_input("Moving Expense ($/SF)", 0.0, 50.0, 5.0, 0.5)
        construction_costs = c4.number_input("Construction Costs ($/SF)", 0.0, 300.0, 100.0, 5.0)
        
        st.markdown("#### Parking Costs")
        c5, c6 = st.columns(2)
        parking_ratio = c5.number_input("Parking Ratio (Spaces per 1,000 SF)", 0.0, 10.0, 4.0, 0.1)
        num_reserved_spaces = c6.number_input("Number of Reserved Spaces", 0, 1000, 5, 1)
        reserved_cost_monthly = c5.number_input("Cost per Reserved Space ($/mo)", 0.0, 500.0, 250.0, 10.0)
        unreserved_cost_monthly = c6.number_input("Cost per Unreserved Space ($/mo)", 0.0, 500.0, 125.0, 10.0)
        
        st.markdown("#### Financial Assumptions")
        discount_rate = st.number_input("Discount Rate (%)", 0.0, 20.0, 8.0, 0.5)
        
        st.markdown("---")
        show_advanced = st.checkbox("Show Advanced Options (Custom Annual Escalations & SF)", value=st.session_state.show_advanced)
        st.session_state.show_advanced = show_advanced
        custom_escalations, custom_sqft = [], []
        if show_advanced:
            num_periods = (term_mos + 11) // 12
            for year in range(num_periods):
                cols = st.columns(2)
                custom_escalations.append(cols[0].number_input(f"Year {year+1} Rent Escalation (%)", -10.0, 50.0, rent_escalation, 0.1, key=f"esc_{year}"))
                custom_sqft.append(cols[1].number_input(f"Year {year+1} Square Footage", 0, 1_000_000, sqft, 100, key=f"sqft_{year}"))

        st.markdown("---")
        c7, c8 = st.columns(2)
        include_parking_in_eff_rent = c7.checkbox("Include Parking in Effective Rent", value=st.session_state.include_parking_in_eff_rent)
        st.session_state.include_parking_in_eff_rent = include_parking_in_eff_rent
        include_parking_in_npv = c8.checkbox("Include Parking in NPV (All-In)", value=st.session_state.include_parking_in_npv)
        st.session_state.include_parking_in_npv = include_parking_in_npv

        if st.button("🚀 Run Lease Analysis", type="primary", use_container_width=True):
            params = locals()
            st.session_state.current_scenario = calculate_lease_metrics(params)

    # --- Results Display ---
    if st.session_state.current_scenario:
        display_lease_analysis_results(st.session_state.current_scenario)

def calculate_lease_metrics(p):
    num_periods = (p['term_mos'] + 11) // 12
    
    # Weighted Avg SF
    if p['show_advanced'] and p['custom_sqft']:
        total_sf_months = sum(p['custom_sqft'][i] * (12 if i < num_periods - 1 else (p['term_mos'] % 12 or 12)) for i in range(num_periods))
        weighted_avg_sqft = total_sf_months / p['term_mos'] if p['term_mos'] > 0 else p['sqft']
    else:
        weighted_avg_sqft = p['sqft']

    # Cash Flows
    initial_outlay = (p['ti_allowance'] - p['construction_costs'] - p['moving_expense']) * p['sqft']
    future_rent, future_opex, future_parking = [], [], []
    detailed_costs = []
    
    current_base_rent = p['base_rent']
    for year in range(num_periods):
        months = 12 if year < num_periods - 1 else (p['term_mos'] % 12 or 12)
        year_sqft = p['custom_sqft'][year] if p['show_advanced'] and p['custom_sqft'] else p['sqft']
        year_esc = p['custom_escalations'][year] if p['show_advanced'] and p['custom_escalations'] else p['rent_escalation']

        if year > 0: current_base_rent *= (1 + year_esc / 100)
        months_to_pay = max(0, months - (p['free_rent_months'] if year == 0 else 0))
        
        period_rent = (current_base_rent * year_sqft) * (months_to_pay / 12)

        # Opex calculation with Base Year Stop logic
        current_year_opex_psf = p['opex'] * (1 + p['opex_escalation']/100)**year
        opex_pass_through_cost = 0
        nnn_opex_cost = 0
        
        if p['use_base_year_stop']:
            if year > 0:
                # Tenant pays the increase over the base year amount
                opex_increase_psf = max(0, current_year_opex_psf - p['opex'])
                opex_pass_through_cost = (opex_increase_psf * year_sqft) * (months / 12)
            # Total opex cost to tenant is just the pass-through
            period_opex = opex_pass_through_cost
        else:
            # Standard NNN opex calculation
            nnn_opex_cost = (current_year_opex_psf * year_sqft) * (months / 12)
            period_opex = nnn_opex_cost

        # One-time costs for display (only in year 1)
        ti_allowance_display = 0
        moving_expense_display = 0
        construction_costs_display = 0
        if year == 0:
            initial_sqft = p['custom_sqft'][0] if p['show_advanced'] and p['custom_sqft'] else p['sqft']
            ti_allowance_display = p['ti_allowance'] * initial_sqft
            moving_expense_display = -p['moving_expense'] * initial_sqft
            construction_costs_display = -p['construction_costs'] * initial_sqft


        total_spaces = (year_sqft / 1000) * p['parking_ratio']
        actual_res = min(p['num_reserved_spaces'], total_spaces)
        unreserved = total_spaces - actual_res
        period_parking = ((actual_res * p['reserved_cost_monthly'] * 12) + (unreserved * p['unreserved_cost_monthly'] * 12)) * (months / 12)

        future_rent.append(-period_rent); future_opex.append(-period_opex); future_parking.append(-period_parking)
        detailed_costs.append({
            "Year": f"Year {year+1} ({months} mos)", 
            "Rent": period_rent, 
            "NNN Operating Expenses": nnn_opex_cost,
            "Opex Pass-Throughs": opex_pass_through_cost,
            "Parking Costs": period_parking, 
            "TI Allowance": ti_allowance_display,
            "Moving Expense": moving_expense_display,
            "Construction Costs": construction_costs_display,
            "Total Annual Cost": period_rent + period_opex + period_parking
        })
    
    # NPV Calculations
    npv_rent = npf.npv(p['discount_rate']/100, future_rent)
    npv_opex = npf.npv(p['discount_rate']/100, future_opex)
    npv_parking = npf.npv(p['discount_rate']/100, future_parking)
    
    npv_all_in = initial_outlay + npv_rent + npv_opex
    if p['include_parking_in_npv']:
        npv_all_in += npv_parking
    
    # Effective Rent Calculation
    total_cost_eff_rent = -(initial_outlay + npv_rent + npv_opex)
    if p['include_parking_in_eff_rent']:
        total_cost_eff_rent -= npv_parking
    avg_eff_rent = total_cost_eff_rent / (p['term_mos']/12) / weighted_avg_sqft if p['term_mos'] > 0 and weighted_avg_sqft > 0 else 0

    return {
        'npv_all_in': npv_all_in, 'avg_eff_rent': avg_eff_rent, 'detailed_costs': detailed_costs,
        'initial_outlay': initial_outlay, 'npv_rent': npv_rent, 'npv_opex': npv_opex, 'npv_parking': npv_parking,
        'total_cost_eff_rent': total_cost_eff_rent, 'term_years': p['term_mos']/12, 'weighted_avg_sqft': weighted_avg_sqft
    }

def display_lease_analysis_results(results):
    st.markdown("---")
    st.markdown("### 📊 Key Financial Metrics")
    
    # Restore the full metrics display
    c1, c2, c3 = st.columns(3)
    c1.metric("NPV (All-In)", f"${results['npv_all_in']:,.0f}", help="The total cost of the lease in today's dollars. A lower (more negative) number is better.")
    c2.metric("Avg. Effective Rent", f"${results['avg_eff_rent']:.2f} /SF/yr", help="The blended, annualized cost per square foot over the lease term.")
    
    total_nominal_cost = -results['initial_outlay'] + sum(d['Total Annual Cost'] for d in results['detailed_costs'])
    c3.metric("Total Nominal Cost", f"${total_nominal_cost:,.0f}", help="The sum of all payments over the lease term, not discounted.")

    c4, c5, c6 = st.columns(3)
    c4.metric("Tenant's TI Expense", f"${-results['initial_outlay']:,.0f}", help="The net out-of-pocket cost for tenant improvements and moving after the landlord's allowance. A positive value is a cost to the tenant.")
    c5.metric("Weighted Avg. SF", f"{results['weighted_avg_sqft']:,.0f} SF", help="The average square footage used for calculations, weighted by the duration of each SF amount.")
    c6.metric("Term (Years)", f"{results['term_years']:.2f} Years", help="The total lease term in years.")


    st.markdown("### 💵 Detailed Annual Costs")
    df = pd.DataFrame(results['detailed_costs']).set_index('Year')
    
    # Always show both opex columns for clarity, just rename the rent column
    if st.session_state.use_base_year_stop:
        df = df.rename(columns={'Rent': 'Gross Rent'})
    else:
        df = df.rename(columns={'Rent': 'Base Rent'})

    df = df.T # Transpose after preparing

    def highlight_total_row(row):
        if row.name == 'Total Annual Cost':
            return ['background-color: #FFF9C4'] * len(row)
        return [''] * len(row)

    def format_costs(df):
        # Format all numeric columns as currency first
        format_dict = {col: "${:,.0f}" for col in df.columns}
        
        # Function to color specific rows
        def style_specific_rows(row):
            styles = [''] * len(row)
            if row.name in ['Moving Expense', 'Construction Costs']:
                styles = ['color: red' if v < 0 else 'color: black' for v in row]
            return styles

        styled_df = df.style.format(format_dict) \
                            .apply(highlight_total_row, axis=1) \
                            .apply(style_specific_rows, axis=1)
        return styled_df

    st.dataframe(format_costs(df), use_container_width=True)


    with st.expander("Show Calculation Breakdowns"):
        st.markdown("##### Average Effective Rent Calculation")
        st.latex(fr'''
        \text{{Avg. Eff. Rent}} = \frac{{\text{{Total Economic Cost}}}}{{\text{{Term (Years)}} \times \text{{Weighted Avg. SF}}}} \\
        = \frac{{\${results['total_cost_eff_rent']:,.0f}}}{{{results['term_years']:.2f} \text{{ yrs}} \times {results['weighted_avg_sqft']:,.0f} \text{{ SF}}}} = \${results['avg_eff_rent']:.2f} \text{{ /SF/yr}}
        ''')
        st.markdown("##### NPV (All-In) Calculation")
        npv_parking_display = results['npv_parking'] if st.session_state.include_parking_in_npv else 0
        st.latex(fr'''
        \text{{NPV}} = \text{{Initial Outlay}} + \text{{NPV(Rent)}} + \text{{NPV(Opex)}} + \text{{NPV(Parking)}} \\
        = {results['initial_outlay']:,.0f} + ({results['npv_rent']:,.0f}) + ({results['npv_opex']:,.0f}) + ({npv_parking_display:,.0f}) = \\${results['npv_all_in']:,.0f}
        ''')

    # Restore the NPV explanation expander
    with st.expander("What is Net Present Value (NPV)?"):
        st.markdown(
            """
            **Net Present Value (NPV)** is a fundamental concept in finance that translates future cash flows into their equivalent value today. The core idea is that **a dollar today is worth more than a dollar tomorrow** because today's dollar can be invested and earn a return.

            - **Discount Rate:** This is the rate of return you could earn on an investment with similar risk. We use this rate to "discount" future cash flows back to their present value. A higher discount rate means future cash flows are worth less in today's terms.
            
            - **NPV > 0:** The investment is expected to generate more value than the initial cost, making it profitable.
            - **NPV < 0:** The investment is expected to result in a net loss. In a lease analysis, the NPV is almost always negative because it represents a cost. The goal is to choose the option with the *least negative* NPV.

            Our "NPV (All-In)" calculation gives you the complete picture by summing up:
            1.  **Initial Outlay:** The net cash you receive or pay at the start (e.g., TI Allowance minus your construction/moving costs). This is already a present value.
            2.  **NPV of Rent:** The present value of all future rent payments.
            3.  **NPV of Operating Expenses (Opex):** The present value of all future opex payments.
            4.  **NPV of Parking:** The present value of all future parking costs (if included).
            """
        )

# --- Purchase Analysis Page ---
def render_purchase_analysis():
    st.markdown("## 🏢 Purchase Analysis")
    if st.session_state.show_education:
        with st.expander("📚 Understanding Purchase Analysis", expanded=False):
            st.markdown("Analyzes a property acquisition, focusing on returns and investment viability.")

    col1, col2 = st.columns([2, 1])
    with col1:
        with st.container(border=True):
            st.markdown("#### Property & Loan")
            c1, c2 = st.columns(2)
            purchase_price = c1.number_input("Purchase Price", 1_000_000, 100_000_000, 5_000_000, 100_000)
            ltv = c2.number_input("Loan-to-Value (LTV) (%)", 0, 90, 70, 5)
            interest_rate = c1.number_input("Interest Rate (%)", 1.0, 15.0, 6.5, 0.1)
            amortization_years = c2.number_input("Amortization (Years)", 10, 30, 25, 1)

            st.markdown("#### Operations & Exit")
            c3, c4 = st.columns(2)
            noi = c3.number_input("Year 1 NOI", 100_000, 10_000_000, 250_000, 10_000)
            noi_growth = c4.number_input("Annual NOI Growth (%)", 0.0, 10.0, 3.0, 0.1)
            exit_cap_rate = c3.number_input("Exit Cap Rate (%)", 3.0, 12.0, 6.0, 0.1)
            analysis_period = c4.number_input("Analysis Period (Years)", 1, 30, 10, 1)

            if st.button("🚀 Run Purchase Analysis", type="primary", use_container_width=True):
                params = locals()
                st.session_state.purchase_results = calculate_purchase_metrics(params)
    
    with col2:
        if st.session_state.purchase_results:
            display_purchase_results(st.session_state.purchase_results)

def calculate_purchase_metrics(p):
    loan_amount = p['purchase_price'] * (p['ltv'] / 100)
    equity = p['purchase_price'] - loan_amount
    
    monthly_rate = p['interest_rate'] / 12 / 100
    num_payments = p['amortization_years'] * 12
    annual_debt_service = npf.pmt(monthly_rate, num_payments, -loan_amount) * 12 if monthly_rate > 0 else loan_amount / p['amortization_years']
    
    cash_flows = [-equity]
    current_noi = p['noi']
    for _ in range(p['analysis_period']):
        cash_flows.append(current_noi - annual_debt_service)
        current_noi *= (1 + p['noi_growth'] / 100)

    exit_price = current_noi / (p['exit_cap_rate'] / 100)
    remaining_loan = npf.fv(monthly_rate, p['analysis_period']*12, -annual_debt_service/12, -loan_amount) if monthly_rate > 0 else loan_amount - (annual_debt_service * p['analysis_period'])
    sale_proceeds = exit_price - remaining_loan
    cash_flows[-1] += sale_proceeds

    irr = npf.irr(cash_flows) * 100
    coc = cash_flows[1] / equity * 100 if equity > 0 else 0
    eqm = sum(cf for cf in cash_flows if cf > 0) / equity if equity > 0 else 0
    return {'irr': irr, 'cash_on_cash': coc, 'equity_multiple': eqm}

def display_purchase_results(results):
    st.markdown("#### Key Metrics")
    st.metric("IRR", f"{results['irr']:.2f}%")
    st.metric("Cash-on-Cash (Yr 1)", f"{results['cash_on_cash']:.2f}%")
    st.metric("Equity Multiple", f"{results['equity_multiple']:.2f}x")


# --- Application Start ---
if __name__ == "__main__":
    main()
