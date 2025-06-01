import streamlit as st
import pandas as pd
from lease_analysis.utils.lease_calculator import calculate_lease_metrics, analyze_lease
from lease_analysis.utils.ui_helpers import create_metric_section
from datetime import date

def create_input_form(i):
    """
    Create a form for lease input parameters.
    
    Args:
        i (int): Form index for unique keys
        
    Returns:
        dict: Dictionary containing the input parameters
    """
    with st.expander(f"Scenario {i+1}", expanded=(i==0)):
        # Make the scenario title larger and bold
        st.markdown(f'<span style="font-size:1.5em;font-weight:bold;">Scenario {i+1}</span>', unsafe_allow_html=True)
        # Basic lease parameters
        name = st.text_input("Name", f"Option {i+1}", key=f"name{i}")
        start_dt = st.date_input("Lease Commencement", date.today(), key=f"sd{i}")
        term_mos = st.number_input("Lease Term (months)", 0, 600, 0, 1, key=f"tm{i}")
        sqft = st.number_input("Rentable SF", 0, 200000, 0, 1, key=f"sq{i}")
        st.markdown("---")
        
        # Rent and OPEX parameters (grouped together)
        st.markdown("#### Rent & Operating Expenses")
        lease_type = st.selectbox(
            "Lease Type",
            ["Full Service (Gross)", "Triple Net (NNN)"],
            key=f"lt{i}"
        )
        
        # Create two columns for rent and operating expenses
        col1, col2 = st.columns(2)
        
        with col1:
            if lease_type == "Triple Net (NNN)":
                st.markdown("##### Operating Expenses")
                opex = st.number_input("OPEX ($/SF/yr)", 0.0, 500.0, 0.0, 0.01, key=f"ox{i}")
                
                st.markdown("##### OPEX Increases")
                opexinc = st.number_input("Opex Annual Increase (Estimated) (%)", 0.0, 100.0, 3.0, 0.1, key=f"oi{i}")
                opex_base = None
            else:
                opex = 0.0
                opexinc = 0.0
                opex_base = None
        
        with col2:
            st.markdown("##### Base Rent")
            base = st.number_input("Base Rent ($/SF/yr)", 0.0, 1000.0, 0.0, 0.01, key=f"b{i}")
            
            # Custom Annual Increases toggle
            custom_inc = st.checkbox("Custom Annual Increases", key=f"ci{i}")
            
            st.markdown("##### Base Rent Increases")
            if custom_inc:
                # Initialize rent_incs list with zeros
                yrs = term_mos//12 + (1 if term_mos%12 else 0)
                rent_incs = [0.0] * yrs
                
                # Allow user to specify which years have increases
                num_increases = st.number_input("Number of Years with Increases", 0, yrs, 0, 1, key=f"num_inc{i}")
                
                if num_increases > 0:
                    st.markdown("Specify the year and increase percentage for each increase:")
                    for j in range(num_increases):
                        col1, col2 = st.columns(2)
                        with col1:
                            year = st.number_input(f"Increase {j+1} Year", 1, yrs, 1, 1, key=f"inc_yr_{i}_{j}")
                        with col2:
                            pct = st.number_input(f"Increase {j+1} (%)", 0.0, 100.0, 0.0, 0.1, key=f"inc_pct_{i}_{j}")
                            rent_incs[year-1] = pct
            else:
                rent_incs = None
                inc = st.number_input("Annual Rent Increase (%)", 0.0, 100.0, 3.0, 0.1, key=f"r{i}")
        
        st.markdown("---")
        
        # Parking parameters
        st.markdown("#### Parking")
        fxp = st.checkbox("Fixed Parking Spaces", key=f"fxp{i}")
        if fxp:
            park_spaces = st.number_input("Total Spaces", 0, 500, 0, 1, key=f"ps{i}")
            reserved_spaces = st.number_input("Reserved Spaces", 0, park_spaces, 0, 1, key=f"rps{i}")
            unreserved_spaces = park_spaces - reserved_spaces
            st.caption(f"→ {unreserved_spaces} unreserved spaces")
        else:
            ratio = st.number_input("Ratio (spaces/1k SF)", 0.0, 100.0, 0.0, 0.1, key=f"rt{i}")
            park_spaces = int(round(ratio*(sqft or 0)/1000))
            st.caption(f"→ {park_spaces} total spaces")
            reserved_spaces = st.number_input("Number of Reserved Spaces", 0, park_spaces, 0, 1, key=f"rps{i}")
            unreserved_spaces = park_spaces - reserved_spaces
            st.caption(f"→ {unreserved_spaces} unreserved spaces")
        
        # Parking costs
        col1, col2 = st.columns(2)
        with col1:
            unreserved_cost = st.number_input("Unreserved Parking ($/space/mo)", 0.0, 500.0, 0.0, 0.01, key=f"upc{i}")
        with col2:
            reserved_cost = st.number_input("Reserved Parking ($/space/mo)", 0.0, 500.0, 0.0, 0.01, key=f"rpc{i}")
        
        # Calculate total parking cost
        park_cost = (unreserved_spaces * unreserved_cost + reserved_spaces * reserved_cost) / park_spaces if park_spaces > 0 else 0
        
        st.markdown("---")
        
        # Construction and TI Allowance section
        st.markdown("#### Construction & Tenant Improvements")
        st.markdown("The tenant will be responsible for any construction costs that exceed the TI allowance.")
        
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("##### Construction Costs")
            const_sf = st.number_input("Construction Cost ($/SF)", 0.0, 1000.0, 0.0, 0.01, key=f"cc{i}")
        
        with col2:
            st.markdown("##### TI Allowance")
            ti_sf = st.number_input("TI Allowance ($/SF)", 0.0, 500.0, 0.0, 1.0, key=f"ti{i}")
            ti_fx = st.checkbox("Fixed TI Allowance (total $)", key=f"tifx{i}")
            if ti_fx:
                tot = st.number_input("TI Allowance (total $)", 0.0, 1e7, 0.0, 1.0, key=f"titot{i}")
                ti_sf = tot/(sqft or 1)
        
        # Calculate and display the tenant's responsibility
        if const_sf > ti_sf:
            tenant_responsibility = const_sf - ti_sf
            st.info(f"Tenant will be responsible for ${tenant_responsibility:.2f}/SF in excess of the TI allowance")
        
        st.markdown("---")
        
        # Additional costs
        st.markdown("#### Additional Costs")
        mv_sf = st.number_input("Moving Exp ($/SF)", 0.0, 500.0, 0.0, 0.01, key=f"mv{i}")
        st.markdown("---")
        
        # Abatement and credits
        st.markdown("#### Abatement & Credits")
        cust_ab = st.checkbox("Custom Abatement per Year", key=f"cab{i}")
        if cust_ab:
            yrs = term_mos//12 + (1 if term_mos%12 else 0)
            abates = [st.number_input(f"Year {y} Abate (mo)", 0, term_mos, 0, 1, key=f"abate_{i}_{y}") for y in range(1,yrs+1)]
            free_mo = 0
        else:
            abates = None
            free_mo = st.number_input("Rent Abatement (mo)", 0, 24, 0, 1, key=f"fr{i}")
        
        ac_fx = st.checkbox("Fixed Additional Credits (total $)", key=f"acfx{i}")
        if ac_fx:
            ac_tot = st.number_input("Additional Credits (total $)", 0.0, 1e7, 0.0, 1.0, key=f"ac_tot{i}")
            add_cred = ac_tot/(sqft or 1)
        else:
            add_cred = st.number_input("Additional Credits ($/SF)", 0.0, 500.0, 0.0, 0.01, key=f"ac{i}")
        
        # Add dividing line before Analysis Parameters
        st.markdown("---")
        # Discount rate
        st.markdown("#### Analysis Parameters")
        disc_pct = st.number_input("Discount Rate (%)", 0.0, 100.0, 0.0, 0.01, key=f"dr{i}")
        
        return {
            "name": name,
            "start_date": start_dt,
            "term_mos": term_mos,
            "sqft": sqft,
            "base": base,
            "inc": inc if not custom_inc else None,
            "rent_incs": rent_incs,
            "lease_type": lease_type,
            "opex_base": opex_base,
            "opex": opex,
            "opexinc": opexinc,
            "park_cost": park_cost,
            "park_spaces": park_spaces,
            "reserved_spaces": reserved_spaces,
            "unreserved_spaces": unreserved_spaces,
            "reserved_cost": reserved_cost,
            "unreserved_cost": unreserved_cost,
            "move_exp": mv_sf,
            "construction": const_sf,
            "free": free_mo,
            "ti": ti_sf,
            "add_cred": add_cred,
            "disc": disc_pct,
            "custom_abate": cust_ab,
            "abates": abates,
        }

def render_inputs_tab():
    """Render the inputs tab with lease parameters and analysis controls."""
    st.header("Configure & Compare Scenarios")
    st.markdown("<p style='font-size: 0.8em; color: gray;'>© 2025 Savills. All rights reserved.</p>", unsafe_allow_html=True)
    compare = st.checkbox("🔁 Compare Multiple Options")
    count = st.number_input("Number of Options", 1, 10, 1) if compare else 1
    inputs = []
    for i in range(int(count)):
        inputs.append(create_input_form(i))
    if st.button("Run Analysis"):
        st.session_state["results"] = [(p, *analyze_lease(p)) for p in inputs]
        st.success("Analysis complete! View results in the Analysis tab.") 