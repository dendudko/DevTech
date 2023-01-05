from sklearn.cluster import DBSCAN
import numpy as np
from Map.map import get_map
from LoadData.load_data import load_data


def main(nrows=None):
    df = load_data('11.11.2015.xlsx', 'marine.xlsx', create_new=False)
    df = df[['lon', 'lat']]
    min_lat = df['lat'].min()
    min_lon = df['lon'].min()
    max_lat = df['lat'].max()
    max_lon = df['lon'].max()
    if nrows:
        df = df.head(nrows)

    # Хромая на обе ноги демонстрация DBSCAN, параметры не подобраны, метрика евклидова
    clustering = DBSCAN(eps=0.0005, min_samples=50).fit_predict(np.radians(df))
    df['cluster'] = clustering
    # print(max(df['cluster']))

    get_map(min_lat, min_lon, max_lat, max_lon, 11, df, create_new=False)


if __name__ == "__main__":
    main()
