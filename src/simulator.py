# src/simulator.py

import streamlit as st
import pandas as pd
import plotly.graph_objects as go

def run_loss_simulation(start_value, losses_percent):
    """
    Calculates energy step-by-step according to the Loss Diagram.
    - start_value: Initial energy (kWh)
    - losses_percent: Dictionary of user-adjusted loss values (as %)
    """
    losses = {k: v / 100.0 for k, v in losses_percent.items()} # Convert % to decimal

    steps = []
    breakdown = {} # To store actual loss values
    current_value = float(start_value)
    
    steps.append({'Step': 'Initial Actual Energy (kWh/month)', 'Energy (kWh)': current_value})

    # 1. Module Quality (can be a Gain or Loss)
    # If positive, it's better than expected quality (Gain).
    # If negative, it's worse than expected quality (Loss).
    module_quality_change = current_value * losses['module_quality']
    current_value += module_quality_change
    breakdown['Module Quality'] = module_quality_change
    steps.append({'Step': 'After Module Quality Adjustment', 'Energy (kWh)': current_value})

    # 2. LID Loss (Light Induced Degradation)
    lid_loss_val = current_value * losses['lid']
    current_value -= lid_loss_val
    breakdown['LID Loss'] = -lid_loss_val # Negative to indicate a loss
    steps.append({'Step': 'After LID Loss', 'Energy (kWh)': current_value})

    # 3. Mismatch Loss
    mismatch_loss_val = current_value * losses['mismatch']
    current_value -= mismatch_loss_val
    breakdown['Mismatch Loss'] = -mismatch_loss_val
    steps.append({'Step': 'After Mismatch Loss', 'Energy (kWh)': current_value})
    
    # 4. Ohmic Wiring Loss
    wiring_loss_val = current_value * losses['wiring']
    current_value -= wiring_loss_val
    breakdown['Ohmic Wiring Loss'] = -wiring_loss_val
    steps.append({'Step': 'Energy Before Inverter', 'Energy (kWh)': current_value})

    # 5. Inverter Loss (Efficiency)
    inverter_loss_val = current_value * losses['inverter_eff']
    current_value -= inverter_loss_val
    breakdown['Inverter Loss'] = -inverter_loss_val
    steps.append({'Step': 'After Inverter Efficiency Loss', 'Energy (kWh)': current_value})
    
    # 6. System Unavailability
    unavailability_loss_val = current_value * losses['unavailability']
    current_value -= unavailability_loss_val
    breakdown['System Unavailability'] = -unavailability_loss_val
    steps.append({'Step': 'Net Energy Output (kWh/month)', 'Energy (kWh)': current_value})
    
    breakdown['Final Energy (Net Output)'] = current_value

    return pd.DataFrame(steps), breakdown

def create_breakdown_bar_chart(breakdown_data, start_energy):
    """
    Creates an "Energy Loss Breakdown" bar chart.
    Args:
        breakdown_data (dict): Dictionary containing loss/gain values and Final Energy.
        start_energy (float): Initial Energy.
    """
    labels = []
    values = []
    colors = []
    
    # Add Initial Energy
    labels.append('Initial Energy')
    values.append(start_energy)
    colors.append('rgba(0, 150, 136, 1.0)') # Teal-like color
    
    # Sort losses/gains, excluding Final Energy
    filtered_breakdown = {k: v for k, v in breakdown_data.items() if k not in ['Final Energy (Net Output)']}
    sorted_losses = sorted(filtered_breakdown.items(), key=lambda item: item[1])

    # Add each loss/gain component
    for label, value in sorted_losses:
        labels.append(label)
        values.append(value)
        if value < 0: # It's a loss (value is negative)
            colors.append('rgba(205, 36, 36, 1.0)') # Red
        else: # It's a gain (value is positive)
            colors.append('rgba(0, 176, 246, 1.0)') # Blue
            
    # Add Final Energy (Net Output)
    final_energy = breakdown_data.get('Final Energy (Net Output)', 0)
    labels.append('Net Energy Output')
    values.append(final_energy)
    colors.append('rgba(4, 90, 168, 1.0)') # Dark blue

    # For waterfall-like bar chart, we need a running total
    x_coords = [labels[0]]
    y_coords = [values[0]]
    measure_type = ['absolute']
    text_values = [f"{values[0]:,.0f}"]
    bar_colors = [colors[0]] # Initial Energy color

    current_sum = values[0]
    for i in range(1, len(labels) - 1): # Exclude initial and final
        x_coords.append(labels[i])
        y_coords.append(values[i]) # These are the deltas
        measure_type.append('relative')
        text_values.append(f"{values[i]:,.0f}")
        bar_colors.append(colors[i])
        current_sum += values[i]

    x_coords.append(labels[-1])
    y_coords.append(values[-1]) # Final total
    measure_type.append('total')
    text_values.append(f"<b>{values[-1]:,.0f}</b>")
    bar_colors.append(colors[-1])
    
    fig = go.Figure(go.Waterfall(
        name="Energy Breakdown", 
        orientation="v", 
        measure=measure_type,
        x=x_coords,
        text=text_values,
        textposition="outside", 
        y=y_coords,
        connector={"line": {"color": "rgb(63, 63, 63)"}},
        totals={"marker": {"color": "rgba(4, 90, 168, 1.0)", "line": {"color": "grey", "width": 1}}}, 
        decreasing={"marker": {"color": "rgba(205, 36, 36, 1.0)"}}, 
        increasing={"marker": {"color": "rgba(0, 176, 246, 1.0)"}} 
    ))
    
    fig.update_layout(
        title_text='<b>Energy Loss Breakdown Analysis</b>',
        yaxis_title="Energy (kWh)", 
        showlegend=False, 
        font=dict(family="Arial, sans-serif", size=12),
        xaxis=dict(tickfont=dict(size=11)), 
        yaxis=dict(gridcolor='lightgrey'), 
        plot_bgcolor='white', 
        margin=dict(t=80, b=40, l=40, r=40)
    )
    return fig

def show_simulator_page():
    """
    Creates the UI for the Simulator. This function is called by the Streamlit page.
    """
    st.title("🛠️ Performance Improvement Simulator")
    st.markdown("Use this tool to simulate the impact of various improvements on energy yield and find the optimal strategies.")
    st.markdown("---")

    # --- Create main 2-column layout ---
    left_col, right_col = st.columns(2, gap="large")

    # =================== Left Column (Controls) ===================
    with left_col:
        st.header("1. Adjust Parameters")
        
        initial_actual_yield = 0.0
        if 'analysis_df' in st.session_state and st.session_state.analysis_df is not None and not st.session_state.analysis_df.empty:
            initial_actual_yield = st.session_state.analysis_df['actual_yield_kwh'].mean() 

        start_energy = st.number_input(
            "Initial Actual Energy (kWh/month)", 
            value=float(f"{initial_actual_yield:.2f}"), 
            format="%.2f",
            help="Enter the average actual energy produced per month from historical data to use as the simulation's starting point."
        )
        
        st.markdown("---")
        
        st.subheader("Adjust Loss Factors")
        st.caption("Adjust these percentages to simulate their impact on energy yield.")
        
        losses = {}
        
        losses['module_quality'] = st.slider("Module Quality & Manufacturing Tolerance (%)", -2.0, 2.0, 0.75, 0.01, help="Positive value indicates better-than-average quality (energy gain), negative value indicates lower quality (energy loss).")
        losses['lid'] = st.slider("LID - Light Induced Degradation (%)", 0.0, 5.0, 1.50, 0.1, help="Degradation during the initial operation period of solar panels (Loss).")
        losses['mismatch'] = st.slider("Mismatch Loss (%)", 0.0, 5.0, 1.10, 0.1, help="Loss due to incompatibility between panels or strings (Loss).")
        losses['wiring'] = st.slider("Ohmic Wiring Loss (%)", 0.0, 4.0, 1.06, 0.01, help="Energy loss due to resistance in DC wiring (Loss).")
        losses['inverter_eff'] = st.slider("Inverter Efficiency Loss (%)", 1.0, 10.0, 2.24, 0.01, help="Energy loss during the DC to AC power conversion process in the inverter (Loss).")
        losses['unavailability'] = st.slider("System Unavailability (%)", 0.0, 10.0, 1.08, 0.01, help="Percentage of time the system is down or unable to produce energy (Downtime Loss).")

    # =================== Right Column (Results) ===================
    with right_col:
        st.header("2. Simulation Results")

        if start_energy > 0:
            baseline_expected_yield_mean = 0.0
            if 'analysis_df' in st.session_state and st.session_state.analysis_df is not None and not st.session_state.analysis_df.empty:
                baseline_expected_yield_mean = st.session_state.analysis_df['expected_yield_kwh'].mean() 
            
            steps_df, breakdown_data = run_loss_simulation(start_energy, losses)
            final_sim_energy = steps_df.iloc[-1]['Energy (kWh)']
            
            # --- Display summary metrics ---
            potential_gain = final_sim_energy - baseline_expected_yield_mean 
            electricity_tariff = st.session_state.system_info.get('electricity_tariff', 4.0)
            potential_revenue = potential_gain * electricity_tariff
            
            sub_col1, sub_col2 = st.columns(2)
            with sub_col1:
                st.metric(
                    label="Simulated Net Energy Output (kWh/month)",
                    value=f"{final_sim_energy:,.2f}"
                )
            with sub_col2:
                st.metric(
                    label="Potential Revenue Gain (THB/month)",
                    value=f"{potential_revenue:,.2f}",
                    help=f"Calculated based on electricity tariff of {electricity_tariff} THB/unit, compared to average expected yield."
                )

            st.markdown("---")

            # --- Display chart and table ---
            st.plotly_chart(create_breakdown_bar_chart(breakdown_data, start_energy), use_container_width=True)
            
            with st.expander("Click to view step-by-step summary table"):
                st.dataframe(steps_df.style.format({'Energy (kWh)': '{:,.2f}'}), use_container_width=True)

        else:
            st.info("⬅️ Please enter the 'Initial Actual Energy' on the left to start the simulation.")