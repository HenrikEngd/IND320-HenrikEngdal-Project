from pymongo import MongoClient
import requests
import streamlit as st
import pandas as pd
from pymongo.server_api import ServerApi
import certifi
from utils.fetch import load_data_from_mongodb

st.set_page_config(
    page_title="IND320 - Data to Decision | Project Homepage",
    layout="centered"
)

df_prod = load_data_from_mongodb('production_data')
st.session_state['ELHUB_Production_data'] = df_prod
df_cons = load_data_from_mongodb('consumption_data')
st.session_state['ELHUB_Consumption_data'] = df_cons


st.markdown("""
### Project Overview
This project is part of the course "IND320 - Data to Decision" at the Norwegian University of Life Sciences.
The application demonstrates data loading, processing, and visualization using Streamlit, Plotly, Spark, and MongoDB.

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
          
### Data Pipeline
```
API → JSON → Pandas → Spark (aggregations) → MongoDB → Streamlit
```
The energy production / consumption data is processed using Spark for distributed aggregations, stored in MongoDB Atlas, and visualized with interactive Plotly charts.
""")
