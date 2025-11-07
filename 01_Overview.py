import streamlit as st
import pandas as pd
import streamlit as st
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="IND320 Project Overview", layout="wide")

# Reference: Norwegian price areas and representative cities
price_areas = pd.DataFrame({
    'price_area': ['NO1', 'NO2', 'NO3', 'NO4', 'NO5'],
    'city': ['Oslo', 'Kristiansand', 'Trondheim', 'Tromsø', 'Bergen'],
    'latitude': [59.9139, 58.1467, 63.4305, 69.6492, 60.3913],
    'longitude': [10.7522, 7.9956, 10.3951, 18.9553, 5.3221]
})

st.title("IND320 Course Project")

# Quick status panel
colA, colB = st.columns(2)
with colA:
    st.metric("Known price areas", len(price_areas))
    st.dataframe(price_areas, hide_index=True, use_container_width=True)
with colB:
    year = st.session_state.get('weather_year', 'N/A')
    area = st.session_state.get('selected_area', 'N/A')
    df_loaded = 'weather_data' in st.session_state and st.session_state['weather_data'] is not None
    st.metric("Weather loaded", "Yes" if df_loaded else "No")
    st.write(f"Selected area (from Page 2): {area}")
    st.write(f"Selected year: {year}")

st.markdown("""
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
