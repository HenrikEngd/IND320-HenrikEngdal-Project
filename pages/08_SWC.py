import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import requests


st.set_page_config(layout="wide")
st.title("Sliding Window Correlation")

df_weather = st.session_state.get('weather_data')
df_prod = st.session_state.get('ELHUB_Production_data')
df_cons = st.session_state.get('ELHUB_Consumption_data')

# Ensure df_weather has a datetime index for resampling
if df_weather is not None and not isinstance(df_weather.index, pd.DatetimeIndex):
    dt_col = 'time' if 'time' in df_weather.columns else df_weather.columns[0]
    df_weather[dt_col] = pd.to_datetime(df_weather[dt_col])
    df_weather = df_weather.set_index(dt_col)


st.sidebar.header("Settings")
variable_energy_type = st.sidebar.radio(
    "Select energy type", ["Production", "Consumption"]
)

# Add price area selector to sidebar
if variable_energy_type == "Production":
    energy_df = df_prod.copy()
    group_col = "productiongroup"
    price_areas = sorted(energy_df['pricearea'].dropna().unique()) if 'pricearea' in energy_df.columns else []
else:
    energy_df = df_cons.copy()
    group_col = "consumptiongroup"
    price_areas = sorted(energy_df['pricearea'].dropna().unique()) if 'pricearea' in energy_df.columns else []

selected_price_area = st.sidebar.selectbox("Select price area", price_areas, key=f"price_area_{variable_energy_type}") if price_areas else None

groups = sorted(energy_df[group_col].dropna().unique())
selected_group = st.sidebar.selectbox("Select group", groups, key=f"group_select_{variable_energy_type}")


st.header("Sliding Window Correlation Controls")
col1, col2 = st.columns(2)
with col1:
    variable_weather = st.selectbox(
        "Select meteorological variable",
        [
            "temperature_2m",
            "precipitation",
            "wind_speed_10m",
            "wind_direction_10m",
            "wind_gusts_10m",
        ],
        key="weather_var_main"
    )
    lag_days = st.slider("Lag (days, + means weather leads)", -30, 30, 0, key=f"lag_slider_{variable_weather}_{variable_energy_type}")

energy_series = energy_df[energy_df[group_col] == selected_group].copy()
energy_series["quantitykwh"] = pd.to_numeric(
    energy_series["quantitykwh"], errors="coerce"
)
energy_series = energy_series.dropna(subset=["quantitykwh"])

if "starttime" in energy_series.columns:
    energy_series.index = pd.to_datetime(energy_series["starttime"])
else:
    energy_series.index = pd.to_datetime(energy_series.index)

energy_series = (
    energy_series.groupby(energy_series.index)["quantitykwh"].sum()
    .resample("D")
    .sum()
)


# Ensure weather_series has a DatetimeIndex before resampling
if not isinstance(df_weather.index, pd.DatetimeIndex):
    weather_series = df_weather.copy()
    weather_series.index = pd.to_datetime(weather_series.index)
    weather_series = weather_series[variable_weather]
else:
    weather_series = df_weather[variable_weather]

if variable_weather == "precipitation":
    weather_series = weather_series.resample("D").sum()
else:
    weather_series = weather_series.resample("D").mean()


if lag_days != 0:
    weather_series = weather_series.shift(lag_days)


df_merged = pd.concat(
    [energy_series.rename("energy"), weather_series.rename("weather")], axis=1
).dropna()


if df_merged.index.tz is not None:
    df_merged.index = df_merged.index.tz_localize(None)

if df_merged.empty:
    st.warning("No overlapping daily data between energy and weather series.")
    st.stop()

x = df_merged["weather"]
y = df_merged["energy"]


min_win = 5
max_win = min(180, len(df_merged))
default_win = min(60, max_win)
with col2:
    window_days = st.slider(
        "Window length (days)", min_win, max_win, default_win, key="window_days_main"
    )
    date_min = df_merged.index.min().date()
    date_max = df_merged.index.max().date()
    latest_start = (df_merged.index.max() - pd.Timedelta(days=window_days - 1)).date()
    if latest_start < date_min:
        latest_start = date_min
    start_date = st.slider(
        "Move window across time (start date)",
        min_value=date_min,
        max_value=latest_start,
        value=latest_start,
        format="YYYY-MM-DD",
        key="start_date_main"
    )


win_start = pd.to_datetime(start_date)  
win_end = win_start + pd.Timedelta(days=window_days - 1)


swc = y.rolling(window_days, center=True).corr(x)
swc_window = swc.loc[win_start:win_end] 

corr_value = x.corr(y)

fig_energy = go.Figure()
fig_energy.add_trace(
    go.Scatter(
        y=y,
        x=y.index,
        mode="lines",
        name=f"{selected_group}",
        line=dict(color="#92ff83"),
    )
)

fig_energy.add_vrect(
    x0=win_start,
    x1=win_end,
    fillcolor="red",
    opacity=0.15,
    line_width=0,
    layer="below",
)

fig_energy.update_layout(
    height=300,
    xaxis_title="Date",
    yaxis_title="Energy (kWh/day)",
    title=f"Daily energy series: {selected_group}",
)
st.plotly_chart(fig_energy, width='stretch')

fig_weather = go.Figure()
fig_weather.add_trace(
    go.Scatter(
        y=x,
        x=x.index,
        mode="lines",
        name=f"{variable_weather}",
        line=dict(color="#92ff83"),
    )
)

fig_weather.add_vrect(
    x0=win_start,
    x1=win_end,
    fillcolor="red",
    opacity=0.15,
    line_width=0,
    layer="below",
)

fig_weather.update_layout(
    height=300,
    xaxis_title="Date",
    yaxis_title=variable_weather,
    title=f"Daily weather series: {variable_weather}",
)
st.plotly_chart(fig_weather, width='stretch')

fig_swc = go.Figure()
fig_swc.add_trace(
    go.Scatter(
        y=swc,
        x=swc.index,
        mode="lines",
        name="Sliding Window Corr",
        line=dict(color="#92ff83"),
    )
)

fig_swc.add_vrect(
    x0=win_start,
    x1=win_end,
    fillcolor="red",
    opacity=0.10,
    line_width=0,
    layer="below",
)

if not swc_window.dropna().empty:
    fig_swc.add_trace(
        go.Scatter(
            y=swc_window,
            x=swc_window.index,
            mode="lines",
            name="Window SWC",
            line=dict(color="red", width=3),
        )
    )

fig_swc.update_layout(
    height=300,
    xaxis_title="Date",
    yaxis_title="Correlation",
    title=(
        f"Sliding Window Correlation (Daily)"
    ),
)
st.plotly_chart(fig_swc, width='stretch')

st.write(
    f"Overall correlation between **{selected_group}** and "
    f"**{variable_weather}** (daily values): **{corr_value:.3f}**"
)