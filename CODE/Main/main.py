from sklearn.cluster import DBSCAN
import numpy as np
from Map.map import get_map
from LoadData.load_data import load_data
import mpu


def main(nrows=None):
    file_name = '11.11.2015'
    # Пока что берем данные для одного дня, если брать больше - DBSCAN работает крайне долго
    df = load_data(f'{file_name}.xlsx', 'marine.xlsx', create_new_clean_xlsx=False)
    min_lat = df['lat'].min()
    min_lon = df['lon'].min()
    max_lat = df['lat'].max()
    max_lon = df['lon'].max()
    if nrows:
        df = df.head(nrows)

    # Хромая на обе ноги демонстрация DBSCAN, параметры не подобраны, метрика уже кастомная, веса наугад
    # dist_list = []

    def custom_dist(a, b, w1, w2, w3, w4):
        # Считаем дистанцию в километрах
        # При таком варианте реализации метрики картина заметно улучшается
        # Вес w1 сейчас отвечает за расстояние между судами, w2 лишний
        euclidean_dist = round(mpu.haversine_distance((a[1], a[0]), (b[1], b[0])), 3)
        # dist = (np.sqrt(w1 * (a[0] - b[0]) ** 2 + w2 * (a[1] - b[1]) ** 2 +
        #                 w3 * (a[2] - b[2]) ** 2 + w4 * (a[3] - b[3]) ** 2))
        dist = np.sqrt(w1 * euclidean_dist ** 2 + w2 * 0 +
                       w3 * (a[2] - b[2]) ** 2 + w4 * (a[3] - b[3]) ** 2)
        # dist_list.append(dist)
        return dist

    clusters = DBSCAN(eps=11.5, min_samples=23, metric=custom_dist,
                      metric_params={'w1': 1.2, 'w2': 1.2, 'w3': 1, 'w4': 1.2}).fit_predict(df)
    df['cluster'] = clusters
    print('Всего кластеров:', max(df['cluster']) + 1)

    get_map(min_lat, min_lon, max_lat, max_lon, 11, df, f'{file_name}.png', create_new_clean_map=False)


if __name__ == "__main__":
    main()
