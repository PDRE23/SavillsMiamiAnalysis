import pandas as pd
import numpy as np
import numpy_financial as npf
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta

def analyze_purchase(p):
    """Analyze property purchase parameters and return summary and cash flow data."""
    # Extract parameters
    property_value = p["property_value"]
    down_payment_pct = p["down_payment_pct"]
    loan_term_years = p["loan_term_years"]
    interest_rate = p["interest_rate"]
    purchase_date = p["purchase_date"]
    holding_period_years = p["holding_period_years"]
    annual_appreciation = p["annual_appreciation"]
    annual_rental_income = p.get("annual_rental_income", 0)
    annual_rental_increase = p.get("annual_rental_increase", 0)
    annual_property_tax = p.get("annual_property_tax", 0)
    annual_insurance = p.get("annual_insurance", 0)
    annual_maintenance = p.get("annual_maintenance", 0)
    annual_hoa = p.get("annual_hoa", 0)
    closing_costs_pct = p.get("closing_costs_pct", 3.0)
    discount_rate = p["discount_rate"]
    
    # Calculate loan details
    down_payment = property_value * (down_payment_pct / 100)
    loan_amount = property_value - down_payment
    monthly_rate = interest_rate / 100 / 12
    total_payments = loan_term_years * 12
    
    # Calculate monthly mortgage payment
    if loan_amount > 0:
        monthly_payment = npf.pmt(monthly_rate, total_payments, -loan_amount)
    else:
        monthly_payment = 0
    
    # Calculate closing costs
    closing_costs = property_value * (closing_costs_pct / 100)
    
    # Initialize cash flow tracking
    cfs, rows = [], []
    remaining_balance = loan_amount
    cumulative_equity = down_payment
    
    for year in range(holding_period_years + 1):
        # Calculate property value at this year
        current_property_value = property_value * (1 + annual_appreciation / 100) ** year
        
        # Calculate rental income for this year
        current_rental_income = annual_rental_income * (1 + annual_rental_increase / 100) ** year
        
        # Calculate annual expenses
        annual_expenses = annual_property_tax + annual_insurance + annual_maintenance + annual_hoa
        
        # Calculate mortgage payments for this year
        annual_mortgage_payments = monthly_payment * 12 if year < loan_term_years else 0
        
        # Calculate principal and interest breakdown for this year
        if year < loan_term_years:
            annual_interest = 0
            annual_principal = 0
            for month in range(12):
                interest_payment = remaining_balance * monthly_rate
                principal_payment = monthly_payment - interest_payment
                annual_interest += interest_payment
                annual_principal += principal_payment
                remaining_balance -= principal_payment
        else:
            annual_interest = 0
            annual_principal = 0
        
        # Calculate net cash flow for this year
        net_cash_flow = current_rental_income - annual_expenses - annual_mortgage_payments
        
        # For year 0, include purchase costs
        if year == 0:
            net_cash_flow -= (down_payment + closing_costs)
        
        # Calculate equity at end of year
        if year < loan_term_years:
            cumulative_equity = down_payment + (loan_amount - remaining_balance)
        else:
            cumulative_equity = current_property_value
        
        cfs.append(net_cash_flow)
        
        # Create row for detailed breakdown
        period_start = purchase_date + relativedelta(years=year)
        period_end = period_start + relativedelta(years=1) - timedelta(days=1)
        
        rows.append({
            "Year": year,
            "Period": f"{period_start:%m/%d/%Y} – {period_end:%m/%d/%Y}",
            "Property Value": round(current_property_value),
            "Rental Income": round(current_rental_income),
            "Property Tax": -round(annual_property_tax),
            "Insurance": -round(annual_insurance),
            "Maintenance": -round(annual_maintenance),
            "HOA": -round(annual_hoa),
            "Mortgage Payment": -round(annual_mortgage_payments),
            "Principal": round(annual_principal),
            "Interest": -round(annual_interest),
            "Net Cash Flow": round(net_cash_flow),
            "Cumulative Equity": round(cumulative_equity)
        })
    
    # Calculate financial metrics
    total_investment = down_payment + closing_costs
    final_property_value = property_value * (1 + annual_appreciation / 100) ** holding_period_years
    total_return = final_property_value - total_investment + sum(cfs[1:])  # Exclude initial investment from cash flows
    
    # Calculate NPV
    npv = npf.npv(discount_rate / 100, cfs)
    
    # Calculate IRR
    try:
        irr = npf.irr(cfs) * 100 if len(cfs) > 1 else 0
    except:
        irr = 0
    
    # Calculate ROI
    roi = (total_return / total_investment) * 100 if total_investment > 0 else 0
    
    # Calculate payback period
    cumulative_cf = np.cumsum(cfs)
    payback_year = np.where(cumulative_cf >= 0)[0]
    payback = payback_year[0] if len(payback_year) > 0 else holding_period_years
    
    # Calculate cap rate
    cap_rate = (annual_rental_income / property_value) * 100 if property_value > 0 else 0
    
    # Calculate cash-on-cash return
    coc_return = (annual_rental_income - annual_property_tax - annual_insurance - 
                  annual_maintenance - annual_hoa - (monthly_payment * 12)) / total_investment * 100
    
    summary = {
        "Option": p["name"],
        "Purchase Date": purchase_date.strftime("%m/%d/%Y"),
        "Property Value": f"${property_value:,.0f}",
        "Down Payment": f"${down_payment:,.0f}",
        "Loan Amount": f"${loan_amount:,.0f}",
        "Monthly Payment": f"${monthly_payment:,.0f}",
        "Closing Costs": f"${closing_costs:,.0f}",
        "Total Investment": f"${total_investment:,.0f}",
        "Final Property Value": f"${final_property_value:,.0f}",
        "Total Return": f"${total_return:,.0f}",
        f"NPV ({discount_rate:.2f}%)": f"${npv:,.0f}",
        "IRR": f"{irr:.2f}%",
        "ROI": f"{roi:.2f}%",
        "Payback (years)": payback,
        "Cap Rate": f"{cap_rate:.2f}%",
        "Cash-on-Cash": f"{coc_return:.2f}%"
    }
    
    return summary, pd.DataFrame(rows)

def calculate_purchase_metrics(params):
    """Calculate purchase metrics based on input parameters."""
    # This function can be used for additional calculations if needed
    return analyze_purchase(params) 