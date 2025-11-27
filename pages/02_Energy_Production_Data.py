import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import requests
from utils.fetch import load_weather_data
from utils.sidebar import price_area_sidebar
from utils.fetch import AREA_COORDINATES

st.set_page_config(page_title="Energy Production Data", layout="wide")

# Read session-cached values (set by other pages) with safe defaults
selected_area_session = st.session_state.get('selected_area', 'NO5')
selected_city_session = st.session_state.get('selected_city', 'Bergen')
weather_year_session = st.session_state.get('weather_year', '2021')


# Load data
df = st.session_state.get('ELHUB_Production_data')

if df is None:
    st.error("No production data available. Please visit the homepage first to load the data.")
    st.stop()

# Add year column if not present
if 'year' not in df.columns:
    df['year'] = df['starttime'].dt.year


# Create two columns
col1, col2 = st.columns(2)



# Add this to ensure 'month' exists
if 'month' not in df.columns:
    df['month'] = df['starttime'].dt.month

# Get unique values for filters
price_areas = sorted(df['pricearea'].unique())
production_groups = sorted(df['productiongroup'].unique())
months = sorted(df['month'].unique())
month_names = ['January', 'February', 'March', 'April', 'May', 'June', 
               'July', 'August', 'September', 'October', 'November', 'December']

# Create two columns
col1, col2 = st.columns(2)

# Pie Chart
with col1:
    st.subheader("Total Production by Type")
    years = list(range(2021, 2025))
    selected_year = st.selectbox("Select Year:", options=years, index=years.index(2021) if 2021 in years else 0)

    # Filter to selected year (after selection)
    df = df[df['year'] == selected_year].reset_index(drop=True)

    # Use global sidebar price-area selector (stored in session_state) and include production groups
    selected_area = price_area_sidebar(price_areas, area_coords=AREA_COORDINATES, default=selected_area_session, groups=production_groups, group_key='selected_group')
    # Ensure other session values are synced
    st.session_state['selected_area'] = selected_area
    st.session_state['selected_city'] = AREA_COORDINATES.get(selected_area, {}).get('name', selected_city_session)
    st.session_state['weather_year'] = weather_year_session  # keep existing year

    # Refresh weather data if missing or area/year changed
    # Prefer using selected_coordinates (from sidebar or map) to load weather; fallback to selected_area
    sel_coords = st.session_state.get('selected_coordinates')

    area_data = df[df['pricearea'] == selected_area]
    production_summary = area_data.groupby('productiongroup')['quantitykwh'].sum().reset_index()
    production_summary.columns = ['productiongroup', 'total_production']
    total = production_summary['total_production'].sum()
    production_summary['percentage'] = (production_summary['total_production'] / total * 100).round(1)
    legend_labels = [f"{row.productiongroup} ({row.percentage:.1f}%)" for row in production_summary.itertuples()]

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
        (df['pricearea'] == selected_area) & 
        (df['productiongroup'].isin(selected_groups)) &
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
            group_data = filtered_df[filtered_df['productiongroup'] == group].sort_values('starttime')

            if not group_data.empty:
                fig2.add_trace(go.Scatter(
                    x=group_data['starttime'],
                    y=group_data['quantitykwh'],
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
            st.metric("Average Production", f"{filtered_df['quantitykwh'].mean():,.0f} kWh")
        with col_metric2:
            st.metric("Peak Production", f"{filtered_df['quantitykwh'].max():,.0f} kWh")
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
