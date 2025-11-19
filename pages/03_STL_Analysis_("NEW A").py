import streamlit as st
import pandas as pd
import numpy as np
from statsmodels.tsa.seasonal import STL
from scipy.signal import spectrogram
import plotly.graph_objects as go

def spectrogram_plot(
	df,
	area='NO5',
	group=None,
	window_len=256,
	overlap=128
):
	"""
	Create a spectrogram plot for production data.
	Parameters:
		df: DataFrame with columns ['startTime', 'priceArea', 'productionGroup', 'quantityKwh']
		area: electricity price area (default 'NO5')
		group: production group (default: first available in df for area)
		window_len: window length for spectrogram (default 256)
		overlap: window overlap (default 128)
	Returns:
		Plotly Figure
	"""
	df = df[df['startTime'].dt.year == 2021].reset_index(drop=True)
	if group is None:
		groups = df[df['priceArea'] == area]['productionGroup'].dropna().unique()
		if len(groups) == 0:
			raise ValueError(f"No production groups found for area {area}")
		group = sorted(groups)[0]
	ts = df[(df['priceArea'] == area) & (df['productionGroup'] == group)].copy()
	ts = ts.sort_values('startTime')
	y = ts['quantityKwh'].astype(float).values
	if len(y) < window_len:
		raise ValueError("Time series shorter than window length.")
	fs = 1.0
	if overlap >= window_len:
		overlap = int(window_len - 1)
	from scipy.signal import spectrogram
	import numpy as np
	f, t, Sxx = spectrogram(y, fs=fs, nperseg=window_len, noverlap=overlap, scaling='spectrum')
	import plotly.graph_objects as go
	fig = go.Figure(data=go.Heatmap(x=t, y=f, z=10*np.log10(Sxx+1e-12), colorscale='Viridis'))
	fig.update_layout(title=f"Spectrogram: {area} / {group}", xaxis_title='Time (hours offset)', yaxis_title='Freq (cycles/hour)', height=600)
	return fig

def stl_decomposition_plot(
	df,
	area='NO5',
	group=None,
	period=24,
	seasonal=13,
	trend=25,
	robust=True
):
	"""
	Perform STL decomposition on production data and return a Plotly figure.
	Parameters:
		df: DataFrame with columns ['startTime', 'priceArea', 'productionGroup', 'quantityKwh']
		area: electricity price area (default 'NO5')
		group: production group (default: first available in df for area)
		period: period length (default 24)
		seasonal: seasonal smoother (default 13)
		trend: trend smoother (default 25)
		robust: use robust fitting (default True)
	Returns:
		Plotly Figure
	"""
	df = df[df['startTime'].dt.year == 2021].reset_index(drop=True)
	if group is None:
		groups = df[df['priceArea'] == area]['productionGroup'].dropna().unique()
		if len(groups) == 0:
			raise ValueError(f"No production groups found for area {area}")
		group = sorted(groups)[0]
	ts = df[(df['priceArea'] == area) & (df['productionGroup'] == group)].copy()
	ts = ts.sort_values('startTime')
	y = ts['quantityKwh'].astype(float).values
	x = ts['startTime']
	if len(y) < max(2*period, seasonal+trend):
		raise ValueError("Not enough points for STL with selected settings.")
	res = STL(y, period=period, seasonal=seasonal, trend=trend, robust=robust).fit()
	# Create a separate figure for each component
	fig_obs = go.Figure()
	fig_obs.add_trace(go.Scatter(x=x, y=y, name='Observed'))
	fig_obs.update_layout(title=f"Observed: {area} / {group}", template='plotly_white', height=300)

	fig_seasonal = go.Figure()
	fig_seasonal.add_trace(go.Scatter(x=x, y=res.seasonal, name='Seasonal', line=dict(color='green')))
	fig_seasonal.update_layout(title=f"Seasonal: {area} / {group}", template='plotly_white', height=300)

	fig_trend = go.Figure()
	fig_trend.add_trace(go.Scatter(x=x, y=res.trend, name='Trend', line=dict(color='orange')))
	fig_trend.update_layout(title=f"Trend: {area} / {group}", template='plotly_white', height=300)

	fig_resid = go.Figure()
	fig_resid.add_trace(go.Scatter(x=x, y=res.resid, name='Residual', line=dict(color='red')))
	fig_resid.update_layout(title=f"Residual: {area} / {group}", template='plotly_white', height=300)

	return fig_obs, fig_seasonal, fig_trend, fig_resid

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

	try:
		fig_obs, fig_seasonal, fig_trend, fig_resid = stl_decomposition_plot(
			df, area=area, group=group, period=period, seasonal=seasonal, trend=trend, robust=robust)
		st.plotly_chart(fig_obs, use_container_width=True)
		st.plotly_chart(fig_seasonal, use_container_width=True)
		st.plotly_chart(fig_trend, use_container_width=True)
		st.plotly_chart(fig_resid, use_container_width=True)
	except Exception as e:
		st.warning(str(e))

with tab_spec:
	st.subheader("Spectrogram (Production)")
	c1, c2, c3 = st.columns([1,1,1])
	with c1:
		area2 = st.selectbox("Price Area (Spec)", options=price_areas, index=price_areas.index(default_area) if default_area in price_areas else 0)
	with c2:
		group2 = st.selectbox("Production Group (Spec)", options=production_groups, index=0)
	with c3:
		window_len = st.slider("Window length", min_value=128, max_value=2048, value=256, step=64)
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

	try:
		fig2 = spectrogram_plot(df, area=area2, group=group2, window_len=window_len, overlap=overlap)
		st.plotly_chart(fig2, use_container_width=True)
	except Exception as e:
		st.warning(str(e))


