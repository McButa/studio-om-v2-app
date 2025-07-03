# src/db_manager.py

import sqlite3
import pandas as pd
from datetime import datetime
import os 
import streamlit as st 

# Define the database file path
DB_FILE = 'solar_pv_analysis.db'

def connect_db():
    """Establishes a connection to the SQLite database."""
    try:
        conn = sqlite3.connect(DB_FILE)
        return conn
    except sqlite3.Error as e:
        st.error(f"Database connection error: {e}") 
        return None

def create_tables():
    """Creates the necessary tables if they don't exist."""
    conn = connect_db()
    if conn:
        try:
            cursor = conn.cursor()
            
            # Table for project information
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS projects (
                    project_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_name TEXT UNIQUE NOT NULL,
                    owner_name TEXT,
                    pnom REAL,
                    commissioning_year INTEGER,
                    electricity_tariff REAL,
                    irr_alert_threshold REAL,
                    degradation_rate REAL,
                    energy_guarantee REAL,
                    temp_coeff REAL,
                    forecast_period INTEGER,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Table for monthly analysis data
            # IMPORTANT: Ensure 'year' and 'month' columns are present here, AND pvsyst_pr_percent, pvsyst_ghi_kwh_m2, pvsyst_yield_kwh
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS monthly_analysis_data (
                    data_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id INTEGER NOT NULL,
                    date TEXT NOT NULL, -- Stored as YYYY-MM-DD
                    actual_yield_kwh REAL,
                    expected_yield_kwh REAL,
                    ideal_yield_kwh REAL,
                    temp_loss_kwh REAL,
                    other_losses_kwh REAL,
                    yield_variance_kwh REAL,
                    yield_variance_percent REAL,
                    actual_ghi_kwh_m2 REAL,
                    pvsyst_ghi_kwh_m2 REAL, -- Added
                    irr_index_percent REAL,
                    irr_alert TEXT,
                    pi_percent REAL,
                    actual_pr_percent REAL,
                    pvsyst_pr_percent REAL, -- Added
                    pvsyst_yield_kwh REAL, -- Added
                    ambient_temp_c REAL,
                    op_year INTEGER,
                    year INTEGER, -- This column must exist for loading/saving
                    month INTEGER, -- This column must exist for loading/saving
                    FOREIGN KEY (project_id) REFERENCES projects (project_id),
                    UNIQUE (project_id, date) 
                )
            ''')
            
            conn.commit()
            return True
        except sqlite3.Error as e:
            st.error(f"Error creating tables: {e}") 
            return False
        finally:
            conn.close()
    return False

def save_project_data(system_info, analysis_df):
    """
    Saves or updates project information and its monthly analysis data to the database.
    
    Args:
        system_info (dict): Dictionary of system parameters.
        analysis_df (pd.DataFrame): DataFrame containing monthly analysis results.
    Returns:
        int or None: project_id if successful, None otherwise.
    """
    conn = connect_db()
    if conn:
        try:
            cursor = conn.cursor()
            
            project_name = system_info.get('project_name')
            if not project_name:
                st.error("Project name is required to save data.") 
                return None

            cursor.execute("SELECT project_id FROM projects WHERE project_name = ?", (project_name,))
            existing_project = cursor.fetchone()

            if existing_project:
                project_id = existing_project[0]
                cursor.execute('''
                    UPDATE projects SET
                        owner_name=?, pnom=?, commissioning_year=?, electricity_tariff=?,
                        irr_alert_threshold=?, degradation_rate=?, energy_guarantee=?,
                        temp_coeff=?, forecast_period=?, updated_at=CURRENT_TIMESTAMP
                    WHERE project_id = ?
                ''', (
                    system_info.get('owner_name'), system_info.get('pnom'), system_info.get('commissioning_year'),
                    system_info.get('electricity_tariff'), system_info.get('irr_alert_threshold'),
                    system_info.get('degradation_rate'), system_info.get('energy_guarantee'),
                    system_info.get('temp_coeff'), system_info.get('forecast_period'), project_id
                ))
            else:
                cursor.execute('''
                    INSERT INTO projects (
                        project_name, owner_name, pnom, commissioning_year, electricity_tariff,
                        irr_alert_threshold, degradation_rate, energy_guarantee,
                        temp_coeff, forecast_period
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    project_name, system_info.get('owner_name'), system_info.get('pnom'), system_info.get('commissioning_year'),
                    system_info.get('electricity_tariff'), system_info.get('irr_alert_threshold'),
                    system_info.get('degradation_rate'), system_info.get('energy_guarantee'),
                    system_info.get('temp_coeff'), system_info.get('forecast_period')
                ))
                project_id = cursor.lastrowid
            
            cursor.execute("DELETE FROM monthly_analysis_data WHERE project_id = ?", (project_id,))

            monthly_data_to_insert = []
            for _, row in analysis_df.iterrows():
                # Ensure all columns exist in the DataFrame before trying to access them
                # Use .get() with a default value for robustness if column might sometimes be missing
                monthly_data_to_insert.append((
                    project_id,
                    row['Date'].strftime('%Y-%m-%d'), 
                    row['actual_yield_kwh'],
                    row['expected_yield_kwh'],
                    row['ideal_yield_kwh'],
                    row['temp_loss_kwh'],
                    row['other_losses_kwh'],
                    row['yield_variance_kwh'],
                    row['yield_variance_%'],
                    row['actual_ghi_kwh_m2'],
                    row['pvsyst_ghi_kwh_m2'], # Added
                    row['irr_index_%'],
                    row['irr_alert'],
                    row['pi_%'],
                    row['actual_pr_percent'],
                    row.get('pvsyst_pr_percent', None), # Added
                    row.get('pvsyst_yield_kwh', None), # Added
                    row['ambient_temp_c'],
                    row['op_year'],
                    row['Year'], 
                    row['Month']  
                ))
            
            # FIX: Updated INSERT statement to include pvsyst_ghi_kwh_m2, pvsyst_pr_percent, pvsyst_yield_kwh
            cursor.executemany('''
                INSERT INTO monthly_analysis_data (
                    project_id, date, actual_yield_kwh, expected_yield_kwh, ideal_yield_kwh,
                    temp_loss_kwh, other_losses_kwh, yield_variance_kwh, yield_variance_percent,
                    actual_ghi_kwh_m2, pvsyst_ghi_kwh_m2, irr_index_percent, irr_alert,
                    pi_percent, actual_pr_percent, pvsyst_pr_percent, pvsyst_yield_kwh, ambient_temp_c, op_year,
                    year, month
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', monthly_data_to_insert)

            conn.commit()
            return project_id
        except sqlite3.Error as e:
            st.error(f"Error saving project data: {e}") 
            return None
        finally:
            conn.close()
    return None

def load_all_project_names():
    """Loads all project names from the database."""
    conn = connect_db()
    project_names = []
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT project_name FROM projects ORDER BY project_name")
            project_names = [row[0] for row in cursor.fetchall()]
        except sqlite3.Error as e:
            st.error(f"Error loading project names: {e}") 
        finally:
            conn.close()
    return project_names

def load_project_data(project_name):
    """
    Loads project information and its monthly analysis data from the database.
    
    Args:
        project_name (str): The name of the project to load.
    Returns:
        tuple or None: (system_info_dict, analysis_df) if successful, None otherwise.
    """
    conn = connect_db()
    if conn:
        try:
            cursor = conn.cursor()
            
            # 1. Load project info
            cursor.execute("SELECT * FROM projects WHERE project_name = ?", (project_name,))
            project_row = cursor.fetchone()

            if not project_row:
                st.warning(f"Project '{project_name}' not found.") 
                return None

            col_names = [description[0] for description in cursor.description]
            system_info = dict(zip(col_names, project_row))
            system_info.pop('project_id', None)
            system_info.pop('created_at', None)
            system_info.pop('updated_at', None)
            
            # 2. Load monthly analysis data
            project_id = project_row[0] 
            cursor.execute("SELECT * FROM monthly_analysis_data WHERE project_id = ? ORDER BY date", (project_id,))
            monthly_data = cursor.fetchall()
            
            if not monthly_data:
                st.warning(f"No monthly analysis data found for project '{project_name}'.") 
                return system_info, pd.DataFrame() 

            # Convert to DataFrame
            monthly_cols = [description[0] for description in cursor.description]
            analysis_df = pd.DataFrame(monthly_data, columns=monthly_cols)
            
            # Convert 'date' column back to datetime object
            analysis_df['date'] = pd.to_datetime(analysis_df['date'])
            # Rename columns to match the analysis_df structure used by other modules
            analysis_df.rename(columns={
                'date': 'Date', 
                'yield_variance_percent': 'yield_variance_%', 
                'irr_index_percent': 'irr_index_%', 
                'pi_percent': 'pi_%',
                'pvsyst_pr_percent': 'pvsyst_pr_percent', 
                'actual_pr_percent': 'actual_pr_percent',
                'pvsyst_yield_kwh': 'pvsyst_yield_kwh', # Added
                'pvsyst_ghi_kwh_m2': 'pvsyst_ghi_kwh_m2', # Added
                'year': 'Year',   
                'month': 'Month'  
            }, inplace=True)
            
            # Drop DB-specific columns not needed for analysis
            analysis_df.drop(columns=['data_id', 'project_id'], inplace=True, errors='ignore')
            
            return system_info, analysis_df
        except sqlite3.Error as e:
            st.error(f"Error loading project data: {e}") 
            return None
        finally:
            conn.close()
    return None