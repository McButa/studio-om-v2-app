# src/analysis.py (The Truly Complete and Corrected Version)

import pandas as pd
import numpy as np
import streamlit as st
import json
from sklearn.ensemble import IsolationForest
from prophet import Prophet

def _get_full_years_df(df):
    """Filters the DataFrame to include only data from full years."""
    if df.empty:
        return pd.DataFrame()
    month_counts = df.groupby('Year')['Month'].nunique()
    full_years = month_counts[month_counts == 12].index
    return df[df['Year'].isin(full_years)].copy()

@st.cache_data
def perform_phase2_analysis(_actual_df, _pvsyst_df, _system_info):
    """
    Performs the Studio OM V2 analysis using weather-adjusted PVsyst data.
    """
    analysis_df = pd.merge(_actual_df, _pvsyst_df, on='Month', how='left')
    
    degradation_rate = _system_info.get('degradation_rate', 0.5) / 100.0
    commissioning_year = _system_info.get('commissioning_year', 2020)
    temp_coeff = _system_info.get('temp_coeff', -0.38) / 100.0

    analysis_df['op_year'] = analysis_df['Year'] - commissioning_year
    analysis_df['op_year'] = analysis_df['op_year'].apply(lambda x: max(x, 0))

    analysis_df['irr_index_%'] = (analysis_df['actual_ghi_kwh_m2'] / analysis_df['pvsyst_ghi_kwh_m2']).replace([np.inf, -np.inf], np.nan) * 100
    analysis_df['irr_index_%'] = analysis_df['irr_index_%'].fillna(0)

    threshold = _system_info.get('irr_alert_threshold', 20.0)
    analysis_df['irr_alert'] = np.where(
        (analysis_df['irr_index_%'] > 100 + threshold) | (analysis_df['irr_index_%'] < 100 - threshold),
        "⚠️ Check Sensor", "✅ OK"
    )

    analysis_df['ideal_yield_kwh'] = analysis_df['pvsyst_yield_kwh'] * (analysis_df['actual_ghi_kwh_m2'] / analysis_df['pvsyst_ghi_kwh_m2']).replace([np.inf, -np.inf], np.nan).fillna(0)
    analysis_df['temp_loss_kwh'] = analysis_df['ideal_yield_kwh'] * temp_coeff * (analysis_df['ambient_temp_c'] - 25)
    analysis_df['expected_yield_kwh'] = analysis_df['ideal_yield_kwh'] + analysis_df['temp_loss_kwh'] 
    analysis_df['expected_yield_kwh'] = analysis_df['expected_yield_kwh'].apply(lambda x: max(x, 0.01))
    analysis_df['pi_%'] = (analysis_df['actual_yield_kwh'] / analysis_df['expected_yield_kwh']) * 100
    analysis_df['other_losses_kwh'] = analysis_df['expected_yield_kwh'] - analysis_df['actual_yield_kwh']
    analysis_df['yield_variance_kwh'] = analysis_df['actual_yield_kwh'] - analysis_df['expected_yield_kwh']
    analysis_df['yield_variance_%'] = (analysis_df['yield_variance_kwh'] / analysis_df['expected_yield_kwh']).replace([np.inf, -np.inf], np.nan) * 100
    analysis_df['yield_variance_%'] = analysis_df['yield_variance_%'].fillna(0)

    insights = {}
    total_actual_yield_mwh = analysis_df['actual_yield_kwh'].sum() / 1000
    total_expected_yield_mwh = analysis_df['expected_yield_kwh'].sum() / 1000
    
    insights['Total Actual Yield (MWh)'] = total_actual_yield_mwh
    insights['Total Expected Yield (MWh)'] = total_expected_yield_mwh 
    insights['Total Ideal Yield (MWh)'] = analysis_df['ideal_yield_kwh'].sum() / 1000
    insights['Total Temperature Loss (MWh)'] = analysis_df['temp_loss_kwh'].sum() / 1000
    insights['Total Other Losses (MWh)'] = analysis_df['other_losses_kwh'].sum() / 1000
    insights['Overall Yield Variance (MWh)'] = total_actual_yield_mwh - total_expected_yield_mwh
    insights['Overall Yield Variance (%)'] = ((total_actual_yield_mwh - total_expected_yield_mwh) / total_expected_yield_mwh) * 100 if total_expected_yield_mwh > 0 else 0
    insights['Average PI (%)'] = (analysis_df['actual_yield_kwh'].sum() / analysis_df['expected_yield_kwh'].sum()) * 100 if analysis_df['expected_yield_kwh'].sum() > 0 else 0
    insights['Average PR (%)'] = analysis_df['actual_pr_percent'].mean()
    insights['Sensor Alerts Count'] = len(analysis_df[analysis_df['irr_alert'] != "✅ OK"])

    final_cols = [
        'Date', 'Year', 'Month', 'op_year', 
        'actual_yield_kwh', 'expected_yield_kwh', 'ideal_yield_kwh', 
        'temp_loss_kwh', 'other_losses_kwh', 
        'yield_variance_kwh', 'yield_variance_%',
        'actual_ghi_kwh_m2', 'pvsyst_ghi_kwh_m2', 'irr_index_%', 'irr_alert',
        'pi_%', 'actual_pr_percent', 'pvsyst_pr_percent', 'ambient_temp_c' 
    ]
    analysis_df = analysis_df[final_cols].sort_values(by='Date').reset_index(drop=True)

    return analysis_df, insights

@st.cache_data
def get_loss_breakdown_data(analysis_df, insights=None, period='overall'):
    if analysis_df.empty:
        return {'ideal': 0, 'temp_loss': 0, 'other_loss': 0, 'actual': 0, 'period_str': 'no data'}
    if period == 'overall':
        if insights is None:
            raise ValueError("Insights dictionary must be provided for 'overall' period.")
        return {
            'ideal': insights.get('Total Ideal Yield (MWh)', 0),
            'temp_loss': insights.get('Total Temperature Loss (MWh)', 0),
            'other_loss': insights.get('Total Other Losses (MWh)', 0),
            'actual': insights.get('Total Actual Yield (MWh)', 0),
            'period_str': "the entire analysis period"
        }
    elif period == 'latest_month':
        latest_row = analysis_df.iloc[-1]
        return {
            'ideal': latest_row['ideal_yield_kwh'] / 1000,
            'temp_loss': latest_row['temp_loss_kwh'] / 1000,
            'other_loss': latest_row['other_losses_kwh'] / 1000,
            'actual': latest_row['actual_yield_kwh'] / 1000,
            'period_str': latest_row['Date'].strftime('%B %Y')
        }
    else:
        raise ValueError("Invalid period. Must be 'overall' or 'latest_month'.")

@st.cache_data
def create_summary_table(insights):
    summary_data = {
        'Metric': ['Total Actual Yield', 'Total Expected Yield (Weather Adjusted)', 'Overall Yield Variance (MWh)', 'Overall Yield Variance (%)', 'Average Performance Index (PI)', 'Average Actual Performance Ratio (PR)', 'Number of Sensor Alerts'],
        'Value': [f"{insights.get('Total Actual Yield (MWh)', 0):.2f} MWh", f"{insights.get('Total Expected Yield (MWh)', 0):.2f} MWh", f"{insights.get('Overall Yield Variance (MWh)', 0):.2f} MWh", f"{insights.get('Overall Yield Variance (%)', 0):.2f} %", f"{insights.get('Average PI (%)', 0):.2f} %", f"{insights.get('Average PR (%)', 0):.2f} %", f"{insights.get('Sensor Alerts Count', 0)} Months"]
    }
    return pd.DataFrame(summary_data)

@st.cache_data
def create_yearly_yield_guarantee_data(analysis_df, system_info):
    commissioning_year = system_info['commissioning_year']
    annual_guarantee_mwh = system_info.get('energy_guarantee', 0)
    yearly_actual_yields = analysis_df.groupby('Year')['actual_yield_kwh'].sum() / 1000
    yearly_actual_yields = yearly_actual_yields.reset_index().rename(columns={'actual_yield_kwh': 'Actual Yearly Yield (MWh)'})
    yearly_expected_yields = analysis_df.groupby('Year')['expected_yield_kwh'].sum() / 1000
    yearly_expected_yields = yearly_expected_yields.reset_index().rename(columns={'expected_yield_kwh': 'Expected Yearly Yield (MWh)'})
    min_year = yearly_actual_yields['Year'].min() if not yearly_actual_yields.empty else commissioning_year
    max_year = yearly_actual_yields['Year'].max() if not yearly_actual_yields.empty else commissioning_year
    all_years_df = pd.DataFrame({'Year': range(int(min_year), int(max_year) + 1)})
    result_df = pd.merge(all_years_df, yearly_actual_yields, on='Year', how='left')
    result_df = pd.merge(result_df, yearly_expected_yields, on='Year', how='left')
    result_df['Energy Guarantee (MWh)'] = annual_guarantee_mwh
    return result_df[['Year', 'Actual Yearly Yield (MWh)', 'Energy Guarantee (MWh)', 'Expected Yearly Yield (MWh)']]

@st.cache_data
def calculate_long_term_forecast(analysis_df, pvsyst_df, system_info):
    full_years_df = _get_full_years_df(analysis_df)
    if full_years_df.empty or pvsyst_df.empty or len(full_years_df) < 12:
        st.warning("Long-term forecast requires at least one full year (12 months) of historical data.")
        return pd.DataFrame()
    pi_df = full_years_df[['Date', 'pi_%']].copy()
    pi_df.rename(columns={'Date': 'ds', 'pi_%': 'y'}, inplace=True)
    model = Prophet(yearly_seasonality=True, changepoint_prior_scale=0.05)
    model.fit(pi_df)
    forecast_period_years = system_info.get('forecast_period', 10)
    future_dates = model.make_future_dataframe(periods=forecast_period_years * 12, freq='MS')
    forecast = model.predict(future_dates)
    forecast_df = forecast[['ds', 'yhat']].copy()
    forecast_df.rename(columns={'ds': 'Date', 'yhat': 'Forecasted PI (%)'}, inplace=True)
    forecast_df['Forecasted PI (%)'] = forecast_df['Forecasted PI (%)'].clip(lower=50, upper=110)
    forecast_df['Year'] = forecast_df['Date'].dt.year
    pvsyst_monthly_yield = pvsyst_df[['Month', 'pvsyst_yield_kwh']].copy()
    forecast_df['Month'] = forecast_df['Date'].dt.month
    forecast_df = pd.merge(forecast_df, pvsyst_monthly_yield, on='Month', how='left')
    forecast_df['Forecasted Monthly Yield (kWh)'] = forecast_df['pvsyst_yield_kwh'] * (forecast_df['Forecasted PI (%)'] / 100.0)
    yearly_forecast = forecast_df.groupby('Year')['Forecasted Monthly Yield (kWh)'].sum().reset_index()
    yearly_forecast.rename(columns={'Forecasted Monthly Yield (kWh)': 'Forecasted Yield (MWh)'}, inplace=True)
    yearly_forecast['Forecasted Yield (MWh)'] /= 1000
    last_full_year = int(full_years_df['Year'].max())
    yearly_actuals = full_years_df.groupby('Year')['actual_yield_kwh'].sum().reset_index()
    yearly_actuals.rename(columns={'actual_yield_kwh': 'Actual Yearly Yield (MWh)'}, inplace=True)
    yearly_actuals['Actual Yearly Yield (MWh)'] /= 1000
    final_df = pd.merge(yearly_forecast, yearly_actuals, on='Year', how='left')
    final_df['Forecasted Yield (MWh)'] = final_df['Actual Yearly Yield (MWh)'].fillna(final_df['Forecasted Yield (MWh)'])
    final_df.drop(columns=['Actual Yearly Yield (MWh)'], inplace=True)
    commissioning_year = system_info['commissioning_year']
    annual_guarantee_mwh = system_info.get('energy_guarantee', 0)
    theoretical_degradation_rate = system_info.get('degradation_rate', 0.5) / 100.0
    final_df['Degraded Guarantee (MWh)'] = annual_guarantee_mwh * ((1 - theoretical_degradation_rate) ** (final_df['Year'] - commissioning_year))
    final_df['Type'] = np.where(final_df['Year'] <= last_full_year, 'Historical', 'Forecast')
    return final_df[['Year', 'Forecasted Yield (MWh)', 'Degraded Guarantee (MWh)', 'Type']]

def calculate_short_term_forecast(analysis_df):
    if analysis_df.empty or len(analysis_df) < 6:
        return None
    recent_df = analysis_df.tail(24)
    pi_df = recent_df[['Date', 'pi_%']].copy()
    pi_df.rename(columns={'Date': 'ds', 'pi_%': 'y'}, inplace=True)
    model = Prophet(yearly_seasonality=True)
    model.fit(pi_df)
    future = model.make_future_dataframe(periods=1, freq='MS')
    forecast = model.predict(future)
    next_month_forecast = forecast.iloc[-1]
    return {"date": next_month_forecast['ds'].strftime('%B %Y'), "pi": next_month_forecast['yhat'], "pi_lower": next_month_forecast['yhat_lower'], "pi_upper": next_month_forecast['yhat_upper']}

def detect_anomalies_with_ml(analysis_df):
    if analysis_df.empty or len(analysis_df) < 3:
        analysis_df['is_anomaly'] = 1
        return analysis_df
    features = ['pi_%', 'other_losses_kwh', 'irr_index_%']
    data_for_model = analysis_df[features].copy().fillna(0)
    model = IsolationForest(contamination='auto', random_state=42, n_estimators=100)
    model.fit(data_for_model)
    predictions = model.predict(data_for_model)
    analysis_df['is_anomaly'] = predictions
    return analysis_df

@st.cache_data
def generate_conclusion_text_phase2(insights, analysis_df, system_info):
    report_lines = []
    recommendations = []
    analysis_df = detect_anomalies_with_ml(analysis_df)
    anomalous_months_df = analysis_df[analysis_df['is_anomaly'] == -1]
    report_lines.append(('h3', "🤖 AI Performance Assistant Insights"))
    report_lines.append(('body', "I've analyzed your PV plant's performance data using the Studio OM V2 analysis engine and machine learning to generate key insights and actionable recommendations."))
    report_lines.append(('h4', "Key Performance Insights"))
    avg_pi = insights.get('Average PI (%)', 0)
    total_actual_yield_mwh = insights.get('Total Actual Yield (MWh)', 0)
    summary_text = f"Over the analysis period, your system generated a total of {total_actual_yield_mwh:.2f} MWh, with an average Performance Index (PI) of {avg_pi:.2f}%. "
    if avg_pi >= 100:
        summary_text += "This indicates excellent system performance."
    elif avg_pi >= 97:
        summary_text += "This indicates good system performance."
    else:
        summary_text += "This suggests some level of underperformance. See anomaly report below for details."
    report_lines.append(('body', summary_text))
    short_term_forecast_result = calculate_short_term_forecast(analysis_df)
    if short_term_forecast_result:
        report_lines.append(('h4', "Next Month Forecast"))
        fc = short_term_forecast_result
        forecast_text = f"For **{fc['date']}**, the expected Performance Index (PI) is forecasted to be around **{fc['pi']:.1f}%** (with a likely range of {fc['pi_lower']:.1f}% to {fc['pi_upper']:.1f}%)."
        report_lines.append(('body', forecast_text))
    full_years_df_for_trend = _get_full_years_df(analysis_df)
    if len(full_years_df_for_trend['Year'].unique()) > 1:
        report_lines.append(('h4', "Degradation Trend"))
        report_lines.append(('body', "Degradation trend analysis is based on full years of data to ensure accuracy."))
    report_lines.append(('h4', "Machine Learning Anomaly Report"))
    if not anomalous_months_df.empty:
        report_lines.append(('body', "Our ML model has identified the following months with unusual performance patterns:"))
        for index, row in anomalous_months_df.iterrows():
            month_str = row['Date'].strftime('%B %Y')
            pi_val = row['pi_%']
            anomaly_summary = f"**Month: {month_str}** (PI: {pi_val:.1f}%)"
            report_lines.append(('bullet', anomaly_summary))
            recommendations.append(f"Investigate Anomaly in {month_str}: Review O&M logs and system components.")
    else:
        report_lines.append(('body', "✅ No significant performance anomalies were detected."))
    if recommendations:
        report_lines.append(('h3', "Actionable Recommendations"))
        if insights.get('Sensor Alerts Count', 0) > 0:
            recommendations.insert(0, "Inspect Irradiance Sensor: Check the pyranometer for cleanliness and calibration.")
        for item in sorted(list(set(recommendations))):
            report_lines.append(('bullet', item))
    else:
        report_lines.append(('h3', "Actionable Recommendations"))
        report_lines.append(('body', "The system is performing optimally. Continue with regular preventive maintenance."))
    return report_lines

# --- THIS IS THE MISSING FUNCTION ---
def validate_pvsyst_baseline(pvsyst_df, location_key, system_pnom):
    """
    Validates a PVsyst DataFrame against regional benchmarks.
    """
    if location_key.startswith("---") or pvsyst_df is None:
        return None, "Please select a project location and upload a PVsyst file.", None
    
    # Use a more robust way to check for file existence
    benchmark_file_path = 'data/th_province_benchmarks.json'
    if not pd.io.common.file_exists(benchmark_file_path):
        benchmark_file_path = 'data/location_benchmarks.json'

    try:
        with open(benchmark_file_path) as f:
            benchmarks = json.load(f)
    except FileNotFoundError:
        return None, f"Benchmark file '{benchmark_file_path}' not found.", "error"
    
    benchmark_data = benchmarks.get(location_key)
    if not benchmark_data or benchmark_data.get('avg_annual_ghi') is None:
        return None, f"Benchmark data not found for '{location_key}'.", "error"

    pvsyst_annual_ghi = pvsyst_df['pvsyst_ghi_kwh_m2'].sum()
    pvsyst_annual_yield = pvsyst_df['pvsyst_yield_kwh'].sum()
    
    if system_pnom <= 0:
        return None, "Nominal Power (Pnom) must be greater than zero.", "error"
    pvsyst_specific_yield = pvsyst_annual_yield / system_pnom

    bm_ghi = benchmark_data['avg_annual_ghi']
    ghi_consistency = 100 - abs(((pvsyst_annual_ghi - bm_ghi) / bm_ghi) * 100)

    bm_yield = benchmark_data['avg_specific_yield']
    yield_consistency = 100 - abs(((pvsyst_specific_yield - bm_yield) / bm_yield) * 100)
    
    avg_consistency = (ghi_consistency + yield_consistency) / 2
    
    if avg_consistency >= 95:
        message = "High Consistency: The baseline aligns well with regional satellite data. Recommended for analysis."
        status = "success"
    elif avg_consistency >= 90:
        message = "Good Consistency: The baseline shows minor deviation but is acceptable for analysis."
        status = "warning"
    else:
        message = "Low Consistency: Significant deviation detected. Results may be unreliable. Please verify the PVsyst report."
        status = "error"

    return f"{avg_consistency:.1f}%", message, status