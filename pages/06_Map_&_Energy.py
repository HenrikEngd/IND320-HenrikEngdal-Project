

# --- Imports ---
import re
import streamlit as st
import folium
from streamlit_folium import st_folium
import json
from shapely.geometry import shape, Point, Polygon, MultiPolygon
import pandas as pd
import branca



# --- Load production and consumption data from session state ---
if 'ELHUB_Production_data' in st.session_state:
    prod_df = st.session_state['ELHUB_Production_data']
else:
    st.error("Production data not found in session state.")
    st.stop()

if 'ELHUB_Consumption_data' in st.session_state:
    cons_df = st.session_state['ELHUB_Consumption_data']
else:
    st.error("Consumption data not found in session state.")
    st.stop()


# --- Streamlit page config and title ---
st.set_page_config(layout="wide")
st.title("Map & Energy Data")


# --- Load GeoJSON for Norwegian price areas ---
geojson_path = "assets/file.geojson"
with open(geojson_path, "r", encoding="utf-8") as f:
    geojson_data = json.load(f)



# --- Normalize area codes to NO1-NO5 format ---
def normalize_to_NO(code):
    if code is None:
        return None
    if isinstance(code, int):
        return f"NO{code}"
    s = str(code).strip().upper()
    s = re.sub(r"[^A-Z0-9]", "", s)
    m = re.match(r"^N0?([1-9])$", s)
    if m:
        return f"NO{m.group(1)}"
    m2 = re.match(r"^NO0?([1-9])$", s)
    if m2:
        return f"NO{m2.group(1)}"
    m3 = re.match(r"^0?([1-9])$", s)
    if m3:
        return f"NO{m3.group(1)}"
    return None


# --- Extract price area code from GeoJSON feature ---
def extract_geojson_area(feature):
    props = feature.get("properties", {})
    candidates = ["ElSpotOmr", "Elspot_omr", "ELSPOT_OMR", "ElSpotOmråde", "ELSPOT_OMRADE"]
    raw = None
    for k in candidates:
        if k in props:
            raw = props[k]
            break
    if raw is None:
        for v in props.values():
            if isinstance(v, (str, int)) and normalize_to_NO(v) is not None:
                raw = v
                break
    return normalize_to_NO(raw)


# --- Build mapping from feature index to area code ---
geo_feature_area = {}
for i, feat in enumerate(geojson_data.get("features", [])):
    geo_feature_area[i] = extract_geojson_area(feat)



# --- Initialize session state for map selection and area means ---
if "clicked_point" not in st.session_state:
    st.session_state.clicked_point = None
if "selected_area" not in st.session_state:
    st.session_state.selected_area = None
if "area_means" not in st.session_state:
    st.session_state.area_means = {}



# --- Sidebar controls for data type, group, and year ---
data_type = st.sidebar.radio("Select data type:", ["Production", "Consumption"], horizontal=True)
df = prod_df if data_type == "Production" else cons_df
group_col = "productiongroup" if data_type == "Production" else "consumptiongroup"

# --- Validate data presence and structure ---
if df.empty or group_col not in df.columns:
    st.warning("No data available (empty dataframe or missing group column).")
    st.stop()

groups = sorted(df[group_col].dropna().unique())
if not groups:
    st.warning("No groups found in the data.")
    st.stop()

selected_group = st.sidebar.selectbox("Select group:", groups)



# --- Set index to 'endtime' and filter valid years (2021-2024) ---
if 'endtime' in df.columns:
    df = df.copy()
    df['endtime'] = pd.to_datetime(df['endtime'], errors='coerce')
    df = df.set_index('endtime')
else:
    st.error("'endtime' column not found in the data.")
    st.stop()

years = df.index.year.unique()
years = sorted([int(y) for y in years if pd.notna(y) and 2021 <= int(y) <= 2024])
if not years:
    st.warning("No valid years (2021-2024) found in the data.")
    st.stop()
selected_year = st.sidebar.selectbox("Select year:", years)



# --- Compute mean quantity per area for selected group and year ---
def compute_area_means():
    df_group = df[df[group_col] == selected_group].copy()
    if df_group.empty:
        return {}

    if not isinstance(df_group.index, pd.DatetimeIndex):
        df_group.index = pd.to_datetime(df_group.index)

    df_group = df_group.copy()
    if not isinstance(df_group.index, pd.DatetimeIndex):
        df_group.index = pd.to_datetime(df_group.index)
    df_group["year"] = df_group.index.year
    df_year = df_group[df_group["year"] == int(selected_year)]
    if df_year.empty:
        return {}

    df_year["pricearea"] = df_year["pricearea"].apply(normalize_to_NO)
    df_year = df_year[df_year["pricearea"].notna()]
    return df_year.groupby("pricearea")["quantitykwh"].mean().to_dict()


# --- Store and validate area means in session state ---
st.session_state.area_means = compute_area_means()
area_means = st.session_state.area_means

if not area_means:
    st.warning(f"No data available for {selected_group} in {selected_year}.")
    st.stop()

# --- Create color scale for map visualization ---
vals = list(area_means.values())
vmin, vmax = min(vals), max(vals)
colormap = branca.colormap.LinearColormap(
    colors=["#210084", "#007c8f", "#54ff85"],
    vmin=vmin, vmax=vmax,
    caption=f"Mean quantity kWh for {selected_group} ({selected_year})"
)


# --- Build folium map and add polygons ---
m = folium.Map(location=[63.0, 10.5], zoom_start=5.4, tiles="OpenStreetMap")


# --- Style function for folium polygons ---
def style_function(feature):
    area = extract_geojson_area(feature)
    fill = "#dddddd"
    if area in area_means:
        fill = colormap(area_means[area])
    if st.session_state.selected_area == area:
        return {"fillColor": fill, "color": "red", "weight": 3, "fillOpacity": 0.65}
    return {"fillColor": fill, "color": "#3333cc", "weight": 1, "fillOpacity": 0.55}


# --- Tooltip content for folium polygons ---
def tooltip_content(feature):
    props = feature.get("properties", {})
    txt = []
    for k in ["ElSpotOmr", "Elspot_omr", "ELSPOT_OMR"]:
        if k in props:
            txt.append(f"{k}: {props[k]}")
    return "<br/>".join(txt)


# --- Add polygons and colormap to map ---
for i, feat in enumerate(geojson_data.get("features", [])):
    folium.GeoJson(
        feat,
        style_function=style_function,
        tooltip=folium.Tooltip(tooltip_content(feat), sticky=True)
    ).add_to(m)

colormap.add_to(m)

# --- Add marker for clicked point ---
if st.session_state.clicked_point:
    folium.Marker(
        st.session_state.clicked_point,
        icon=folium.Icon(color="red", icon="info-sign")
    ).add_to(m)


# --- Handle map click events to update selected area and coordinates ---
map_data = st_folium(m, width=1000, height=700)
if map_data and map_data.get("last_clicked"):
    lat = map_data["last_clicked"]["lat"]
    lon = map_data["last_clicked"]["lng"]
    st.session_state.clicked_point = (lat, lon)

    point = Point(lon, lat)
    clicked_area = None
    for feat in geojson_data.get("features", []):
        geom = shape(feat["geometry"])
        if isinstance(geom, (Polygon, MultiPolygon)) and geom.contains(point):
            clicked_area = extract_geojson_area(feat)
            break

    st.session_state.selected_area = clicked_area
