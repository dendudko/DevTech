from sklearn.cluster import DBSCAN
import numpy as np
from Map.map import get_map
from LoadData.load_data import load_data
import matplotlib.pyplot as plt


def main(nrows=None):
    df = load_data('11.11.2015.xlsx', 'marine.xlsx', create_new=False)
    # df = df[['lon', 'lat']]
    min_lat = df['lat'].min()
    min_lon = df['lon'].min()
    max_lat = df['lat'].max()
    max_lon = df['lon'].max()
    if nrows:
        df = df.head(nrows)

    # Хромая на обе ноги демонстрация DBSCAN, параметры не подобраны, метрика уже кастомная, веса наугад
    # dist_list = []
    def custom_dist(a, b, w1, w2, w3, w4):
        dist = (np.sqrt(w1 * (a[0] - b[0]) ** 2 + w2 * (a[1] - b[1]) ** 2 +
                        w3 * (a[2] - b[2]) ** 2 + w4 * (a[3] - b[3]) ** 2))
        # dist_list.append(dist)
        return dist

    clustering = DBSCAN(eps=3.22, min_samples=30, metric=custom_dist,
                        metric_params={'w1': 1.2, 'w2': 1.2, 'w3': 1, 'w4': 1.5}).fit_predict(df)
    df['cluster'] = clustering
    print(max(df['cluster']))

    get_map(min_lat, min_lon, max_lat, max_lon, 11, df, create_new=False)

    # sum_5 = 0
    # dist_list_5 = []
    # for i in range(len(dist_list)):
    #     sum_5 += dist_list[i]
    #     if (i + 1) % 5 == 0:
    #         dist_list_5.append(sum_5 / 5)
    #         sum_5 = 0
    #
    # dist_list_5.sort()
    # plt.plot(dist_list_5)
    # plt.show()
    # ВЫШЕ В КОММЕНТАХ ПОПЫТКА СЧИТАТЬ 5 БЛИЖАЙШИХ СОСЕДЕЙ


if __name__ == "__main__":
    main()
