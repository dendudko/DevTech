from flask import Flask, render_template, request, jsonify
import time
from Main.main import call_find_path,call_clustering
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
    print(parameters_for_graph, coords)
    call_find_path(parameters_for_graph, coords)


    return jsonify("/static/img/graph.png")

def get_coordinates(coords):
    lat, long = coords.split(',')
    return lat, long

@app.route('/get_DBSCAN_parameters', methods=['POST'])
def get_DBSCAN_parameters():
    parameters_for_DBSCAN = request.get_json()
    # вызвать функцию кластеризации
    print(parameters_for_DBSCAN)
    call_clustering(parameters_for_DBSCAN)

    return jsonify(parameters_for_DBSCAN)


@app.route('/')
def index():
    clustering_params = {'weight_distance': 2, 'weight_speed': 1, 'weight_course': 20, 'eps': 0.29, 'min_samples': 50}
    graph_params = {'distance_delta': 50, 'angle_of_vision': 15, 'weight_time_graph': 1, 'weight_course_graph': 3}

    return render_template('index.html',
                           clustering_params=clustering_params,
                           graph_params=graph_params,
                           int=int,
                           len=len
                           )

if __name__ == '__main__':
    app.run(debug=True)
