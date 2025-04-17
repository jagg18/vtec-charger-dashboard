from datetime import date
import duckdb
import pandas as pd

import db_queries as db
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

def generate_tooltip(dict_tooltips):
    """
    Generate tooltip for Altair chart.
    """
    if dict_tooltips is None:
        return []
    return [
        alt.Tooltip(f'{key}:T', title=val) if val is date else
        alt.Tooltip(f'{key}:B', title=val) if isinstance(val, bool) else
        alt.Tooltip(f'{key}:Q', title=val) if isinstance(val, (int, float)) else
        alt.Tooltip(f'{key}:N', title=val)
        for key, val in dict_tooltips.items()
    ]

def render_chart(data, label_x, label_y, legend, title, date_range, custom_colors, dict_tooltips=None):
    # st.dataframe(data, use_container_width=True)
    st.markdown(
            f"""
            ### {title}
            <hr style='border:1px solid {st.get_option('theme.primaryColor')}; margin-top: -0.5em; margin-bottom: 1em;'>

            - **Click on the legend** to toggle meter names on and off.
            - **Click and drag on the timeline chart** below to zoom into a specific date range.
            - **Hover over the lines** on the chart to view exact usage values and details.
            - **Click the button on the top right corner of the table** to download the data as a CSV file.
            """,
            unsafe_allow_html=True
        )

    interval = alt.selection_interval(encodings=['x'], value={'x': date_range})
    selection = alt.selection_point(fields=[legend], bind='legend')
    highlight = alt.selection_point(
        on="pointerover", fields=[label_x], nearest=True, clear="pointerout"
    )

    # Generate tooltip based on the provided dictionary
    if dict_tooltips:
        tooltip = generate_tooltip(dict_tooltips)
    else:
        tooltip = [
            alt.Tooltip(f'{label_x}:T', title=f'{label_x}', format='%b %Y'),
            alt.Tooltip(f'{legend}:N', title=f'{legend}'),
            alt.Tooltip(f'{label_y}:Q', title=f'{label_y}')
        ]

    # Create a base chart
    base = alt.Chart(data).mark_line().encode(
        x=alt.X(f'{label_x}:T', axis=alt.Axis(format='%b %Y')),
        y=alt.Y(f'{label_y}:Q'),
        color=alt.Color(f'{legend}:N', scale=alt.Scale(range=custom_colors)),
        opacity=alt.condition(selection, alt.value(1), alt.value(0.2)),
        tooltip=tooltip
    ).properties(
        width=600,
        height=200
    ).add_params(selection)

    # Create a chart for showing the selected interval
    upper = base.encode(
        alt.X(f'{label_x}:T', axis=alt.Axis(format='%b %Y')).scale(domain=interval), # show the selected interval
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

def get_df_monthly_summary():
    query = db.get_query_monthly_kwh_and_charge_event(st.secrets.datasource.schema_name)
    return get_df_from_db(query)

def get_daily_data():
    query = db.get_query_daily_kwh(st.secrets.datasource.schema_name)
    return get_df_from_db(query)

def get_pivot_monthly_summary(df):
    # Pivot the DataFrame to show meters as columns
    pivot_df = df.pivot_table(
        index=['year_no','month_no'],
        columns='meter_name',
        values=['charging_events','total_usage_kwh'],
        aggfunc='sum',
    ).fillna(0)
    
    return pivot_df

def render_df_monthly_summary(df):
    display_df = df.copy()
    display_df.rename(
        columns={col: f"{col} (kWh)" for col in display_df.columns[1:]},
        inplace=True
    )

    # Rename the last index if it's a string like "Total"
    if isinstance(display_df.index[-1], str):
        display_df.index = [
            f"{i} (kWh)" if i == display_df.index[-1] else i
            for i in display_df.index
        ]

    st.dataframe(display_df, use_container_width=True)

def get_totals(df):
    # Calculate the totals for each meter
    totals = df.sum(axis=0).to_frame().T
    totals.index = [('Total', '')]
    # Append the totals to the original DataFrame
    df = pd.concat([df, totals], ignore_index=False)
    df.index = df.index.map(lambda idx: tuple(str(i) for i in idx))
    # df.index = df.index.set_levels(df.index.levels[1].astype(str), level=0)

    # Calculate the totals for each column
    cols = df.columns.get_level_values(1).unique().to_list()
    totals_row = []
    for col in cols:
        total = df.xs(col, axis=1, level=1).sum(axis=1)
        totals_row.append(total)

    df_totals_row = pd.DataFrame(totals_row).T
    df_totals_row.columns = ['Charging Events', 'Total Usage (kWh)']

    # Convert to MultiIndex columns with 'Total' as the top level
    df_totals_row.columns = pd.MultiIndex.from_product([['Total'], df_totals_row.columns])

    # Concatenate to the original DataFrame
    df = pd.concat([df, df_totals_row], axis=1)
    return df

def render_metrics_all_time(df):
    df.index = df.index.set_levels(
        ['Charging Events', 'Total Usage (kWh)'],
        level=1
    )
    # st.dataframe(df, use_container_width=True)
    # Extract the meter names from the columns
    index_l0 = df.index.levels[0]
    # Extract metric names from the columns
    index_l1 = df.index.levels[1]

    for i in range(len(index_l1)):
        st.markdown(
            f"""
            ##### {index_l1[i]}
            """,
            unsafe_allow_html=True
        )


        cols = st.columns(len(index_l0))
        for j, col in enumerate(cols):
            col.metric(
                label=index_l0[j],
                value=(
                    # HACK Format the value based on the metric type
                    f"{int(df[index_l0[j]].loc[index_l1[i]])}" if index_l1[i] == 'Charging Events' else
                    f"{df[index_l0[j]].loc[index_l1[i]]:.2f}"
                    ),
                delta=None, delta_color="normal", label_visibility="visible", border=True)

def app():
    
    custom_colors = [
        '#00A4B6',
        '#DF2048',
        '#81ACBB',
        '#F8962F',
        '#BE4127',
        '#86BB7D',
        '#EBD11C',
    ]
    
    st.write("Fetching data from the database...")
    
    # Fetch data
    df_base = get_df_monthly_summary()
    # st.dataframe(df_base, use_container_width=True)
    df_daily = get_daily_data()

    start_date = None
    end_date = None

    # Display data in the app
    if not df_base.empty:
        st.write("Data fetched successfully!")

        st.title("VTEC Charger Data Dashboard")
        st.markdown(
            f"""
            ### Dashboard Overview
            <hr style='border:1px solid {st.get_option('theme.primaryColor')}; margin-top: -0.5em; margin-bottom: 1em;'>

            """,
            unsafe_allow_html=True
        )
        
        st.markdown(
        """
        This dashboard visualizes the usage trends of VTEC chargers over time. Data is aggregated monthly by meter and presented through interactive charts.

        Use the sidebar to filter by month and explore:

        - **Total usage per meter**
        - **Daily usage patterns** for each meter
        - **Monthly comparisons** across meters

        Gain insights into when and how VTEC chargers are being used most effectively.
        """)

        with st.sidebar:
            st.subheader("Filter by Date")
            st.markdown(
                """
                Use the date filters to select a range of months for analysis.
                """
            )
            # --- Date filter component ---
            start_date = st.date_input(
                "Select start date",
                value=df_base['month'].min(),
            )

            # --- Date filter component ---
            end_date = st.date_input(
                "Select end date",
                value=(date.today()),
            )

            # Check if a valid range was selected
            if start_date > end_date:
                st.warning("Please select a valid start and end date.")

        # Check if a valid range was selected
        if start_date <= end_date:
            filtered_df = df_base[(df_base['month'] >= start_date) & (df_base['month'] <= end_date)]
        else:
            filtered_df = df_base

        st.markdown(
            f"""
            ### All-Time Usage
            <hr style='border:1px solid {st.get_option('theme.primaryColor')}; margin-top: -0.5em; margin-bottom: 1em;'>
            """,
            unsafe_allow_html=True
        )
        # Pivot the DataFrame to show meters as columns
        df_pivot_monthly_summary = get_pivot_monthly_summary(filtered_df)

        # Reorder MultiIndex to: meter_name (level 0), metric (level 1)
        df_pivot_monthly_summary.columns = df_pivot_monthly_summary.columns.swaplevel(0, 1)
        df_pivot_monthly_summary = df_pivot_monthly_summary.sort_index(axis=1, level=0)
        # st.dataframe(df_pivot_monthly_summary, use_container_width=True)

        
        # Display all-time metrics
        df_totals_condensed = df_pivot_monthly_summary.sum()
        df_totals_condensed = df_totals_condensed.round(2)
        # st.subheader("All-Time Usage Totals")
        # st.dataframe(df_totals, use_container_width=True)
        render_metrics_all_time(df_totals_condensed)

        # Get date range from today - 11 months
        date_range = (date.today(), date.today())

        df_timestamp = filtered_df.copy()
        df_timestamp['month'] = pd.to_datetime(
            df_timestamp['year_no'].astype(str) + '-' +
            df_timestamp['month_no'].astype(str)
        ).dt.strftime('%b %Y')
        
        render_chart(
            data=df_timestamp,
            label_x='month',
            label_y='total_usage_kwh',
            legend='meter_name',
            title='Monthly Total Usage per Meter',
            date_range=date_range,
            custom_colors=custom_colors,
        )

        # Get totals
        df_totals = get_totals(df_pivot_monthly_summary)
        # Display the monthly summary table
        render_df_monthly_summary(df_totals)

        # Fetch weekly data
    

    if not df_daily.empty:
        # st.write(start_date, end_date)
        # st.dataframe(df_daily, use_container_width=True)

        # Check if a valid range was selected
        if start_date <= end_date:
            filtered_df = df_daily[
                (df_daily['year'].astype(int) >= start_date.year) & 
                (df_daily['year'].astype(int) <= end_date.year)
            ]
        else:
            filtered_df = df_daily


        # Define your custom order
        day_order = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
        # Set day_name as categorical with the custom order
        df_daily['day_name'] = pd.Categorical(df_daily['day_name'], categories=day_order, ordered=True)

        # Create legend selection for year
        year_selection = alt.selection_point(fields=['year'], bind='legend')

        st.markdown(
            f"""
            ### Meter Usage by Day of the Week
            <hr style='border:1px solid {st.get_option('theme.primaryColor')}; margin-top: -0.5em; margin-bottom: 1em;'>

            This chart shows the total usage of each meter by day of the week.
            - **Click on the legend** to toggle year selection.
            - **Hover over the bars** to view exact usage values and details.
            - Click the button on the top right corner of the chart to download an image.
            """,
            unsafe_allow_html=True
        )

        # Create grouped bar chart
        base_chart = alt.Chart(filtered_df).mark_bar().encode(
            x=alt.X('day_name:N', title='Day of the Week', sort=day_order),
            y=alt.Y('total_usage_kwh:Q', title='Total Usage (kWh)'),
            color=alt.Color('year:N', title='Year', scale=alt.Scale(range=custom_colors)),
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
    else:
        st.warning("No data available.")

# Run the app
if __name__ == '__main__':
    app()
