import streamlit as st
import pandas as pd

# Page configuration
st.set_page_config(page_title="Weather Data Table", layout="wide")

st.title("Weather Data Overview")
st.markdown("---")

# Get data from session state (loaded in homepage)
df = st.session_state.get('weather_data', None)

if df is None:
    st.error("No weather data available. Please visit the homepage first to load the data.")
    st.stop()

if df is not None:
    # Filter data for the first month
    first_month_df = df[df['time'].dt.strftime('%Y-%m') == '2020-01']
    
    # Get numeric columns only (exclude non-numeric like 'time' or any string columns)
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
    
    st.subheader("Weather Parameters - First Month Analysis")
    st.markdown("Each row shows statistics and trends for one weather parameter during January 2020")
    
    # Display the table
    st.dataframe(
        table_df,
        column_config={
            "Parameter": st.column_config.TextColumn(
                "Weather Parameter",
                help="The weather measurement parameter",
                width="medium"
            ),
            "Mean": st.column_config.NumberColumn(
                "Mean Value",
                help="Average value for January 2020"
            ),
            "Min": st.column_config.NumberColumn(
                "Minimum",
                help="Lowest recorded value in January 2020"
            ),
            "Max": st.column_config.NumberColumn(
                "Maximum", 
                help="Highest recorded value in January 2020"
            ),
            "Std Dev": st.column_config.NumberColumn(
                "Standard Deviation",
                help="Standard deviation showing data variability"
            ),
            # using LineChartColumn for trend visualization
            "First Month Trend": st.column_config.LineChartColumn(
                "Trend",
                help="Hourly trend visualization for the entire first month",
                width="large"
            )
        },
        width='stretch',
        hide_index=True
    )

else:
    st.error("Unable to load data. Please check if the data file exists and is properly formatted.")

