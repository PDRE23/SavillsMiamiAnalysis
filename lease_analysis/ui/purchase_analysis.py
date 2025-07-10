import streamlit as st
import pandas as pd
from lease_analysis.utils.ui_helpers import create_metric_section
from lease_analysis.visualization.purchase_charts import create_purchase_breakdown_chart

def render_purchase_analysis_tab():
    """Render the purchase analysis tab with results and visualizations."""
    results = st.session_state.get("purchase_results", [])
    if not results:
        st.warning("Run purchase analysis first in Inputs.")
        return
    
    for idx, (p, s, wf) in enumerate(results):
        st.subheader(f"Purchase Scenario {idx+1}: {s['Option']}")
        
        # Display metrics
        st.markdown("### 📊 Purchase Summary")
        
        # Create metric columns for purchase analysis
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Property Value", s["Property Value"])
            st.metric("Down Payment", s["Down Payment"])
            st.metric("Loan Amount", s["Loan Amount"])
            st.metric("Monthly Payment", s["Monthly Payment"])
        
        with col2:
            st.metric("Total Investment", s["Total Investment"])
            st.metric("Final Property Value", s["Final Property Value"])
            st.metric("Total Return", s["Total Return"])
            st.metric("Cap Rate", s["Cap Rate"])
        
        with col3:
            st.metric("NPV", s[f"NPV ({p['discount_rate']:.2f}%)"])
            st.metric("IRR", s["IRR"])
            st.metric("ROI", s["ROI"])
            st.metric("Cash-on-Cash", s["Cash-on-Cash"])
        
        # Create and display charts
        st.markdown("### 📈 Annual Cash Flow Breakdown")
        purchase_fig = create_purchase_breakdown_chart(wf)
        st.plotly_chart(purchase_fig, use_container_width=True)
        
        # Display cash flow table
        with st.expander("📋 Show Detailed Cash Flow Table"):
            disp = wf.copy()
            for c in disp.columns:
                if c not in ["Year", "Period"]:
                    disp[c] = disp[c].map(lambda x: f"${int(x):,}")
            st.dataframe(disp, use_container_width=True)
        
        # Display equity build-up
        st.markdown("### 🏠 Equity Build-up")
        equity_cols = ["Year", "Property Value", "Cumulative Equity"]
        equity_df = wf[equity_cols].copy()
        equity_df["Loan Balance"] = equity_df["Property Value"] - equity_df["Cumulative Equity"]
        
        # Format for display
        display_df = equity_df.copy()
        for c in ["Property Value", "Cumulative Equity", "Loan Balance"]:
            display_df[c] = display_df[c].map(lambda x: f"${int(x):,}")
        
        st.dataframe(display_df, use_container_width=True) 