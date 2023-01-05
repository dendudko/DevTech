import folium
import math
import shapely
from ImageProcessing.image_processing import create_screenshot
from LoadData.load_data import load_data
from sklearn.cluster import DBSCAN
import numpy as np
import matplotlib.colors as mcolors

# Бесполезно рисовать стрелки, если хотим карту, как изображение
def arrow_points_calculate(_map, ini_lat, ini_long, heading):
    length_scale = 0.03
    sides_scale = 0.015
    sides_angle = 15

    latA = ini_lat
    longA = ini_long

    latB = length_scale * math.cos(math.radians(heading)) + latA
    longB = length_scale * math.sin(math.radians(heading)) + longA

    latC = sides_scale * math.cos(math.radians(heading + 180 - sides_angle)) + latB
    longC = sides_scale * math.sin(math.radians(heading + 180 - sides_angle)) + longB

    latD = sides_scale * math.cos(math.radians(heading + 180 + sides_angle)) + latB
    longD = sides_scale * math.sin(math.radians(heading + 180 + sides_angle)) + longB

    pointA = (latA, longA)
    pointB = (latB, longB)
    pointC = (latC, longC)
    pointD = (latD, longD)

    arrow_points = [pointA, pointB, pointC, pointD, pointB]
    folium.PolyLine(locations=arrow_points, color="purple", fill=True, fill_color="purple",
                    weight=0.3, fill_opacity=1).add_to(_map)


def main(nrows=None):
    df = load_data('11.11.2015.xlsx', 'marine.xlsx', nrows=nrows, create_new=False)
    df = df[['lon', 'lat']]
    max_lon = df['lon'].max()
    max_lat = df['lat'].max()
    min_lon = df['lon'].min()
    min_lat = df['lat'].min()

    aqua_map = folium.Map(
        zoom_control=False
    )
    aqua_map.fit_bounds([[min_lon, min_lat], [max_lon, max_lat]])

    # Полигоны для вида
    polygon_geom = shapely.Polygon(zip(df['lat'].values.tolist(), df['lon'].values.tolist()))
    polygon_geom2 = shapely.geometry.LinearRing(polygon_geom.exterior.coords).convex_hull
    folium.GeoJson(polygon_geom2,
                   style_function=lambda x: {'fillColor': 'blue', 'weight': 2, 'opacity': 0.5}
                   ).add_to(aqua_map)

    # Popup с координатами
    folium.LatLngPopup().add_to(aqua_map)

    # Хромая на обе ноги демонстрация DBSCAN
    # db = DBSCAN(eps=2/6371, min_samples=10, algorithm='ball_tree', metric='haversine').fit_predict(np.radians(df))
    # df['cluster'] = db
    # print(max(df['cluster']))
    # colors = list(mcolors.CSS4_COLORS.keys())
    # print(colors)
    # colors[-1] = 'black'
    # colors[7] = 'yellowgreen'

    for i, row in df.iterrows():
        folium.CircleMarker(
            location=(row['lon'], row['lat']),
            radius=0.1,
            weight=1,
            color = 'red',
            # color=colors[int(row['cluster'])],
            fill=True
        ).add_to(aqua_map)
        # arrow_points_calculate(aqua_map, row['lon'], row['lat'], row['course'])
        # print(i)

    aqua_map.save('../App/index.html')
    create_screenshot()


if __name__ == "__main__":
    main()
