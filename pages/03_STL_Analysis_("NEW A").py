import streamlit as st
import pandas as pd
import numpy as np
from statsmodels.tsa.seasonal import STL
from scipy.signal import spectrogram
import plotly.graph_objects as go
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
import certifi

st.set_page_config(page_title="NEW A: STL & Spectrogram", layout="wide")

st.title("NEW A: STL Decomposition and Spectrogram")

# Get area context from Page 2 if available
default_area = st.session_state.get('selected_area', 'NO5')

df = st.session_state.get('ELHUB_Production_data', None)
if df is None:
    st.error("No production data available. Please visit the homepage first to load the data.")
    st.stop()

df = df[df['startTime'].dt.year == 2021].reset_index(drop=True)
price_areas = sorted(df['priceArea'].dropna().unique())
production_groups = sorted(df['productionGroup'].dropna().unique())

tab_stl, tab_spec = st.tabs(["STL Decomposition", "Spectrogram"])

with tab_stl:
	st.subheader("Seasonal-Trend Decomposition (STL)")
	c1, c2, c3, c4, c5 = st.columns([1,1,1,1,1])
	with c1:
		area = st.selectbox("Price Area", options=price_areas, index=price_areas.index(default_area) if default_area in price_areas else 0)
	with c2:
		group = st.selectbox("Production Group", options=production_groups, index=0)
	with c3:
		period = st.number_input("Period (hours)", min_value=24, max_value=24*14, value=24, step=1)
	with c4:
		seasonal = st.slider("Seasonal smoother", min_value=7, max_value=61, value=13, step=2)
	with c5:
		trend = st.slider("Trend smoother", min_value=13, max_value=121, value=25, step=2)
	robust = st.checkbox("Robust", value=True)

	ts = df[(df['priceArea']==area) & (df['productionGroup']==group)].copy()
	ts = ts.sort_values('startTime')
	y = ts['quantityKwh'].astype(float).values
	x = ts['startTime']
	if len(y) < max(2*period, seasonal+trend):
		st.warning("Not enough points for STL with selected settings.")
	else:
		res = STL(y, period=period, seasonal=seasonal, trend=trend, robust=robust).fit()
		fig = go.Figure()
		fig.add_trace(go.Scatter(x=x, y=y, name='Observed'))
		fig.add_trace(go.Scatter(x=x, y=res.seasonal, name='Seasonal'))
		fig.add_trace(go.Scatter(x=x, y=res.trend, name='Trend'))
		fig.add_trace(go.Scatter(x=x, y=res.resid, name='Residual'))
		fig.update_layout(title=f"STL: {area} / {group}", template='plotly_white', height=600)
		st.plotly_chart(fig, use_container_width=True)

with tab_spec:
	st.subheader("Spectrogram (Production)")
	c1, c2, c3 = st.columns([1,1,1])
	with c1:
		area2 = st.selectbox("Price Area (Spec)", options=price_areas, index=price_areas.index(default_area) if default_area in price_areas else 0)
	with c2:
		group2 = st.selectbox("Production Group (Spec)", options=production_groups, index=0)
	with c3:
		window_len = st.slider("Window length", min_value=128, max_value=2048, value=256, step=64)
	# Overlap must be strictly less than window length; cap slider accordingly
	max_overlap = int(max(0, window_len - 1))
	default_overlap = int(min(128, max_overlap))
	overlap = st.slider(
		"Window overlap",
		min_value=0,
		max_value=max_overlap,
		value=default_overlap,
		step=32,
		help="Overlap must be less than window length"
	)

	ts2 = df[(df['priceArea']==area2) & (df['productionGroup']==group2)].copy()
	ts2 = ts2.sort_values('startTime')
	y2 = ts2['quantityKwh'].astype(float).values
	if len(y2) < window_len:
		st.warning("Time series shorter than window length.")
	else:
		fs = 1.0
		# Guard against invalid overlap due to prior UI state
		if overlap >= window_len:
			st.warning("Overlap must be less than window length. Adjusted overlap to window_len-1.")
			overlap = int(window_len - 1)
		f, t, Sxx = spectrogram(y2, fs=fs, nperseg=window_len, noverlap=overlap, scaling='spectrum')
		fig2 = go.Figure(data=go.Heatmap(x=t, y=f, z=10*np.log10(Sxx+1e-12), colorscale='Viridis'))
		fig2.update_layout(title=f"Spectrogram: {area2} / {group2}", xaxis_title='Time (hours offset)', yaxis_title='Freq (cycles/hour)', height=600)
		st.plotly_chart(fig2, use_container_width=True)

