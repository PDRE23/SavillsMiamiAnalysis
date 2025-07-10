import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np

def create_purchase_breakdown_chart(cash_flow_df):
    """
    Create a stacked bar chart showing the annual cash flow breakdown for purchase analysis.
    
    Args:
        cash_flow_df (pd.DataFrame): DataFrame containing annual cash flow data
        
    Returns:
        plotly.graph_objects.Figure: The purchase breakdown chart
    """
    fig = go.Figure()
    
    # Define colors for different components
    colors = {
        "Rental Income": "green",
        "Property Tax": "red",
        "Insurance": "orange",
        "Maintenance": "purple",
        "HOA": "brown",
        "Mortgage Payment": "blue",
        "Net Cash Flow": "black"
    }
    
    # Add bars for each cost component
    for col in ["Rental Income", "Property Tax", "Insurance", "Maintenance", "HOA", "Mortgage Payment"]:
        if col in cash_flow_df.columns:
            # Use absolute values for display
            values = abs(cash_flow_df[col])
            fig.add_trace(go.Bar(
                name=col,
                x=cash_flow_df["Year"],
                y=values,
                text=[f"${x:,.0f}" for x in values],
                textposition="auto",
                marker_color=colors.get(col, "gray")
            ))
    
    # Update layout
    fig.update_layout(
        title="Annual Cash Flow Breakdown",
        xaxis_title="Year",
        yaxis_title="Amount ($)",
        barmode="stack",
        showlegend=True,
        legend_title="Components",
        template="plotly_white"
    )
    
    return fig

def create_equity_chart(cash_flow_df):
    """
    Create a line chart showing equity build-up over time.
    
    Args:
        cash_flow_df (pd.DataFrame): DataFrame containing annual cash flow data
        
    Returns:
        plotly.graph_objects.Figure: The equity build-up chart
    """
    fig = go.Figure()
    
    # Add property value line
    fig.add_trace(go.Scatter(
        x=cash_flow_df["Year"],
        y=cash_flow_df["Property Value"],
        mode="lines+markers",
        name="Property Value",
        line=dict(color="blue", width=3),
        text=[f"${x:,.0f}" for x in cash_flow_df["Property Value"]],
        textposition="top center"
    ))
    
    # Add cumulative equity line
    fig.add_trace(go.Scatter(
        x=cash_flow_df["Year"],
        y=cash_flow_df["Cumulative Equity"],
        mode="lines+markers",
        name="Cumulative Equity",
        line=dict(color="green", width=3),
        text=[f"${x:,.0f}" for x in cash_flow_df["Cumulative Equity"]],
        textposition="bottom center"
    ))
    
    # Update layout
    fig.update_layout(
        title="Property Value vs Equity Build-up",
        xaxis_title="Year",
        yaxis_title="Amount ($)",
        showlegend=True,
        template="plotly_white"
    )
    
    return fig

def create_purchase_comparison_chart(results):
    """
    Create a bar chart comparing key investment metrics across purchase scenarios.
    
    Args:
        results (list): List of purchase analysis results
        
    Returns:
        plotly.graph_objects.Figure: The comparison chart
    """
    # Extract metrics for comparison
    metrics = []
    for idx, (p, s, wf) in enumerate(results):
        # Extract numeric values
        total_return = float(s["Total Return"].replace("$", "").replace(",", ""))
        npv = float(s[f"NPV ({p['discount_rate']:.2f}%)"].replace("$", "").replace(",", ""))
        irr = float(s["IRR"].replace("%", ""))
        roi = float(s["ROI"].replace("%", ""))
        cap_rate = float(s["Cap Rate"].replace("%", ""))
        coc_return = float(s["Cash-on-Cash"].replace("%", ""))
        
        metrics.append({
            "Scenario": s["Option"],
            "Total Return": total_return,
            "NPV": npv,
            "IRR": irr,
            "ROI": roi,
            "Cap Rate": cap_rate,
            "Cash-on-Cash": coc_return
        })
    
    # Create DataFrame
    df = pd.DataFrame(metrics)
    
    # Create figure with subplots
    fig = go.Figure()
    
    # Add bars for each metric
    metric_colors = {
        "Total Return": "blue",
        "NPV": "green",
        "IRR": "orange",
        "ROI": "purple",
        "Cap Rate": "red",
        "Cash-on-Cash": "brown"
    }
    
    for metric in ["Total Return", "NPV", "IRR", "ROI", "Cap Rate", "Cash-on-Cash"]:
        fig.add_trace(go.Bar(
            name=metric,
            x=df["Scenario"],
            y=df[metric],
            text=[f"${x:,.0f}" if metric in ["Total Return", "NPV"] else f"{x:.1f}%" for x in df[metric]],
            textposition="auto",
            marker_color=metric_colors.get(metric, "gray")
        ))
    
    # Update layout
    fig.update_layout(
        title="Purchase Scenario Comparison",
        xaxis_title="Scenario",
        yaxis_title="Value",
        barmode="group",
        showlegend=True,
        legend_title="Metrics",
        template="plotly_white"
    )
    
    return fig

def create_lease_vs_purchase_chart(lease_results, purchase_results):
    """
    Create a comparison chart between lease and purchase scenarios.
    
    Args:
        lease_results (list): List of lease analysis results
        purchase_results (list): List of purchase analysis results
        
    Returns:
        plotly.graph_objects.Figure: The lease vs purchase comparison chart
    """
    fig = go.Figure()
    
    # Process lease results
    lease_metrics = []
    for p, s, wf in lease_results:
        total_cost = float(s["Total Cost"].replace("$", "").replace(",", ""))
        npv = float(s[f"NPV ({p['disc']:.2f}%)"].replace("$", "").replace(",", ""))
        lease_metrics.append({
            "Scenario": f"Lease: {s['Option']}",
            "Total Cost": total_cost,
            "NPV": npv,
            "Type": "Lease"
        })
    
    # Process purchase results
    purchase_metrics = []
    for p, s, wf in purchase_results:
        total_investment = float(s["Total Investment"].replace("$", "").replace(",", ""))
        npv = float(s[f"NPV ({p['discount_rate']:.2f}%)"].replace("$", "").replace(",", ""))
        purchase_metrics.append({
            "Scenario": f"Purchase: {s['Option']}",
            "Total Investment": total_investment,
            "NPV": npv,
            "Type": "Purchase"
        })
    
    # Combine metrics
    all_metrics = lease_metrics + purchase_metrics
    df = pd.DataFrame(all_metrics)
    
    # Create comparison chart
    fig.add_trace(go.Bar(
        name="Total Cost/Investment",
        x=df["Scenario"],
        y=df["Total Cost"] if "Total Cost" in df.columns else df["Total Investment"],
        text=[f"${x:,.0f}" for x in (df["Total Cost"] if "Total Cost" in df.columns else df["Total Investment"])],
        textposition="auto",
        marker_color=["red" if x == "Lease" else "blue" for x in df["Type"]]
    ))
    
    fig.update_layout(
        title="Lease vs Purchase Comparison",
        xaxis_title="Scenario",
        yaxis_title="Total Cost/Investment ($)",
        showlegend=False,
        template="plotly_white"
    )
    
    return fig 