import streamlit as st
import pandas as pd
from lease_analysis.utils.ui_helpers import create_metric_section
from lease_analysis.visualization.purchase_charts import create_purchase_comparison_chart

def render_purchase_comparison_tab():
    """Render the purchase comparison tab with scenario comparisons."""
    results = st.session_state.get("purchase_results", [])
    if len(results) < 2:
        st.warning("Need at least 2 purchase scenarios to compare. Run analysis first in Inputs.")
        return
    
    st.subheader("📊 Purchase Scenario Comparison")
    
    # Create comparison metrics
    metrics = []
    for idx, (p, s, wf) in enumerate(results):
        # Extract numeric values for comparison
        total_return = float(s["Total Return"].replace("$", "").replace(",", ""))
        npv = float(s[f"NPV ({p['discount_rate']:.2f}%)"].replace("$", "").replace(",", ""))
        irr = float(s["IRR"].replace("%", ""))
        roi = float(s["ROI"].replace("%", ""))
        cap_rate = float(s["Cap Rate"].replace("%", ""))
        coc_return = float(s["Cash-on-Cash"].replace("%", ""))
        
        metrics.append({
            "Scenario": s["Option"],
            "Property Value": s["Property Value"],
            "Total Investment": s["Total Investment"],
            "Total Return": total_return,
            "NPV": npv,
            "IRR": irr,
            "ROI": roi,
            "Cap Rate": cap_rate,
            "Cash-on-Cash": coc_return,
            "Payback (years)": s["Payback (years)"]
        })
    
    # Display comparison table
    df = pd.DataFrame(metrics)
    st.dataframe(df, use_container_width=True)
    
    # Create and display comparison chart
    st.markdown("### 📈 Investment Metrics Comparison")
    fig = create_purchase_comparison_chart(results)
    st.plotly_chart(fig, use_container_width=True)
    
    # Additional insights
    st.markdown("### 💡 Key Insights")
    
    # Find best performing scenarios
    if len(results) > 0:
        best_roi = max(metrics, key=lambda x: x["ROI"])
        best_npv = max(metrics, key=lambda x: x["NPV"])
        best_irr = max(metrics, key=lambda x: x["IRR"])
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Best ROI", f"{best_roi['Scenario']}", f"{best_roi['ROI']:.2f}%")
        
        with col2:
            st.metric("Best NPV", f"{best_npv['Scenario']}", f"${best_npv['NPV']:,.0f}")
        
        with col3:
            st.metric("Best IRR", f"{best_irr['Scenario']}", f"{best_irr['IRR']:.2f}%") 