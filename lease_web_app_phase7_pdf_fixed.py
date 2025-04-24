
import streamlit as st
import pandas as pd
import numpy_financial as npf
import io
from PIL import Image
from fpdf import FPDF
import base64

# Load and encode logo
logo_image = Image.open("savills_logo.png")
buffered = io.BytesIO()
logo_image.save(buffered, format="PNG")
logo_base64 = base64.b64encode(buffered.getvalue()).decode()

# Page config
st.set_page_config(page_title="Savills Lease Analyzer", layout="wide")

# Header
st.markdown(
    f"""
    <div style="display: flex; align-items: center; justify-content: space-between;">
        <div style="display: flex; align-items: center;">
            <img src="data:image/png;base64,{logo_base64}" width="100">
            <div style="margin-left: 1rem;">
                <h1 style="margin: 0; font-family: 'Segoe UI', sans-serif; color: #003366;">Savills | Lease Analyzer</h1>
                <p style="margin: 0; font-size: 14px; color: #777;">Created by Peyton Dowd</p>
            </div>
        </div>
    </div>
    """,
    unsafe_allow_html=True
)

st.markdown("---")

compare_mode = st.toggle("Compare Multiple Lease Options")
num_options = st.slider("How many lease options would you like to compare?", 1, 5, 1) if compare_mode else 1

all_summaries = []
all_annuals = {}

def analyze_lease(label, term_years, sqft, base_rent_start, rent_increase_pct,
                  opex_start, opex_increase_pct, free_rent_months, discount_rate,
                  ti_allowance, moving_allowance, parking_cost, parking_spaces):

    base_rents = []
    opexes = []
    gross_rents = []
    total_base_rent = total_opex = 0

    for year in range(1, term_years + 1):
        base_rent = base_rent_start * ((1 + rent_increase_pct / 100) ** (year - 1))
        opex = opex_start * ((1 + opex_increase_pct / 100) ** (year - 1))
        gross = (base_rent + opex) * sqft

        base_rents.append(round(base_rent, 2))
        opexes.append(round(opex, 2))
        gross_rents.append(round(gross, 2))

        total_base_rent += base_rent * sqft
        total_opex += opex * sqft

    free_rent_credit = (base_rent_start * sqft / 12) * free_rent_months
    ti_credit = ti_allowance * sqft
    parking_total = parking_cost * parking_spaces * 12 * term_years
    total_occupancy_cost = (total_base_rent - free_rent_credit) + total_opex + parking_total - ti_credit - moving_allowance
    avg_effective_rent = total_occupancy_cost / term_years / sqft
    npv = npf.npv(discount_rate / 100, gross_rents)

    summary = {
        "Option": label,
        "Term (Years)": term_years,
        "RSF": sqft,
        "Base Rent ($)": f"${total_base_rent:,.0f}",
        "Free Rent Credit ($)": f"${free_rent_credit:,.0f}",
        "TI Credit ($)": f"${ti_credit:,.0f}",
        "Moving Allowance ($)": f"${moving_allowance:,.0f}",
        "Parking Cost ($)": f"${parking_total:,.0f}",
        "Opex ($)": f"${total_opex:,.0f}",
        "Occupancy Cost ($)": f"${total_occupancy_cost:,.0f}",
        "Avg Eff. Rent ($/SF/yr)": f"${avg_effective_rent:,.2f}",
        "NPV ($)": f"${npv:,.0f}"
    }

    annual_schedule = pd.DataFrame({
        "Year": list(range(1, term_years + 1)),
        "Base Rent ($/SF)": base_rents,
        "Opex ($/SF)": opexes,
        "Gross Rent ($)": gross_rents
    })

    return summary, annual_schedule

def generate_pdf(option_name, summary_dict, annual_df):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.set_text_color(0, 51, 102)
    pdf.cell(200, 10, f"Lease Summary - {option_name}", ln=True, align="C")

    pdf.set_font("Arial", "", 12)
    pdf.set_text_color(0, 0, 0)
    pdf.ln(10)

    for k, v in summary_dict.items():
        pdf.cell(90, 8, str(k), ln=0)
        pdf.cell(90, 8, str(v), ln=1)

    pdf.ln(5)
    pdf.set_font("Arial", "B", 14)
    pdf.cell(200, 10, "Annual Breakdown", ln=True)
    pdf.set_font("Arial", "", 10)

    col_names = list(annual_df.columns)
    col_widths = [40, 50, 50, 50]

    for col_name, width in zip(col_names, col_widths):
        pdf.cell(width, 8, col_name, border=1)
    pdf.ln()

    for _, row in annual_df.iterrows():
        pdf.cell(col_widths[0], 8, str(row["Year"]), border=1)
        pdf.cell(col_widths[1], 8, f"${row['Base Rent ($/SF)']:,.2f}", border=1)
        pdf.cell(col_widths[2], 8, f"${row['Opex ($/SF)']:,.2f}", border=1)
        pdf.cell(col_widths[3], 8, f"${row['Gross Rent ($)']:,.2f}", border=1)
        pdf.ln()

    return pdf.output(dest="S").encode("latin1")

for i in range(num_options):
    st.markdown(f"### 🧾 Lease Option {i + 1}")
    with st.expander(f"Lease Inputs {i + 1}", expanded=(not compare_mode or i == 0)):
        col1, col2 = st.columns(2)
        with col1:
            label = st.text_input(f"Option Name", value=f"Option {i + 1}", key=f"name_{i}")
            term = st.number_input("Lease Term (Years)", min_value=1, value=10, key=f"term_{i}")
            sqft = st.number_input("RSF", min_value=1, value=10000, key=f"sqft_{i}")
            base_rent = st.number_input("Starting Base Rent ($/SF/yr)", value=40.0, key=f"rent_{i}")
            rent_increase = st.number_input("Base Rent Increase (%)", value=3.0, key=f"increase_{i}")
            opex = st.number_input("Starting Opex ($/SF/yr)", value=12.0, key=f"opex_{i}")
            opex_increase = st.number_input("Opex Increase (%)", value=3.0, key=f"opex_inc_{i}")
        with col2:
            free_rent = st.number_input("Free Rent (Months)", value=3, key=f"free_{i}")
            discount = st.number_input("Discount Rate (%)", value=7.0, key=f"disc_{i}")
            ti = st.number_input("TI Allowance ($/SF)", value=50.0, key=f"ti_{i}")
            moving = st.number_input("Moving Allowance ($)", value=10000.0, key=f"move_{i}")
            parking = st.number_input("Parking Cost/Space ($/mo)", value=150.0, key=f"park_{i}")
            spaces = st.number_input("Parking Spaces", value=20, key=f"spaces_{i}")

    summary, annual = analyze_lease(label, term, sqft, base_rent, rent_increase,
                                    opex, opex_increase, free_rent, discount,
                                    ti, moving, parking, spaces)

    all_summaries.append(summary)
    all_annuals[label] = annual

    if num_options == 1:
        st.markdown("### 📈 Annual Rent Breakdown")
        st.dataframe(annual, use_container_width=True)
        pdf_data = generate_pdf(label, summary, annual)
        b64_pdf = base64.b64encode(pdf_data).decode()
        href = f'<a href="data:application/octet-stream;base64,{b64_pdf}" download="{label.replace(" ","_")}_summary.pdf">📄 Download PDF Summary</a>'
        st.markdown(href, unsafe_allow_html=True)

st.markdown("### 📊 Lease Comparison Summary")
summary_df = pd.DataFrame(all_summaries)
st.dataframe(summary_df, use_container_width=True)

with io.BytesIO() as buffer:
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        summary_df.to_excel(writer, index=False, sheet_name="Summary")
        for label, df in all_annuals.items():
            df.to_excel(writer, index=False, sheet_name=label[:31])
    st.download_button(
        label="📥 Download Excel (Includes Annual Breakdown)",
        data=buffer.getvalue(),
        file_name="lease_comparison_savills_with_annuals.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
