# tests/test_analyze.py

import pandas as pd
from lease_web_app import analyze_lease
from datetime import date

def test_simple_lease():
    params = {
        'name': 'Test',
        'term_mos': 60,  # 5 years
        'start_date': date.today(),
        'sqft': 1000,
        'base': 10.0,
        'inc': 0.0,
        'lease_type': 'Triple Net (NNN)',
        'opex': 2.0,
        'opexinc': 0.0,
        'park_cost': 0.0,
        'park_spaces': 0,
        'free': 0,
        'ti': 0.0,
        'add_cred': 0.0,
        'move_exp': 0.0,
        'construction': 0.0,
        'disc': 0.0,
        'custom_abate': False,
        'abates': None
    }
    summary, df = analyze_lease(params)

    # Total cost = (base + opex) * sqft * term
    expected_cost = (10 + 2) * 1000 * 5
    assert summary['Total Cost'] == f"${expected_cost:,.0f}"

    # Average effective rent = total cost / (term * sqft)
    expected_avg = expected_cost / (5 * 1000)
    assert summary['Avg Eff. Rent'] == f"${expected_avg:.2f} /SF/yr"

    # DataFrame has correct number of rows
    assert len(df) == 5

