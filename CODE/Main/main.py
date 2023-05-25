import mpu
from sklearn.cluster import DBSCAN
from sklearn.preprocessing import StandardScaler
from sklearn.utils import parallel_backend
from LoadData.load_data import load_data
from Map.map import MapBuilder
import pickle


def custom_dist(a, b, w1, w2, w3):
    # Считаем дистанцию в километрах
    # При таком варианте реализации метрики картина заметно улучшается
    # (на самом деле нет, надо лучше подбирать параметры и веса)
    # w1 - расстояние, w2 - скорость, w3 - курс
    # dist = (np.sqrt(w1 * (a[0] - b[0]) ** 2 + w2 * (a[1] - b[1]) ** 2 +
    #                 w3 * (a[2] - b[2]) ** 2 + w4 * (a[3] - b[3]) ** 2))
    euclidean_dist = mpu.haversine_distance((a[1], a[0]), (b[1], b[0]))
    dist = (w1 * euclidean_dist ** 2 + w2 * (a[2] - b[2]) ** 2 + w3 * (a[3] - b[3]) ** 2) ** 0.5
    return dist


def main(file_name='all_merged', eps=0.3, min_samples=50, nrows=None, create_new_empty_map=False, save_count=-1):
    df = load_data(f'{file_name}.xlsx', 'marine.xlsx', create_new_clean_xlsx=False)
    min_lat = df['lat'].min()
    min_lon = df['lon'].min()
    max_lat = df['lat'].max()
    max_lon = df['lon'].max()
    if nrows:
        df = df.head(nrows)

    # Хромая на обе ноги демонстрация DBSCAN, параметры не подобраны, веса почти наугад...

    # Нормализуем данные, значительно увеличивает вычислительную эффективность
    scaler = StandardScaler()
    X = scaler.fit_transform(df)
    # Распараллеливаем вычисления
    with parallel_backend('loky', n_jobs=-1):
        # Нашел более правильную реализацию метрики, вроде работает получше и побыстрее
        clusters = DBSCAN(eps=eps, min_samples=min_samples, metric='minkowski', p=2,
                          metric_params={'w': [2, 2, 1, 20]}).fit_predict(X)
        # clusters = DBSCAN(eps=eps, min_samples=min_samples, metric=custom_dist,
        #                   metric_params={'w1': 5000, 'w2': 0.033, 'w3': 0.083}).fit_predict(df)

    df['cluster'] = clusters

    main_log = 'Номер эксперимента: ' + str(save_count) + '\n'
    main_log += 'eps = ' + str(eps) + '\n'
    main_log += 'min_samples = ' + str(min_samples) + '\n'
    main_log += 'Всего кластеров: ' + str(max(df['cluster']) + 1) + '\n'
    main_log += 'Доля шума: ' + str(df['cluster'].value_counts()[-1]) + ' / ' + str(len(df)) + '\n'

    map_builder = MapBuilder(west=min_lat, south=min_lon, east=max_lat, north=max_lon, zoom=12, df=df,
                             file_name=f'{file_name}', create_new_empty_map=create_new_empty_map,
                             save_count=save_count)
    map_builder.create_clustered_map()

    # Обнуляем несериализуемые pickle поля
    map_builder.map_image = None
    map_builder.context = None
    # Сохраняем дамп объекта map_builder
    with open('map_builder_dump.pickle', 'wb') as dump_file:
        pickle.dump(map_builder, dump_file, protocol=pickle.HIGHEST_PROTOCOL)

    return main_log


def run_all():
    log_for_file = ''
    # for i in range(7):
    #     for j in range(5):
    #         exp_eps = round(0.27 + i * 0.005, 3)
    #         exp_min_samples = 40 + j * 5
    #         # exp_eps = 0.27 + random() * 0.08
    #         # exp_min_samples = 40 + round(random() * 80)
    #         log = main(file_name='all_merged', eps=exp_eps, min_samples=exp_min_samples, nrows=None,
    #                    save_count=int(str(i) + str(j)))
    #         log_for_file += log + '\n'
    #         print(log)

    log = main(file_name='all_merged', eps=0.29, min_samples=50, nrows=None)
    log_for_file += log
    print(log)

    # with open('log.txt', 'w', encoding='utf-16') as f:
    #     f.write(log_for_file)
    #     f.close()


if __name__ == "__main__":
    # run_all()

    # pickle отлично решает задачу сериализации объекта MapBuilder
    with open('map_builder_dump.pickle', 'rb') as load_file:
        map_builder_loaded = pickle.load(load_file)
        map_builder_loaded.create_clustered_map()

    # Обнуляем несериализуемые pickle поля
    map_builder_loaded.map_image = None
    map_builder_loaded.context = None
    # Сохраняем дамп объекта map_builder
    with open('map_builder_dump.pickle', 'wb') as dump_file:
        pickle.dump(map_builder_loaded, dump_file, protocol=pickle.HIGHEST_PROTOCOL)

