from shiny import App, ui, render
import pandas as pd
import geopandas as gpd
import plotly.express as px
import tempfile

# Paths for input files
csv_path = "/Users/apple/Desktop/class/Dap-2/problem_sets/final_project/Untitled/Final-Project_Luyao-Guo_Ruyu-Zhang/shiny-app/cleaned_data.csv"
shapefile_path = "/Users/apple/Desktop/class/Dap-2/problem_sets/final_project/Untitled/Final-Project_Luyao-Guo_Ruyu-Zhang/shiny-app/tl_2023_us_state.shp"

# Load cleaned data
def load_cleaned_data(csv_path):
    cleaned_data = pd.read_csv(csv_path)

    # Ensure necessary columns exist
    if 'Housing_Burden' not in cleaned_data.columns:
        cleaned_data['Housing_Burden'] = (cleaned_data['RENTGRS'] / cleaned_data['INCTOT']) * 100
        cleaned_data['Housing_Burden'].replace([float('inf'), -float('inf')], 0, inplace=True)
        cleaned_data['Housing_Burden'].fillna(0, inplace=True)

    # Fill missing values for relevant columns
    cleaned_data['INCTOT'].fillna(0, inplace=True)
    cleaned_data['AGE'].fillna(0, inplace=True)

    return cleaned_data

# GeoDataFrame merging function
def merge_geodata(cleaned_data, shapefile_path):
    gdf_states = gpd.read_file(shapefile_path)
    gdf_states['STATEFP'] = gdf_states['STATEFP'].astype(int)

    # Explicit calculation of metrics at the state level
    state_summary_hb = cleaned_data.groupby('STATEFIP').agg(
        avg_housing_burden=('Housing_Burden', 'mean'),  # Average housing burden per state
        total_elderly_population=('AGE', 'count'),     # Total elderly population (count of AGE rows per state)
        avg_income=('INCTOT', 'mean')                 # Average income per state
    ).reset_index()

    # Rename for merging consistency
    state_summary_hb.rename(columns={'STATEFIP': 'STATEFP'}, inplace=True)

    # Merge with shapefile
    merged_gdf = gdf_states.merge(state_summary_hb, on='STATEFP', how='left')

    return merged_gdf

# Load and process data
cleaned_data = load_cleaned_data(csv_path)
merged_gdf = merge_geodata(cleaned_data, shapefile_path)

# Shiny app UI
app_ui = ui.page_fluid(
    ui.panel_title("Housing Burden Among Older Adults"),
    ui.input_select(
        id="metric",
        label="Select Metric",
        choices={
            "avg_housing_burden": "Average Housing Burden",
            "total_elderly_population": "Total Elderly Population",
            "avg_income": "Average Income",
        },
        selected="avg_housing_burden",
    ),
    ui.output_image("map_plot")
)

# Shiny app server
def server(input, output, session):
    @output
    @render.image
    def map_plot():
        metric = input.metric()
        metric_label = {
            "avg_housing_burden": "Average Housing Burden (%)",
            "total_elderly_population": "Total Elderly Population",
            "avg_income": "Average Income ($)"
        }[metric]

        # Create the Plotly map
        fig = px.choropleth(
            merged_gdf,
            geojson=merged_gdf.geometry,
            locations=merged_gdf.index,
            color=metric,
            color_continuous_scale="OrRd",
            labels={metric: metric_label},
            title=f"{metric_label} by State"
        )
        fig.update_geos(fitbounds="locations", visible=False)

        # Save the map to a temporary file and return the path
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as temp:
            fig.write_image(temp.name)
            return {"src": temp.name, "alt": metric_label}

# Shiny app initialization
app = App(app_ui, server)

