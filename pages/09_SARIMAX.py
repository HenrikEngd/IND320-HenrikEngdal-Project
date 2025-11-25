

import streamlit as st
import pandas as pd
import numpy as np
import statsmodels.api as sm
import matplotlib.pyplot as plt
import os
import json

# --- Load Data ---


# Use session_state if available, else load and cache
def load_energy_data():
	if 'ELHUB_Production_data' in st.session_state and 'ELHUB_Consumption_data' in st.session_state:
		prod = st.session_state['ELHUB_Production_data']
		cons = st.session_state['ELHUB_Consumption_data']
	else:
		# stop and throw error
		st.error("No energy data available. Please visit the homepage first to load the data.")
		st.stop()
	return prod, cons
	

@st.cache_data
def load_weather_data():
	weather_path = os.path.join('assets', 'open-meteo-subset.csv')
	weather = pd.read_csv(weather_path, parse_dates=['time'])
	return weather

# --- UI ---
st.title('SARIMAX Forecasting: Energy Production & Consumption')

prod, cons = load_energy_data()
weather = load_weather_data()

tab = st.radio('Select data type:', ['Production', 'Consumption'])
df = prod if tab == 'Production' else cons


# Robustly detect datetime column
datetime_candidates = [col for col in df.columns if pd.api.types.is_datetime64_any_dtype(df[col]) or 'date' in col.lower() or 'time' in col.lower()]
if len(datetime_candidates) == 0:
	st.error('No datetime column found in the selected data. Please ensure your data contains a valid datetime column (e.g., "time" or "date").')
	st.stop()
date_col = datetime_candidates[0]
try:
	df[date_col] = pd.to_datetime(df[date_col], errors='raise')
except Exception as e:
	st.error(f'Failed to parse datetime column "{date_col}": {e}')
	st.stop()
df = df.sort_values(date_col)

target_col = 'quantityKwh'
st.info('Target property: quantityKwh')

# Exogenous variables
exog_options = [c for c in df.columns if c not in [date_col, target_col]]
exog_vars = st.multiselect('Add exogenous variables from energy data:', exog_options)

# Timeframe selection (slider for years 2021-2025)
years = [2021, 2022, 2023, 2024, 2025]
min_year, max_year = df[date_col].dt.year.min(), df[date_col].dt.year.max()
slider_min = max(min(years), min_year)
slider_max = min(max(years), max_year)
train_years = st.slider('Select training period (years):', min_value=slider_min, max_value=slider_max, value=(slider_min, slider_max), step=1)
forecast_horizon = st.number_input('Forecast horizon (steps):', min_value=1, max_value=365, value=30)

# Mask for selected years
mask = (df[date_col].dt.year >= train_years[0]) & (df[date_col].dt.year <= train_years[1])
train_df = df.loc[mask].copy()
train_df = train_df.set_index(date_col)


# --- SARIMAX Parameters (fixed, notebook style) ---
st.info('SARIMAX parameters are fixed to: order=(1,1,1), seasonal_order=(1,1,1,12), trend="c" (as in the notebook)')
order = (1, 1, 1)
seasonal_order = (1, 1, 1, 12)
trend = 'c'

# --- Prepare Data ---
y = train_df[target_col]
exog = None
if exog_vars:
	exog_df = pd.DataFrame(index=train_df.index)
	for col in exog_vars:
		exog_df[col] = train_df[col].values
	exog = exog_df

# --- Fit and Forecast ---
if st.button('Run SARIMAX Forecast'):
	try:
		progress_text = 'Training SARIMAX model...'
		progress_bar = st.progress(0, text=progress_text)
		# Use statsmodels.api SARIMAX, fixed params as in notebook
		model = sm.tsa.statespace.SARIMAX(
			y,
			exog=exog,
			trend=trend,
			order=order,
			seasonal_order=seasonal_order,
			enforce_stationarity=False,
			enforce_invertibility=False
		)
		# Simulate progress during fitting (since SARIMAX fit is blocking)
		import threading, time
		fit_result = {}
		def fit_model():
			fit_result['results'] = model.fit(disp=False)
		fit_thread = threading.Thread(target=fit_model)
		fit_thread.start()
		i = 0
		while fit_thread.is_alive():
			i = (i + 1) % 100
			progress_bar.progress(i / 100, text=progress_text)
			time.sleep(0.1)
		fit_thread.join()
		progress_bar.progress(1.0, text='Training complete!')
		results = fit_result['results']
		st.text(results.summary())

		# Prepare exog for forecast horizon
		steps = forecast_horizon
		exog_future = None
		if exog is not None:
			# Repeat last exog row for forecast horizon
			last_exog = exog.iloc[[-1]]
			exog_future = pd.DataFrame(np.repeat(last_exog.values, steps, axis=0), columns=exog.columns)

		forecast = results.get_forecast(steps=steps, exog=exog_future)
		pred = forecast.predicted_mean
		conf_int = forecast.conf_int()

		# Plot (notebook style)
		fig, ax = plt.subplots(figsize=(10, 5))
		y.plot(ax=ax, label='Train')
		# Use the index of y for last date
		last_date = y.index[-1]
		freq = pd.infer_freq(y.index) or 'D'
		idx = pd.date_range(last_date, periods=steps+1, freq=freq)[1:]
		pred.index = idx
		conf_int.index = idx
		pred.plot(ax=ax, label='Forecast')
		ax.fill_between(idx, conf_int.iloc[:, 0], conf_int.iloc[:, 1], color='pink', alpha=0.3, label='Confidence Interval')
		ax.legend()
		ax.set_title(f'SARIMAX Forecast for {target_col}')
		st.pyplot(fig)
		st.success('Forecast complete!')
	except Exception as e:
		st.error(f'Error: {e}')
		st.stop()
