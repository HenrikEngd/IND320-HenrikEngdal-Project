import streamlit as st
import pandas as pd
import requests
from datetime import datetime

st.set_page_config(page_title="Weather Data Table", layout="wide")

st.title("Weather Area Selection & Data Overview (2021)")
st.markdown("---")

# Mapping of price areas to representative city coordinates
PRICE_AREAS = pd.DataFrame({
    'priceArea': ['NO1', 'NO2', 'NO3', 'NO4', 'NO5'],
    'city': ['Oslo', 'Kristiansand', 'Trondheim', 'Tromsø', 'Bergen'],
    'latitude': [59.9139, 58.1467, 63.4305, 69.6492, 60.3913],
    'longitude': [10.7522, 7.9956, 10.3951, 18.9553, 5.3221]
})

ARCHIVE_API = "https://archive-api.open-meteo.com/v1/era5"
HOURLY = [
    "temperature_2m", "precipitation", "wind_speed_10m", "wind_gusts_10m", "wind_direction_10m"
]

def fetch_open_meteo(lat: float, lon: float, year: int, hourly: list = None, tz: str = "UTC") -> pd.DataFrame:
    if hourly is None:
        hourly = HOURLY
    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": f"{year}-01-01",
        "end_date": f"{year}-12-31",
        "hourly": ",".join(hourly),
        "timezone": tz,
    }
    r = requests.get(ARCHIVE_API, params=params, timeout=60)
    r.raise_for_status()
    data = r.json()
    times = pd.to_datetime(data["hourly"]["time"])  # parse ISO timestamps
    df = pd.DataFrame({"time": times})
    for var in hourly:
        if var in data["hourly"]:
            df[var] = data["hourly"][var]
    return df

# Area selector (persist selection)
left, right = st.columns([2, 1])
with left:
    selected_area = st.radio("Select Price Area:", options=list(PRICE_AREAS['priceArea']), horizontal=True)
with right:
    year = 2021
    st.metric("Year", year)

# Resolve coordinates
row = PRICE_AREAS[PRICE_AREAS['priceArea'] == selected_area].iloc[0]
lat, lon = float(row['latitude']), float(row['longitude'])

# Fetch and cache in session state
if (
    st.session_state.get('selected_area') != selected_area or
    st.session_state.get('weather_year') != year or
    st.session_state.get('weather_data') is None
):
    with st.spinner(f"Downloading ERA5 weather for {row['city']} ({selected_area}) in {year}..."):
        df = fetch_open_meteo(lat, lon, year)
        st.session_state['weather_data'] = df
        st.session_state['selected_area'] = selected_area
        st.session_state['selected_city'] = row['city']
        st.session_state['weather_year'] = year

# Get data
df = st.session_state.get('weather_data')

if df is None or df.empty:
    st.error("Weather data not available. Try selecting area again.")
    st.stop()

st.success(f"Loaded {len(df):,} hourly records for {st.session_state['selected_city']} ({selected_area}) - {year}")

# Table summary like original Page 4
# Filter data for the first month
first_month_df = df[df['time'].dt.strftime('%Y-%m') == f'{year}-01']

# Get numeric columns only (exclude non-numeric like 'time')
numeric_columns = list(df.select_dtypes(include='number').columns)

# Create table data for display
table_data = []
for column in numeric_columns:
    mdf = pd.to_numeric(first_month_df[column], errors='coerce')
    row_data = {
        'Parameter': column,
        'Mean': f"{mdf.mean():.2f}",
        'Min': f"{mdf.min():.2f}",
        'Max': f"{mdf.max():.2f}",
        'Std Dev': f"{mdf.std():.2f}",
        'First Month Trend': first_month_df[column].values
    }
    table_data.append(row_data)

table_df = pd.DataFrame(table_data)

st.subheader("Weather Parameters - January Summary")
st.markdown("Each row shows statistics and trend for January")

st.dataframe(
    table_df,
    column_config={
        "Parameter": st.column_config.TextColumn("Weather Parameter", width="medium"),
        "Mean": st.column_config.NumberColumn("Mean"),
        "Min": st.column_config.NumberColumn("Minimum"),
        "Max": st.column_config.NumberColumn("Maximum"),
        "Std Dev": st.column_config.NumberColumn("Standard Deviation"),
        "First Month Trend": st.column_config.LineChartColumn("Trend", width="large"),
    },
    width='stretch',
    hide_index=True
)