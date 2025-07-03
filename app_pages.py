# app_pages.py (Final Version with Short-Term Forecast Plotting)

import streamlit as st
from datetime import datetime
from src import data_loader, analysis, plotting, db_manager, simulator

# ==============================================================================
# PAGE 1: HOME & INPUT
# ==============================================================================
def show_home_input_page():
    """
    Contains the content for the main Home & Input page, after baseline validation.
    """
    
    if 'db_initialized' not in st.session_state:
        if db_manager.create_tables():
            st.session_state.db_initialized = True
        else:
            st.error("Failed to initialize database tables. Please check console for errors.")
            st.stop()

    for key in [
        'actual_df', 'analysis_df', 'insights', 
        'summary_table_df', 'conclusion_text_list',
        'sensor_health_fig', 'weather_analysis_fig', 'performance_index_fig', 
        'yield_analysis_fig', 'guarantee_fig', 
        'overall_loss_breakdown_fig', 'latest_month_loss_breakdown_fig', 
        'forecast_df', 'forecast_plot_fig', 'guarantee_df',
        'short_term_forecast_result', 'short_term_forecast_fig' # Added for short-term forecast
    ]:
        if key not in st.session_state:
            st.session_state[key] = None

    st.title("🏠 Home & Input")
    st.markdown("Your baseline has been validated. Please provide the actual production data and any additional system information to complete the analysis.")
    st.markdown("---")

    st.header("1. Confirmed Project Information")
    st.info(f"You are working on project: **{st.session_state.system_info['project_name']}**")
    
    info = st.session_state.system_info
    col1, col2, col3 = st.columns(3)
    with col1:
        info['project_name'] = st.text_input("Project Name", value=info.get('project_name', 'N/A'), disabled=True)
        info['pnom'] = st.number_input("Nominal Power (Pnom, kWp)", value=info.get('pnom', 1000.0), format="%.2f", disabled=True)
        info['commissioning_year'] = st.number_input("Commissioning Year (C.O.D)", value=info.get('commissioning_year', 2020), help="The year when the power plant began commercial operation.")
    with col2:
        info['owner_name'] = st.text_input("Owner Name", value=info.get('owner_name', 'Streamlit User'), help="Name or entity of the project owner.")
        info['energy_guarantee'] = st.number_input("Annual Energy Guarantee (MWh at Year 1)", value=info.get('energy_guarantee', 1600.0), format="%.2f", help="The guaranteed energy production in the first year as per contract (MWh/year).")
        info['electricity_tariff'] = st.number_input("Electricity Tariff (THB/kWh)", value=info.get('electricity_tariff', 4.0), format="%.2f", help="The buyback rate or the avoided electricity cost per unit (THB/kWh).")
    with col3:
        st.write("Advanced Technical Parameters")
        info['temp_coeff'] = st.number_input("Temp. Coeff. of Pmax (%/°C)", value=info.get('temp_coeff', -0.38), step=0.01, format="%.2f", help="The percentage decrease in panel efficiency for every 1°C increase in cell temperature above 25°C.")
        info['degradation_rate'] = st.number_input("Annual Degradation Rate (%)", value=info.get('degradation_rate', 0.5), step=0.1, format="%.2f", help="The theoretical annual degradation rate of panel efficiency.")
        info['irr_alert_threshold'] = st.slider("Irradiance Alert Threshold (%)", 5.0, 50.0, value=info.get('irr_alert_threshold', 20.0), help="The percentage threshold for actual irradiance deviation from expected values.")
    
    st.subheader("Long-term Forecast Parameters")
    info['forecast_period'] = st.slider("Forecast Period (Years)", 5, 25, value=info.get('forecast_period', 10), help="Number of years to forecast future energy production and performance.")
    st.markdown("---")

    st.header("2. Upload Actual Data File")
    st.caption("The PVsyst baseline is already loaded. Now, please upload the monthly actual production and weather data file.")
    
    actual_file_obj = st.file_uploader("Select Actual Data File (Excel)", type=['xlsx', 'xls'], key="actual_uploader")
    if actual_file_obj is not None:
        with st.spinner("Processing Actual data file..."):
            df, error = data_loader.load_actual_data(actual_file_obj)
            if error: 
                st.error(error)
                st.session_state.actual_df = None
            else: 
                st.session_state.actual_df = df
                st.success("✅ Actual data file loaded successfully!")
    else:
        st.session_state.actual_df = None
    
    if st.session_state.get('actual_df') is not None: 
        st.caption("First 5 rows of actual data:")
        st.dataframe(st.session_state.actual_df.head(), use_container_width=True)
    
    st.markdown("---")

    st.header("3. Run Full Analysis")
    is_disabled = st.session_state.get('actual_df') is None
    
    if st.button("Run Full Analysis & Save Project", type="primary", disabled=is_disabled):
        with st.spinner("Performing Analysis & Generating All Charts... Please wait."):
            analysis_df, insights = analysis.perform_phase2_analysis(
                _actual_df=st.session_state.actual_df, 
                _pvsyst_df=st.session_state.pvsyst_df, 
                _system_info=st.session_state.system_info
            )
            st.session_state.analysis_df = analysis_df
            st.session_state.insights = insights
            
            project_id = db_manager.save_project_data(st.session_state.system_info, analysis_df)
            if project_id:
                st.success(f"Analysis complete and project '{st.session_state.system_info['project_name']}' saved! You can now navigate to 'Analysis Report'.")
            else:
                st.error("Failed to save project data to database.")
            
            st.session_state.conclusion_text_list = analysis.generate_conclusion_text_phase2(
                insights, 
                analysis_df, 
                st.session_state.system_info
            )
            
            # --- Calculate and Plot Short-term Forecast ---
            st.session_state['short_term_forecast_result'] = analysis.calculate_short_term_forecast(analysis_df)
            if st.session_state['short_term_forecast_result']:
                st.session_state['short_term_forecast_fig'] = plotting.plot_short_term_forecast(
                    analysis_df, 
                    st.session_state['short_term_forecast_result']
                )
            else:
                st.session_state['short_term_forecast_fig'] = None

            # The rest of the plotting logic
            st.session_state.summary_table_df = analysis.create_summary_table(insights)
            st.session_state.guarantee_df = analysis.create_yearly_yield_guarantee_data(analysis_df, st.session_state.system_info) 
            st.session_state.forecast_df = analysis.calculate_long_term_forecast(analysis_df, st.session_state.pvsyst_df, st.session_state.system_info) 
            info = st.session_state.system_info
            st.session_state.sensor_health_fig = plotting.plot_sensor_health(analysis_df, info['irr_alert_threshold'])
            st.session_state.weather_analysis_fig = plotting.plot_weather_analysis(analysis_df) 
            st.session_state.performance_index_fig = plotting.plot_system_performance(analysis_df)
            st.session_state.yield_analysis_fig = plotting.plot_yield_analysis(analysis_df)
            st.session_state.guarantee_fig = plotting.plot_yearly_yield_vs_guarantee(st.session_state.guarantee_df) 
            overall_breakdown_data = analysis.get_loss_breakdown_data(analysis_df, insights, period='overall')
            st.session_state.overall_loss_breakdown_fig = plotting.plot_loss_breakdown(overall_breakdown_data, f"<b>Overall Energy Loss Analysis</b><br><sup>For {overall_breakdown_data['period_str']}</sup>") 
            latest_month_breakdown_data = analysis.get_loss_breakdown_data(analysis_df, period='latest_month')
            st.session_state.latest_month_loss_breakdown_fig = plotting.plot_loss_breakdown(latest_month_breakdown_data, f"<b>Monthly Energy Loss Analysis</b><br><sup>For {latest_month_breakdown_data['period_str']}</sup>")
            st.session_state.forecast_plot_fig = plotting.plot_long_term_forecast(st.session_state.forecast_df) 
            
        st.balloons()

    st.markdown("---")
    st.markdown("<div style='text-align: center; color: grey;'>Developed by <b>Studio OM</b></div>", unsafe_allow_html=True)

# ==============================================================================
# PAGE 2: ANALYSIS REPORT
# ==============================================================================
def show_analysis_report_page():
    """
    Displays the analysis report page with various tabs.
    """
    st.title("📈 Analysis Report & Results")

    if 'analysis_df' not in st.session_state or st.session_state.analysis_df is None:
        st.warning("⚠️ Please go to the 'Home & Input' page to upload data and run the analysis first.")
        st.stop()

    analysis_df = st.session_state.analysis_df
    insights = st.session_state.insights

    st.markdown("---")
    st.header("Key Performance Indicators (KPIs)")
    kpi_col1, kpi_col2, kpi_col3, kpi_col4 = st.columns(4)
    kpi_col1.metric("Performance Index (PI)", f"{insights.get('Average PI (%)', 0):.2f}%")
    kpi_col2.metric("Total Actual Yield", f"{insights.get('Total Actual Yield (MWh)', 0):.2f} MWh")
    kpi_col3.metric("Overall Yield Variance", f"{insights.get('Overall Yield Variance (MWh)', 0):.2f} MWh", f"{insights.get('Overall Yield Variance (%)', 0):.2f}%")
    kpi_col4.metric("Sensor Alerts", f"{insights.get('Sensor Alerts Count', 0)} Months")

    st.markdown("---")
    tabs = st.tabs(["💡 **Executive Summary**", "📊 **Performance Charts**", "🔮 **Long-term Forecast**", "📈 **Data Integrity**", "📋 **Detailed Data**"])
    
    with tabs[0]:
        st.header("Executive Summary")
        st.caption("Overview for executives and actionable recommendations.")
        
        # Display the short-term forecast plot at the top of the summary
        if st.session_state.get('short_term_forecast_fig'):
            st.plotly_chart(st.session_state.short_term_forecast_fig, use_container_width=True)
        
        if st.session_state.get('latest_month_loss_breakdown_fig'):
            st.plotly_chart(st.session_state.latest_month_loss_breakdown_fig, use_container_width=True)
        
        if st.session_state.get('conclusion_text_list'):
            for style, text in st.session_state.conclusion_text_list:
                if style == 'h3':
                    st.subheader(text)
                elif style == 'h4':
                    st.markdown("---") 
                    st.markdown(f"**{text}**")
                elif style == 'bullet':
                    st.markdown(f"- {text}")
                else:
                    st.write(text)
        else:
            st.info("No summary text available. Please run the analysis.")

    with tabs[1]:
        st.header("Monthly Performance Charts")
        if st.session_state.get('performance_index_fig'): st.plotly_chart(st.session_state.performance_index_fig, use_container_width=True)
        if st.session_state.get('yield_analysis_fig'): st.plotly_chart(st.session_state.yield_analysis_fig, use_container_width=True)
        if st.session_state.get('guarantee_fig'): st.plotly_chart(st.session_state.guarantee_fig, use_container_width=True)
        if st.session_state.get('overall_loss_breakdown_fig'): 
            st.plotly_chart(st.session_state.overall_loss_breakdown_fig, use_container_width=True)

    with tabs[2]:
        st.header("Long-term Forecast & Guarantee")
        if st.session_state.get('forecast_plot_fig'): st.plotly_chart(st.session_state.forecast_plot_fig, use_container_width=True)
        if st.session_state.get('forecast_df') is not None and not st.session_state.forecast_df.empty:
            st.subheader("Forecast Data Table")
            st.dataframe(st.session_state.forecast_df.style.format({'Forecasted Yield (MWh)': '{:,.1f}', 'Degraded Guarantee (MWh)': '{:,.1f}'}), use_container_width=True)

    with tabs[3]:
        st.header("Data Integrity & Weather Analysis")
        if st.session_state.get('sensor_health_fig'): st.plotly_chart(st.session_state.sensor_health_fig, use_container_width=True)
        if st.session_state.get('weather_analysis_fig'): st.plotly_chart(st.session_state.weather_analysis_fig, use_container_width=True)

    with tabs[4]:
        st.header("Detailed Analysis Data Table")
        with st.expander("Click to view the full data table"):
            st.dataframe(analysis_df, use_container_width=True)

# ==============================================================================
# PAGE 3: SIMULATOR
# ==============================================================================
def show_simulator_page():
    """
    Calls the simulator page function from the simulator module.
    """
    simulator.show_simulator_page()
# In app_pages.py

# ... (other functions and imports remain the same) ...

# ==============================================================================
# PAGE 4: ABOUT (IMPROVED MARKETING LANGUAGE)
# ==============================================================================
def show_about_page():
    """
    Displays the About page with information about the application,
    using more marketing-oriented language.
    """
    st.title("About Studio OM - Solar PV Analysis Tool") # Adjusted title

    # --- Studio OM Logo and Title ---
    col1, col2 = st.columns([1, 4])
    with col1:
        st.image("images/studio_om_logo.png", width=200)
    with col2:
        st.markdown("<br>", unsafe_allow_html=True) 
        st.title("")

    st.markdown("---")
    st.header("Transforming Solar Data into Actionable Intelligence") # New header
    st.markdown("Studio OM V2 is a cutting-edge platform designed to empower solar asset owners and operators with **precise insights** and **proactive strategies** for maximizing PV plant performance.")

    st.markdown("---")
    st.subheader("Key Features & Our Proprietary Methodology:") # Adjusted subheader
    st.markdown("""
- **Studio OM V2 Analysis Engine:** Our **proprietary** weather-adjusted performance analysis engine provides **unparalleled accuracy** by precisely accounting for real-world weather conditions. This ensures a true measure of your plant's health and performance.

- **ML-Powered Anomaly Detection:** Leveraging **advanced machine learning algorithms**, our system intelligently identifies unusual performance patterns that traditional methods might miss, providing **early warnings** for potential issues and enabling **proactive maintenance**.

- **Time-Series Forecasting (Prophet Integration):** Utilizing the robust Prophet model, we deliver **highly reliable short-term and long-term yield predictions**, incorporating seasonal trends and historical performance for **smarter future planning and financial foresight**.

- **Interactive Visualizations:** Built with Plotly, our dynamic charts offer **intuitive and actionable insights** at a glance, making complex data easy to understand and facilitating rapid decision-making.

- **Performance Simulator:** Our integrated simulator allows you to **strategically evaluate the financial impact** of various operational improvements, helping you optimize your O&M investments and identify the most cost-effective solutions.

- **Data Integrity Validation:** We ensure the reliability of your analysis from the start with **automated checks** on your PVsyst baseline data against regional benchmarks, building confidence in your results.
""")

    st.markdown("---")
    st.subheader("The Power Behind Studio OM V2:") # Adjusted subheader
    st.markdown("""
Studio OM V2 is engineered to transform raw operational data into **actionable intelligence**. By combining industry-standard methodologies with cutting-edge machine learning, we empower you to:

- **Maximize Energy Yield:** Identify and address performance gaps effectively to ensure your plant operates at its peak potential.
- **Optimize O&M Costs:** Make data-driven decisions on maintenance and operations, reducing unnecessary expenses and improving efficiency.
- **Enhance Financial Planning:** Gain clear foresight into future energy production and revenue, supporting robust financial projections and investment decisions.
- **Ensure Data Reliability:** Build unwavering confidence in your analysis with validated inputs and transparent methodologies.

Our commitment is to provide a **transparent, precise, and powerful** tool that elevates your solar PV asset management to the next level.
""")
    st.markdown("---")
    st.markdown("<div style='text-align: center; color: grey;'>Developed by <b>Studio OM</b></div>", unsafe_allow_html=True)