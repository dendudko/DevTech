from flask import Flask, render_template, request, jsonify
import time
from Main.main import *
from PIL import Image
import os

def compress_image(image_path, output_folder, quality):
    # Открываем изображение для сжатия
    with Image.open(image_path) as img:
        # Сжимаем изображение с помощью Pillow
        img.save(os.path.join(output_folder, os.path.basename(image_path)),
                 optimize=True,
                 quality=quality)

app = Flask(__name__)


@app.route('/get_graphs_parameters', methods=['POST'])
def get_graphs_parameters():
    parameters_for_graph = request.get_json()

    # вызвать функцию построения графа
    start_long,start_lat = get_coordinates(parameters_for_graph['start_coords'])
    end_long,end_lat = get_coordinates(parameters_for_graph['end_coords'])
    coords = dict(start_lat=start_lat,start_long=start_long,end_lat=end_lat,end_long=end_long)
    del parameters_for_graph['start_coords']
    del parameters_for_graph['end_coords']
    for key in parameters_for_graph:
        parameters_for_graph[key] = float(parameters_for_graph[key])
    for key in coords:
        coords[key] = float(coords[key])

    grapg_data = call_find_path(parameters_for_graph, coords)
    # compress_image(grapg_data[0], 'static\\logs', 0)
    return jsonify(grapg_data)

def get_coordinates(coords):
    lat, long = coords.split(',')
    return lat, long

@app.route('/get_DBSCAN_parameters', methods=['POST'])
def get_DBSCAN_parameters():
    parameters_for_DBSCAN = request.get_json()
    # вызвать функцию кластеризации
    for key in parameters_for_DBSCAN:
        parameters_for_DBSCAN[key] = float(parameters_for_DBSCAN[key])

    clusters_data = call_clustering(parameters_for_DBSCAN)
    print(clusters_data)
    return jsonify(clusters_data)


@app.route('/')
def index():
    clustering_params = load_clustering_params()
    graph_params = load_graph_params()

    return render_template('index.html',
                           clustering_params=clustering_params,
                           graph_params=graph_params,
                           int=int,
                           len=len
                           )

if __name__ == '__main__':
    app.run(debug=True)
