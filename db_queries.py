def get_query_monthly_kwh_and_charge_event(schema_name):
  """
  Query to get the total kWh and charging events per month for each meter.
  """
  # SQL query to get monthly kWh and charging events
  # This query aggregates data by year, month, and meter name
  # It counts distinct days with usage > 0 for charging events
  # and sums the total usage in kWh
  return f"""
        SELECT
        date_trunc('month', end_date_time) AS month,
        EXTRACT(YEAR FROM end_date_time) AS year_no,
        EXTRACT(MONTH FROM end_date_time) AS month_no,
        meter_name,
        COUNT(DISTINCT EXTRACT(DAY FROM end_date_time)) FILTER (WHERE total_usage_kwh > 0) AS charging_events,
        SUM(total_usage_kwh) AS total_usage_kwh
    FROM {schema_name}.fact_meter_readings
    GROUP BY
        month,
        EXTRACT(YEAR FROM end_date_time),
        EXTRACT(MONTH FROM end_date_time),
        meter_name
    ORDER BY  
        year_no, 
        month_no,
        meter_name;
    """

def get_query_daily_kwh(schema_name):
  """
  Query to get the daily kWh usage for each meter.
  """
  # SQL query to get daily kWh usage
  # This query aggregates data by year, month, day, and meter name
  # It sums the total usage in kWh for each day
  # and extracts the day name and day of the week
  # query = f"""
    #         SELECT
    #             EXTRACT(YEAR FROM end_date_time) AS year,
    #             meter_name,
    #             SUM(total_usage_kwh) AS total_usage_kwh,
    #             strftime(end_date_time, '%A') AS day_name
    #         FROM {st.secrets.datasource.schema_name}.fact_meter_readings
    #         GROUP BY EXTRACT(YEAR FROM end_date_time),
    #                  strftime(end_date_time, '%A'),
    #                  EXTRACT(DOW FROM end_date_time),
    #                  meter_name 
    #         ORDER BY year, meter_name ASC;
    #         """
  return f"""
      SELECT
          strftime(end_date_time, '%Y') AS year,
          strftime(end_date_time, '%A') AS day_name,
          meter_name,
          SUM(total_usage_kwh) AS total_usage_kwh
      FROM {schema_name}.fact_meter_readings
      WHERE total_usage_kwh > 0
      GROUP BY 
          year,
          day_name,
          meter_name
      ORDER BY 
          meter_name, 
          year;
    """