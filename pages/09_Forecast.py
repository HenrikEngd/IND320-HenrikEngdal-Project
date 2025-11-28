
import streamlit as st
import pandas as pd
import numpy as np
import datetime
import statsmodels.api as sm
import plotly.graph_objects as go
from utils.sidebar import price_area_sidebar

st.set_page_config(layout="wide")
st.title("Forecasting with SARIMAX")

df_prod = st.session_state.get('ELHUB_Production_data')
df_cons = st.session_state.get('ELHUB_Consumption_data')
prod_groups = sorted(df_prod['productiongroup'].dropna().unique()) if df_prod is not None and 'productiongroup' in df_prod.columns else []
cons_groups = sorted(df_cons['consumptiongroup'].dropna().unique()) if df_cons is not None and 'consumptiongroup' in df_cons.columns else []

kind = st.sidebar.radio("Select Dataset", ["Production", "Consumption"], key="forecast_dataset_radio")
if kind.lower() == "production":
    selected_area = price_area_sidebar(['NO1','NO2','NO3','NO4','NO5'], default=st.session_state.get('selected_area', 'NO5'), groups=prod_groups, group_key='selected_group')
    selected_group = st.session_state.get('selected_group', prod_groups[0] if prod_groups else None)
    df = df_prod
    group_col = 'productiongroup'
elif kind.lower() == "consumption":
    selected_area = price_area_sidebar(['NO1','NO2','NO3','NO4','NO5'], default=st.session_state.get('selected_area', 'NO5'), groups=cons_groups, group_key='selected_group')
    selected_group = st.session_state.get('selected_group', cons_groups[0] if cons_groups else None)
    df = df_cons
    group_col = 'consumptiongroup'
else:
    st.warning("Please select a dataset.")
    st.stop()

@st.cache_resource(show_spinner=True)
def fit_sarimax(series, order, seasonal_order, exog=None):
    model = sm.tsa.SARIMAX(
        series,
        order=order,
        seasonal_order=seasonal_order,
        exog=exog,
        enforce_stationarity=False,
        enforce_invertibility=False
    )
    return model.fit(disp=False)

def select_series(df, group_col, selected_group, selected_area):
    if df is None or df.empty or group_col not in df.columns:
        return pd.Series(dtype=float), {}
    # Filter by sidebar selections
    filtered = df[(df[group_col] == selected_group) & (df['pricearea'] == selected_area)].copy() if 'pricearea' in df.columns else df[df[group_col] == selected_group].copy()
    if filtered.empty:
        return pd.Series(dtype=float), {"pricearea": selected_area, "group": selected_group}
    # Detect datetime column
    datetime_col = None
    for col in filtered.columns:
        if pd.api.types.is_datetime64_any_dtype(filtered[col]) or 'date' in col.lower() or 'time' in col.lower():
            datetime_col = col
            break
    if datetime_col is None:
        return pd.Series(dtype=float), {"pricearea": selected_area, "group": selected_group}
    filtered.loc[:, datetime_col] = pd.to_datetime(filtered[datetime_col], errors='coerce')
    filtered = filtered.set_index(datetime_col)
    filtered = filtered.sort_index()
    series = (
        filtered.groupby(filtered.index)
        .agg({"quantitykwh": "sum"})
        .sort_index()["quantitykwh"]
    )
    # Daily resampling
    series = series.resample("D").sum().fillna(0)
    try:
        inferred = series.index.inferred_freq
        if inferred:
            series = series.asfreq(inferred)
    except Exception:
        pass
    return series, {"pricearea": selected_area, "group": selected_group}

prod_df = st.session_state.get('ELHUB_Production_data')
cons_df = st.session_state.get('ELHUB_Consumption_data')

# Use the filtered df, group, and area from sidebar
series, meta = select_series(df, group_col, selected_group, selected_area)

if series.empty:
    st.warning("No data available for selected options. Make sure you specify the group in the sidebar")
    st.stop()

st.header("Training Data Period Selection")
min_date = series.index.min().date()
max_date = series.index.max().date()
start_date, end_date = st.date_input(
    "Select training data period",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date
)

if start_date > end_date:
    st.error("Start date must be before end date.")
    st.stop()

# Convert date_input to tz-aware datetime to match series index
start_dt = pd.Timestamp(datetime.datetime.combine(start_date, datetime.time(0, 0)))
end_dt = pd.Timestamp(datetime.datetime.combine(end_date, datetime.time(23, 59, 59)))
series = series.loc[start_dt:end_dt]

fig_series = go.Figure()
fig_series.add_trace(go.Scatter(
    x=series.index, 
    y=series.values, 
    mode="lines", 
    name="Observed",
    line=dict(color="#92ff83") 
))
fig_series.update_layout(title="Observed Series", xaxis_title="Date", yaxis_title="Quantity kWh")
st.plotly_chart(fig_series, width="stretch")




# --- SARIMAX parameters with session state persistence ---
st.subheader("SARIMAX parameters")
def get_param(name, default):
    return st.session_state.get(name, default)

col1, col2, col3, col4 = st.columns(4)
with col1:
    p = st.number_input("AR term (p)", 0, 5, get_param('sarimax_p', 3), key='sarimax_p')
    P = st.number_input("Seasonal AR term (P)", 0, 2, get_param('sarimax_P', 1), key='sarimax_P')
with col2:
    d = st.number_input("Differencing term (d)", 0, 2, get_param('sarimax_d', 1), key='sarimax_d')
    D = st.number_input("Seasonal differencing (D)", 0, 1, get_param('sarimax_D', 1), key='sarimax_D')
with col3:
    q = st.number_input("MA term (q)", 0, 5, get_param('sarimax_q', 1), key='sarimax_q')
    Q = st.number_input("Seasonal MA term (Q)", 0, 2, get_param('sarimax_Q', 0), key='sarimax_Q')
with col4:
    m = st.number_input("Seasonal period (m)", 1, 168, get_param('sarimax_m', 24), key='sarimax_m')
    steps = st.number_input("Forecast horizon (steps)", 1, 168, get_param('sarimax_steps', 48), key='sarimax_steps')

with st.sidebar:
    forecast_button = st.button("Run Forecast")

# --- Only run SARIMAX and update plot when button is pressed ---
if forecast_button:
    with st.spinner("Fitting SARIMAX model..."):
        model_fit = fit_sarimax(series, order=(p, d, q), seasonal_order=(P, D, Q, m))
        forecast_res = model_fit.get_forecast(steps=steps)
        forecast_mean = forecast_res.predicted_mean
        conf_int = forecast_res.conf_int()
        # Store results in session_state
        st.session_state['sarimax_forecast'] = {
            'forecast_mean': forecast_mean,
            'conf_int': conf_int,
            'params': (p, d, q, P, D, Q, m, steps),
            'series': series
        }


if forecast_button:
    with st.spinner("Fitting SARIMAX model..."):
        model_fit = fit_sarimax(series, order=(p, d, q), seasonal_order=(P, D, Q, m))
        forecast_res = model_fit.get_forecast(steps=steps)
        forecast_mean = forecast_res.predicted_mean
        conf_int = forecast_res.conf_int()

    # Plot forecast with Plotly
    fig_forecast = go.Figure()
    fig_forecast.add_trace(go.Scatter(
        x=series.index, y=series.values, mode="lines", name="Observed",
        line=dict(color="#3400df")  
    ))
    fig_forecast.add_trace(go.Scatter(x=forecast_mean.index, y=forecast_mean.values, mode="lines", name="Forecast", line=dict(color="red")))
    fig_forecast.add_trace(go.Scatter(
        x=conf_int.index.tolist() + conf_int.index[::-1].tolist(),
        y=conf_int.iloc[:,0].tolist() + conf_int.iloc[:,1][::-1].tolist(),
        fill="toself", fillcolor="rgba(255, 183, 77, 0.3)", 
        line=dict(color="rgba(255,183,77,0)"), showlegend=True, name="Confidence Interval"
    ))
    fig_forecast.update_layout(title="SARIMAX Forecast", xaxis_title="Date", yaxis_title="Quantity kWh")
    st.plotly_chart(fig_forecast, width="stretch")
