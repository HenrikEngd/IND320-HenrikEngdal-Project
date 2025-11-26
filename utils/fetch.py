import streamlit as st
import pandas as pd
import requests 
import requests_cache
from retry_requests import retry
import openmeteo_requests
from pymongo import MongoClient
from pymongo.server_api import ServerApi

# Coordinates/names for Norwegian price areas (shared across pages)
AREA_COORDINATES = {
    'NO1': {'latitude': 59.91, 'longitude': 10.75, 'name': 'Oslo'},
    'NO2': {'latitude': 58.15, 'longitude': 8.01,  'name': 'Kristiansand'},
    'NO3': {'latitude': 63.43, 'longitude': 10.39, 'name': 'Trondheim'},
    'NO4': {'latitude': 69.65, 'longitude': 18.96, 'name': 'Tromsø'},
    'NO5': {'latitude': 60.39, 'longitude': 5.32,  'name': 'Bergen'},
} 

# Removed TARGET_YEAR = 2021
BASE_WEATHER_URL = "https://archive-api.open-meteo.com/v1/archive"


# Global Robust Client Setup
cache_session = requests_cache.CachedSession('.cache', expire_after=-1)
retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
openmeteo_client = openmeteo_requests.Client(session=retry_session) 

@st.cache_data(ttl=3600, show_spinner="Fetching ELHUB data...")
def load_data_from_mongodb(collection_name: str) -> pd.DataFrame:
    uri = st.secrets["database"]["uri"]
    client = MongoClient(uri, server_api=ServerApi('1'))

    db = client[st.secrets["database"]["db_name"]]
    col = db[collection_name]
    items = list(col.find({}, {'_id': 0}).limit(2000))
    df = pd.DataFrame(items)
    client.close()

    df.columns = [c.lower() for c in df.columns]
    return df

@st.cache_data(ttl=3600, show_spinner="Fetching weather data...")
def load_weather_data(pricearea, start, end) -> pd.DataFrame:
    """Load weather data from Open-Meteo API based on price area or lat/lon and year"""

    area = pricearea.upper()
    if area not in AREA_COORDINATES:
        raise ValueError(f"Price Area {area} not found in coordinates dictionary.")
        
    latitude = AREA_COORDINATES[area]['latitude']
    longitude = AREA_COORDINATES[area]['longitude']  # Lookup coordinates
    hourly_variables = ["temperature_2m", "precipitation", "wind_speed_10m", "wind_gusts_10m", "wind_direction_10m"]
    
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "start_date": start,
        "end_date": end,
        "hourly": hourly_variables,
        "models": "era5",
    }
       
    responses = openmeteo_client.weather_api(BASE_WEATHER_URL, params=params)
    response = responses[0]

    hourly = response.Hourly()
    hourly_data = {
        "time": pd.date_range(
            start=pd.to_datetime(hourly.Time(), unit="s"),
            end=pd.to_datetime(hourly.TimeEnd(), unit="s"),
            freq=pd.Timedelta(seconds=hourly.Interval()),
            inclusive="left"
        )
    }
    for i, var in enumerate(hourly_variables):
        hourly_data[var] = hourly.Variables(i).ValuesAsNumpy()

    df = pd.DataFrame(hourly_data)
    # Do NOT set 'time' as index, keep it as a column
    return df