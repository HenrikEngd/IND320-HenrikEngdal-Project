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
The application demonstrates data loading, processing, and visualization using Streamlit, Plotly, Spark, and MongoDB.

**Data Sources:**
- Weather data from [Open-Meteo](https://open-meteo.com/)
- Norwegian energy production data from [Elhub API](https://api.elhub.no/)

**Technologies:**
- **Streamlit**: Interactive web application framework
- **Plotly**: Advanced interactive visualizations
- **Apache Spark**: Distributed data processing and aggregations
- **MongoDB Atlas**: Cloud database for energy production data
- **Cassandra**: Distributed NoSQL database integration

### Content
- **Home Page**: Overview of the project and data load status
- **Second Page**: Statistical analysis table with weather parameters for January 2020 (mean, min, max, std)
- **Third Page**: Dynamic weather data visualization with parameter selection and month range filter using Plotly charts
- **Fourth Page**: Energy Production Analysis
  - Interactive Plotly pie chart showing production distribution by type (hydro, wind, thermal, etc.)
  - Time-series line chart with multi-group selection
  - Data filtered by Norwegian price areas (NO1-NO5)
  - Real-time data from MongoDB Atlas
  - Powered by Apache Spark aggregations

### Data Pipeline
```
API → JSON → Pandas → Spark (aggregations) → MongoDB → Streamlit
```
The energy production data is processed using Apache Spark for distributed aggregations, stored in MongoDB Atlas, and visualized with interactive Plotly charts.
""")
