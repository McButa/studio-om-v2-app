# src/data_loader.py

import pandas as pd
import streamlit as st

# --- NEW: Column name mapping for Phase 2 ---
PVSYST_BASELINE_MAP = {
    'Statistical Period': 'Month_Str',
    'Baseline E_Grid (kWh)': 'pvsyst_yield_kwh',
    'Baseline PR (%)': 'pvsyst_pr_percent',
    'GlobHor': 'pvsyst_ghi_kwh_m2'
}

ACTUAL_DATA_MAP = {
    'Statistical Period': 'Date',
    'Inverter Yield (kWh)': 'actual_yield_kwh',
    'Performance Ratio (%)': 'actual_pr_percent',
    'Global Irradiation (kWh/m²)': 'actual_ghi_kwh_m2',
    'Ambient Temp. C': 'ambient_temp_c' 
}

# REMOVED: @st.cache_data
def load_pvsyst_baseline(uploaded_file):
    """
    Loads and processes the PVsyst baseline/simulation file.
    """
    if uploaded_file is None:
        return None, "No PVsyst baseline file uploaded."

    try:
        df = pd.read_excel(uploaded_file)
        df.rename(columns=PVSYST_BASELINE_MAP, inplace=True)

        required_cols = list(PVSYST_BASELINE_MAP.values())
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            return None, f"PVsyst file is missing required columns: {', '.join(missing_cols)}. Please ensure the Excel file contains these headers."

        # Extract month number for merging (e.g., '2023-01' -> 1)
        # Assuming 'Month_Str' is in YYYY-MM format
        df['Month'] = pd.to_datetime(df['Month_Str'], format='%Y-%m').dt.month
        
        # Convert data to numeric, coercing errors
        for col in ['pvsyst_yield_kwh', 'pvsyst_pr_percent', 'pvsyst_ghi_kwh_m2']:
            df[col] = pd.to_numeric(df[col], errors='coerce')

        df.dropna(inplace=True)
        
        # Select only necessary columns for analysis
        final_cols = ['Month', 'pvsyst_yield_kwh', 'pvsyst_pr_percent', 'pvsyst_ghi_kwh_m2']
        return df[final_cols], None

    except Exception as e:
        return None, f"Failed to read or process PVsyst file. Error: {e}"

# REMOVED: @st.cache_data
def load_actual_data(uploaded_file):
    """
    Loads and processes the actual performance and weather data file.
    """
    if uploaded_file is None:
        return None, "No actual data file uploaded."

    try:
        df = pd.read_excel(uploaded_file)
        df.rename(columns=ACTUAL_DATA_MAP, inplace=True)

        required_cols = list(ACTUAL_DATA_MAP.values())
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            return None, f"Actual data file is missing required columns: {', '.join(missing_cols)}. Please ensure the Excel file contains these headers."

        # Convert date and numeric columns
        # Assuming 'Date' column is in YYYY-MM format
        df['Date'] = pd.to_datetime(df['Date'], format='%Y-%m')
        for col in ['actual_yield_kwh', 'actual_pr_percent', 'actual_ghi_kwh_m2', 'ambient_temp_c']: 
            df[col] = pd.to_numeric(df[col], errors='coerce')
            
        df.dropna(inplace=True)
        
        # Add Year and Month columns for analysis
        df['Year'] = df['Date'].dt.year
        df['Month'] = df['Date'].dt.month

        return df, None

    except Exception as e:
        return None, f"Failed to read or process actual data file. Error: {e}"