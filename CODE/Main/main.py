import mpu
import numpy as np
from sklearn.cluster import DBSCAN
from LoadData.load_data import load_data
from Map.map import get_map


def main(nrows=None):
    file_name = '12.11.2015'
    # Пока что берем данные для одного дня, если брать больше - DBSCAN работает крайне долго
    df = load_data(f'{file_name}.xlsx', 'marine.xlsx', create_new_clean_xlsx=False)
    min_lat = df['lat'].min()
    min_lon = df['lon'].min()
    max_lat = df['lat'].max()
    max_lon = df['lon'].max()
    if nrows:
        df = df.head(nrows)

    # Хромая на обе ноги демонстрация DBSCAN, параметры не подобраны, метрика уже кастомная, веса почти наугад...

    def custom_dist(a, b, w1, w2, w3):
        # Считаем дистанцию в километрах
        # При таком варианте реализации метрики картина заметно улучшается
        # w1 - расстояние, w2 - скорость, w3 - курс
        # dist = (np.sqrt(w1 * (a[0] - b[0]) ** 2 + w2 * (a[1] - b[1]) ** 2 +
        #                 w3 * (a[2] - b[2]) ** 2 + w4 * (a[3] - b[3]) ** 2))
        euclidean_dist = mpu.haversine_distance((a[1], a[0]), (b[1], b[0]))
        dist = (w1 * euclidean_dist ** 2 + w2 * (a[2] - b[2]) ** 2 + w3 * (a[3] - b[3]) ** 2) ** 0.25
        return dist

    # w1 - расстояние, w2 - скорость, w3 - курс
    # расстояние * w1, скорость * w2, курс * w3 = 100 при дефолтном значении (до умножения)
    # для разницы в курсе = 12, скорости = 50, расстоянии = 0.5
    clusters = DBSCAN(eps=8.888, min_samples=16, metric=custom_dist,
                      metric_params={'w1': 400 * 2, 'w2': 0.004 * 4, 'w3': 0.7 * 32}).fit_predict(df)
    # clusters = DBSCAN(eps=11.5, min_samples=23, metric=custom_dist,
    #                   metric_params={'w1': 1.2, 'w2': 1.2, 'w3': 1.2, 'w4': 1.2}).fit_predict(df)

    df['cluster'] = clusters
    print('Всего кластеров:', max(df['cluster']) + 1)

    get_map(min_lat, min_lon, max_lat, max_lon, 11, df, f'{file_name}.png', create_new_clean_map=False)


if __name__ == "__main__":
    main()
