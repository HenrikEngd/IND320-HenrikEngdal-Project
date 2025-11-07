import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import scipy.fftpack as fft
from sklearn.neighbors import LocalOutlierFactor

st.set_page_config(page_title="NEW B: Outliers & Anomalies", layout="wide")

st.title("NEW B: Temperature SPC and Precipitation LOF")

# Expect weather data from Page 2
df = st.session_state.get('weather_data')
selected_area = st.session_state.get('selected_area', 'NO5')
selected_city = st.session_state.get('selected_city', 'Bergen')
weather_year = st.session_state.get('weather_year', '2021')

st.caption(f"Context — Area: {selected_area}, City: {selected_city}, Year: {weather_year}")

if df is None or df.empty:
	st.error("Weather data not loaded. Please visit the Weather Area Selection page first.")
	st.stop()

tab_spc, tab_lof = st.tabs(["Temperature SPC", "Precipitation LOF"])

with tab_spc:
	st.subheader("Temperature Outlier Detection (SPC with DCT High-Pass)")
	col1, col2 = st.columns([1,1])
	with col1:
		dct_cutoff = st.slider("DCT high-frequency coeffs", min_value=50, max_value=600, value=200, step=25,
							   help="Higher retains more high-frequency variation (less smoothing)")
	with col2:
		n_std = st.slider("Robust Std Deviations", min_value=2.0, max_value=6.0, value=3.5, step=0.5,
						  help="Control limit width based on MAD-derived std")

	# Resolve temperature column (allow variants like 'temperature_2m (°C)')
	temp_candidates = [c for c in df.columns if 'temperature_2m' in c]
	temp_col = temp_candidates[0] if temp_candidates else None
	if temp_col is None:
		st.error("No temperature_2m column variant found.")
	else:
		working = df.dropna(subset=[temp_col]).copy()
		temps = working[temp_col].astype(float).values
		coeffs = fft.dct(temps, norm='ortho')
		hp = np.zeros_like(coeffs)
		hp[-dct_cutoff:] = coeffs[-dct_cutoff:]
		satv = fft.idct(hp, norm='ortho')
		satv_mean = float(np.mean(satv))
		mad = float(np.median(np.abs(satv - np.median(satv))))
		robust_std = mad * 1.4826 if mad > 0 else float(np.std(satv))
		upper = satv_mean + n_std * robust_std
		lower = satv_mean - n_std * robust_std
		outlier_mask = (satv - satv_mean > n_std * robust_std) | (satv_mean - satv > n_std * robust_std)
		working['is_outlier'] = outlier_mask

		fig = go.Figure()
		fig.add_trace(go.Scatter(x=working['time'], y=working[temp_col], name='Temperature', mode='lines'))
		if outlier_mask.any():
			fig.add_trace(go.Scatter(x=working.loc[outlier_mask,'time'], y=working.loc[outlier_mask, temp_col],
									 name='Outliers', mode='markers', marker=dict(color='red', size=6)))
		# Translate SATV bounds to approximate y-levels by shifting around the series mean
		y_mean = float(np.mean(temps))
		fig.add_hline(y=y_mean + (upper - satv_mean), line_dash='dash', line_color='green', annotation_text='Upper CL')
		fig.add_hline(y=y_mean + (lower - satv_mean), line_dash='dash', line_color='orange', annotation_text='Lower CL')
		fig.update_layout(title='Temperature with SPC Outliers', xaxis_title='Time', yaxis_title='Temperature (°C)',
						  template='plotly_white', height=560)
		st.plotly_chart(fig, use_container_width=True)

		# Summary
		total = len(working)
		n_out = int(outlier_mask.sum())
		st.info(f"Outliers: {n_out} of {total} ({(n_out/total):.2%})")
		if n_out:
			st.dataframe(working.loc[outlier_mask, ['time', temp_col]].head(25), hide_index=True)

with tab_lof:
	st.subheader("Precipitation Anomaly Detection (Local Outlier Factor)")
	contamination = st.slider("Anomaly proportion (contamination)", min_value=0.001, max_value=0.05, value=0.01, step=0.001,
							  help="Expected share of anomalies")
	# Resolve precipitation column (allow variants like 'precipitation (mm)')
	precip_candidates = [c for c in df.columns if c.startswith('precipitation')]
	precip_col = precip_candidates[0] if precip_candidates else None
	if precip_col is None:
		st.error("No precipitation column variant found.")
	else:
		w2 = df.dropna(subset=[precip_col]).copy()
		X = w2[[precip_col]].astype(float).values
		lof = LocalOutlierFactor(n_neighbors=35, contamination=contamination)
		labels = lof.fit_predict(X)
		w2['is_anomaly'] = labels == -1

		fig2 = go.Figure()
		fig2.add_trace(go.Scatter(x=w2['time'], y=w2[precip_col], name='Precipitation', mode='lines', line=dict(color='#2ca02c')))
		if w2['is_anomaly'].any():
			fig2.add_trace(go.Scatter(x=w2.loc[w2['is_anomaly'],'time'], y=w2.loc[w2['is_anomaly'], precip_col],
									  name='Anomalies', mode='markers', marker=dict(color='purple', size=6)))
		fig2.update_layout(title='Precipitation with LOF Anomalies', xaxis_title='Time', yaxis_title='Precipitation (mm)',
						   template='plotly_white', height=560)
		st.plotly_chart(fig2, use_container_width=True)

		# Summary
		total2 = len(w2)
		n_anom = int(w2['is_anomaly'].sum())
		st.info(f"Anomalies: {n_anom} of {total2} ({(n_anom/total2):.2%})")
		if n_anom:
			st.dataframe(w2.loc[w2['is_anomaly'], ['time', precip_col]].head(25), hide_index=True)

