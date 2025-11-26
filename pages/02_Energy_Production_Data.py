import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import requests
from utils.sidebar import price_area_sidebar

st.set_page_config(page_title="Energy Production Data", layout="wide")

# Read session-cached values (set by other pages) with safe defaults
weather_df_session = st.session_state.get('weather_data')
selected_area_session = st.session_state.get('selected_area', 'NO5')
selected_city_session = st.session_state.get('selected_city', 'Bergen')
weather_year_session = st.session_state.get('weather_year', '2021')

# Coordinates/names for Norwegian price areas (shared across pages)
AREA_COORDINATES = {
    'NO1': {'latitude': 59.91, 'longitude': 10.75, 'name': 'Oslo'},
    'NO2': {'latitude': 60.39, 'longitude': 5.32,  'name': 'Bergen'},
    'NO3': {'latitude': 63.43, 'longitude': 10.39, 'name': 'Trondheim'},
    'NO4': {'latitude': 69.65, 'longitude': 18.96, 'name': 'Tromsø'},
    'NO5': {'latitude': 60.47, 'longitude': 8.47,  'name': 'Gol'}
} 
# Load and cache data globally
@st.cache_data
def load_weather_data(price_area: str = None, lat: float = None, lon: float = None, start: str = '2021', end: str = '2024'):
    """Load weather data from Open-Meteo API based on price area or lat/lon and year"""
    try:
        coords = None
        if lat is not None and lon is not None:
            coords = {'latitude': lat, 'longitude': lon}
        elif price_area is not None:
            if price_area not in AREA_COORDINATES:
                st.error(f"Unknown price area: {price_area}")
                return None
            coords = AREA_COORDINATES[price_area]

        if coords is None:
            st.error("No coordinates supplied to load weather data")
            return None

        # Build Open-Meteo API URL for selected year
        start_date = f"{start}-01-01"
        end_date = f"{end}-12-31"
        url = (
            f"https://archive-api.open-meteo.com/v1/archive?"
            f"latitude={coords['latitude']}&longitude={coords['longitude']}"
            f"&start_date={start_date}&end_date={end_date}"
            f"&hourly=temperature_2m,precipitation,wind_speed_10m,wind_direction_10m,wind_gusts_10m"
            f"&timezone=Europe/Oslo"
        )

        # Fetch data from API
        response = requests.get(url)

        if response.status_code != 200:
            st.error(f"API request failed with status code: {response.status_code}")
            return None

        data = response.json()

        # Convert to DataFrame
        df = pd.DataFrame({
            'time': pd.to_datetime(data['hourly']['time']),
            'temperature_2m': data['hourly']['temperature_2m'],
            'precipitation': data['hourly']['precipitation'],
            'wind_speed_10m': data['hourly']['wind_speed_10m'],
            'wind_direction_10m': data['hourly']['wind_direction_10m'],
            'wind_gusts_10m': data['hourly']['wind_gusts_10m']
        })

        return df

    except Exception as e:
        st.error(f"Error loading weather data: {str(e)}")
        return None


# Load data and filter to only 2021
df = st.session_state.get('ELHUB_Production_data', None)
if df is None:
    st.error("No production data available. Please visit the homepage first to load the data.")
    st.stop()

df = df[df['startTime'].dt.year == 2021].reset_index(drop=True)

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

    # Use global sidebar price-area selector (stored in session_state) and include production groups
    selected_area = price_area_sidebar(price_areas, area_coords=AREA_COORDINATES, default=selected_area_session, groups=production_groups, group_key='selected_group')
    # Ensure other session values are synced
    st.session_state['selected_area'] = selected_area
    st.session_state['selected_city'] = AREA_COORDINATES.get(selected_area, {}).get('name', selected_city_session)
    st.session_state['weather_year'] = weather_year_session  # keep existing year

    # Refresh weather data if missing or area/year changed
    # Prefer using selected_coordinates (from sidebar or map) to load weather; fallback to selected_area
    sel_coords = st.session_state.get('selected_coordinates')
    if (
        ('weather_data' not in st.session_state)
        or (st.session_state.get('weather_area') != selected_area)
        or (str(st.session_state.get('weather_year')) != str(weather_year_session))
    ):
        if sel_coords:
            wdf = load_weather_data(lat=sel_coords[0], lon=sel_coords[1], start=weather_year_session, end=weather_year_session)
        else:
            wdf = load_weather_data(selected_area, start=weather_year_session, end=weather_year_session)
        if wdf is not None:
            st.session_state['weather_data'] = wdf
            st.session_state['weather_area'] = selected_area
            st.session_state['weather_year'] = weather_year_session

    area_data = df[df['priceArea'] == selected_area]
    production_summary = area_data.groupby('productionGroup')['quantityKwh'].sum().reset_index()
    production_summary.columns = ['productionGroup', 'total_production']
    total = production_summary['total_production'].sum()
    production_summary['percentage'] = (production_summary['total_production'] / total * 100).round(1)
    legend_labels = [f"{row.productionGroup} ({row.percentage:.1f}%)" for row in production_summary.itertuples()]

    fig1 = go.Figure(data=[go.Pie(
        labels=legend_labels,
        values=production_summary['total_production'],
        hole=0,
        textinfo='none',
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
            'font': {'size': 16}
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

    st.plotly_chart(fig1, use_container_width=True)
    st.metric("Total Production (kWh)", f"{total:,.0f}")

# Line Plot
with col2:
    st.subheader("Production Over Time")
    
    # Read selected group(s) from sidebar session key
    # Sidebar stores a single selected group under 'selected_group'; to support multiple groups, keep this as a single-item list
    sel_group = st.session_state.get('selected_group')
    if sel_group and sel_group != 'All groups':
        selected_groups = [sel_group]
    else:
        # All groups selected -> default to all production groups
        selected_groups = production_groups
    
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
