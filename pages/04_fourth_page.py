import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import plotly.graph_objects as go
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi

st.set_page_config(page_title="Energy Production Analysis", layout="wide")

st.title("Energy Production Analysis")

# MongoDB connection
@st.cache_resource
def get_mongo_client():
    """Create and return MongoDB client"""
    db_user = st.secrets["database"]["db_user"]
    secret = st.secrets["database"]["secret"]

    uri = f"mongodb+srv://{db_user}:{secret}@cluster0.xxdbouc.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
    client = MongoClient(uri, server_api=ServerApi('1'))
    
    # Test connection
    try:
        client.admin.command('ping')
    except Exception as e:
        st.error(f"MongoDB connection failed: {e}")
    
    return client

# Load and process data
@st.cache_data
def load_data():
    """Load and process data from MongoDB"""
    client = get_mongo_client()
    
    database = client['ca2_database'] 
    collection = database['data']
    
    # Fetch all documents from MongoDB
    records = list(collection.find({}, {'_id': 0}))
    
    if not records:
        st.error("No data found in MongoDB! Please run your notebook to insert data first.")
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

# Load data
df = load_data()

# Get unique values for filters
price_areas = sorted(df['priceArea'].unique())
production_groups = sorted(df['productionGroup'].unique())
months = sorted(df['month'].unique())
month_names = ['January', 'February', 'March', 'April', 'May', 'June', 
               'July', 'August', 'September', 'October', 'November', 'December']

# Create two columns
col1, col2 = st.columns(2)

# Pie Chart
with col1:
    st.subheader("Total Production by Type")
    
    # Radio buttons for price area selection
    selected_area = st.radio(
        "Select Price Area:",
        options=price_areas,
        horizontal=True
    )
    
    # Calculate total production by group for selected area
    area_data = df[df['priceArea'] == selected_area]
    production_summary = area_data.groupby('productionGroup')['quantityKwh'].sum().reset_index()
    production_summary.columns = ['productionGroup', 'total_production']
    production_summary = production_summary.sort_values('total_production', ascending=False)
    
    # Calculate percentages
    total = production_summary['total_production'].sum()
    production_summary['percentage'] = (production_summary['total_production'] / total * 100)
    
    # Create custom labels with percentages for legend
    legend_labels = [
        f"{row['productionGroup']} ({row['percentage']:.1f}%)" 
        for _, row in production_summary.iterrows()
    ]
    
    # Create Plotly pie chart with no text on the pie itself
    fig1 = go.Figure(data=[go.Pie(
        labels=legend_labels,  # Use custom labels with percentages
        values=production_summary['total_production'],
        hole=0, 
        textinfo='none',  # Using legend, so no need for text on pie
        hovertemplate='<b>%{label}</b><br>Production: %{value:,.0f} kWh<extra></extra>',
        marker=dict(
            colors=['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', 
                    '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf'],
            line=dict(color='white', width=2)
        )
    )])
    
    fig1.update_layout(
        title={
            'text': f"Total Production Distribution in {selected_area}",
            'x': 0.5,
            'xanchor': 'center',
            'font': {'size': 16, 'weight': 'bold'}
        },
        showlegend=True,
        legend=dict(
            orientation="v",
            yanchor="middle",
            y=0.5,
            xanchor="left",
            x=1.02,
            font=dict(size=10)
        ),
        height=450,
        margin=dict(l=20, r=180, t=60, b=20)
    )
    
    # Display the pie chart
    st.plotly_chart(fig1, use_container_width=True)
    
    # Display summary statistics
    st.metric("Total Production (kWh)", f"{production_summary['total_production'].sum():,.0f}")

# Line Plot
with col2:
    st.subheader("Production Over Time")
    
    # Pills for production group selection
    selected_groups = st.pills(
        "Select Production Groups:",
        options=production_groups,
        selection_mode="multi",
        default=production_groups[:5]  # Default to  5 groups
    )
    
    # Ensure at least one group is selected
    if not selected_groups:
        selected_groups = [production_groups[0]]
    
    # Month selection - show all 12 months
    selected_month = st.selectbox(
        "Select Month:",
        options=list(range(1, 13)),  # All 12 months
        format_func=lambda x: month_names[x-1],
        index=0  # Default to January
    )
    
    # Filter data based on selections
    filtered_df = df[
        (df['priceArea'] == selected_area) & 
        (df['productionGroup'].isin(selected_groups)) &
        (df['month'] == selected_month)
    ]
    
    if not filtered_df.empty:
        # Create Plotly line chart
        fig2 = go.Figure()
        
        # Define colors for usage
        colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', 
                  '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf']
        
        # Add a line for each production group
        for i, group in enumerate(selected_groups):
            group_data = filtered_df[filtered_df['productionGroup'] == group].sort_values('startTime')
            
            if not group_data.empty:
                fig2.add_trace(go.Scatter(
                    x=group_data['startTime'],
                    y=group_data['quantityKwh'],
                    mode='lines+markers',
                    name=group,
                    line=dict(color=colors[i % len(colors)], width=2),
                    marker=dict(size=4),
                    hovertemplate=f'<b>{group}</b><br>Time: %{{x}}<br>Production: %{{y:,.0f}} kWh<extra></extra>'
                ))
        
        # Update layout
        fig2.update_layout(
            title={
                'text': f"Energy Production in {selected_area} - {month_names[selected_month-1]}",
                'x': 0.5,
                'xanchor': 'center',
                'font': {'size': 16, 'weight': 'bold'}
            },
            xaxis_title="Time",
            yaxis_title="Quantity (kWh)",
            hovermode='x unified',
            height=500,
            showlegend=True,
            legend=dict(
                title="Production Group",
                yanchor="top",
                y=0.99,
                xanchor="left",
                x=1.01
            ),
            template='plotly_white',
            margin=dict(r=150)
        )
        
        # Update axes
        fig2.update_xaxes(
            showgrid=True,
            gridwidth=1,
            gridcolor='lightgray',
            tickformat='%Y-%m-%d %H:%M'
        )
        
        fig2.update_yaxes(
            showgrid=True,
            gridwidth=1,
            gridcolor='lightgray'
        )
        
        # Display the chart
        st.plotly_chart(fig2, use_container_width=True)
        
        # Display metrics
        col_metric1, col_metric2 = st.columns(2)
        with col_metric1:
            st.metric("Average Production", f"{filtered_df['quantityKwh'].mean():,.0f} kWh")
        with col_metric2:
            st.metric("Peak Production", f"{filtered_df['quantityKwh'].max():,.0f} kWh")
    else:
        st.warning("No data available for the selected filters.")

# Data Source Documentation
st.markdown("---")
with st.expander("Data Source Information"):
    st.markdown("""
    ### Data Source
    
    **Provider:** Elhub - The Norwegian energy data hub
    
    **API Endpoint:** https://api.elhub.no/energy-data/v0/price-areas?dataset=PRODUCTION_PER_GROUP_MBA_HOUR
    
    **Dataset:** `PRODUCTION_PER_GROUP_MBA_HOUR`
    - Contains hourly energy production data grouped by production type
    - Covers all Norwegian price areas (NO1-NO5)
    
    **Time Period:** Full year 2021 (January - December)
    
    **Production Groups Include:**
    - **Hydro** - Hydroelectric power from water resources
    - **Wind** - Wind power generation
    - **Thermal** - Thermal power plants
    - **Nuclear** - Nuclear power generation (if applicable)
    - **Other** - Other renewable and non-renewable sources
    
    **Data Fields:**
    - `priceArea`: Norwegian price area identifier (NO1, NO2, NO3, NO4, NO5)
    - `productionGroup`: Type of energy production source
    - `quantityKwh`: Production quantity measured in kilowatt-hours
    - `startTime`: Beginning of the measurement period
    - `endTime`: End of the measurement period
    - `lastUpdatedTime`: Timestamp of when the data was last updated
    
    **Data Storage:**
    - Data is stored in MongoDB
    - Processed using Spark
    
    **Last Updated:** Data reflects measurements from 2021, with metadata updates as recent as {last_update}
                
    ---
    **Total Records in Database:** {total_records:,}
    
    **API Source:** https://api.elhub.no/
    """.format(
        last_update=df['lastUpdatedTime'].max().strftime('%Y-%m-%d') if 'lastUpdatedTime' in df.columns and pd.notna(df['lastUpdatedTime'].max()) else 'N/A',
        total_records=len(df)
    ))
