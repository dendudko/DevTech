import os.path

import pandas as pd

pd.set_option('display.max_rows', None, 'display.max_columns', None)


# state_on_date - файл с данными за день, marine - файл с данными о судах
# clean_{state_on_date} - подготовленный файл с данными за день
def load_data(state_on_date, marine, nrows=None, create_new=False):
    if os.path.exists('../DB/clean_' + state_on_date) and not create_new:
        df = pd.read_excel('../DB/clean_' + state_on_date, nrows=nrows)
        return df
    else:
        df = pd.read_excel('../DB/' + state_on_date, nrows=nrows)
        df_marine = pd.read_excel('../DB/' + marine)
        df = process_data(df, df_marine, state_on_date)
        return df


def process_data(df, df_marine, name):
    df = df.drop(columns={'id_track', 'age', 'date_add'})
    df = df.drop_duplicates()
    df = pd.merge(df, df_marine[['id_marine', 'port', 'length']], how='left', on='id_marine').dropna(axis=0)
    df = df.loc[(df['course'] != 511) & (df['port'] != 0) & (df['length'] != 0)].reset_index(drop=True)
    df = df[['lat', 'lon', 'speed', 'course']]
    df.to_excel(f'../DB/clean_{name}', index=False)
    return df


# print(load_data('11.11.2015.xlsx', 'marine.xlsx', nrows=None, create_new=True))
