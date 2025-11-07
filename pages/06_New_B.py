import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import scipy.fftpack as fft
from sklearn.neighbors import LocalOutlierFactor

st.set_page_config(page_title="Outliers & Anomalies", layout="wide")

st.title("New B: Temperature SPC & Precipitation LOF")

df = st.session_state.get('weather_data')
if df is None:
    st.error("Weather data not loaded. Please visit the Weather Area Selection page first.")
    st.stop()

spc_tab, lof_tab = st.tabs(["Temperature SPC", "Precipitation LOF"])

with spc_tab:
    st.subheader("Temperature Outlier Detection (SPC + DCT High-Pass)")
    dct_cutoff = st.slider("DCT high-frequency coefficient count", min_value=50, max_value=500, value=200, step=25)
    n_std = st.slider("Robust Std Deviation Multipliers", min_value=2.0, max_value=6.0, value=3.5, step=0.5)

    temp_col = 'temperature_2m'
    working = df.dropna(subset=[temp_col]).copy()
    temps = working[temp_col].values
    coeffs = fft.dct(temps, norm='ortho')
    hp = np.zeros_like(coeffs)
    hp[-dct_cutoff:] = coeffs[-dct_cutoff:]
    satv = fft.idct(hp, norm='ortho')
    satv_mean = np.mean(satv)
    mad = np.median(np.abs(satv - np.median(satv)))
    robust_std = mad * 1.4826 if mad > 0 else np.std(satv)
    upper = satv_mean + n_std * robust_std
    lower = satv_mean - n_std * robust_std
    outlier_mask = (satv - satv_mean > n_std * robust_std) | (satv_mean - satv > n_std * robust_std)

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=working['time'], y=working[temp_col], name='Temperature', mode='lines'))
    if outlier_mask.any():
        fig.add_trace(go.Scatter(x=working.loc[outlier_mask,'time'], y=working.loc[outlier_mask,temp_col],
                                 name='Outliers', mode='markers', marker=dict(color='red', size=6)))
    fig.add_hline(y=np.mean(temps) + (upper - satv_mean), line_dash='dash', line_color='green', annotation_text='Upper CL')
    fig.add_hline(y=np.mean(temps) + (lower - satv_mean), line_dash='dash', line_color='orange', annotation_text='Lower CL')
    fig.update_layout(title='Temperature with SPC Outliers', xaxis_title='Time', yaxis_title='Temperature (°C)', template='plotly_white', height=550)
    st.plotly_chart(fig, use_container_width=True)

with lof_tab:
    st.subheader("Precipitation Anomaly Detection (Local Outlier Factor)")
    contamination = st.slider("Expected anomaly proportion", min_value=0.001, max_value=0.05, value=0.01, step=0.001)
    precip_col = 'precipitation'
    w2 = df.dropna(subset=[precip_col]).copy()
    X = w2[[precip_col]].values
    lof = LocalOutlierFactor(n_neighbors=35, contamination=contamination)
    labels = lof.fit_predict(X)
    w2['is_anomaly'] = labels == -1

    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(x=w2['time'], y=w2[precip_col], name='Precipitation', mode='lines', line=dict(color='#2ca02c')))
    if w2['is_anomaly'].any():
        fig2.add_trace(go.Scatter(x=w2.loc[w2['is_anomaly'],'time'], y=w2.loc[w2['is_anomaly'], precip_col],
                                  name='Anomalies', mode='markers', marker=dict(color='purple', size=6)))
    fig2.update_layout(title='Precipitation with LOF Anomalies', xaxis_title='Time', yaxis_title='Precipitation (mm)', template='plotly_white', height=550)
    st.plotly_chart(fig2, use_container_width=True)
