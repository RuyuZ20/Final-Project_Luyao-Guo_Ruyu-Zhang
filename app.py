from shiny import App, ui, render, reactive
import geopandas as gpd
import matplotlib.pyplot as plt

# Load and prepare your data
base_path = "/Users/apple/Desktop/class/Dap-2/problem_sets/final_project/Untitled/Final-Project_Luyao-Guo_Ruyu-Zhang"
shapefile_path = f"{base_path}/tl_2023_us_state.shp"

# Ensure merged_gdf is properly created
try:
    gdf_states = gpd.read_file(shapefile_path)
    # Example preprocessing: replace this with actual data creation logic
    gdf_states["STATEFP"] = gdf_states["STATEFP"].astype(int)
    merged_gdf = gdf_states[["STATEFP", "geometry"]].copy()
    merged_gdf["avg_housing_burden"] = 15  # Dummy data
    merged_gdf["total_elderly_population"] = 1000  # Dummy data
except Exception as e:
    print(f"Error loading data: {e}")
    merged_gdf = None

# Define the Shiny app UI
app_ui = ui.page_fluid(
    ui.h2("Interactive Housing Burden Map"),
    ui.input_select(
        id="filter",
        label="Filter by:",
        choices=["avg_housing_burden", "total_elderly_population"],  # Column names from merged_gdf
    ),
    ui.output_plot("map")
)

# Define the server logic
def server(input, output, session):
    # Reactive data filtering
    @reactive.Calc
    def filtered_data():
        # Use the global merged_gdf
        global merged_gdf
        if merged_gdf is None:
            raise ValueError("Data is not loaded.")
        filter_column = input.filter()
        gdf = merged_gdf.copy()  # Work with a copy
        gdf["display_value"] = gdf[filter_column]
        return gdf

    # Render the interactive map
    @output
    @render.plot
    def map():
        data = filtered_data()  # Get filtered data
        fig, ax = plt.subplots(1, 1, figsize=(12, 8))
        data.plot(
            column="display_value",
            ax=ax,
            cmap="OrRd",
            edgecolor="0.8",
            legend=True,
            legend_kwds={
                "label": f"{input.filter()} by State",
                "orientation": "vertical",
            },
        )
        ax.set_axis_off()
        plt.title(f"Map of {input.filter()} by State", fontsize=15)
        return fig

# Create the Shiny app
app = App(app_ui, server)
