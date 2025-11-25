import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from sklearn.neighbors import LocalOutlierFactor
from scipy.fftpack import dct, idct
def temp_spc_satv(times, temps, dct_cutoff=200, n_std=3.5, robust=True, scale_mad=True):
    # Defensive: check for empty input
    if len(temps) == 0:
        raise ValueError("Temperature array is empty.")
    t = np.asarray(times)
    x = np.asarray(temps, dtype=float)
    n = len(x)
    # Validate parameters
    if not isinstance(dct_cutoff, int) or dct_cutoff <= 0 or dct_cutoff > n:
        raise ValueError(f"dct_cutoff must be an integer between 1 and the length of the dataset ({n}). Got {dct_cutoff}.")
    if not isinstance(n_std, (int, float)) or n_std <= 0:
        raise ValueError(f"n_std must be a positive number. Got {n_std}.")
    # Interpolate NaNs
    if np.isnan(x).any():
        nans = np.isnan(x)
        not_nans = ~nans
        x[nans] = np.interp(np.where(nans)[0], np.where(not_nans)[0], x[not_nans])

    # DCT low-pass for trend
    X = dct(x, norm="ortho")
    X_lp = np.zeros_like(X)
    X_lp[:dct_cutoff] = X[:dct_cutoff]
    trend = idct(X_lp, norm="ortho")

    # SATV (high-pass)
    satv = x - trend

    # Robust or classical limits in SATV space
    if robust:
        center = np.median(satv)
        mad = np.median(np.abs(satv - center))
        spread = (1.4826 * mad) if scale_mad else mad
    else:
        center = np.mean(satv)
        spread = np.std(satv)

    upper_satv = center + n_std * spread
    lower_satv = center - n_std * spread

    # Map limits to temperature space
    upper_curve = trend + upper_satv
    lower_curve = trend + lower_satv

    # Outliers in SATV space
    is_outlier = (satv > upper_satv) | (satv < lower_satv)

    # Plot
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=t[~is_outlier], y=x[~is_outlier], mode="lines", name="Inliers", line=dict(width=1)))
    fig.add_trace(go.Scatter(x=t[is_outlier], y=x[is_outlier], mode="markers", name="Outliers", marker=dict(size=6, opacity=0.9)))
    fig.add_trace(go.Scatter(x=t, y=upper_curve, mode="lines", name="Upper SPC limit", line=dict(color="blue", dash="dash")))
    fig.add_trace(go.Scatter(x=t, y=lower_curve, mode="lines", name="Lower SPC limit", line=dict(color="blue", dash="dash")))
    fig.update_layout(template="plotly_white", title=dict(text="Temperature with SPC boundaries (SATV)", x=0.5, xanchor="center", font=dict(size=30)), xaxis_title="Date", yaxis_title="Temperature (°C)")
    summary = {
        "n_outliers": int(is_outlier.sum()),
        "n_total": int(n),
        "percent_outliers": round(100 * is_outlier.mean(), 2),
        "satv_center": float(center),
        "satv_spread": float(spread),
        "upper_satv_limit": float(upper_satv),
        "lower_satv_limit": float(lower_satv),
        "dct_cutoff": dct_cutoff,
        "n_std": n_std,
        "robust": robust,
        "scale_mad": scale_mad
    }
    return fig, is_outlier, summary

def precip_lof(times, precip, contamination=0.01, n_neighbors=20):
    arr = np.array(precip, dtype=float).reshape(-1, 1)
    t = np.asarray(times)
    lof = LocalOutlierFactor(n_neighbors=n_neighbors, contamination=contamination)
    labels = lof.fit_predict(arr)
    is_outlier = labels == -1
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=t[~is_outlier], y=arr[~is_outlier, 0], mode="lines", name="Inliers", line=dict(width=1)))
    fig.add_trace(go.Scatter(x=t[is_outlier], y=arr[is_outlier, 0], mode="markers", name="LOF Outliers", marker=dict(color="#d62828", size=6, opacity=0.8)))
    fig.update_layout(template="plotly_white", title=dict(text="Precipitation with LOF Anomalies", x=0.5, xanchor="center", font=dict(size=30)), xaxis_title="Date", yaxis_title="Precipitation (mm)")
    summary = {
        "n_total": len(arr),
        "n_outliers": int(is_outlier.sum()),
        "percent_outliers": round(100 * is_outlier.mean(), 2),
        "contamination": contamination,
        "n_neighbors": n_neighbors
    }
    return fig, is_outlier, summary

st.set_page_config(page_title="Outliers & Anomalies", layout="wide")

st.title("Temperature SPC and Precipitation LOF")

# Expect weather data from Page 2
df = st.session_state.get('weather_data')
selected_area = st.session_state.get('selected_area', 'NO5')
selected_city = st.session_state.get('selected_city', 'Bergen')
weather_year = st.session_state.get('weather_year', '2021')


st.caption(f"Context — Area: {selected_area}, City: {selected_city}, Year: {weather_year}")

if df is None or df.empty:
    st.error("Weather data not loaded. Please visit the Energy Production Analysis page first.")
    st.stop()

tab_spc, tab_lof = st.tabs(["Temperature SPC", "Precipitation LOF"])

with tab_spc:
    st.subheader("Temperature Outlier Detection (SPC with DCT High-Pass)")
    # UI controls for SPC parameters
    dct_cutoff = st.slider("DCT frequency cutoff", min_value=10, max_value=1000, value=200, step=1,
        help="Number of low DCT frequencies to remove (higher = more aggressive outlier detection)")
    n_std = st.slider("SPC n_std (threshold)", min_value=1.0, max_value=5.0, value=3.5, step=0.1,
        help="Number of robust standard deviations for outlier boundary")
    temp_candidates = [c for c in df.columns if c.startswith('temperature')]
    temp_col = temp_candidates[0] if temp_candidates else None
    if temp_col is None:
        st.error("No temperature column variant found.")
    else:
        w1 = df.dropna(subset=[temp_col]).copy()
        times = w1['time']
        temps = w1[temp_col].astype(float).values
        try:
            fig, is_outlier, summary = temp_spc_satv(times, temps, dct_cutoff=dct_cutoff, n_std=n_std)
            st.plotly_chart(fig, use_container_width=True)
            st.info(f"Outliers: {summary['n_outliers']} of {summary['n_total']} ({summary['percent_outliers']:.2f}%)")
        except Exception as e:
            st.warning(f"SPC calculation failed: {e}")
        # Only show summary, not table

with tab_lof:
    st.subheader("Precipitation Anomaly Detection (Local Outlier Factor)")
    contamination = st.slider("Anomaly proportion (contamination)", min_value=0.001, max_value=0.05, value=0.01, step=0.001,
        help="Expected share of anomalies")
    n_neighbors = st.slider("Number of neighbors", min_value=5, max_value=100, value=20, step=1,
        help="Number of neighbors for LOF (higher = more robust, slower)")
    precip_candidates = [c for c in df.columns if c.startswith('precipitation')]
    precip_col = precip_candidates[0] if precip_candidates else None
    if precip_col is None:
        st.error("No precipitation column variant found.")
    else:
        w2 = df.dropna(subset=[precip_col]).copy()
        times2 = w2['time']
        precip = w2[precip_col].astype(float).values
        fig2, is_anomaly, summary2 = precip_lof(times2, precip, contamination=contamination, n_neighbors=n_neighbors)
        st.plotly_chart(fig2, use_container_width=True)
        st.info(f"Anomalies: {summary2['n_outliers']} of {summary2['n_total']} ({summary2['percent_outliers']:.2f}%)")
        # Only show summary, not table



