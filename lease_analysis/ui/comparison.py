import streamlit as st
import pandas as pd
from lease_analysis.utils.ui_helpers import create_metric_section
from lease_analysis.visualization.charts import create_comparison_chart

def render_comparison_tab():
    """Render the comparison tab with scenario comparisons."""
    results = st.session_state.get("results", [])
    if len(results) < 2:
        st.warning("Need at least 2 scenarios to compare. Run analysis first in Inputs.")
        return
    
    st.subheader("📊 Scenario Comparison")
    
    # Create comparison metrics
    metrics = []
    for idx, (p, s, wf) in enumerate(results):
        metrics.append({
            "Scenario": s["Option"],
            "Total Cost": s["Total Cost"],
            "NPV": s["NPV"],
            "IRR": s["IRR"],
            "ROI": s["ROI"],
            "Payback": s["Payback"],
            "Avg. Annual Cost": s["Avg. Annual Cost"]
        })
    
    # Display comparison table
    df = pd.DataFrame(metrics)
    st.dataframe(df, use_container_width=True)
    
    # Create and display comparison chart
    st.markdown("### 📈 Cost Comparison")
    fig = create_comparison_chart(results)
    st.plotly_chart(fig, use_container_width=True) 