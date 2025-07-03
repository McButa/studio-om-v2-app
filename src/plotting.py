# src/plotting.py (Final Corrected Version with datetime import)

import plotly.graph_objects as go
import pandas as pd
from datetime import datetime # <-- FIXED: Added this import

def plot_sensor_health(analysis_df, threshold):
    """Plots the Sensor Sanity Check graph."""
    df_plot = analysis_df.copy()
    df_plot['DateStr'] = df_plot['Date'].dt.strftime('%Y-%b')
    df_plot['upper_bound'] = df_plot['pvsyst_ghi_kwh_m2'] * (1 + threshold / 100)
    df_plot['lower_bound'] = df_plot['pvsyst_ghi_kwh_m2'] * (1 - threshold / 100)

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df_plot['DateStr'], y=df_plot['upper_bound'], fill=None, mode='lines', line=dict(color='rgba(0,176,246,0.2)'), name=f'Upper Bound (+{threshold}%)'))
    fig.add_trace(go.Scatter(x=df_plot['DateStr'], y=df_plot['lower_bound'], fill='tonexty', mode='lines', line=dict(color='rgba(0,176,246,0.2)'), name=f'Lower Bound (-{threshold}%)'))
    fig.add_trace(go.Scatter(x=df_plot['DateStr'], y=df_plot['pvsyst_ghi_kwh_m2'], mode='lines', line=dict(dash='dash', color='grey'), name='GHI (PVsyst Baseline)'))
    fig.add_trace(go.Scatter(x=df_plot['DateStr'], y=df_plot['actual_ghi_kwh_m2'], mode='lines+markers', line=dict(color='orange'), name='Actual Measured GHI'))
    
    fig.update_layout(
        title_text="<b>1. Sensor Sanity Check</b><br><sup>Reliability of Solar Irradiance Data</sup>",
        xaxis_title='Month', yaxis_title='Irradiance (kWh/m²)', hovermode='x unified', legend_title='Legend'
    )
    return fig

def plot_weather_analysis(analysis_df):
    """Plots the Weather Analysis graph (Irradiance Index)."""
    df_plot = analysis_df.copy()
    df_plot['DateStr'] = df_plot['Date'].dt.strftime('%Y-%b')
    df_plot['color'] = df_plot['irr_index_%'].apply(lambda x: 'green' if x >= 100 else 'salmon')
    fig = go.Figure(go.Bar(x=df_plot['DateStr'], y=df_plot['irr_index_%'], marker_color=df_plot['color'], name='Irradiance Index'))
    fig.add_hline(y=100, line_dash="dash", line_color="grey", annotation_text="PVsyst Baseline", 
                  annotation_position="bottom right", annotation_font_size=10)
    
    fig.update_layout(
        title_text="<b>2. Weather Analysis</b><br><sup>Irradiance Index Compared to Forecast (PVsyst)</sup>",
        xaxis_title='Month', yaxis_title='Irradiance Index (%)', yaxis_ticksuffix='%', hovermode='x unified'
    )
    return fig

def plot_system_performance(analysis_df):
    """Plots the main System Performance graph (PI vs. PR)."""
    df_plot = analysis_df.copy()
    df_plot['DateStr'] = df_plot['Date'].dt.strftime('%Y-%b')
    fig = go.Figure()
    fig.add_trace(go.Bar(x=df_plot['DateStr'], y=df_plot['pi_%'], name='Performance Index (PI)', marker_color='royalblue'))
    fig.add_trace(go.Scatter(x=df_plot['DateStr'], y=df_plot['actual_pr_percent'], mode='lines+markers', name='Actual PR', line=dict(color='darkorange')))
    fig.add_hline(y=100, line_dash="dash", line_color="grey", annotation_text="Target PI", 
                  annotation_position="top right", annotation_font_size=10)
    
    fig.update_layout(
        title_text="<b>3. System Performance</b><br><sup>Monthly Performance Index (PI) and Performance Ratio (PR)</sup>",
        xaxis_title='Month', yaxis_title='Performance (%)', yaxis_ticksuffix='%', hovermode='x unified', 
        legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01)
    )
    return fig

def plot_yield_analysis(analysis_df):
    """Plots the energy yield analysis, showing the effect of losses."""
    df_plot = analysis_df.copy()
    df_plot['DateStr'] = df_plot['Date'].dt.strftime('%Y-%b')
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df_plot['DateStr'], y=df_plot['expected_yield_kwh'], mode='lines', line=dict(dash='dash', color='grey'), name='Expected Yield (Weather Adjusted)'))
    fig.add_trace(go.Scatter(x=df_plot['DateStr'], y=df_plot['actual_yield_kwh'], mode='lines+markers', line=dict(color='royalblue'), name='Actual Yield', fill='tonexty', fillcolor='rgba(255, 87, 51, 0.1)'))
    
    fig.update_layout(
        title_text="<b>4. Energy Yield Analysis</b><br><sup>Actual Energy Production vs. Expected Potential</sup>",
        xaxis_title='Month', yaxis_title='Energy (kWh)', hovermode='x unified', legend_title='Legend',
        annotations=[dict(x=0.5, y=-0.25, xref='paper', yref='paper', text='<i>The shaded area represents total system losses (temperature, soiling, equipment issues, etc.)</i>', showarrow=False, align='center', font=dict(size=10))]
    )
    return fig

def plot_yearly_yield_vs_guarantee(guarantee_df): 
    """Plots yearly actual yield vs guarantee vs expected using Plotly."""
    fig = go.Figure()
    fig.add_trace(go.Bar(x=guarantee_df['Year'], y=guarantee_df['Actual Yearly Yield (MWh)'], name='Actual Yearly Yield', marker_color='royalblue'))
    fig.add_trace(go.Scatter(x=guarantee_df['Year'], y=guarantee_df['Energy Guarantee (MWh)'], mode='lines', name='Annual Energy Guarantee', line=dict(color='red', dash='dash', width=3)))
    fig.add_trace(go.Scatter(x=guarantee_df['Year'], y=guarantee_df['Expected Yearly Yield (MWh)'], mode='lines+markers', name='Expected Yearly Yield (Ideal)', line=dict(color='green', dash='dot', width=2)))
    
    fig.update_layout(
        title_text="<b>5. Yearly Yield vs. Guarantee</b><br><sup>Comparison of Annual Production against Contractual Guarantee and Forecasted Values</sup>",
        xaxis_title='Year', yaxis_title='Energy Yield (MWh)', legend_title='Legend', 
        xaxis=dict(tickmode='linear', dtick=1), barmode='group', hovermode='x unified'
    )
    return fig

def plot_loss_breakdown(breakdown_data_dict, title_text): 
    """
    Creates a waterfall chart showing the energy loss breakdown.
    """
    ideal = breakdown_data_dict.get('ideal', 0)
    temp_loss = breakdown_data_dict.get('temp_loss', 0) 
    other_loss = breakdown_data_dict.get('other_loss', 0) 
    actual = breakdown_data_dict.get('actual', 0)
    
    if ideal == 0 and actual == 0:
        return go.Figure().update_layout(title_text="<b>No Data for Energy Loss Breakdown</b>", 
                                         annotations=[dict(text="Please upload data and run the analysis.", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False, font=dict(size=14))])

    names = ["<b>Reference Yield</b><br><sup>(Weather Adjusted)</sup>", "<b>Temperature Loss</b>", "<b>Other Losses</b><br><sup>(Soiling, System, etc.)</sup>", "<b>Actual Yield</b>"]
    y_values = [ideal, temp_loss, -other_loss, actual]
    texts = [f"<b>{ideal:,.1f}</b>", f"{temp_loss:,.1f}", f"{-other_loss:,.1f}", f"<b>{actual:,.1f}</b>"]

    fig = go.Figure(go.Waterfall(
        name="Energy Breakdown", orientation="v", measure=["absolute", "relative", "relative", "total"], 
        x=names, text=texts, textposition="outside", y=y_values, 
        connector={"line": {"color": "rgb(63, 63, 63)"}},
        totals={"marker": {"color": "rgba(4, 90, 168, 1.0)", "line": {"color": "grey", "width": 1}}}, 
        decreasing={"marker": {"color": "rgba(205, 36, 36, 1.0)"}}, 
        increasing={"marker": {"color": "rgba(0, 176, 246, 1.0)"}} 
    ))
    
    fig.update_layout(
        title_text=title_text, yaxis_title="Energy (MWh)", showlegend=False, font=dict(family="Arial, sans-serif", size=12),
        xaxis=dict(tickfont=dict(size=11)), yaxis=dict(gridcolor='lightgrey'), plot_bgcolor='white', 
        margin=dict(t=80, b=40, l=40, r=40)
    )
    return fig

def plot_long_term_forecast(forecast_df):
    """Plots the long-term forecast of energy yield against the degraded guarantee."""
    if forecast_df.empty:
        return go.Figure().update_layout(title_text="<b>No Long-term Forecast Data</b>", 
                                         annotations=[dict(text="Please check analysis data and forecast parameters on the Home page.", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False, font=dict(size=14))])
    
    hist_df = forecast_df[forecast_df['Type'] == 'Historical']
    fcst_df = forecast_df[forecast_df['Type'] == 'Forecast']
    
    fig = go.Figure()
    fig.add_trace(go.Bar(x=hist_df['Year'], y=hist_df['Forecasted Yield (MWh)'], name='Historical Actual Yield', marker_color='royalblue'))
    fig.add_trace(go.Bar(x=fcst_df['Year'], y=fcst_df['Forecasted Yield (MWh)'], name='Forecasted Yield (Based on Actual Degradation)', marker_color='lightblue'))
    fig.add_trace(go.Scatter(x=forecast_df['Year'], y=forecast_df['Degraded Guarantee (MWh)'], mode='lines+markers', name='Degraded Annual Guarantee', line=dict(color='red', dash='dash', width=3)))
    
    fig.update_layout(
        title_text="<b>🔮 Long-term Yield Forecast vs. Guarantee</b><br><sup>Assessing Future Yield Trends and Contractual Guarantee Comparison</sup>",
        xaxis_title='Year', yaxis_title='Energy Yield (MWh)', legend_title='Legend', 
        xaxis=dict(tickmode='linear', dtick=1), barmode='group', hovermode='x unified'
    )
    return fig

def plot_short_term_forecast(analysis_df, short_term_forecast_result):
    """
    Plots the historical PI and the forecasted PI for the next month
    with a more professional and informative layout. (Corrected X-axis logic)
    """
    if not short_term_forecast_result or analysis_df.empty:
        return go.Figure().update_layout(title_text="<b>Not enough data for Short-term Forecast</b>")

    hist_df = analysis_df.tail(12).copy()
    
    fc_date = datetime.strptime(short_term_forecast_result['date'], '%B %Y')
    fc_pi = short_term_forecast_result['pi']
    fc_pi_lower = short_term_forecast_result['pi_lower']
    fc_pi_upper = short_term_forecast_result['pi_upper']
    
    historical_avg_pi = hist_df['pi_%'].mean()

    fig = go.Figure()

    fig.add_hline(
        y=100, line_dash="dash", line_color="green",
        annotation_text="Target PI (100%)", 
        annotation_position="bottom right",
        annotation_font=dict(size=10, color="green")
    )
    fig.add_hline(
        y=historical_avg_pi, 
        line_dash="dot", 
        line_color="rgba(128, 128, 128, 0.7)",
        line_width=1.5,
        annotation_text=f"Historical Avg ({historical_avg_pi:.1f}%)", 
        annotation_position="top left",
        annotation_font=dict(size=10, color="grey")
    )

    fig.add_trace(go.Scatter(
        x=[hist_df['Date'].iloc[-1], fc_date],
        y=[fc_pi_upper, fc_pi_upper],
        fill=None, mode='lines', line=dict(color='rgba(255, 159, 64, 0)'),
        showlegend=False
    ))
    fig.add_trace(go.Scatter(
        x=[hist_df['Date'].iloc[-1], fc_date],
        y=[fc_pi_lower, fc_pi_lower],
        fill='tonexty',
        mode='lines', line=dict(color='rgba(255, 159, 64, 0)'),
        fillcolor='rgba(255, 159, 64, 0.2)',
        name='Forecast Uncertainty'
    ))

    fig.add_trace(go.Scatter(
        x=hist_df['Date'],
        y=hist_df['pi_%'],
        mode='lines+markers',
        name='Historical PI',
        line=dict(color='royalblue', width=2),
        marker=dict(size=6)
    ))

    fig.add_trace(go.Scatter(
        x=[fc_date],
        y=[fc_pi],
        mode='markers',
        name=f'Forecasted PI ({fc_pi:.1f}%)',
        marker=dict(color='darkred', size=14, symbol='star',
                    line=dict(width=1, color='white'))
    ))

    fig.update_layout(
        title=dict(
            text=f"<b>Short-term Forecast: Performance Index (PI) for {short_term_forecast_result['date']}</b>",
            font=dict(size=20),
            x=0.5,
            xanchor='center'
        ),
        xaxis_title=None,
        yaxis_title="Performance Index (%)",
        yaxis_ticksuffix='%',
        yaxis_range=[min(hist_df['pi_%'].min(), fc_pi_lower) - 10, max(hist_df['pi_%'].max(), 105)],
        hovermode='x unified',
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        plot_bgcolor='white',
        margin=dict(l=60, r=40, t=80, b=40)
    )
    fig.update_xaxes(showgrid=False, tickformat='%Y-%b')
    fig.update_yaxes(gridwidth=1, gridcolor='lightgrey')

    return fig