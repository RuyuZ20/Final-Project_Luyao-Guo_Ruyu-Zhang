from shiny import App, ui, render
import pandas as pd
import geopandas as gpd
import plotly.express as px
import tempfile
import os

# Paths for input files
base_path = '/Users/ruyuzhang/Desktop/PPHA 30538'
csv_path = os.path.join(base_path, "cleaned_data.csv")
shapefile_path = os.path.join(base_path, "tl_2023_us_state.shp")

# Load cleaned data
def load_cleaned_data(csv_path):
    cleaned_data = pd.read_csv(csv_path)
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
    
    # Input selectors at the top
    ui.row(
        ui.column(
            4,  
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
            )
        )
    ),
    
    ui.row(
        ui.column(
            6, 
            ui.output_image("dynamic_plot", height="600px")
        ),
        ui.column(
            6,  
            ui.tags.div(
                ui.output_text("state_info"),
                style="white-space: normal; max-width: 100%;"
            )
        )
    )
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
            fig.update_geos(
                fitbounds="geojson",
                visible=False,
                projection_scale=2.0  
            )
            fig.update_layout(
                height=800,  
                width=1000,  
                margin={"r": 0, "t": 0, "l": 0, "b": 0},  
                coloraxis_colorbar=dict(
                    title=metric_label,
                    ticks="outside"
                )
            )
        else:
            # Create the state-specific Plotly map
            selected_state_fp = input.state()
            state_data = cleaned_data[cleaned_data['STATEFIP'] == int(selected_state_fp)]

            # Debugging: Check for extreme or invalid values in Housing_Burden
            print("Descriptive statistics for Housing_Burden in selected state:")
            print(state_data['Housing_Burden'].describe())
            print("Rows with Housing_Burden > 100%:")
            print(state_data[state_data['Housing_Burden'] > 100])


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

            # Calculate statistics
            avg_burden = state_data["Housing_Burden"].mean()
            total_population = len(state_data)
            avg_income = state_data["INCTOT"].mean()
            max_burden = state_data["Housing_Burden"].max()
            min_burden = state_data["Housing_Burden"].min()

            state_name = merged_gdf.loc[merged_gdf["STATEFP"] == int(selected_state_fp), "NAME"].values[0]

            # Display statistics with line breaks
            return (
                f"State: {state_name}"
                f"Average Housing Burden: {avg_burden:.2f}%"
                f"Total Elderly Population: {total_population}"
                f"Average Income: ${avg_income:.2f}"
                f"Max Housing Burden: {max_burden:.2f}%"
                f"Min Housing Burden: {min_burden:.2f}%"
            )
        return 

# Shiny app initialization
app = App(app_ui, server)
