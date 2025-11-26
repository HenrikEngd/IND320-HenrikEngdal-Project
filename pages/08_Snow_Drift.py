
# Calculate snow drift per year in a selected range of years
# Let user choose the year range
# Use the coordinates chosen on the Price Area Map page. Dont calculate/plot if no selection made.
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from math import pow
from utils.sidebar import price_area_sidebar

st.title("Snow Drift Analysis")

# Ensure sidebar selector is present for global price-area selection
# Snow drift does not have production groups, but if production groups are available in session, expose them
prod_df = st.session_state.get('ELHUB_Production_data')
prod_groups = None
if prod_df is not None and 'productionGroup' in prod_df.columns:
    prod_groups = sorted(prod_df['productionGroup'].dropna().unique())
_ = price_area_sidebar(['NO1','NO2','NO3','NO4','NO5'], default=st.session_state.get('selected_area', 'NO5'), groups=prod_groups, group_key='selected_group')

# Let user choose year range (years correspond to the season start year, e.g. 2021 -> season 1 Jul 2021 - 30 Jun 2022)
start_year, end_year = st.slider("Select Year Range", 2020, 2024, (2021, 2024))

# Ensure coordinates are selected on Price Area Map page
if "selected_coordinates" not in st.session_state:
    st.warning("Please select coordinates on the Price Area Map page first.")
    st.stop()

lat, lon = st.session_state.selected_coordinates

CSV_PATH = "assets/open-meteo-subset.csv"

def normalize_weather_df(raw_df: pd.DataFrame) -> pd.DataFrame:
    """Normalize an incoming weather dataframe (either from session or CSV) to expected column names.

    Expected normalized columns:
      - time (datetime)
      - temperature_2m (°C)
      - precipitation (mm)
      - wind_speed_10m (m/s)
      - wind_direction_10m (°)
    """
    df2 = raw_df.copy()
    # Lowercase and strip columns for loose matching
    col_map = {c: c for c in df2.columns}
    lc = {c.lower().strip(): c for c in df2.columns}

    def find_col(possible_names):
        for name in possible_names:
            if name.lower() in lc:
                return lc[name.lower()]
        return None

    # time / date
    time_col = find_col(['time', 'date', 'datetime'])
    if time_col is None:
        raise KeyError('No time column found in weather data')
    df2['time'] = pd.to_datetime(df2[time_col])

    # temperature
    tcol = find_col(['temperature_2m (°c)', 'temperature_2m', 'temperature', 'temp'])
    if tcol:
        df2['temperature_2m (°C)'] = df2[tcol]

    # precipitation
    pcol = find_col(['precipitation (mm)', 'precipitation', 'precip'])
    if pcol:
        df2['precipitation (mm)'] = df2[pcol]
    else:
        df2['precipitation (mm)'] = 0.0

    # wind speed
    wcol = find_col(['wind_speed_10m (m/s)', 'wind_speed_10m', 'wind_speed', 'windspeed'])
    if wcol:
        df2['wind_speed_10m (m/s)'] = df2[wcol]
    else:
        df2['wind_speed_10m (m/s)'] = 0.0

    # wind direction
    wdcol = find_col(['wind_direction_10m (°)', 'wind_direction_10m', 'wind_direction', 'winddir', 'wind_deg'])
    if wdcol:
        df2['wind_direction_10m (°)'] = df2[wdcol]
    else:
        # If missing, fill with zeros and warn later
        df2['wind_direction_10m (°)'] = 0.0

    return df2

# Prefer cached session weather_data if present
raw_df = st.session_state.get('weather_data', None)
used_source = 'session'
if raw_df is None:
    try:
        raw_df = pd.read_csv(CSV_PATH)
        used_source = 'csv'
    except Exception as e:
        st.error(f"Unable to load weather data from session or CSV: {e}")
        st.stop()

try:
    df = normalize_weather_df(raw_df)
except KeyError as e:
    st.error(f"Weather data missing required column: {e}")
    st.stop()

st.write(f"Using weather data from: `{used_source}` — rows: {len(df):,}")

# We expect these columns (based on assets/open-meteo-subset.csv)
expected_cols = ['time', 'temperature_2m (°C)', 'precipitation (mm)', 'wind_speed_10m (m/s)', 'wind_direction_10m (°)']
missing = [c for c in expected_cols if c not in df.columns]
if missing:
    st.error(f"Required columns missing from data: {missing}")
    st.stop()

# Helper functions adapted from Snow_drift.py
def sector_index(direction):
    return int(((direction + 11.25) % 360) // 22.5)

def compute_Qupot(hourly_wind_speeds, dt=3600):
    return sum((u ** 3.8) * dt for u in hourly_wind_speeds) / 233847

def compute_sector_transport(hourly_wind_speeds, hourly_wind_dirs, dt=3600):
    sectors = [0.0] * 16
    for u, d in zip(hourly_wind_speeds, hourly_wind_dirs):
        idx = sector_index(d)
        sectors[idx] += ((u ** 3.8) * dt) / 233847
    return sectors

def compute_snow_transport(T, F, theta, Swe, hourly_wind_speeds):
    Qupot = compute_Qupot(hourly_wind_speeds)
    Qspot = 0.5 * T * Swe
    Srwe = theta * Swe
    if Qupot > Qspot:
        Qinf = 0.5 * T * Srwe
        control = "Snowfall controlled"
    else:
        Qinf = Qupot
        control = "Wind controlled"
    Qt = Qinf * (1 - 0.14 ** (F / T))
    return {
        'Qupot (kg/m)': Qupot,
        'Qspot (kg/m)': Qspot,
        'Srwe (mm)': Srwe,
        'Qinf (kg/m)': Qinf,
        'Qt (kg/m)': Qt,
        'Control': control
    }

def compute_fence_height(Qt, fence_type):
    Qt_tonnes = Qt / 1000.0
    ft = fence_type.lower()
    if ft == 'wyoming':
        factor = 8.5
    elif ft in ['slat-and-wire', 'slat and wire']:
        factor = 7.7
    elif ft == 'solid':
        factor = 2.9
    else:
        raise ValueError("Unsupported fence type")
    H = (Qt_tonnes / factor) ** (1 / 2.2)
    return H

# Prepare dataframe: add season column (season year = year if month >=7 else year-1)
df = df.copy()
df['season'] = df['time'].apply(lambda dt: dt.year if dt.month >= 7 else dt.year - 1)

# Filter dataset to selected years range (season start in range)
seasons = list(range(start_year, end_year + 1))
df = df[df['season'].isin(seasons)].reset_index(drop=True)

if df.empty:
    st.warning("No data available for the selected year range.")
    st.stop()

# Snow transport parameters (controls)
T = st.number_input("Maximum transport distance T (m)", value=3000, step=100)
F = st.number_input("Fetch distance F (m)", value=30000, step=1000)
theta = st.number_input("Relocation coefficient theta", value=0.5, format="%.2f")


def compute_results(input_df: pd.DataFrame, start_year: int, end_year: int, T: float, F: float, theta: float):
    """Compute seasonal snow transport results and aggregated sectors.

    Returns: (results_df, avg_sectors, fence_df)
    """
    # Work on a copy
    df_loc = input_df.copy()
    # Filter to seasons
    seasons = list(range(start_year, end_year + 1))
    df_loc = df_loc[df_loc['season'].isin(seasons)].reset_index(drop=True)
    if df_loc.empty:
        return None, None, None

    results = []
    sector_aggregate = []
    for s in sorted(df_loc['season'].unique()):
        grp = df_loc[df_loc['season'] == s]
        if grp.empty:
            continue
        grp = grp.copy()
        grp['Swe_hourly'] = grp.apply(lambda r: r['precipitation (mm)'] if r.get('temperature_2m (°C)', 9999) < 1 else 0, axis=1)
        total_Swe = grp['Swe_hourly'].sum()
        wind_speeds = grp['wind_speed_10m (m/s)'].tolist()
        wind_dirs = grp['wind_direction_10m (°)'].tolist()
        res = compute_snow_transport(T, F, theta, total_Swe, wind_speeds)
        res['season'] = s
        results.append(res)
        sectors = compute_sector_transport(wind_speeds, wind_dirs)
        sector_aggregate.append(sectors)

    results_df = pd.DataFrame(results).sort_values('season')
    if results_df.empty:
        return None, None, None

    results_df['Qt (tonnes/m)'] = results_df['Qt (kg/m)'] / 1000.0

    # Average sectors across seasons
    avg_sectors = np.mean(sector_aggregate, axis=0)

    # Fence heights
    fence_types = ['Wyoming', 'Slat-and-wire', 'Solid']
    fence_rows = []
    for _, row in results_df.iterrows():
        season = row['season']
        Qt = row['Qt (kg/m)']
        fr = {'season': season}
        for ft in fence_types:
            fr[ft] = compute_fence_height(Qt, ft)
        fence_rows.append(fr)
    fence_df = pd.DataFrame(fence_rows).set_index('season')

    return results_df, avg_sectors, fence_df


# Button-controlled update: compute on first load or when user clicks Update
update_button = st.button("Update plots")
params = (start_year, end_year, T, F, theta)

# Decide whether to compute now
do_compute = False
if 'snow_drift_results' not in st.session_state:
    # first load -> compute once
    do_compute = True
elif update_button:
    do_compute = True

if do_compute:
    results_df, avg_sectors, fence_df = compute_results(df, start_year, end_year, T, F, theta)
    st.session_state['snow_drift_results'] = {
        'params': params,
        'results_df': results_df,
        'avg_sectors': avg_sectors,
        'fence_df': fence_df
    }

# Retrieve cached results
cached = st.session_state.get('snow_drift_results')
if not cached or cached.get('results_df') is None:
    st.warning("No results available for the selected range. Click 'Update plots' to compute.")
    st.stop()

results_df = cached['results_df']
avg_sectors = cached['avg_sectors']
fence_df = cached['fence_df']

st.subheader("Average Snow Drift per Season")
st.dataframe(results_df[['season', 'Qt (tonnes/m)', 'Control']].set_index('season'))

# Plot Qt per season as a bar
fig = px.bar(results_df, x='season', y='Qt (tonnes/m)', title='Average Snow Drift per Season (tonnes/m)')
st.plotly_chart(fig, use_container_width=True)

st.subheader("Directional Wind Rose (16 sectors)")
angles = np.arange(0, 360, 360/16)
avg_tonnes = np.array(avg_sectors) / 1000.0
rose_fig = go.Figure()
rose_fig.add_trace(go.Barpolar(r=avg_tonnes, theta=angles, width=[360/16]*16,
                              name='Avg transport (tonnes/m)', marker_color='royalblue', opacity=0.8))
rose_fig.update_layout(polar=dict(radialaxis=dict(title='tonnes/m')),
                       title='Average Directional Distribution of Snow Transport')
st.plotly_chart(rose_fig, use_container_width=True)

st.subheader("Fence Height Estimates")
st.dataframe(fence_df)

st.markdown("---")
st.caption("Snow drift calculations adapted from Snow_drift.py (Tabler, 2003). Using assets/open-meteo-subset.csv for meteorological inputs.")



