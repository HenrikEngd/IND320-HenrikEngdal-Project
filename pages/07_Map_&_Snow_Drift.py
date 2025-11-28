
import streamlit as st
import folium
from streamlit_folium import st_folium
import json
from shapely.geometry import shape, Point, Polygon, MultiPolygon
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from utils.fetch import load_weather_data
from pathlib import Path


# --- Load GeoJSON ---
geojson_path = Path("assets/file.geojson")
if not geojson_path.exists():
    st.error(f"GeoJSON file not found at {geojson_path}")
    st.stop()
with open(geojson_path, "r", encoding="utf-8") as f:
    geojson_data = json.load(f)

def normalize_area_name(name):
    if isinstance(name, str):
        name = name.replace(" ", "")
        if name.startswith("N0") and len(name) == 3:
            return "NO" + name[-1]
    return name

for feature in geojson_data["features"]:
    raw_name = feature["properties"].get("ElSpotOmr")
    feature["properties"]["ElSpotOmrNorm"] = normalize_area_name(raw_name)


# --- Session state init ---
if "clicked_point" not in st.session_state:
    st.session_state.clicked_point = None
if "selected_area" not in st.session_state:
    st.session_state.selected_area = None
if "selected_feature_id" not in st.session_state:
    st.session_state.selected_feature_id = None

st.title("Map & Snow Drift")


# --- Data type selection (Production/Consumption) ---
data_type = st.sidebar.radio("Select data type:", ["Production", "Consumption"], horizontal=True)

# --- Dummy data for choropleth (replace with real data as needed) ---
value_map = {"NO1": 5.0, "NO2": 3.5, "NO3": 4.2, "NO4": 6.1, "NO5": 2.8}
df_vals = pd.DataFrame({"pricearea": list(value_map.keys()), "quantitykwh": list(value_map.values())})

# --- Map ---
m = folium.Map(location=[63.0, 10.5], zoom_start=5.5)

vmin = df_vals["quantitykwh"].min()
vmax = df_vals["quantitykwh"].max()
thresholds = np.linspace(vmin, vmax, 6).tolist() if not np.isclose(vmin, vmax) else [vmin-1e-6, vmin, vmax+1e-6]

folium.Choropleth(
    geo_data=geojson_data,
    name="choropleth",
    data=df_vals,
    columns=["pricearea", "quantitykwh"],
    key_on="feature.properties.ElSpotOmrNorm",
    fill_color="YlGnBu",
    fill_opacity=0.6,
    line_opacity=0.3,
    line_color="black",
    legend_name=f"{data_type} mean quantity (kWh)",
    threshold_scale=thresholds,
    nan_fill_color="lightgray"
).add_to(m)

folium.GeoJson(
    geojson_data,
    name="tooltips",
    tooltip=folium.GeoJsonTooltip(
        fields=["ElSpotOmrNorm"],
        aliases=["Price area:"],
        labels=True,
        sticky=True
    ),
    style_function=lambda _: {"color": "transparent", "weight": 0, "fillOpacity": 0}
).add_to(m)

# Highlight clicked point and selected area
if st.session_state.clicked_point:
    folium.Marker(
        location=st.session_state.clicked_point,
        icon=folium.Icon(color="red", icon="info-sign")
    ).add_to(m)

if st.session_state.selected_area:
    def highlight_style(feat):
        return {"color": "#d62728", "weight": 4, "fillOpacity": 0} \
            if feat["properties"].get("ElSpotOmrNorm") == st.session_state.selected_area \
            else {"color": "transparent", "weight": 0, "fillOpacity": 0}

    folium.GeoJson(
        geojson_data,
        name="selected_highlight",
        style_function=highlight_style,
        tooltip=None,
    ).add_to(m)

map_data = st_folium(m, width=950, height=630)

# --- Capture click events ---
if map_data and map_data.get("last_clicked"):
    lat = map_data["last_clicked"]["lat"]
    lon = map_data["last_clicked"]["lng"]
    st.session_state.clicked_point = (lat, lon)

    point = Point(lon, lat)
    clicked_area = None
    for feature in geojson_data["features"]:
        geom = shape(feature["geometry"])
        if isinstance(geom, (Polygon, MultiPolygon)) and geom.contains(point):
            clicked_area = feature["properties"].get("ElSpotOmrNorm")
            break
    st.session_state.selected_area = clicked_area

if st.session_state.selected_area:
    val = value_map.get(st.session_state.selected_area, None)
    if val is not None and not pd.isna(val):
        st.sidebar.success(f"Selected area: **{st.session_state.selected_area}** → {val:.2f} kWh")
    else:
        st.sidebar.success(f"Selected area: **{st.session_state.selected_area}** (no data)")

if st.session_state.clicked_point:
    st.sidebar.write(f"Clicked coordinates: {st.session_state.clicked_point}")

# Choropleth (single layer)
folium.Choropleth(
    geo_data=geojson_data,
    data=df_vals,
    columns=["pricearea", "quantitykwh"],
    key_on="feature.properties.ElSpotOmrNorm",
    fill_color="YlGnBu",
    fill_opacity=0.6,
    line_opacity=0.3,
    line_color="black",
    legend_name=f"{data_type} mean quantity (kWh)",
    threshold_scale=thresholds,
    nan_fill_color="lightgray"
).add_to(m)

# Highlight the selected polygon outline (pre-filtered; no filter_function)
if st.session_state.get("selected_feature_id") is not None:
    sel_id = st.session_state.get("selected_feature_id")
    sel_feats = [
        f for f in geojson_data.get("features", [])
        if f.get("id") == sel_id or (f.get("properties") or {}).get("id") == sel_id
    ]
    if sel_feats:
        folium.GeoJson(
            {"type": "FeatureCollection", "features": sel_feats},
            style_function=lambda f: {"fillOpacity": 0, "color": "red", "weight": 3},
            name="selection"
        ).add_to(m)
else:
    st.info("Please choose a location on the map to plot data.")

# Single pin (last clicked)
folium.Marker(
    location=st.session_state.selected_coordinates,
    icon=folium.Icon(color="red"),
    popup=f"{st.session_state.selected_coordinates[0]:.5f}, {st.session_state.selected_coordinates[1]:.5f}"
).add_to(m)

# Render map at full width
out = st_folium(m, key="choropleth_map", height=600, width=1200)


# Process click: update pin, polygon ID, and price area, then rerun
if out and out.get("last_clicked"):
    lat = out["last_clicked"]["lat"]
    lon = out["last_clicked"]["lng"]
    new_coord = [lat, lon]
    if new_coord != st.session_state.selected_coordinates:
        st.session_state.selected_coordinates = new_coord
        # No need for feature_id/id_to_name logic; selection is handled by shapely/GeoJSON logic above
        st.rerun()
        st.stop()


# Ensure sidebar selector is present for global price-area selection
# Snow drift does not have production groups, but if production groups are available in session, expose them


# Price area selection is now only via the map; sidebar selector removed for this page.


# --- Only allow snow drift analysis if a valid area is selected ---
if not st.session_state.selected_area or not st.session_state.clicked_point:
    st.warning("No valid price area selected on the map above. Please click a location inside a price area (NO1–NO5).")
    st.stop()

lat, lon = st.session_state.clicked_point

def normalize_weather_df(raw_df: pd.DataFrame) -> pd.DataFrame:
    """Normalize an incoming weather dataframe (either from session or CSV) to expected column names.

    Expected normalized columns:
      - time (datetime)
      - temperature_2m (°C)
      - precipitation (mm)
      - wind_speed_10m (m/s)
      - wind_direction_10m (°)
    """
    if raw_df is None:
        st.warning("No weather data loaded. Please upload or load weather data.")
        return pd.DataFrame()
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



# Always load weather data for the currently selected price area (from map selection)
selected_area = st.session_state.selected_area
df_weather = load_weather_data(pricearea=selected_area, start="2021-01-01", end="2024-12-31")
st.session_state['weather_data'] = df_weather

try:
    df = normalize_weather_df(df_weather)
except KeyError as e:
    st.error(f"Weather data missing required column: {e}")
    st.stop()

# We expect these columns (based on assets/open-meteo-subset.csv)
expected_cols = ['time', 'temperature_2m (°C)', 'precipitation (mm)', 'wind_speed_10m (m/s)', 'wind_direction_10m (°)']
missing = [c for c in expected_cols if c not in df.columns]
if missing:
    st.error(f"Required columns missing from data: {missing}")
    st.stop()



# --- Snow drift helper functions ---
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


# --- Year range selection (move up so start_year/end_year are always defined) ---
start_year, end_year = st.slider(
    "Select seasonal year range (July–June)",
    min_value=2020, max_value=2024, value=(2021, 2024),
    key="year_range_slider"
)

# Defining year to start at July 1:
df = df.copy()
df['season'] = df['time'].apply(lambda dt: dt.year if dt.month >= 7 else dt.year - 1)

# Filter dataset to selected years range (season start in range)
seasons = list(range(start_year, end_year + 1))
df = df[df['season'].isin(seasons)].reset_index(drop=True)

if df.empty:
    st.warning("No data available for the selected year range.")
    st.stop()


# --- Snow transport parameters (controls) ---
col1, col2, col3 = st.columns(3)
with col1:
    T = st.number_input("Maximum transport distance T (m)", value=3000, step=100)
with col2:
    F = st.number_input("Fetch distance F (m)", value=30000, step=1000)
with col3:
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


# --- Button-controlled update: compute on first load or when user clicks Update ---
update_button = st.button("Update plots")
params = (start_year, end_year, T, F, theta)
do_compute = False
if 'snow_drift_results' not in st.session_state:
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

cached = st.session_state.get('snow_drift_results')
if not cached or cached.get('results_df') is None:
    st.warning("No results available for the selected range. Click 'Update plots' to compute.")
    st.stop()

results_df = cached['results_df']
avg_sectors = cached['avg_sectors']
fence_df = cached['fence_df']


# Add a season label column for July–June periods
results_df = results_df.copy()
results_df["season_label"] = results_df["season"].apply(lambda y: f"{y}–{y+1}")

# Ensure correct order for x-axis
season_order = [f"{y}–{y+1}" for y in sorted(results_df["season"].unique())]

# Plot Qt per season as a bar with season_label
fig = px.bar(
    results_df,
    x="season_label",
    y="Qt (tonnes/m)",
    title="Average Snow Drift per Season (tonnes/m)",
    category_orders={"season_label": season_order}
)
fig.update_xaxes(title="Season (July–June)")
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


st.header("Monthly Snow Drift")
def calculate_monthly_snow_drift_july_to_june(df, T, F, theta, year):
    """Calculate snow drift for each month from July (year) to June (year+1)."""
    if df.empty:
        return pd.DataFrame()
    df = df.copy()
    df['month'] = df['time'].dt.to_period('M').dt.to_timestamp()
    # Filter for July (year) to June (year+1)
    start = pd.Timestamp(year=year, month=7, day=1)
    end = pd.Timestamp(year=year+1, month=6, day=30, hour=23, minute=59, second=59)
    df = df[(df['time'] >= start) & (df['time'] <= end)]
    # Create ordered list of months July (year) to June (year+1)
    months = [pd.Timestamp(year=year, month=m, day=1) for m in range(7,13)] + [pd.Timestamp(year=year+1, month=m, day=1) for m in range(1,7)]
    monthly = []
    for month in months:
        grp = df[df['month'] == month]
        if grp.empty:
            monthly.append({"month": month.strftime("%b %Y"), "snow_drift_kgm": 0})
            continue
        Swe = grp.apply(lambda r: r['precipitation (mm)'] if r.get('temperature_2m (°C)', 9999) < 1 else 0, axis=1).sum()
        wind_speeds = grp['wind_speed_10m (m/s)'].tolist()
        drift = compute_snow_transport(T, F, theta, Swe, wind_speeds)
        monthly.append({"month": month.strftime("%b %Y"), "snow_drift_kgm": drift['Qt (kg/m)']})
    return pd.DataFrame(monthly)


# Plot monthly snow drift for all July–June periods in the selected year range
if not df.empty:
    min_year = df['time'].dt.year.min()
    max_year = df['time'].dt.year.max()
    # Only allow periods where July (year) to June (year+1) is possible
    valid_years = [y for y in range(start_year, end_year)]
    all_seasons = []
    for year in valid_years:
        df_monthly = calculate_monthly_snow_drift_july_to_june(df, T, F, theta, year)
        if not df_monthly.empty:
            # Add a column for the season label
            season_label = f"{year}–{year+1}"
            df_monthly["season"] = season_label
            # Add a column for plotting x-axis (month name only, always July to June)
            months_order = [
                pd.Timestamp(year=2000, month=m, day=1).strftime("%b") for m in range(7,13)
            ] + [
                pd.Timestamp(year=2001, month=m, day=1).strftime("%b") for m in range(1,7)
            ]
            # Map month to month name (ignore year for x-axis)
            df_monthly["month_name"] = months_order
            all_seasons.append(df_monthly)
    if all_seasons:
        plot_df = pd.concat(all_seasons, ignore_index=True)
        # Plot with Plotly for explicit x-axis control, one line per season
        import plotly.graph_objects as go
        fig = go.Figure()
        for season in plot_df["season"].unique():
            season_df = plot_df[plot_df["season"] == season]
            fig.add_trace(go.Scatter(
                x=season_df["month_name"],
                y=season_df["snow_drift_kgm"],
                mode="lines+markers",
                name=season,
                marker=dict(size=8),
            ))
        fig.update_layout(
            xaxis=dict(title="Month (July–June)", categoryorder="array", categoryarray=months_order),
            yaxis=dict(title="Snow Drift (kg/m²)"),
            margin=dict(l=40, r=20, t=30, b=40),
            height=350,
            legend_title_text="Season (July–June)"
        )
        st.write(f"### Monthly snow drift for all July–June periods in selected range (kg/m²)")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No monthly snow drift data available for the selected range.")


