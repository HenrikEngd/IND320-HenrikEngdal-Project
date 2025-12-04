import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
from utils.sidebar import price_area_sidebar
import requests

# Page configuration
st.set_page_config(page_title="Weather Data Analysis", layout="wide")

st.title("Weather Data Analysis")
st.markdown("---")

# Ensure the global price-area selector is shown and session coords are kept in sync
# If production groups are available in session data, expose them in the sidebar
df_weather = st.session_state.get('weather_data')
prod_df = st.session_state.get('ELHUB_Production_data')
prod_groups = None
if prod_df is not None and 'productiongroup' in prod_df.columns:
    prod_groups = sorted(prod_df['productiongroup'].dropna().unique())
selected_area = price_area_sidebar(['NO1','NO2','NO3','NO4','NO5'], default=st.session_state.get('selected_area', 'NO5'))


if "weather_year" not in st.session_state:
    st.session_state["weather_year"] = 2024  # or set a default value

# Get selected area from session state (set by sidebar)
sel_area = st.session_state.get('selected_area', 'NO5')
weather_year_session = st.session_state['weather_year']

# --- Year selector in sidebar ---
with st.sidebar:
    years = list(range(2020, 2025))
    default_year = 2024
    selected_year = st.selectbox('Select Year', years, index=years.index(default_year) if default_year in years else 0)
    st.session_state['weather_year'] = selected_year
    
# Check if weather data needs to be (re)fetched
last_area = st.session_state.get('weather_area')
last_year = st.session_state.get('weather_year_last')
df = st.session_state.get('weather_data', None)
if (df is None) or (last_area != sel_area) or (last_year != weather_year_session):
    # Fetch new weather data for the selected area and year
    from utils.fetch import load_weather_data
    start_date = f"{weather_year_session}-01-01"
    end_date = f"{weather_year_session}-12-31"
    df = load_weather_data(sel_area, start=start_date, end=end_date)
    st.session_state['weather_data'] = df
    st.session_state['weather_area'] = sel_area
    st.session_state['weather_year_last'] = weather_year_session

if df is None:
    st.error("No weather data available. Please visit the homepage first to load the data.")
    st.stop()

sel_coords = st.session_state.get('selected_coordinates')


if df is not None:
    # Detect datetime column automatically
    datetime_col = None
    for col in df.columns:
        if pd.api.types.is_datetime64_any_dtype(df[col]) or 'date' in col.lower() or 'time' in col.lower():
            datetime_col = col
            break
    if datetime_col is None:
        st.error("No datetime column found in weather data.")
        st.stop()

    # Filter data for the first available month
    first_month = df[datetime_col].dt.to_period('M').min()
    first_month_df = df[df[datetime_col].dt.to_period('M') == first_month]

    # Get numeric columns only (exclude non-numeric like datetime_col or any string columns)
    numeric_columns = list(df.select_dtypes(include='number').columns)

    # Create table data for display
    table_data = []
    for column in numeric_columns:
        # Get first month data for this column
        first_month_values = first_month_df[column].values
        # Calculate statistics (numeric-safe)
        mean_val = pd.to_numeric(first_month_df[column], errors='coerce').mean()
        min_val = pd.to_numeric(first_month_df[column], errors='coerce').min()
        max_val = pd.to_numeric(first_month_df[column], errors='coerce').max()
        std_val = pd.to_numeric(first_month_df[column], errors='coerce').std()
        # Create row data
        row_data = {
            'Parameter': column,
            'Mean': f"{mean_val:.2f}",
            'Min': f"{min_val:.2f}",
            'Max': f"{max_val:.2f}",
            'Std Dev': f"{std_val:.2f}",
            'First Month Trend': first_month_values
        }
        table_data.append(row_data)
    # Convert to DataFrame
    table_df = pd.DataFrame(table_data)

if df is not None:
    # Work on a local copy to avoid mutating cached data in session state
    df_local = df.copy()
    # Extract month as integer for easier filtering
    df_local['month'] = df_local[datetime_col].dt.month
    months = sorted(df_local['month'].unique())
    month_names = [df_local[df_local['month'] == m][datetime_col].dt.strftime('%B').iloc[0] for m in months]
    month_map = dict(zip(months, month_names))

    # Create two columns for controls
    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader("Column Selection")
        # Get numeric columns (excluding datetime_col and 'month')
        numeric_columns = [col for col in df_local.select_dtypes(include='number').columns if col not in [datetime_col, 'month']]
        column_options = ['All Columns'] + numeric_columns
        selected_column = st.selectbox(
            "Choose a column to visualize:",
            options=column_options,
            index=0,
            help="Select a specific column or 'All Columns' to show all data together"
        )

    with col2:
        st.subheader("Month Selection")
        # Month selection slider using month numbers, but display names
        selected_month_range = st.select_slider(
            "Select months range",
            options=months,
            value=(months[0], months[3]),
            format_func=lambda x: month_map[x],
            help="Use the slider to select a contiguous range of months"
        )

    # Filter data within selected month range
    filtered_df = df_local[(df_local['month'] >= selected_month_range[0]) & (df_local['month'] <= selected_month_range[1])]
    
    st.markdown("---")
    
    # Create the plot
    if len(filtered_df) > 0:
        st.subheader(f"Weather Data Visualization")

        import numpy as np
        fig = go.Figure()
        # Only plot selected columns, do not plot the 'month' line
        plot_cols = [col for col in numeric_columns if col not in ["wind_direction_10m", "month"]]

        if selected_column == 'All Columns':
            for i, col in enumerate(plot_cols):
                fig.add_trace(go.Scatter(
                    x=filtered_df['time'],
                    y=filtered_df[col],
                    mode='lines',
                    name=col,
                    line=dict(width=2),
                ))
        else:
            fig.add_trace(go.Scatter(
                x=filtered_df['time'],
                y=filtered_df[selected_column],
                mode='lines',
                name=selected_column,
                line=dict(width=2),
            ))

        # --- Wind direction arrows ---
        if "wind_direction_10m" in filtered_df.columns:
            arrow_every = max(1, len(filtered_df) // 90)
            # Use all numeric columns except wind_direction_10m for y-range
            y_min = filtered_df[plot_cols].min().min() if plot_cols else 0
            y_max = filtered_df[plot_cols].max().max() if plot_cols else 1
            arrow_y = y_min - (y_max - y_min) * 0.1
            arrow_len = (y_max - y_min) * 0.1

            for i in range(0, len(filtered_df), arrow_every):
                t = filtered_df['time'].iloc[i]
                wind_dir = filtered_df['wind_direction_10m'].iloc[i]
                theta = np.deg2rad(wind_dir + 180)
                dx = np.cos(theta) * arrow_len
                dy = np.sin(theta) * arrow_len
                fig.add_annotation(
                    x=t, y=arrow_y,
                    ax=t, ay=arrow_y + dy,
                    xref="x", yref="y", axref="x", ayref="y",
                    text="",
                    showarrow=True,
                    arrowhead=3,
                    arrowsize=1.3,
                    arrowwidth=1.4,
                    arrowcolor="#3498DB",
                )
            # Add legend entry for wind direction
            fig.add_trace(go.Scatter(
                x=[None], y=[None],
                mode="lines+markers",
                line=dict(color="#3498DB", width=2),
                marker=dict(symbol="triangle-right", color="#3498DB", size=10),
                name="Wind Direction",
                showlegend=True
            ))

        # Dynamic title
        first_month = filtered_df['time'].dt.strftime('%B').iloc[0]
        last_month = filtered_df['time'].dt.strftime('%B').iloc[-1]
        if first_month == last_month:
            header_text = f"{selected_column if selected_column != 'All Columns' else 'All columns'} for {first_month}"
        else:
            header_text = f"{selected_column if selected_column != 'All Columns' else 'All columns'} for {first_month} – {last_month}"

        fig.update_layout(
            title=dict(
                text=header_text,
                x=0.5,
                xanchor="center",
                font=dict(size=24)
            ),
            xaxis_title="Time",
            template="plotly_white",
            height=600,
            legend=dict(orientation="h", y=-0.2),
            margin=dict(r=150)
        )

        # Y-axis range
        if selected_column == "All Columns":
            fig.update_yaxes(range=[arrow_y - (y_max - y_min) * 0.08, y_max], nticks=11)
        else:
            y_min_col = filtered_df[selected_column].min()
            y_max_col = filtered_df[selected_column].max()
            fig.update_yaxes(range=[y_min_col, y_max_col], nticks=11)

        st.plotly_chart(fig, width='stretch')
        
    else:
        st.warning("No data available for the selected month(s).")
        
else:
    st.error("Unable to load data. Please check if the data file exists and is properly formatted.")

