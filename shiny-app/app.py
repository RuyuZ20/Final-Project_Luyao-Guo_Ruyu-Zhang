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
        avg_housing_burden=('Housing_Burden', 'mean'),
        total_elderly_population=('AGE', 'count'),
        avg_income=('INCTOT', 'mean')
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
    ui.input_radio_buttons(
        id="view_mode",
        label="View Mode",
        choices={
            "us_plot": "US Plot",
            "state_plot": "State Plot",
        },
        selected="us_plot"
    ),
    ui.input_select(
        id="state",
        label="Select State (for State Plot)",
        choices={int(row.STATEFP): str(row.NAME) for _, row in merged_gdf.iterrows()},
        selected=int(merged_gdf.iloc[0]["STATEFP"])
    ),
    ui.output_image("dynamic_plot"),
    ui.output_text("state_info")
)

# Shiny app server
def server(input, output, session):
    @output
    @render.image
    def dynamic_plot():
        metric = input.metric()
        metric_label = {
            "avg_housing_burden": "Average Housing Burden (%)",
            "total_elderly_population": "Total Elderly Population",
            "avg_income": "Average Income ($)"
        }[metric]

        if input.view_mode() == "us_plot":
            # Create the US-wide Plotly map
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
        else:
            # Create the state-specific Plotly map
            selected_state_fp = input.state()
            state_data = cleaned_data[cleaned_data['STATEFIP'] == int(selected_state_fp)]

            fig = px.histogram(
                state_data,
                x="Housing_Burden",
                nbins=20,
                title=f"Housing Burden Distribution in {merged_gdf.loc[merged_gdf['STATEFP'] == int(selected_state_fp), 'NAME'].values[0]}",
                labels={"Housing_Burden": "Housing Burden (%)"}
            )
            fig.update_layout(xaxis_title="Housing Burden (%)", yaxis_title="Count")

        # Save the plot to a temporary file
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as temp:
            fig.write_image(temp.name)
            return {"src": temp.name, "alt": metric_label}

    @output
    @render.text
    def state_info():
        if input.view_mode() == "state_plot":
            selected_state_fp = input.state()
            state_data = cleaned_data[cleaned_data['STATEFIP'] == int(selected_state_fp)]

            avg_burden = state_data["Housing_Burden"].mean()
            total_population = len(state_data)
            avg_income = state_data["INCTOT"].mean()

            state_name = merged_gdf.loc[merged_gdf["STATEFP"] == int(selected_state_fp), "NAME"].values[0]
            return (
                f"State: {state_name}\n"
                f"Average Housing Burden: {avg_burden:.2f}%\n"
                f"Total Elderly Population: {total_population}\n"
                f"Average Income: ${avg_income:.2f}"
            )
        return "Select a state to see details."

# Shiny app initialization
app = App(app_ui, server)
