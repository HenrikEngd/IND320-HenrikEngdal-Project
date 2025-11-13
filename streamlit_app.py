import streamlit as st
import pandas as pd


st.title("IND320 Course Project")


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
