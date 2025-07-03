# baseline_validator_page.py (Final Standard Import Version)

import streamlit as st
import json
from src import data_loader, analysis # Back to standard import

def show_page():
    st.set_page_config(
        page_title="Baseline Validation - Studio OM",
        page_icon="🔎",
        layout="centered"
    )

    st.title("🔎 AI Baseline Analysis & Validation")
    st.markdown("Welcome! Please provide your project's baseline information to begin. Our AI will analyze your PVsyst file for consistency before proceeding.")
    st.markdown("---")

    st.header("1. Provide Project Information")

    try:
        with open('data/location_benchmarks.json') as f:
            benchmarks = json.load(f)
        location_options = list(benchmarks.keys())
    except FileNotFoundError:
        st.error("Error: `location_benchmarks.json` not found. Please ensure the file exists in the `data/` directory.")
        st.stop()

    col1, col2 = st.columns(2)
    with col1:
        project_name_input = st.text_input("Project Name", help="Enter a unique name for your project.")
    with col2:
        pnom_input = st.number_input("Nominal Power (Pnom, kWp)", min_value=1.0, value=1000.0, format="%.2f", help="The total installed capacity of the solar plant.")

    location_input = st.selectbox(
        "Project Location in Thailand",
        location_options,
        index=0,
        help="Select the region in Thailand where your project is located. This allows our AI to use the correct climate data for comparison."
    )

    st.markdown("---")
    st.header("2. Upload PVsyst Baseline File")
    pvsyst_file_obj = st.file_uploader("Select your monthly PVsyst simulation report (Excel)", type=['xlsx', 'xls'])

    st.markdown("---")
    st.header("3. Run Analysis")

    result_container = st.container()

    if st.button("🤖 Run AI Baseline Analysis", type="primary", use_container_width=True, disabled=(not pvsyst_file_obj or not project_name_input or location_input.startswith("--- Select"))):
        with st.spinner("AI is analyzing your baseline file... Please wait."):
            pvsyst_df, error = data_loader.load_pvsyst_baseline(pvsyst_file_obj)

            if error:
                result_container.error(f"Failed to process PVsyst file: {error}")
            else:
                score, message, status = analysis.validate_pvsyst_baseline(
                    pvsyst_df,
                    location_input,
                    pnom_input
                )

                if score:
                    st.session_state['validation_results'] = {
                        'score': score,
                        'message': message,
                        'status': status,
                        'project_name': project_name_input,
                        'pnom': pnom_input,
                        'location': location_input,
                        'pvsyst_df': pvsyst_df
                    }
                else:
                    result_container.error("Could not perform validation. Please check your inputs.")

    if 'validation_results' in st.session_state and st.session_state.validation_results:
        res = st.session_state.validation_results
        with result_container:
            st.subheader(f"Analysis for '{res['project_name']}'")
            if res['status'] == "success":
                st.success(f"**Consistency Score: {res['score']}** - {res['message']}")
            elif res['status'] == "warning":
                st.warning(f"**Consistency Score: {res['score']}** - {res['message']}")
            else:
                st.error(f"**Consistency Score: {res['score']}** - {res['message']}")

            st.markdown("---")
            st.subheader("Do you want to proceed with this baseline?")

            c1, c2 = st.columns(2)
            with c1:
                if st.button("✅ Confirm & Proceed", use_container_width=True, type="primary"):
                    st.session_state['system_info'] = {
                        'project_name': res['project_name'],
                        'pnom': res['pnom'],
                        'project_location': res['location'],
                        'owner_name': 'Streamlit User',
                        'commissioning_year': 2020,
                        'electricity_tariff': 4.0,
                        'irr_alert_threshold': 20.0,
                        'degradation_rate': 0.5,
                        'energy_guarantee': res['pnom'] * 1.5,
                        'temp_coeff': -0.38,
                        'forecast_period': 10
                    }
                    st.session_state['pvsyst_df'] = res['pvsyst_df']
                    st.session_state['baseline_confirmed'] = True
                    del st.session_state['validation_results']
                    st.rerun()

            with c2:
                if st.button("❌ Reject & Re-upload", use_container_width=True):
                    del st.session_state['validation_results']
                    st.rerun()