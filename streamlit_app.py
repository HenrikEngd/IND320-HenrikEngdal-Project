from pymongo import MongoClient
import requests
import streamlit as st
import pandas as pd
from pymongo.server_api import ServerApi
import certifi
from utils.fetch import load_data_from_mongodb, load_weather_data

st.set_page_config(
    page_title="IND320 - Data to Decision | Project Homepage",
    layout="centered"
)

df_prod = load_data_from_mongodb('production_data')
st.session_state['ELHUB_Production_data'] = df_prod
df_cons = load_data_from_mongodb('consumption_data')
st.session_state['ELHUB_Consumption_data'] = df_cons
df_weather = load_weather_data(pricearea=None, start="2021-01-01", end="2024-12-31") #None -> Loads all areas
st.session_state['weather_data'] = df_weather


st.markdown("""
### Project Overview
This project is part of the course "IND320 - Data to Decision" at the Norwegian University of Life Sciences.
The application demonstrates a complete data pipeline for energy analytics, including data ingestion, processing, storage, and interactive visualization.

**Key Features:**
- Load and explore Norwegian energy production and consumption data
- Integrate and analyze weather data alongside energy datasets
- Perform distributed data processing and aggregations using Spark
- Visualize trends, correlations, and statistics with interactive Plotly charts
- Filter, group, and compare data by region, time, and energy type
- Download processed datasets for further analysis
- Interactive dashboards and data exploration with Streamlit

**Data Sources:**
- Weather data from [Open-Meteo](https://open-meteo.com/)
- Norwegian energy production / consumption data from [Elhub API](https://api.elhub.no/)
- Geodata from [NVE](https://temakart.nve.no/tema/nettanlegg)

**Technologies:**
- **Streamlit**: Interactive web application framework
- **Plotly**: Advanced interactive visualizations
- **Spark**: Distributed data processing and aggregations
- **MongoDB**: Cloud database for energy production / consumption data
- **Cassandra**: Distributed NoSQL database integration
""")
