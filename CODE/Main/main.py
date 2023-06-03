from sklearn.cluster import DBSCAN
from sklearn.preprocessing import StandardScaler
from sklearn.utils import parallel_backend
from LoadData.load_data import load_data
from Map.map import MapBuilder
import pickle


def clustering(clustering_params, file_name='all_merged', create_new_empty_map=False):
    weight_distance = clustering_params['weight_distance']
    weight_speed = clustering_params['weight_speed']
    weight_course = clustering_params['weight_course']
    eps = clustering_params['eps']
    min_samples = clustering_params['min_samples']

    df = load_data(f'{file_name}.xlsx', 'marine.xlsx', create_new_clean_xlsx=False)
    min_lat = df['lat'].min()
    min_lon = df['lon'].min()
    max_lat = df['lat'].max()
    max_lon = df['lon'].max()

    # Нормализуем данные, значительно увеличивает вычислительную эффективность
    scaler = StandardScaler()
    X = scaler.fit_transform(df)
    # Распараллеливаем вычисления
    with parallel_backend('loky', n_jobs=-1):
        # Нашел более правильную реализацию метрики, вроде работает получше и побыстрее
        clusters = DBSCAN(eps=eps, min_samples=min_samples, metric='minkowski', p=2,
                          metric_params={'w': [weight_distance, weight_distance,
                                               weight_speed, weight_course]}).fit_predict(X)

    df['cluster'] = clusters

    map_builder = MapBuilder(west=min_lat, south=min_lon, east=max_lat, north=max_lon, zoom=12, df=df,
                             file_name=f'{file_name}', create_new_empty_map=create_new_empty_map)
    clustered_images = map_builder.create_clustered_map()

    # Обнуляем несериализуемые pickle поля
    map_builder.map_image = None
    map_builder.context = None
    # Сохраняем дамп объекта map_builder
    with open('./Main/map_builder_dump.pickle', 'wb') as dump_file:
        pickle.dump(map_builder, dump_file, protocol=pickle.HIGHEST_PROTOCOL)

    return clustered_images


def call_clustering(clustering_params={}):
    # clustering_params = {'weight_distance': 2, 'weight_speed': 1, 'weight_course': 20, 'eps': 0.29, 'min_samples': 50}
    # pickle отлично решает задачу сериализации объекта MapBuilder
    try:
        with open('./Main/map_builder_dump.pickle', 'rb') as load_file:
            map_builder_loaded = pickle.load(load_file)
            if map_builder_loaded.clustering_params == clustering_params:
                return map_builder_loaded.create_clustered_map()
            else:
                map_builder_loaded.clustering_params = clustering_params
                clustering(clustering_params)

    except FileNotFoundError or EOFError:
        clustering(clustering_params)
        with open('map_builder_dump.pickle', 'rb') as load_file:
            map_builder_loaded = pickle.load(load_file)
            map_builder_loaded.clustering_params = clustering_params

            # Обнуляем несериализуемые pickle поля
            map_builder_loaded.map_image = None
            map_builder_loaded.context = None
            # Сохраняем дамп объекта map_builder
        with open('./Main/map_builder_dump.pickle', 'wb') as dump_file:
            pickle.dump(map_builder_loaded, dump_file, protocol=pickle.HIGHEST_PROTOCOL)


def call_find_path(graph_params={}, coords={}):
    # graph_params = {'distance_delta': 120, 'angle_of_vision': 30, 'weight_time_graph': 1, 'weight_course_graph': 0.01
    try:
        with open('./Main/map_builder_dump.pickle', 'rb') as load_file:
            map_builder_loaded = pickle.load(load_file)

            if len(map_builder_loaded.graph_params.keys()) == 0:
                map_builder_loaded.graph_params = graph_params
                graph_img = map_builder_loaded.find_path(coords['start_long'], coords['start_lat'], coords['end_long'], coords['end_lat'], create_new_graph=True)
            elif map_builder_loaded.graph_params == graph_params:
                graph_img = map_builder_loaded.find_path(coords['start_long'], coords['start_lat'], coords['end_long'], coords['end_lat'], create_new_graph=False)
            elif map_builder_loaded.graph_params['distance_delta'] == graph_params['distance_delta'] and \
                    map_builder_loaded.graph_params['angle_of_vision'] == graph_params['angle_of_vision'] and \
                    (map_builder_loaded.graph_params['weight_time_graph'] != graph_params['weight_time_graph'] or
                     map_builder_loaded.graph_params['weight_course_graph'] != graph_params['weight_course_graph']):
                map_builder_loaded.graph_params = graph_params
                map_builder_loaded.recalculate_edges()
                graph_img = map_builder_loaded.find_path(coords['start_long'], coords['start_lat'], coords['end_long'], coords['end_lat'], create_new_graph=False)
            else:
                map_builder_loaded.graph_params = graph_params
                graph_img = map_builder_loaded.find_path(coords['start_long'], coords['start_lat'], coords['end_long'], coords['end_lat'], create_new_graph=True)

            print(map_builder_loaded.graph)

    except FileNotFoundError or EOFError:
        clustering_params = {'weight_distance': 2, 'weight_speed': 1, 'weight_course': 20, 'eps': 0.29,
                             'min_samples': 50}
        clustering(clustering_params)
        with open('./Main/map_builder_dump.pickle', 'rb') as load_file:
            map_builder_loaded = pickle.load(load_file)
            map_builder_loaded.clustering_params = clustering_params

            map_builder_loaded.graph_params = graph_params
            graph_img = map_builder_loaded.find_path(coords['start_long'], coords['start_lat'], coords['end_long'], coords['end_lat'], create_new_graph=True)

            print(map_builder_loaded.graph)

    # Обнуляем несериализуемые pickle поля
    map_builder_loaded.map_image = None
    map_builder_loaded.context = None
    # Сохраняем дамп объекта map_builder
    with open('./Main/map_builder_dump.pickle', 'wb') as dump_file:
        pickle.dump(map_builder_loaded, dump_file, protocol=pickle.HIGHEST_PROTOCOL)
    print(graph_img)
    return graph_img

def load_graph_params():
    try:
        with open('./Main/map_builder_dump.pickle', 'rb') as load_file:
            map_builder_loaded = pickle.load(load_file)
            graph_params = map_builder_loaded.graph_params
            if len(graph_params) == 0:
                graph_params = {'distance_delta': 120, 'angle_of_vision': 30, 'weight_time_graph': 1,
                                'weight_course_graph': 0.01}
    except FileNotFoundError or EOFError:
        graph_params = {'distance_delta': 120, 'angle_of_vision': 30, 'weight_time_graph': 1,
                        'weight_course_graph': 0.01}
    return graph_params

def load_clustering_params():
    try:
        with open('./Main/map_builder_dump.pickle', 'rb') as load_file:
            map_builder_loaded = pickle.load(load_file)
            clustering_params = map_builder_loaded.clustering_params
            if len(clustering_params) == 0:
                clustering_params = {'weight_distance': 2, 'weight_speed': 1, 'weight_course': 20, 'eps': 0.29,
                                     'min_samples': 50}
    except FileNotFoundError or EOFError:
        clustering_params = {'weight_distance': 2, 'weight_speed': 1, 'weight_course': 20, 'eps': 0.29,
                             'min_samples': 50}
    return clustering_params

