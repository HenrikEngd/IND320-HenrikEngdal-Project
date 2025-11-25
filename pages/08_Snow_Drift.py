
# Calculate snow drift per year in a selected range of years
# Let user choose the year range
# Use the coordinates chosen on the Price Area Map page. Dont calculate/plot if no selection made.
import streamlit as st
import pandas as pd
import plotly.express as px
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, year, avg


st.title("Snow Drift Analysis")

# Year range selection
start_year, end_year = st.slider("Select Year Range", 2021, 2024, (2021, 2024))

# Get weather data from session state (loaded in homepage)
df = st.session_state.get('weather_data', None)
if df is None:
    st.error("No weather data available. Please visit the homepage first to load the data.")
    st.stop()

# Check if coordinates are selected from the Price Area Map page
if "selected_coordinates" not in st.session_state:
    st.warning("Please select coordinates on the Price Area Map page first.")
    st.stop()

lat, lon = st.session_state.selected_coordinates

# Filter data for the selected coordinates and year range
filtered = df[(df['latitude'] == lat) &
              (df['longitude'] == lon) &
              (df['date'].dt.year >= start_year) &
              (df['date'].dt.year <= end_year)]

if filtered.empty:
    st.warning("No data available for the selected coordinates and year range.")
else:
    # Calculate average snow drift per year
    filtered['year'] = filtered['date'].dt.year
    snow_drift_per_year = filtered.groupby('year')['snow_drift'].mean().reset_index(name='avg_snow_drift')

    # Plotting
    fig = px.line(snow_drift_per_year, x="year", y="avg_snow_drift", title="Average Snow Drift per Year")
    st.plotly_chart(fig)

