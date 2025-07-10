import streamlit as st
import pandas as pd
from lease_analysis.utils.purchase_calculator import analyze_purchase
from datetime import date

def create_purchase_input_form(i):
    """
    Create a form for property purchase input parameters.
    
    Args:
        i (int): Form index for unique keys
        
    Returns:
        dict: Dictionary containing the input parameters
    """
    with st.expander(f"Purchase Scenario {i+1}", expanded=(i==0)):
        # Make the scenario title larger and bold
        st.markdown(f'<span style="font-size:1.5em;font-weight:bold;">Purchase Scenario {i+1}</span>', unsafe_allow_html=True)
        
        # Basic property parameters
        name = st.text_input("Name", f"Purchase Option {i+1}", key=f"p_name{i}")
        purchase_date = st.date_input("Purchase Date", date.today(), key=f"p_purchase_date{i}")
        property_value = st.number_input("Property Value ($)", 0, 10000000, 500000, 10000, key=f"p_property_value{i}")
        holding_period_years = st.number_input("Holding Period (years)", 1, 50, 10, 1, key=f"p_holding_period{i}")
        st.markdown("---")
        
        # Financing parameters
        st.markdown("#### Financing")
        col1, col2 = st.columns(2)
        
        with col1:
            down_payment_pct = st.number_input("Down Payment (%)", 0.0, 100.0, 20.0, 1.0, key=f"p_down_payment_pct{i}")
            loan_term_years = st.number_input("Loan Term (years)", 0, 50, 30, 1, key=f"p_loan_term{i}")
        
        with col2:
            interest_rate = st.number_input("Interest Rate (%)", 0.0, 20.0, 5.0, 0.1, key=f"p_interest_rate{i}")
            closing_costs_pct = st.number_input("Closing Costs (%)", 0.0, 10.0, 3.0, 0.1, key=f"p_closing_costs_pct{i}")
        
        # Calculate and display loan details
        down_payment = property_value * (down_payment_pct / 100)
        loan_amount = property_value - down_payment
        st.info(f"Down Payment: ${down_payment:,.0f} | Loan Amount: ${loan_amount:,.0f}")
        
        st.markdown("---")
        
        # Property appreciation
        st.markdown("#### Property Appreciation")
        annual_appreciation = st.number_input("Annual Appreciation (%)", -10.0, 20.0, 3.0, 0.1, key=f"p_annual_appreciation{i}")
        
        st.markdown("---")
        
        # Rental income (optional)
        st.markdown("#### Rental Income (Optional)")
        include_rental = st.checkbox("Include Rental Income", key=f"p_include_rental{i}")
        
        if include_rental:
            col1, col2 = st.columns(2)
            with col1:
                annual_rental_income = st.number_input("Annual Rental Income ($)", 0, 1000000, 0, 1000, key=f"p_annual_rental_income{i}")
            with col2:
                annual_rental_increase = st.number_input("Annual Rental Increase (%)", 0.0, 20.0, 2.0, 0.1, key=f"p_annual_rental_increase{i}")
        else:
            annual_rental_income = 0
            annual_rental_increase = 0
        
        st.markdown("---")
        
        # Annual expenses
        st.markdown("#### Annual Expenses")
        col1, col2 = st.columns(2)
        
        with col1:
            annual_property_tax = st.number_input("Property Tax ($/year)", 0, 100000, 0, 100, key=f"p_property_tax{i}")
            annual_insurance = st.number_input("Insurance ($/year)", 0, 50000, 0, 100, key=f"p_insurance{i}")
        
        with col2:
            annual_maintenance = st.number_input("Maintenance ($/year)", 0, 100000, 0, 100, key=f"p_maintenance{i}")
            annual_hoa = st.number_input("HOA Fees ($/year)", 0, 50000, 0, 100, key=f"p_hoa{i}")
        
        st.markdown("---")
        
        # Analysis parameters
        st.markdown("#### Analysis Parameters")
        discount_rate = st.number_input("Discount Rate (%)", 0.0, 20.0, 8.0, 0.1, key=f"p_discount_rate{i}")
        
        return {
            "name": name,
            "purchase_date": purchase_date,
            "property_value": property_value,
            "down_payment_pct": down_payment_pct,
            "loan_term_years": loan_term_years,
            "interest_rate": interest_rate,
            "holding_period_years": holding_period_years,
            "annual_appreciation": annual_appreciation,
            "annual_rental_income": annual_rental_income,
            "annual_rental_increase": annual_rental_increase,
            "annual_property_tax": annual_property_tax,
            "annual_insurance": annual_insurance,
            "annual_maintenance": annual_maintenance,
            "annual_hoa": annual_hoa,
            "closing_costs_pct": closing_costs_pct,
            "discount_rate": discount_rate,
        }

def render_purchase_inputs_tab():
    """Render the purchase inputs tab with property parameters and analysis controls."""
    st.header("Configure Purchase Scenarios")
    st.markdown("<p style='font-size: 0.8em; color: gray;'>© 2025 Savills. All rights reserved.</p>", unsafe_allow_html=True)
    
    compare = st.checkbox("🔁 Compare Multiple Purchase Options")
    count = st.number_input("Number of Purchase Options", 1, 10, 1) if compare else 1
    
    inputs = []
    for i in range(int(count)):
        inputs.append(create_purchase_input_form(i))
    
    if st.button("Run Purchase Analysis"):
        results = []
        for params in inputs:
            try:
                summary, cash_flow = analyze_purchase(params)
                results.append((params, summary, cash_flow))
            except Exception as e:
                st.error(f"Error analyzing purchase scenario: {str(e)}")
                return
        
        st.session_state["purchase_results"] = results
        st.success("Purchase analysis completed! Check the Analysis tab for results.") 