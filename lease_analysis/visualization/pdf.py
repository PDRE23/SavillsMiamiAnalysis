from fpdf import FPDF
import tempfile
from PIL import Image
import plotly.graph_objects as go
import pandas as pd

class LeaseReportPDF(FPDF):
    """Custom PDF class for generating lease analysis reports."""
    
    def __init__(self):
        super().__init__()
        self.set_auto_page_break(auto=True, margin=15)
    
    def add_header(self, title):
        """Add a header with logo and title."""
        self.image("savills_logo.png", x=10, y=10, w=40)
        self.ln(20)  # space below the logo
        self.set_font("Arial", 'B', 16)
        self.cell(0, 10, title, ln=True)
    
    def add_summary_table(self, summary_dict):
        """Add a summary table to the PDF."""
        self.set_font("Arial", '', 10)
        col_width = self.w / 2
        self.ln(5)
        
        for key, value in summary_dict.items():
            self.cell(col_width, 8, str(key), border=1)
            self.cell(col_width, 8, str(value), border=1)
            self.ln()
    
    def add_chart(self, fig, title):
        """Add a chart to the PDF."""
        self.ln(5)
        self.set_font("Arial", 'B', 12)
        self.cell(0, 10, title, ln=True)
        
        # Save chart to temporary file
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            fig.write_image(tmp.name, format="png", width=700, height=400)
            self.image(tmp.name, w=self.w - 30)
    
    def add_cash_flow_table(self, cash_flow_df):
        """Add a cash flow table to the PDF."""
        self.ln(5)
        self.set_font("Arial", 'B', 12)
        self.cell(0, 10, "Annual Cash Flow Table", ln=True)
        
        self.set_font("Arial", '', 8)
        cols = cash_flow_df.columns.tolist()
        col_width = self.w / len(cols)
        
        # Add headers
        for col in cols:
            self.cell(col_width, 6, col[:15], border=1)
        self.ln()
        
        # Add data rows
        for _, row in cash_flow_df.iterrows():
            for val in row:
                v = f"${int(val):,}" if isinstance(val, (int, float)) else str(val)
                self.cell(col_width, 6, v[:15], border=1)
            self.ln()

def generate_lease_report(summary_dict, cash_flow_df, lease_params, cost_chart):
    """
    Generate a complete lease analysis report in PDF format.
    
    Args:
        summary_dict (dict): Dictionary containing lease summary metrics
        cash_flow_df (pd.DataFrame): DataFrame containing cash flow data
        lease_params (dict): Dictionary containing lease parameters
        cost_chart (plotly.graph_objects.Figure): Cost breakdown chart
        
    Returns:
        bytes: PDF file contents
    """
    pdf = LeaseReportPDF()
    
    # Add summary page
    pdf.add_page()
    pdf.add_header("Lease Analysis Summary")
    pdf.add_summary_table(summary_dict)
    
    # Add cost breakdown chart
    pdf.add_chart(cost_chart, "Annual Rent Breakdown")
    
    # Add cash flow table
    pdf.add_cash_flow_table(cash_flow_df)
    
    # Get PDF contents
    return pdf.output(dest='S').encode('latin1') 