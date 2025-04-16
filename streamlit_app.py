import duckdb
import pandas as pd

import streamlit as st
import altair as alt

# Connect to the PostgreSQL database
def create_connection():
    conn = duckdb.connect(f"md:{st.secrets.datasource.db_name}?motherduck_token={st.secrets.datasource.token}")
    return conn

def get_df_from_db(query):
    conn = create_connection()
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

def render_chart(data, label_x, label_y, legend, title, divider, date_range):
    st.header(title, divider=divider)
    interval = alt.selection_interval(encodings=['x'], value={'x': date_range})
    selection = alt.selection_point(fields=[legend], bind='legend')
    highlight = alt.selection_point(
        on="pointerover", fields=[label_x], nearest=True, clear="pointerout"
    )

    # Create a base chart
    base = alt.Chart(data).mark_line().encode(
        x=alt.X(f'{label_x}:T', axis=alt.Axis(format='%b %Y')),
        y=alt.Y(f'{label_y}:Q'),
        color=f'{legend}:N',
        opacity=alt.condition(selection, alt.value(1), alt.value(0.2)),
    ).properties(
        width=600,
        height=200
    ).add_params(selection)

    # Create a chart for showing the selected interval
    upper = base.encode(
        alt.X(f'{label_x}:T').scale(domain=interval), # show the selected interval
        alt.Y(f'{label_y}:Q').scale(zero=False), # to remove the zero line if not needed
    )

    # Add a circle to highlight the selected point/s
    circle = upper.mark_circle().encode(
        size=alt.condition(highlight, alt.value(100), alt.value(0), empty=False)
    ).add_params(highlight)

    # Create a view to select the interval
    view = base.encode(
        alt.Y(f'{label_y}:Q').scale(zero=False),
    ).properties(height=60).add_params(interval)

    st.altair_chart((upper + circle) & view, use_container_width=False)

def get_weekly_data():
    query = f"""
            SELECT
                EXTRACT(YEAR FROM end_date_time) AS year,
                meter_name,
                SUM(total_usage_kwh) AS total_usage_kwh,
                strftime(end_date_time, '%A') AS day_name
            FROM {st.secrets.datasource.schema_name}.fact_meter_readings
            GROUP BY EXTRACT(YEAR FROM end_date_time),
                     strftime(end_date_time, '%A'),
                     EXTRACT(DOW FROM end_date_time),
                     meter_name 
            ORDER BY year, meter_name ASC;
            """
    return get_df_from_db(query)

def app():
    query = f"""
            SELECT 
                date_trunc('month', start_date_time) AS month,
                meter_name,
                SUM(total_usage_kwh) AS total_usage_kwh
            FROM {st.secrets.datasource.schema_name}.fact_meter_readings
            GROUP BY month, meter_name
            ORDER BY month, meter_name;
            """
    
    st.write("Fetching data from the database...")
    
    # Fetch data
    df = get_df_from_db(query)
    
    # Display data in the app
    if not df.empty:
        st.write("Data fetched successfully!")
        st.title("Monthly Meter Usage")

        # Get min and max month
        min_date, max_date = df['month'].min(), df['month'].max()

        # Date slider
        with st.sidebar:
            # Generate a list of month start dates
            months = pd.date_range(min_date, max_date, freq='MS').to_pydatetime().tolist()

            filter_min_date, filter_max_date = st.select_slider(
                "Select month range",
                options=months,
                value=(months[0], months[-1]),
                format_func=lambda date: date.strftime('%b %Y')
            )

        # Filter data based on selections
        filtered_df = df[
            (df['month'] >= filter_min_date.date())
            & (df['month'] <= filter_max_date.date())
        ]

        # Interval Default Range
        start_date = filter_max_date - \
            pd.offsets.DateOffset(months=11)
        
        date_range = (start_date.date(), filter_max_date)
        
        render_chart(
            data=filtered_df,
            label_x='month',
            label_y='total_usage_kwh',
            legend='meter_name',
            title='Monthly Total Usage per Meter',
            divider='rainbow',
            date_range=date_range
        )

        # Pivot the DataFrame to show meters as columns
        pivot_df = df.pivot_table(
            index='month',
            columns='meter_name',
            values='total_usage_kwh',
            aggfunc='sum',
            dropna=False
        ).fillna(0)

        # Add row totals (across meters)
        pivot_df['Total'] = pivot_df.sum(axis=1)

        pivot_df.reset_index(inplace=True)

        pivot_df['month'].apply(lambda x: x.strftime('%m/%Y'))

        # # Add column totals (across months)
        pivot_df.loc['Total'] = pivot_df.sum(numeric_only=True, min_count=1)

        # Display
        st.dataframe(pivot_df, use_container_width=True)
    else:
        st.warning("No data available.")

    # Fetch data
    df_weekly = get_weekly_data()

    if not df_weekly.empty:
        # Define your custom order
        day_order = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
        # Set day_name as categorical with the custom order
        df_weekly['day_name'] = pd.Categorical(df_weekly['day_name'], categories=day_order, ordered=True)

        # Create legend selection for year
        year_selection = alt.selection_point(fields=['year'], bind='legend')

        st.title("Meter Usage by Day of the Week")

        # Create grouped bar chart
        base_chart = alt.Chart(df_weekly).mark_bar().encode(
            x=alt.X('day_name:N', title='Day of the Week', sort=day_order),
            y=alt.Y('total_usage_kwh:Q', title='Total Usage (kWh)'),
            color=alt.Color('year:N', title='Year'),
            xOffset='year:N',
            opacity=alt.condition(year_selection, alt.value(1), alt.value(0.2)),
            tooltip=['year', 'meter_name', 'day_name', 'total_usage_kwh']
        ).add_params(
            year_selection
        ).properties(
            width=500,
            height=200,
        )

        chart = base_chart.facet(
            row=alt.Row('meter_name:N', title='Meter')
        )

        st.altair_chart(chart, use_container_width=True)

# Run the app
if __name__ == '__main__':
    app()
