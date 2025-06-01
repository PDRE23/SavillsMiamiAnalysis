# Savills Lease Analyzer

A Streamlit application for analyzing and comparing commercial lease scenarios.

## Features

- Analyze multiple lease scenarios with different parameters
- Compare lease options side by side
- Visualize costs and cash flows with interactive charts
- Export results to Excel and PDF
- Support for both Triple Net (NNN) and Full Service (Gross) leases
- Detailed financial metrics including NPV, payback period, and effective rent

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/savills-lease-analyzer.git
cd savills-lease-analyzer
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

3. Use the application:
   - Input tab: Configure lease parameters
   - Analysis tab: View detailed analysis and charts
   - Comparison tab: Compare multiple scenarios and export results

## Input Parameters

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

## Output

- Summary metrics
- Annual cost breakdown
- Net cash flow waterfall
- Detailed cash flow table
- Excel export
- PDF report

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