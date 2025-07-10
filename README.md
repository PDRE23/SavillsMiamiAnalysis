# Savills Property Analyzer

A Streamlit application for analyzing and comparing commercial lease scenarios and property purchase investments.

## Features

### Lease Analysis
- Analyze multiple lease scenarios with different parameters
- Compare lease options side by side
- Visualize costs and cash flows with interactive charts
- Export results to Excel and PDF
- Support for both Triple Net (NNN) and Full Service (Gross) leases
- Detailed financial metrics including NPV, payback period, and effective rent

### Purchase Analysis
- Analyze property purchase investments with comprehensive financial modeling
- Compare multiple purchase scenarios with different financing options
- Calculate key investment metrics: NPV, IRR, ROI, Cap Rate, Cash-on-Cash Return
- Model property appreciation and rental income growth
- Track equity build-up and loan amortization
- Support for various property types and financing structures

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/savills-property-analyzer.git
cd savills-property-analyzer
```

2. Create a virtual environment (recommended):
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

1. Start the application:
```bash
streamlit run lease_analysis/app.py
```

2. Open your web browser and navigate to the URL shown in the terminal (typically http://localhost:8501)

3. Choose your analysis mode:
   - **Lease Analyzer**: For analyzing commercial lease scenarios
   - **Purchase Analyzer**: For analyzing property purchase investments

4. Use the application:
   - Input tab: Configure parameters for your scenarios
   - Analysis tab: View detailed analysis and charts
   - Comparison tab: Compare multiple scenarios and export results

## Lease Analysis Parameters

- Basic Information:
  - Lease term (months)
  - Rentable square footage
  - Start date
  - Base rent ($/SF/yr)

- Lease Type:
  - Triple Net (NNN)
  - Full Service (Gross)

- Operating Expenses:
  - OPEX base year
  - Annual OPEX increase

- Parking:
  - Fixed spaces or ratio
  - Cost per space

- Credits and Abatements:
  - TI allowance
  - Moving expenses
  - Rent abatement
  - Additional credits

- Financial:
  - Discount rate
  - Custom rent increases

## Purchase Analysis Parameters

- Property Information:
  - Property value
  - Purchase date
  - Holding period
  - Annual appreciation rate

- Financing:
  - Down payment percentage
  - Loan term (years)
  - Interest rate
  - Closing costs percentage

- Income & Expenses:
  - Annual rental income (optional)
  - Annual rental increase rate
  - Property taxes
  - Insurance costs
  - Maintenance expenses
  - HOA fees

- Analysis:
  - Discount rate for NPV calculations

## Output

### Lease Analysis
- Summary metrics
- Annual cost breakdown
- Net cash flow waterfall
- Detailed cash flow table
- Excel export
- PDF report

### Purchase Analysis
- Investment summary metrics
- Annual cash flow breakdown
- Equity build-up tracking
- Loan amortization schedule
- Key investment ratios (Cap Rate, Cash-on-Cash)
- Comparison charts and tables

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Created by Peyton Dowd
- © 2025 Savills. All rights reserved. 