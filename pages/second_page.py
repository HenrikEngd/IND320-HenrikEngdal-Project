import streamlit as st
import pandas as pd

# Page configuration
st.set_page_config(page_title="Weather Data Table", layout="wide")

st.title("Weather Data Overview")
st.markdown("---")

# Load and prepare data
@st.cache_data
def load_data():
    """Load and prepare the weather data"""
    try:
        df = pd.read_csv("assets/open-meteo-subset.csv")
        # Convert time column to datetime
        df['time'] = pd.to_datetime(df['time'])
        return df
    except FileNotFoundError:
        st.error("❌ Could not find the data file. Please ensure 'assets/open-meteo-subset.csv' exists.")
        return None
    except Exception as e:
        st.error(f"❌ Error loading data: {str(e)}")
        return None

# Load data
df = load_data()

if df is not None:
    # Filter data for the first month (January 2020)
    first_month_df = df[df['time'].dt.strftime('%Y-%m') == '2020-01']
    
    # Get numeric columns (excluding time)
    numeric_columns = [col for col in df.columns if col != 'time']
    
    # Create table data for display
    table_data = []
    
    for column in numeric_columns:
        # Get first month data for this column
        first_month_values = first_month_df[column].values
        
        # Calculate statistics
        mean_val = first_month_df[column].mean()
        min_val = first_month_df[column].min()
        max_val = first_month_df[column].max()
        std_val = first_month_df[column].std()
        
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
    
    # Display the table with line chart column
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
            "First Month Trend": st.column_config.LineChartColumn(
                "Trend",
                help="Hourly trend visualization for the entire first month",
                width="large"
            )
        },
        width='stretch',
        hide_index=True
    )
    
    st.markdown("---")
    
    # Additional insights section
    st.subheader("Key Insights from First Month Data")
    
    # Create insights columns
    insight_col1, insight_col2 = st.columns(2)
    
    with insight_col1:
        st.markdown("**Data Statistics:**")
        st.write(f"• **Total hourly measurements**: {len(first_month_df):,}")
        st.write(f"• **Date range**: {first_month_df['time'].min().strftime('%Y-%m-%d')} to {first_month_df['time'].max().strftime('%Y-%m-%d')}")
        st.write(f"• **Weather parameters tracked**: {len(numeric_columns)}")
        
        # Find most variable parameter
        cv_values = {}
        for col in numeric_columns:
            mean_val = first_month_df[col].mean()
            std_val = first_month_df[col].std()
            if mean_val != 0:
                cv_values[col] = (std_val / abs(mean_val)) * 100
        
        if cv_values:
            most_variable = max(cv_values.keys(), key=lambda x: cv_values[x])
            st.write(f"• **Most variable parameter**: {most_variable} (CV: {cv_values[most_variable]:.1f}%)")
    
    with insight_col2:
        st.markdown("**Temperature Insights:**")
        temp_col = 'temperature_2m (°C)'
        if temp_col in numeric_columns:
            temp_data = first_month_df[temp_col]
            st.write(f"• **Average temperature**: {temp_data.mean():.1f}°C")
            st.write(f"• **Temperature range**: {temp_data.min():.1f}°C to {temp_data.max():.1f}°C")
            st.write(f"• **Daily temperature swing**: {temp_data.max() - temp_data.min():.1f}°C")
        
        st.markdown("**Wind Insights:**")
        wind_col = 'wind_speed_10m (m/s)'
        if wind_col in numeric_columns:
            wind_data = first_month_df[wind_col]
            st.write(f"• **Average wind speed**: {wind_data.mean():.1f} m/s")
            st.write(f"• **Max wind speed**: {wind_data.max():.1f} m/s")
    

else:
    st.error("Unable to load data. Please check if the data file exists and is properly formatted.")

