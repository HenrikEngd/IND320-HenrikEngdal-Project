import streamlit as st
import pandas as pd

# Set the title of the page
st.title("Second Page")

# Load the dataset and display it
df = pd.read_csv('./assets/open-meteo-subset.csv')
st.dataframe(df)

# Convert 'time' column to datetime and filter for the first month
df['time'] = pd.to_datetime(df['time'])
first_month = df[df['time'].dt.month == 1]

# Create a line chart for each day in the first month
st.line_chart(first_month.set_index('time')[[
    'temperature_2m (°C)',
    'precipitation (mm)',
    'wind_speed_10m (m/s)',
    'wind_gusts_10m (m/s)',
    'wind_direction_10m (°)'
]])