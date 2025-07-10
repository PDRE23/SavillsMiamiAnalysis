"""
Savills Property Analyzer - Main Entry Point
This file serves as the entry point for Streamlit Cloud deployment.
"""

import sys
import os

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import and run the main application
from lease_analysis.app import main

if __name__ == "__main__":
    main() 