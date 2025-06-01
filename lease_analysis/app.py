import streamlit as st
from PIL import Image
from lease_analysis.ui.inputs import render_inputs_tab
from lease_analysis.ui.analysis import render_analysis_tab
from lease_analysis.ui.comparison import render_comparison_tab

def main():
    """Main application entry point."""
    # Configure page
    st.set_page_config(page_title="Savills Lease Analyzer", layout="wide")
    
    # Header
    st.title("Savills | Lease Analyzer")
    logo = Image.open("savills_logo.png")
    st.image(logo, width=150)
    st.caption("Created by Peyton Dowd")
    st.markdown("---")
    
    # Create tabs
    tab_inputs, tab_analysis, tab_comparison = st.tabs(["Inputs", "Analysis", "Comparison"])
    
    # Render each tab
    with tab_inputs:
        render_inputs_tab()
    
    with tab_analysis:
        render_analysis_tab()
    
    with tab_comparison:
        render_comparison_tab()

if __name__ == "__main__":
    main() 