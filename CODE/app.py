from flask import Flask, render_template, request, jsonify
from Main.main import *

app = Flask(__name__)

@app.route('/get_graphs_parameters', methods=['POST'])
def get_graphs_parameters():
    parameters_for_graph = request.get_json()

    # вызвать функцию построения графа
    start_long, start_lat = get_coordinates(parameters_for_graph['start_coords'])
    end_long, end_lat = get_coordinates(parameters_for_graph['end_coords'])
    coords = dict(start_lat=start_lat, start_long=start_long, end_lat=end_lat, end_long=end_long)
    del parameters_for_graph['start_coords']
    del parameters_for_graph['end_coords']

    for i, key in enumerate(parameters_for_graph):
        parameters_for_graph[key] = float(parameters_for_graph[key])
        if i == len(parameters_for_graph) - 3:
            break

    for key in coords:
        coords[key] = float(coords[key])

    print(parameters_for_graph,coords)
    graph_data = call_find_path(parameters_for_graph, coords)
    return jsonify(graph_data)

def get_coordinates(coords):
    lat, long = coords.split(',')
    return lat, long

@app.route('/get_DBSCAN_parameters', methods=['POST'])
def get_DBSCAN_parameters():
    parameters_for_DBSCAN = request.get_json()
    print(parameters_for_DBSCAN)
    # вызвать функцию кластеризации

    for i, key in enumerate(parameters_for_DBSCAN):
        parameters_for_DBSCAN[key] = float(parameters_for_DBSCAN[key])
        if i == len(parameters_for_DBSCAN) - 2:
            break

    clusters_data = call_clustering(parameters_for_DBSCAN)
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
