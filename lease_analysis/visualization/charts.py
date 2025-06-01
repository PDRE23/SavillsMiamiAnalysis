import plotly.graph_objects as go
import pandas as pd
import numpy as np
from lease_analysis.utils.lease_calculator import calculate_lease_metrics

def create_rent_breakdown_chart(cash_flow_df):
    """
    Create a stacked bar chart showing the annual rent breakdown.
    
    Args:
        cash_flow_df (pd.DataFrame): DataFrame containing annual cash flow data
        
    Returns:
        plotly.graph_objects.Figure: The rent breakdown chart
    """
    fig = go.Figure()
    
    # Add bars for each cost component
    for col in ["Base Rent", "Opex", "Parking Exp"]:
        if col in cash_flow_df.columns:
            fig.add_trace(go.Bar(
                name=col,
                x=cash_flow_df["Period"],
                y=cash_flow_df[col],
                text=[f"${x:,.0f}" for x in cash_flow_df[col]],
                textposition="auto",
            ))
    
    # Update layout
    fig.update_layout(
        title="Annual Rent Breakdown",
        xaxis_title="Year",
        yaxis_title="Cost ($)",
        barmode="stack",
        showlegend=True,
        legend_title="Components",
        template="plotly_white"
    )
    
    return fig

def create_comparison_chart(results):
    """Create a bar chart comparing key metrics across scenarios."""
    # Extract metrics for comparison
    metrics = []
    for idx, (p, s, wf) in enumerate(results):
        metrics.append({
            "Scenario": s["Option"],
            "Total Cost": s["Total Cost"],
            "NPV": s["NPV"],
            "IRR": s["IRR"],
            "ROI": s["ROI"]
        })
    
    # Create DataFrame
    df = pd.DataFrame(metrics)
    
    # Create figure
    fig = go.Figure()
    
    # Add bars for each metric
    for metric in ["Total Cost", "NPV", "IRR", "ROI"]:
        fig.add_trace(go.Bar(
            name=metric,
            x=df["Scenario"],
            y=df[metric],
            text=[f"${x:,.0f}" if metric in ["Total Cost", "NPV"] else f"{x:.1f}%" for x in df[metric]],
            textposition="auto",
        ))
    
    # Update layout
    fig.update_layout(
        title="Scenario Comparison",
        xaxis_title="Scenario",
        yaxis_title="Value",
        barmode="group",
        showlegend=True,
        legend_title="Metrics",
        template="plotly_white"
    )
    
    return fig 