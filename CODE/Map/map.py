import io
import urllib.request
import random

import pandas
from cairo import ImageSurface, FORMAT_ARGB32, Context
import math
import mercantile
import matplotlib.colors as mcolors
import shapely
import numpy as np


def get_map(west, south, east, north, zoom, df, name, create_new_clean_map=False):
    if create_new_clean_map:
        tiles = list(mercantile.tiles(west, south, east, north, zoom))

        min_x = min([t.x for t in tiles])
        min_y = min([t.y for t in tiles])
        max_x = max([t.x for t in tiles])
        max_y = max([t.y for t in tiles])

        tile_size = (256, 256)
        # создаем пустое изображение в которое как мозайку будем вставлять тайлы
        map_image = ImageSurface(
            FORMAT_ARGB32,
            tile_size[0] * (max_x - min_x + 1),
            tile_size[1] * (max_y - min_y + 1)
        )

        ctx = Context(map_image)

        headers = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64)'
                                 'AppleWebKit/537.11 (KHTML, like Gecko)'
                                 'Chrome/23.0.1271.64 Safari/537.11',
                   'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                   'Accept-Charset': 'ISO-8859-1,utf-8;q=0.7,*;q=0.3',
                   'Accept-Encoding': 'none',
                   'Accept-Language': 'en-US,en;q=0.8',
                   'Connection': 'keep-alive'}

        for t in tiles:
            server = random.choice(['a', 'b', 'c'])  # у OSM три сервера, распределяем нагрузку
            url = 'http://{server}.tile.openstreetmap.org/{zoom}/{x}/{y}.png'.format(
                server=server,
                zoom=t.z,
                x=t.x,
                y=t.y
            )
            # print(url)
            request = urllib.request.Request(url=url, headers=headers)
            response = urllib.request.urlopen(request)

            img = ImageSurface.create_from_png(io.BytesIO(response.read()))

            ctx.set_source_surface(
                img,
                (t.x - min_x) * tile_size[0],
                (t.y - min_y) * tile_size[0]
            )
            ctx.paint()

        # расчитываем коэффициенты
        bounds = {
            "left": min([mercantile.xy_bounds(t).left for t in tiles]),
            "right": max([mercantile.xy_bounds(t).right for t in tiles]),
            "bottom": min([mercantile.xy_bounds(t).bottom for t in tiles]),
            "top": max([mercantile.xy_bounds(t).top for t in tiles]),
        }

        # коэффициенты скалирования по оси x и y
        kx = map_image.get_width() / (bounds['right'] - bounds['left'])
        ky = map_image.get_height() / (bounds['top'] - bounds['bottom'])

        # пересчитываем размеры по которым будем обрезать
        left_top = mercantile.xy(west, north)
        right_bottom = mercantile.xy(east, south)
        offset_left = (left_top[0] - bounds['left']) * kx
        offset_top = (bounds['top'] - left_top[1]) * ky
        offset_right = (bounds['right'] - right_bottom[0]) * kx
        offset_bottom = (right_bottom[1] - bounds['bottom']) * ky

        # обрезанное изображение
        map_image_clipped = ImageSurface(
            FORMAT_ARGB32,
            map_image.get_width() - int(offset_left + offset_right),
            map_image.get_height() - int(offset_top + offset_bottom),
        )

        # вставляем кусок исходного изображения
        ctx = Context(map_image_clipped)
        ctx.set_source_surface(map_image, -offset_left, -offset_top)
        ctx.paint()

        map_image = map_image_clipped
    else:
        map_image = ImageSurface.create_from_png(f'../Map/{name}')

    # рассчитываем координаты углов в веб-меркаоторе
    left_top = tuple(mercantile.xy(west, north))
    right_bottom = tuple(mercantile.xy(east, south))

    # расчитываем коэффициенты
    kx = map_image.get_width() / (right_bottom[0] - left_top[0])
    ky = map_image.get_height() / (right_bottom[1] - left_top[1])

    # сохраняем результат
    if create_new_clean_map:
        with open(f'../Map/{name}', 'wb') as f:
            map_image.write_to_png(f)

    map_paint(map_image, df, left_top, kx, ky, name)


def map_paint(map_image, df, left_top, kx, ky, name):
    # тут создаем rgba массив цветов из CSS4, меняем [-1] элемент, чтобы шум был заданного нами цвета
    # ВРЕМЕННОЕ РЕШЕНИЕ, С ЦВЕТАМИ НАДО ЧТО-ТО ПРИДУМАТЬ
    colors = list(mcolors.CSS4_COLORS.keys())
    # Шум
    colors[-1] = 'black'
    # colors[-1] = 'red'
    colors[7] = 'yellowgreen'
    colors = mcolors.to_rgba_array(colors)

    context = Context(map_image)
    df1 = pandas.DataFrame(columns=['x', 'y', 'cluster'])
    color_costyl = 3
    for i, row in df.iterrows():
        # gps в web-mercator
        x, y = mercantile.xy(row['lat'], row['lon'])
        # переводим x, y в координаты изображения
        x = (x - left_top[0]) * kx
        y = (y - left_top[1]) * ky
        r = 0
        if 'cluster' in df.columns:
            if int(row['cluster']) == -1:
                red = colors[-1][0]
                green = colors[-1][1]
                blue = colors[-1][2]
                alpha = 0.6
                r = 3
            else:
                red = colors[int(row['cluster']) * color_costyl][0]
                green = colors[int(row['cluster']) * color_costyl][1]
                blue = colors[int(row['cluster']) * color_costyl][2]
                alpha = 1
                r = 4
        else:
            red, green, blue, alpha = 1, 0, 0, 1
        context.arc(x, y, r, 0 * math.pi / 180, 360 * math.pi / 180)
        context.set_source_rgba(red, green, blue, alpha)
        # if 'cluster' not in df.columns or row['cluster'] != -1:
        #     context.fill()
        context.fill()
        # Добавляем расчитанную точку в новый датафрейм
        df1.loc[df1.shape[0]] = [x, y, row['cluster']]

    # Создаем и добавляем полигоны
    polygons = []
    polygon_bounds = []
    if 'cluster' in df.columns:
        for i in range(int(max(df['cluster'])) + 1):
            polygons.append(df1.where(df1['cluster'] == i).dropna(how='any'))
            polygon_geom = shapely.Polygon(zip(polygons[i]['x'].values.tolist(), polygons[i]['y'].values.tolist()))
            polygon_geom2 = shapely.geometry.LinearRing(polygon_geom.exterior.coords).convex_hull
            # Проверка класса polygon_geom2, без этого код может падать из-за Linestring вместо Polygon
            if isinstance(polygon_geom2, shapely.Polygon):
                a, b = polygon_geom2.exterior.coords.xy
                polygon_bounds.append(tuple(list(zip(a, b))))
                red = colors[i * color_costyl][0]
                green = colors[i * color_costyl][1]
                blue = colors[i * color_costyl][2]
                alpha = 0.4
                context.set_source_rgba(red, green, blue, alpha)
                # Берем последний элемент массива из-за рассинхронизации со счетчиком i
                for dot in polygon_bounds[-1]:
                    context.line_to(dot[0], dot[1])
                context.fill()

    # Ищем пересечения полигонов
    intersections = []
    intersection_bounds = []
    for i in range(len(polygon_bounds)):
        for j in range(i + 1, len(polygon_bounds)):
            if shapely.intersects(shapely.Polygon(polygon_bounds[i]), shapely.Polygon(polygon_bounds[j])):
                intersections.append(shapely.intersection(shapely.Polygon(polygon_bounds[i]),
                                                          shapely.Polygon(polygon_bounds[j])))
    for i in range(len(intersections)):
        # Проверка, является ли i-ое intersection непустым (экземпляром класса Polygon)
        if isinstance(intersections[i], shapely.Polygon):
            a, b = intersections[i].exterior.coords.xy
            intersection_bounds.append(tuple(list(zip(a, b))))
    for i in range(len(intersection_bounds)):
        red = 0
        green = 0
        blue = 0
        alpha = 0.3
        context.set_source_rgba(red, green, blue, alpha)
        for dot in intersection_bounds[i]:
            context.line_to(dot[0], dot[1])
        context.fill()

    # Накидываем точки на границу пересечения полигонов
    # Пока что не сохраняю, для какого пересечения и каких кластеров получены точки
    points = []
    for i in range(len(intersection_bounds)):
        distance_delta = 5
        distances = np.arange(0, shapely.LineString(intersection_bounds[i]).length, distance_delta)
        points.append([shapely.LineString(intersection_bounds[i]).interpolate(distance) for distance in distances])
        for dot in points[-1]:
            context.arc(dot.x, dot.y, 2, 0 * math.pi / 180, 360 * math.pi / 180)
            context.set_source_rgba(255, 0, 0, 1)
            context.fill()

    with open(f'../Map/clustered_{name}', 'wb') as f:
        map_image.write_to_png(f)
