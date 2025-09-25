import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

st.title("Third Page")

df = pd.read_csv('./assets/open-meteo-subset.csv')
st.dataframe(df)

df['time'] = pd.to_datetime(df['time'])
month_names = df['time'].dt.strftime('%B %Y').unique()
selected_month = st.select_slider('Select month:', options=month_names, value=month_names[0])

month_mask = df['time'].dt.strftime('%B %Y') == selected_month
month_df = df[month_mask]

columns = list(df.columns)
columns.remove('time')
columns_option = ['All columns'] + columns
selected_column = st.selectbox('Select column to plot:', columns_option)

st.subheader(f"Data Plot for {selected_month}")
fig, ax = plt.subplots(figsize=(10, 5))
if selected_column == 'All columns':
    for col in columns:
        ax.plot(month_df['time'], month_df[col], label=col)
else:
    ax.plot(month_df['time'], month_df[selected_column], label=selected_column)

ax.set_xlabel('Time')
ax.set_ylabel('Value')
ax.set_title(f"{selected_column} for {selected_month}" if selected_column != 'All columns' else f"All Columns for {selected_month}")
ax.legend()
plt.xticks(rotation=45)
plt.tight_layout()
st.pyplot(fig)