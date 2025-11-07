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

# MongoDB client (certifi-based TLS to avoid SSL issues)
@st.cache_resource
def get_mongo_client():
	db_user = st.secrets["database"]["db_user"]
	secret = st.secrets["database"]["secret"]
	uri = f"mongodb+srv://{db_user}:{secret}@cluster0.xxdbouc.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
	client = MongoClient(uri, server_api=ServerApi('1'), tls=True, tlsCAFile=certifi.where())
	return client

@st.cache_data
def load_production_data():
	client = get_mongo_client()
	database = client['ca2_database']
	collection = database['data']
	records = list(collection.find({}, {'_id': 0}))
	if not records:
		st.error("No production data found in MongoDB. Ensure CA2 ingestion ran.")
		st.stop()
	df = pd.DataFrame(records)
	df['startTime'] = pd.to_datetime(df['startTime'], errors='coerce')
	df = df.dropna(subset=['startTime']).reset_index(drop=True)
	return df

df = load_production_data()
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
	overlap = st.slider("Window overlap", min_value=0, max_value=1024, value=128, step=32)

	ts2 = df[(df['priceArea']==area2) & (df['productionGroup']==group2)].copy()
	ts2 = ts2.sort_values('startTime')
	y2 = ts2['quantityKwh'].astype(float).values
	if len(y2) < window_len:
		st.warning("Time series shorter than window length.")
	else:
		fs = 1.0
		f, t, Sxx = spectrogram(y2, fs=fs, nperseg=window_len, noverlap=overlap, scaling='spectrum')
		fig2 = go.Figure(data=go.Heatmap(x=t, y=f, z=10*np.log10(Sxx+1e-12), colorscale='Viridis'))
		fig2.update_layout(title=f"Spectrogram: {area2} / {group2}", xaxis_title='Time (hours offset)', yaxis_title='Freq (cycles/hour)', height=600)
		st.plotly_chart(fig2, use_container_width=True)

