
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

# Check if coordinates are selected from the Price Area Map page
if "selected_coordinates" not in st.session_state:
    st.warning("Please select coordinates on the Price Area Map page first.")
else:
    lat, lon = st.session_state.selected_coordinates

    # Initialize Spark session
    spark = SparkSession.builder.appName("SnowDriftAnalysis").getOrCreate()

    # Load weather data (assuming data is stored in CSV files per year)
    weather_dfs = []
    for year_val in range(start_year, end_year + 1):
        df = spark.read.csv(f"data/weather_{year_val}.csv", header=True, inferSchema=True)
        weather_dfs.append(df)

    # Combine dataframes
    weather_data = weather_dfs[0]
    for df in weather_dfs[1:]:
        weather_data = weather_data.union(df)

    # Filter data for the selected coordinates and year range
    filtered_data = weather_data.filter(
        (col("latitude") == lat) &
        (col("longitude") == lon) &
        (year(col("date")).between(start_year, end_year))
    )

    # Calculate average snow drift per year
    snow_drift_per_year = filtered_data.withColumn("year", year(col("date"))) \
        .groupBy("year") \
        .agg(avg("snow_drift").alias("avg_snow_drift")) \
        .orderBy("year")

    # Convert to Pandas DataFrame for visualization
    snow_drift_pd = snow_drift_per_year.toPandas()

    # Plotting
    fig = px.line(snow_drift_pd, x="year", y="avg_snow_drift", title="Average Snow Drift per Year")
    st.plotly_chart(fig)

    