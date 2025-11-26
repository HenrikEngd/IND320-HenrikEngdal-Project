from pymongo import MongoClient
import requests
import streamlit as st
import pandas as pd
from pymongo.server_api import ServerApi
import certifi

# MongoDB connection
@st.cache_resource
def get_mongo_client():
    """Create and return MongoDB client"""
    db_user = st.secrets["database"]["db_user"]
    secret = st.secrets["database"]["secret"]

    uri = f"mongodb+srv://{db_user}:{secret}@cluster0.xxdbouc.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
    # Use certifi CA bundle to avoid SSL CERTIFICATE_VERIFY_FAILED on macOS
    client = MongoClient(
        uri,
        server_api=ServerApi('1'),
        tls=True,
        tlsCAFile=certifi.where(),
    )
    
    # Test connection
    try:
        client.admin.command('ping')
    except Exception as e:
        st.error(f"MongoDB connection failed: {e}")
    
    return client

# Load and process data
@st.cache_data
def load_ELHUB_Production_data():
    """Load and process data from MongoDB"""
    client = get_mongo_client()

    database = client['ELBHUB_Data']
    collection = database['production_data']

    # Fetch all documents from MongoDB
    records = list(collection.find({}, {'_id': 0}))
    
    if not records:
        st.error("No data found in MongoDB!")
        st.stop()
    
    # Convert to DataFrame
    df = pd.DataFrame(records)
    
    # Clean the data - remove any records with list or invalid values
    def is_valid_record(row):
        """Check if a record has valid data types"""
        for col in ['startTime', 'endTime', 'lastUpdatedTime', 'priceArea', 'productionGroup', 'quantityKwh']:
            if col in row and isinstance(row[col], list):
                return False
        return True
    
    # Filter out invalid records
    valid_indices = df.apply(is_valid_record, axis=1)
    initial_count = len(df)
    df = df[valid_indices].reset_index(drop=True)
    
    if len(df) < initial_count:
        st.warning(f"Filtered out {initial_count - len(df)} invalid records from the dataset.")
    
    # Convert date columns to datetime (with error handling)
    try:
        df['startTime'] = pd.to_datetime(df['startTime'], errors='coerce')
        df['endTime'] = pd.to_datetime(df['endTime'], errors='coerce')
        df['lastUpdatedTime'] = pd.to_datetime(df['lastUpdatedTime'], errors='coerce')
        
        # Remove rows where datetime conversion failed
        df = df.dropna(subset=['startTime']).reset_index(drop=True)
        
        # Add month columns
        df['month'] = df['startTime'].dt.month
        df['month_name'] = df['startTime'].dt.strftime('%B')
        
    except Exception as e:
        st.error(f"Error processing datetime columns: {e}")
        st.stop()
    
    return df

@st.cache_data
def load_ELHUB_Consumption_data():
    """Load and process consumption data from MongoDB"""
    client = get_mongo_client()

    database = client['ELBHUB_Data']
    collection = database['consumption_data']

    # Fetch all documents from MongoDB
    records = list(collection.find({}, {'_id': 0}))
    
    if not records:
        st.error("No consumption data found in MongoDB!")
        st.stop()
    
    # Convert to DataFrame
    df = pd.DataFrame(records)
    
    # Convert date columns to datetime (with error handling)
    try:
        df['startTime'] = pd.to_datetime(df['startTime'], errors='coerce')
        df['endTime'] = pd.to_datetime(df['endTime'], errors='coerce')
        df['lastUpdatedTime'] = pd.to_datetime(df['lastUpdatedTime'], errors='coerce')
        
        # Remove rows where datetime conversion failed
        df = df.dropna(subset=['startTime']).reset_index(drop=True)
        
        # Add month columns
        df['month'] = df['startTime'].dt.month
        df['month_name'] = df['startTime'].dt.strftime('%B')
        
    except Exception as e:
        st.error(f"Error processing datetime columns: {e}")
        st.stop()
    
    return df


st.session_state['ELHUB_Production_data'] = load_ELHUB_Production_data()
st.session_state['ELHUB_Consumption_data'] = load_ELHUB_Consumption_data()

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
