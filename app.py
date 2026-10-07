import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots


st.set_page_config(page_title="Lithium Price Dashboard", layout="wide")


@st.cache_data
def load_data():
    try:
        df_merged = pd.read_csv('lithium_ev_merged.csv')
        seasonality = pd.read_csv('seasonality.csv')
        forecast = pd.read_csv('forecast.csv')
        corr_df = pd.read_csv('correlation.csv')
        return df_merged, seasonality, forecast, corr_df
    except FileNotFoundError:
        st.error("Data files not found. Please run the analysis notebook first.")
        st.stop()

df_merged, seasonality, forecast, corr_df = load_data()


# Header
st.title("Lithium Carbonate (Li₂CO₃) Price Dashboard")
st.markdown("This dashboard analyzes lithium price dynamics and their correlation with EV sales.")


# Key metrics with USD conversion
st.subheader("Key Metrics")

# TODO: replace with a live FX API (e.g., exchangerate.host) in production
CNY_TO_USD = 7.2

current_price_cny = df_merged['price_cny'].iloc[-1]
current_price_usd = current_price_cny / CNY_TO_USD

latest_year = df_merged['Year'].max()
avg_latest_cny = df_merged[df_merged['Year'] == latest_year]['price_cny'].mean()
avg_latest_usd = avg_latest_cny / CNY_TO_USD

forecast_cny = forecast['price_cny'].iloc[-1]
forecast_usd = forecast_cny / CNY_TO_USD

col1, col2, col3 = st.columns(3)
col1.metric(
    "Current Price",
    f"{current_price_cny:,.0f} CNY/t",
    f"≈ {current_price_usd:,.0f} USD/t"
)
col2.metric(
    f"Avg Price ({latest_year})",
    f"{avg_latest_cny:,.0f} CNY/t",
    f"≈ {avg_latest_usd:,.0f} USD/t"
)
col3.metric(
    "Forecast (6m)",
    f"{forecast_cny:,.0f} CNY/t",
    f"≈ {forecast_usd:,.0f} USD/t"
)


# Main price chart with event annotations
st.subheader("Price Dynamics (2021-2026)")

fig_price = px.line(
    df_merged,
    x='date',
    y='price_cny',
    title='Lithium Price Over Time',
    labels={'price_cny': 'Price (CNY/t)', 'date': 'Date'}
)

# The 2022 spike was driven by a supply deficit; the 2023 crash followed a wave of new supply.
fig_price.add_annotation(
    x='2022-11-01', y=600000,
    text="Peak 2022: Supply Deficit",
    showarrow=True, arrowhead=1
)
fig_price.add_annotation(
    x='2023-04-12', y=177000,
    text="Crash 2023: Oversupply",
    showarrow=True, arrowhead=1, ay=30, ax=-30
)

st.plotly_chart(fig_price, use_container_width=True)


# Correlation between price and EV sales
st.subheader("Lithium Price vs Global EV Sales")

# Aggregate global data by year. Price is averaged; EV sales is constant within a year.
df_global = df_merged[df_merged['Entity'] == 'World'].groupby('Year').agg({
    'price_cny': 'mean',
    'Electric cars sold': 'first'
}).reset_index()

# Load precomputed correlation (calculated in analysis.ipynb)
corr_value = corr_df[corr_df['region'] == 'World']['correlation'].values[0]
st.markdown(f"**Pearson correlation: {corr_value:.2f}** (strong negative)")

fig_dual = make_subplots(specs=[[{"secondary_y": True}]])

fig_dual.add_trace(
    go.Bar(
        x=df_global['Year'],
        y=df_global['Electric cars sold'],
        name='EV Sales (units)',
        marker_color='#4A90E2',
        opacity=0.6
    ),
    secondary_y=False
)

fig_dual.add_trace(
    go.Scatter(
        x=df_global['Year'],
        y=df_global['price_cny'],
        name='Lithium Price (CNY/t)',
        mode='lines+markers',
        line=dict(color='#FF6B6B', width=3),
        marker=dict(size=10)
    ),
    secondary_y=True
)

fig_dual.update_yaxes(title_text="EV Sales (units)", secondary_y=False)
fig_dual.update_yaxes(title_text="Lithium Price (CNY/t)", secondary_y=True)
fig_dual.update_layout(title_text="Price vs EV Sales (World, Yearly)", hovermode='x unified')

st.plotly_chart(fig_dual, use_container_width=True)

peak_month = seasonality.loc[seasonality['price_cny'].idxmax(), 'Month']
cheapest_month = seasonality.loc[seasonality['price_cny'].idxmin(), 'Month']

st.markdown(f"""
**Interpretation:** The negative correlation ({corr_value:.2f}) is driven by the 2022 supply shock:
after prices spiked to ~600k CNY/t, new supply came online and prices crashed — while EV sales
kept growing steadily. This reflects supply dynamics, not demand.
""")


# Seasonality and forecast side by side
col_seasonality, col_forecast = st.columns(2)

with col_seasonality:
    st.subheader("Seasonality")
    fig_season = px.bar(
        seasonality,
        x='Month',
        y='price_cny',
        title='Avg Price by Month',
        labels={'price_cny': 'Avg Price (CNY/t)', 'Month': 'Month'}
    )
    st.plotly_chart(fig_season, use_container_width=True)

with col_forecast:
    st.subheader("Forecast (Next 6 Months)")
    fig_forecast = px.line(
        forecast,
        x='date',
        y='price_cny',
        color='type',
        title='Price Forecast',
        labels={'price_cny': 'Price (CNY/t)', 'date': 'Date'}
    )
    st.plotly_chart(fig_forecast, use_container_width=True)


# Key insights, generated from the data rather than hardcoded
st.markdown(f"""
**Key Insights:**
- Pearson correlation between EV sales and lithium prices: **{corr_value:.2f}** (strong negative).
- Prices historically peak in **{peak_month}**.
- **{cheapest_month}** is the cheapest month for procurement.
- Forecast suggests a gradual decline to ~{forecast_cny:,.0f} CNY/t by March 2027.
""")