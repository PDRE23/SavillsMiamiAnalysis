import streamlit as st
import pandas as pd
from lease_analysis.utils.ui_helpers import create_metric_section
from lease_analysis.visualization.charts import create_rent_breakdown_chart

def render_analysis_tab():
    """Render the analysis tab with results and visualizations."""
    results = st.session_state.get("results", [])
    if not results:
        st.warning("Run analysis first in Inputs.")
        return
    
    for idx, (p, s, wf) in enumerate(results):
        st.subheader(f"Scenario {idx+1}: {s['Option']}")
        
        # Display metrics
        st.markdown("### 📊 Lease Summary")
        create_metric_section(s, p["lease_type"])
        
        # Create and display charts
        st.markdown("### 📈 Annual Rent Breakdown")
        rent_fig = create_rent_breakdown_chart(wf)
        st.plotly_chart(rent_fig, use_container_width=True)
        
        # Display cash flow table
        with st.expander("📋 Show Cash-Flow Table"):
            disp = wf.copy()
            for c in disp.columns:
                if c != "Period":
                    disp[c] = disp[c].map(lambda x: f"${int(x):,}")
            st.dataframe(disp, use_container_width=True) 