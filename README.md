# VTEC Charger Dashboard

A Streamlit dashboard for exploring VTEC charger usage data stored in MotherDuck. The app summarizes charger activity by meter, month, year, and day of week using interactive Altair charts and downloadable Streamlit data tables.

## Features

- Monthly total usage by meter in kWh
- Charging event totals by meter
- Date range filtering from the Streamlit sidebar
- Interactive Altair line chart with legend filtering, hover tooltips, and timeline zooming
- Day-of-week usage chart faceted by meter and grouped by year
- Monthly summary table with per-meter totals and overall totals

## Tech Stack

- [Streamlit](https://streamlit.io/) for the web app
- [DuckDB](https://duckdb.org/) with [MotherDuck](https://motherduck.com/) for database access
- [pandas](https://pandas.pydata.org/) for data shaping
- [Altair](https://altair-viz.github.io/) for interactive charts

## Repository Structure

```text
.
├── streamlit_app.py     # Streamlit app entry point
├── db_queries.py        # SQL query helpers
├── requirements.txt     # Python dependencies
└── README.md
```

## Data Source

The dashboard expects a MotherDuck database with a schema containing a `fact_meter_readings` table.

The app queries these columns:

| Column | Purpose |
| --- | --- |
| `end_date_time` | Timestamp used for monthly, yearly, and weekday grouping |
| `meter_name` | Charger or meter name shown in charts and summaries |
| `total_usage_kwh` | Usage value aggregated by the dashboard |

## Local Setup

1. Clone the repository:

```bash
git clone https://github.com/jagg18/vtec-charger-dashboard.git
cd vtec-charger-dashboard
```

2. Create and activate a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate
```

On Windows PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Add Streamlit secrets.

Create `.streamlit/secrets.toml` in the project root:

```toml
[datasource]
db_name = "your_motherduck_database_name"
token = "your_motherduck_token"
schema_name = "your_schema_name"
```

Use `schema_name = "main"` if your MotherDuck tables live in the default schema.

Do not commit `.streamlit/secrets.toml`. It should stay local because it contains a private MotherDuck token.

5. Run the app:

```bash
streamlit run streamlit_app.py
```

## Streamlit Community Cloud Deployment

When deploying to Streamlit Community Cloud, add the same secrets in the app's **Settings > Secrets** panel:

```toml
[datasource]
db_name = "your_motherduck_database_name"
token = "your_motherduck_token"
schema_name = "your_schema_name"
```

The app entry point is:

```text
streamlit_app.py
```

## MotherDuck Token

Create or copy your MotherDuck access token from your MotherDuck account settings. The app uses it in this DuckDB connection string:

```python
duckdb.connect(f"md:{st.secrets.datasource.db_name}?motherduck_token={st.secrets.datasource.token}")
```

## Notes

- The dashboard filters monthly data by the selected start and end dates.
- Daily usage is filtered by year based on the selected date range.
- The charts rely on `total_usage_kwh > 0` for charging activity in the daily usage query.
