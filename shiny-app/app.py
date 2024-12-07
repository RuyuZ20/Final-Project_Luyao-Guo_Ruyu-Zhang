from shiny import App, ui, render
import pandas as pd
import geopandas as gpd
import plotly.express as px
import tempfile
import os

# Paths for input files
base_path = '/Users/apple/Desktop/class/Dap-2/problem_sets/final_project/Untitled/Final-Project_Luyao-Guo_Ruyu-Zhang'
csv_path = os.path.join(base_path, "cleaned_data.csv")
shapefile_path = os.path.join(base_path, "tl_2023_us_state.shp")

def load_cleaned_data(csv_path):
    cleaned_data = pd.read_csv(csv_path)
    return cleaned_data

def merge_geodata(cleaned_data, shapefile_path):
    gdf_states = gpd.read_file(shapefile_path)
    gdf_states['STATEFP'] = gdf_states['STATEFP'].astype(int)

    state_summary_hb = cleaned_data.groupby('STATEFIP').agg(
        avg_housing_burden=('Housing_Burden', 'mean'),
        total_elderly_population=('AGE', 'count'),
        avg_income=('INCTOT', 'mean')
    ).reset_index()

    state_summary_hb.rename(columns={'STATEFIP': 'STATEFP'}, inplace=True)
    merged_gdf = gdf_states.merge(state_summary_hb, on='STATEFP', how='left')

    return merged_gdf

cleaned_data = load_cleaned_data(csv_path)
merged_gdf = merge_geodata(cleaned_data, shapefile_path)

app_ui = ui.page_fluid(
    ui.panel_title("Housing Burden Among Older Adults"),
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
            ui.output_image("dynamic_plot")
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
            fig = px.choropleth(
                merged_gdf,
                geojson=merged_gdf.geometry,
                locations=merged_gdf.index,
                color=metric,
                color_continuous_scale="OrRd",
                labels={metric: metric_label},
                title=f"{metric_label} by State",
                scope='usa',
            )
            fig.update_geos(
                projection_type="albers usa",
                visible=False
            )
            fig.update_layout(
                title_x=0.5,
                margin={"r":20, "t":60, "l":20, "b":20},  
                width=800,
                height=600,
                coloraxis_colorbar=dict(
                    title=metric_label,
                    ticks="outside",
                    len=0.4,
                    y=0.5
                )
            )
        else:
            selected_state_fp = input.state()
            state_data = cleaned_data[cleaned_data['STATEFIP'] == int(selected_state_fp)]

            fig = px.histogram(
                state_data,
                x="Housing_Burden",
                nbins=20,
                title=f"Housing Burden Distribution in {merged_gdf.loc[merged_gdf['STATEFP'] == int(selected_state_fp), 'NAME'].values[0]}",
                labels={"Housing_Burden": "Housing Burden (%)"}
            )
            fig.update_layout(
                height=500,
                width=700,
                xaxis_title="Housing Burden (%)", 
                yaxis_title="Count"
            )

        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as temp:
            # 增加format='png'参数
            fig.write_image(temp.name, format='png')
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
            max_burden = state_data["Housing_Burden"].max()
            min_burden = state_data["Housing_Burden"].min()

            state_name = merged_gdf.loc[merged_gdf["STATEFP"] == int(selected_state_fp), "NAME"].values[0]

            return (
                f"State: {state_name}\n"
                f"Average Housing Burden: {avg_burden:.2f}%\n"
                f"Total Elderly Population: {total_population}\n"
                f"Average Income: ${avg_income:.2f}\n"
                f"Max Housing Burden: {max_burden:.2f}%\n"
                f"Min Housing Burden: {min_burden:.2f}%"
            )
        return ""

app = App(app_ui, server)




