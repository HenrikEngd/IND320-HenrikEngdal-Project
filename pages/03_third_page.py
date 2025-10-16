import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# Page configuration
st.set_page_config(page_title="Weather Data Analysis", layout="wide")

st.title("Weather Data Analysis")
st.markdown("---")

# Get data from session state (loaded in homepage)
df = st.session_state.get('weather_data', None)

if df is None:
    st.error("No weather data available. Please visit the homepage first to load the data.")
    st.stop()

if df is not None:
    # Work on a local copy to avoid mutating cached data in session state
    df_local = df.copy()
    # Extract month for filtering
    df_local['month'] = df_local['time'].dt.strftime('%Y-%m')
    # Get unique months for the slider
    months = sorted(df_local['month'].unique())
    
    # Create month abbreviations mapping
    month_mapping = {}
    month_display_names = []
    
    for month_str in months:
        # Convert '2020-01' to 'Jan 2020'
        year, month_num = month_str.split('-')
        month_abbrev = datetime.strptime(month_num, '%m').strftime('%b')
        display_name = f"{month_abbrev} {year}"
        month_mapping[display_name] = month_str
        month_display_names.append(display_name)
    
    # Create two columns for controls
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("Column Selection")
        # Get numeric columns (excluding time)
        numeric_columns = [col for col in df_local.select_dtypes(include='number').columns if col not in ['time']]
        column_options = ['All Columns'] + numeric_columns
        
        selected_column = st.selectbox(
            "Choose a column to visualize:",
            options=column_options,
            index=0,
            help="Select a specific column or 'All Columns' to show all data together"
        )
    
    with col2:
        st.subheader("Month Selection")
        # Month selection slider with abbreviated names
        # Default to the first month only (January) — two handles set to the first month if range is available
        default_month_value = (
            (month_display_names[0], month_display_names[0])
            if len(month_display_names) >= 2
            else month_display_names[0]
        )
        selected_month_display = st.select_slider(
            "Select month range:",
            options=month_display_names,
            value=default_month_value,
            help="Use the slider to select a contiguous range of months"
        )
    
    # Convert display selection back to actual month values for filtering
    if isinstance(selected_month_display, str):
        selected_months = [month_mapping[selected_month_display]]
    elif isinstance(selected_month_display, tuple):
        # Get all months between the selected range
        start_display = selected_month_display[0]
        end_display = selected_month_display[1]
        start_idx = month_display_names.index(start_display)
        end_idx = month_display_names.index(end_display)
        selected_display_range = month_display_names[start_idx:end_idx + 1]
        selected_months = [month_mapping[display] for display in selected_display_range]
    else:
        selected_months = [month_mapping[selected_month_display]]
    
    # Filter data based on selected months
    filtered_df = df_local[df_local['month'].isin(selected_months)]
    
    st.markdown("---")
    
    # Create the plot
    if len(filtered_df) > 0:
        # Get display names for selected months
        selected_display_names = [display for display, month in month_mapping.items() if month in selected_months]
        
        st.subheader(f"Weather Data Visualization")
        
        if selected_column == 'All Columns':
            # Create subplot for all columns
            fig = go.Figure()
            
            colors = ['#FF6B6B', "#7AFFA4", "#D8ABFF", "#FF71FA", '#FFEAA7']
            
            for i, col in enumerate(numeric_columns):
                fig.add_trace(go.Scatter(
                    x=filtered_df['time'],
                    y=filtered_df[col],
                    mode='lines',
                    name=col,
                    line=dict(color=colors[i % len(colors)], width=2),
                    hovertemplate=f'<b>{col}</b><br>Date: %{{x}}<br>Value: %{{y}}<extra></extra>'
                ))
            
            fig.update_layout(
                title={
                    'text': f"All Weather Parameters Over Time ({', '.join(selected_display_names)})",
                    'x': 0.5,
                    'font': {'size': 20}
                },
                xaxis_title="Date and Time",
                yaxis_title="Values (Various Units)",
                hovermode='x unified',
                height=600,
                showlegend=True,
                legend=dict(
                    yanchor="top",
                    y=0.99,
                    xanchor="left",
                    x=1.01
                ),
                template='plotly_white',
                margin=dict(r=150)
            )
            
            # Update x-axis formatting
            fig.update_xaxes(
                showgrid=True,
                gridwidth=1,
                gridcolor='lightgray',
                tickformat='%Y-%m-%d %H:%M'
            )
            
            fig.update_yaxes(
                showgrid=True,
                gridwidth=1,
                gridcolor='lightgray'
            )
            
        else:
            # Create plot for single column
            fig = px.line(
                filtered_df,
                x='time',
                y=selected_column,
                title=f"{selected_column} Over Time ({', '.join(selected_display_names)})",
                labels={
                    'time': 'Date and Time',
                    selected_column: selected_column
                },
                height=600
            )
            
            fig.update_traces(
                line=dict(color='#3498DB', width=2),
                hovertemplate=f'<b>{selected_column}</b><br>Date: %{{x}}<br>Value: %{{y}}<extra></extra>'
            )
            
            fig.update_layout(
                title={
                    'text': fig.layout.title.text,
                    'x': 0.5,
                    'font': {'size': 20}
                },
                template='plotly_white',
                hovermode='x'
            )
            
            # Update axes
            fig.update_xaxes(
                title_text="Date and Time",
                showgrid=True,
                gridwidth=1,
                gridcolor='lightgray',
                tickformat='%Y-%m-%d %H:%M'
            )
            
            fig.update_yaxes(
                title_text=selected_column,
                showgrid=True,
                gridwidth=1,
                gridcolor='lightgray'
            )
        
        # Display the plot
        st.plotly_chart(fig, width='stretch')
        
    else:
        st.warning("No data available for the selected month(s).")
        
else:
    st.error("Unable to load data. Please check if the data file exists and is properly formatted.")

