# tests/test_analyze.py
import pandas as pd
from lease_web_app import analyze_lease

def test_simple_lease():
    params = {
        'name': 'Test',
        'term': 5,
        'sqft': 1000,
        'base': 10.0,
        'inc': 0.0,
        'opex': 2.0,
        'opexinc': 0.0,
        'park_cost': 0.0,
        'park_spaces': 0,
        'free': 0,
        'ti': 0.0,
        'move': 0.0,
        'disc': 0.0,
        'pdfs': None
    }
    summary, ann_df, wf_df = analyze_lease(params)

    # Total occupancy cost = (base+opex)*sqft*term
    expected = (10 + 2) * 1000 * 5
    assert summary['Occupancy Cost'] == f"${expected:,.0f}"

    # Avg effective rent = total cost / (term*sqft)
    avg = expected / (5 * 1000)
    assert summary['Avg Eff. Rent'] == f"${avg:.2f}"

    # DataFrames have correct number of rows
    assert len(ann_df) == 5
    assert len(wf_df)  == 5
