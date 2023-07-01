import os.path
import pandas as pd


# pd.set_option('display.max_rows', None, 'display.max_columns', None)

# data_file_name - название файла с данными за день
# marine_file_name - название файла с данными о судах
# clean_{file_name} - подготовленный файл с данными за день
def load_data(data_file_name, marine_file_name, create_new_clean_xlsx=False):
    if os.path.exists('./db/clean/clean_' + data_file_name) and not create_new_clean_xlsx:
        df = pd.read_excel('./db/clean/clean_' + data_file_name)
        return df
    else:
        df = pd.read_excel('./db/dirty/' + data_file_name)
        df_marine = pd.read_excel('./db/dirty/' + marine_file_name)
        df = process_data(df, df_marine, data_file_name)
        return df


def process_data(df_data, df_marine, data_file_name):
    try:
        df_data = df_data[['id_marine', 'lat', 'lon', 'speed', 'course']]
        df_data = pd.merge(df_data, df_marine[['id_marine', 'port', 'length']], how='left', on='id_marine').dropna(
            axis=0)
        df_data = df_data.loc[(df_data['course'] != 511) & (df_data['port'] != 0) & (df_data['length'] != 0)]. \
            reset_index(drop=True)
        df_data = df_data[['lat', 'lon', 'speed', 'course']]
    except KeyError:
        pass
    df_data = df_data.drop_duplicates().dropna(axis=0)
    df_data.to_excel(f'./db/clean/clean_{data_file_name}', index=False)
    return df_data
