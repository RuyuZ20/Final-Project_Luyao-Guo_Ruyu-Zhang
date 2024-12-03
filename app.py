from shiny import App, ui, render, reactive
import geopandas as gpd
import matplotlib.pyplot as plt
from sklearn.cluster import KMeans
import numpy as np

# Load the shapefile
base_path = "/Users/apple/Desktop/class/Dap-2/problem_sets/final_project/Untitled/Final-Project_Luyao-Guo_Ruyu-Zhang"
shapefile_path = f"{base_path}/tl_2023_us_state.shp"

# Ensure merged_gdf is properly created
try:
    gdf_states = gpd.read_file(shapefile_path)
    gdf_states["STATEFP"] = gdf_states["STATEFP"].astype(int)

    # Add dummy data (replace with your actual data)
    gdf_states["avg_housing_burden"] = np.random.uniform(5, 50, len(gdf_states))
    gdf_states["total_elderly_population"] = np.random.randint(500, 5000, len(gdf_states))
    gdf_states["avg_income"] = np.random.uniform(20000, 100000, len(gdf_states))
    merged_gdf = gdf_states.copy()
except Exception as e:
    print(f"Error loading data: {e}")
    merged_gdf = None

# Define the Shiny app UI
app_ui = ui.page_fluid(
    ui.h2("Interactive Housing Burden Map"),
    ui.input_select(
        id="filter",
        label="Filter by:",
        choices=["avg_housing_burden", "total_elderly_population", "avg_income"],
    ),
    ui.output_plot("map"),
    ui.output_plot("cluster_map")
)

# Define the server logic
def server(input, output, session):
    # Reactive data filtering
    @reactive.Calc
    def filtered_data():
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

    # Perform K-means clustering
    @reactive.Calc
    def clustered_data():
        global merged_gdf
        if merged_gdf is None:
            raise ValueError("Data is not loaded.")
        kmeans = KMeans(n_clusters=3, random_state=42)
        features = merged_gdf[["avg_housing_burden", "total_elderly_population", "avg_income"]]
        clusters = kmeans.fit_predict(features)
        gdf = merged_gdf.copy()
        gdf["cluster"] = clusters
        return gdf

    # Render the cluster map
    @output
    @render.plot
    def cluster_map():
        data = clustered_data()  # Get clustered data
        fig, ax = plt.subplots(1, 1, figsize=(12, 8))
        data.plot(
            column="cluster",
            ax=ax,
            cmap="viridis",
            edgecolor="0.8",
            legend=True,
            legend_kwds={
                "label": "Cluster Categories",
                "orientation": "vertical",
            },
        )
        ax.set_axis_off()
        plt.title("Clustered Map of Housing Burden", fontsize=15)
        return fig

# Create the Shiny app
app = App(app_ui, server)
