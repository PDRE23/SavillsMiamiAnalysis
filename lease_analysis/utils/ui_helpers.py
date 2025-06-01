import streamlit as st

def explain(label, tooltip):
    """
    Create a label with a tooltip icon.
    
    Args:
        label (str): The label text
        tooltip (str): The tooltip text
        
    Returns:
        str: HTML string with label and tooltip
    """
    return f'{label} <span title="{tooltip}">ℹ️</span>'

def create_metric_section(summary, lease_type):
    """Create a section displaying key lease metrics."""
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(
            "Total Cost",
            f"${summary['Total Cost']:,.0f}",
            help="Total cost over lease term"
        )
        st.metric(
            "NPV",
            f"${summary['NPV']:,.0f}",
            help="Net Present Value"
        )
    
    with col2:
        st.metric(
            "IRR",
            f"{summary['IRR']:.1f}%",
            help="Internal Rate of Return"
        )
        st.metric(
            "ROI",
            f"{summary['ROI']:.1f}%",
            help="Return on Investment"
        )
    
    with col3:
        st.metric(
            "Payback Period",
            f"{summary['Payback']} years",
            help="Time to recover initial investment"
        )
        st.metric(
            "Avg. Annual Cost",
            f"${summary['Avg. Annual Cost']:,.0f}",
            help="Average annual cost"
        )

def create_metric_section(summary_dict, lease_type):
    """
    Create a section of metrics in the UI.
    
    Args:
        summary_dict (dict): Dictionary containing lease summary metrics
        lease_type (str): Type of lease (Triple Net or Full Service)
    """
    left, right = st.columns([1, 1])
    
    with left:
        st.markdown(explain("**Total Cost**", "Total cost over the lease term."), unsafe_allow_html=True)
        st.metric("", summary_dict["Total Cost"])
        
        st.markdown(explain("**Avg Eff. Rent**", "Effective gross rent per SF per year, averaged across full years."), unsafe_allow_html=True)
        st.metric("", summary_dict["Avg Eff. Rent"])
        
        st.markdown(explain("**Payback**", "Months to recoup total credits (TI, additional, abatement) via rent."), unsafe_allow_html=True)
        st.metric("", summary_dict["Payback"])
        
        st.markdown(explain("**Construction Cost**", "Total construction cost based on $/SF input."), unsafe_allow_html=True)
        st.metric("", summary_dict["Construction Cost"])
        
        st.markdown(explain("**Lease Type**", "Gross (Full Service) or NNN (Triple Net)"), unsafe_allow_html=True)
        st.metric("", lease_type)
    
    with right:
        npv_label = next(k for k in summary_dict if k.startswith("NPV"))
        st.markdown(explain(f"**{npv_label}**", "Net present value of net cash flows using the given discount rate."), unsafe_allow_html=True)
        st.metric("", summary_dict[npv_label])
        
        st.markdown(explain("**TI Allowance**", "Total tenant improvement allowance (TI $/SF × SF)."), unsafe_allow_html=True)
        st.metric("", summary_dict["TI Allowance"])
        
        st.markdown(explain("**Moving Exp**", "Moving cost calculated as $/SF × SF."), unsafe_allow_html=True)
        st.metric("", summary_dict["Moving Exp"])
        
        st.markdown(explain("**Additional Credit**", "Other landlord incentives such as cash allowances or early occupancy."), unsafe_allow_html=True)
        st.metric("", summary_dict["Additional Credit"]) 