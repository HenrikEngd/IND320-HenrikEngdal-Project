import streamlit as st
import pandas as pd

# Load and cache data globally
@st.cache_data
def load_weather_data():
    # Load, prepare and cache the data
    try:   
        df = pd.read_csv("assets/open-meteo-subset.csv")
        # Convert time column to datetime
        df['time'] = pd.to_datetime(df['time'])
        return df
    except FileNotFoundError:
        st.error("Could not find the data file")
        return None
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        return None

# Load data once and store in session state
if 'weather_data' not in st.session_state:
    st.session_state.weather_data = load_weather_data()

st.title("IND320 Course Project")

# Show data load status
if st.session_state.weather_data is None:
    st.error("Failed to load the data")


st.markdown("""
### Project Overview
This project is part of the course "IND320 - Data to Decision" at the Norwegian University of Life Sciences.
The application demonstrates data loading, processing, and visualization using Streamlit and Plotly.
The dataset used is a subset of weather data from [Open-Meteo](https://open-meteo.com/).

### Content
- Home Page: Overview of the project and data load status.
- Second Page: Table with weather parameters for January 2020, incl. mean, min, max, std.
- Third Page: Dynamic visualization with parameter selection and month range filter.
""")
