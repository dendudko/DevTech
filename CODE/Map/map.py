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


def get_colors():
    # тут создаем rgba массив цветов из CSS4 и перемешиваем
    # ВРЕМЕННОЕ РЕШЕНИЕ, С ЦВЕТАМИ НАДО ЧТО-ТО ПРИДУМАТЬ
    # Удаляю черный
    css4_colors = list(mcolors.CSS4_COLORS.keys())
    random.shuffle(css4_colors)
    css4_colors.remove('black')
    css4_colors = mcolors.to_rgba_array(css4_colors)
    return css4_colors


colors = get_colors()


class MapBuilder:
    def __init__(self, west, south, east, north, zoom, df, file_name, create_new_empty_map=False, save_count=-1):
        # Задаваемые параметры
        self.west = west
        self.south = south
        self.east = east
        self.north = north
        self.zoom = zoom
        self.df = df
        self.file_name = file_name
        self.create_new_empty_map = create_new_empty_map
        self.save_count = save_count

        # Местные поля
        self.map_image = None
        self.left_top = None
        self.kx = None
        self.ky = None
        self.context = None

        self.df_points_on_image = pandas.DataFrame()
        self.polygons = []
        self.polygon_bounds = []
        self.intersections = {}
        self.intersection_bounds = {}
        self.intersection_bounds_points = {}

    def delete_noise(self):
        # Удаление шума, спорное решение
        self.df = self.df.loc[(self.df['cluster'] != -1)].dropna(axis=0).reset_index(drop=True)

    def calculate_points_on_image(self):
        self.df_points_on_image = pandas.DataFrame(columns=['x', 'y', 'speed', 'course', 'cluster'])

        # Добавляем объекты с пересчитанными координатами в df_points_on_image
        # gps в web-mercator
        xy = [mercantile.xy(x, y) for x, y in zip(self.df.lat, self.df.lon)]
        # переводим x, y в координаты изображения
        self.df_points_on_image.x = [(row[0] - self.left_top[0]) * self.kx for row in xy]
        self.df_points_on_image.y = [(row[1] - self.left_top[1]) * self.ky for row in xy]
        self.df_points_on_image.speed = self.df.speed
        self.df_points_on_image.course = self.df.course
        self.df_points_on_image.cluster = self.df.cluster

    def show_points(self, frac=1.0):
        # Снижаю количество отображаемых точек (надо бы найти какой-то нормальный алгоритм)
        for row in self.df_points_on_image.sample(frac=frac).itertuples(index=False):
            if int(row[4]) == -1:
                red = 0
                green = 0
                blue = 0
                alpha = 0.25
                r = 2
            else:
                red = colors[int(row[4])][0]
                green = colors[int(row[4])][1]
                blue = colors[int(row[4])][2]
                alpha = 1
                r = 2
            self.context.arc(row[0], row[1], r, 0 * math.pi / 180, 360 * math.pi / 180)
            self.context.set_source_rgba(red, green, blue, alpha)
            self.context.fill()

            # Рисуем линии, отображающие направление, стрелки перегружают картинку, будут просто линии)
            self.context.set_line_width(1.5)
            self.context.move_to(row[0], row[1])
            # Не уверен в какую сторону должно быть направление (+90 / -90), надо уточнить
            angle = math.radians(row[3] + 90)
            self.context.line_to(row[0] + row[2] / 10 * math.cos(angle), row[1] + row[2] / 10 * math.sin(angle))
            self.context.stroke()

    def show_polygons(self):
        # Создаем и добавляем полигоны
        if 'cluster' in self.df_points_on_image.columns:
            for i in range(int(max(self.df_points_on_image['cluster'])) + 1):
                self.polygons.append(
                    self.df_points_on_image.where(self.df_points_on_image['cluster'] == i).dropna(how='any'))
                polygon_geom = shapely.Polygon(
                    zip(self.polygons[i]['x'].values.tolist(), self.polygons[i]['y'].values.tolist()))
                polygon_geom2 = shapely.geometry.LinearRing(polygon_geom.exterior.coords).convex_hull
                # Проверка класса polygon_geom2, без этого код может падать из-за Linestring вместо Polygon
                if isinstance(polygon_geom2, shapely.Polygon):
                    a, b = polygon_geom2.exterior.coords.xy
                    self.polygon_bounds.append(tuple(list(zip(a, b))))
                    red = colors[i][0]
                    green = colors[i][1]
                    blue = colors[i][2]
                    alpha = 0.25
                    self.context.set_source_rgba(red, green, blue, alpha)
                    # Берем последний элемент массива из-за рассинхронизации со счетчиком i
                    for dot in self.polygon_bounds[-1]:
                        self.context.line_to(dot[0], dot[1])
                    self.context.fill_preserve()

                    # Дополнительно выделяю границу полигона
                    self.context.set_line_width(1.5)
                    self.context.set_source_rgba(red, green, blue, 1)
                    self.context.stroke()

    def show_intersections(self):
        # Ищем и отображаем пересечения полигонов
        self.intersections = {}
        self.intersection_bounds = {}
        for i in range(len(self.polygon_bounds)):
            for j in range(i + 1, len(self.polygon_bounds)):
                if shapely.intersects(shapely.Polygon(self.polygon_bounds[i]), shapely.Polygon(self.polygon_bounds[j])):
                    self.intersections[i, j] = (shapely.intersection(shapely.Polygon(self.polygon_bounds[i]),
                                                                     shapely.Polygon(self.polygon_bounds[j])))
        for key, intersection in self.intersections.items():
            # Проверка, является ли i-ое intersection непустым (экземпляром класса Polygon)
            if isinstance(intersection, shapely.Polygon):
                a, b = intersection.exterior.coords.xy
                self.intersection_bounds[key] = (tuple(list(zip(a, b))))
        for key, intersection_bound in self.intersection_bounds.items():
            red = 0
            green = 0
            blue = 0
            alpha = 0.1
            self.context.set_source_rgba(red, green, blue, alpha)
            for dot in intersection_bound:
                self.context.line_to(dot[0], dot[1])
            self.context.fill()

    def show_intersection_bounds_points(self):
        # Накидываем точки на границу пересечения полигонов
        self.intersection_bounds_points = {}
        for key, intersection_bound in self.intersection_bounds.items():
            # Расстояние между точками границы пересечения
            distance_delta = 5
            distances = np.arange(0, shapely.LineString(intersection_bound).length, distance_delta)
            self.intersection_bounds_points[key] = (
                [shapely.LineString(intersection_bound).interpolate(distance) for distance in distances])
            for dot in self.intersection_bounds_points[key]:
                self.context.arc(dot.x, dot.y, 2, 0 * math.pi / 180, 360 * math.pi / 180)
                self.context.set_source_rgba(255, 0, 0, 1)
                self.context.fill()

    def save_clustered_image(self):
        if self.save_count != -1:
            file_name = self.file_name + '_' + str(self.save_count)
            with open(f'../images/clustered/clustered_{file_name}.png', 'wb') as f:
                self.map_image.write_to_png(f)
        else:
            with open(f'../images/clustered/clustered_{self.file_name}.png', 'wb') as f:
                self.map_image.write_to_png(f)
        f.close()

    # Возможно стоит убрать мелкие кластеры...
    def create_clustered_map(self):
        self.create_empty_map()
        # Удаляю шум, не уверен, стоит ли
        self.delete_noise()
        self.calculate_points_on_image()
        self.show_polygons()
        self.show_intersections()
        self.show_intersection_bounds_points()
        # frac - можно выбрать, какую долю объектов нанести на карту
        self.show_points(frac=0.2)
        self.save_clustered_image()
        # self.save_count = 0
        # self.show_points()
        # self.save_clustered_image()

    def create_empty_map(self):
        if self.create_new_empty_map:
            tiles = list(mercantile.tiles(self.west, self.south, self.east, self.north, self.zoom))

            min_x = min([t.x for t in tiles])
            min_y = min([t.y for t in tiles])
            max_x = max([t.x for t in tiles])
            max_y = max([t.y for t in tiles])

            tile_size = (256, 256)
            # создаем пустое изображение в которое как мозайку будем вставлять тайлы
            self.map_image = ImageSurface(
                FORMAT_ARGB32,
                tile_size[0] * (max_x - min_x + 1),
                tile_size[1] * (max_y - min_y + 1)
            )

            ctx = Context(self.map_image)

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
            self.kx = self.map_image.get_width() / (bounds['right'] - bounds['left'])
            self.ky = self.map_image.get_height() / (bounds['top'] - bounds['bottom'])

            # пересчитываем размеры по которым будем обрезать
            self.left_top = mercantile.xy(self.west, self.north)
            right_bottom = mercantile.xy(self.east, self.south)
            offset_left = (self.left_top[0] - bounds['left']) * self.kx
            offset_top = (bounds['top'] - self.left_top[1]) * self.ky
            offset_right = (bounds['right'] - right_bottom[0]) * self.kx
            offset_bottom = (right_bottom[1] - bounds['bottom']) * self.ky

            # обрезанное изображение
            map_image_clipped = ImageSurface(
                FORMAT_ARGB32,
                self.map_image.get_width() - int(offset_left + offset_right),
                self.map_image.get_height() - int(offset_top + offset_bottom),
            )

            # вставляем кусок исходного изображения
            ctx = Context(map_image_clipped)
            ctx.set_source_surface(self.map_image, -offset_left, -offset_top)
            ctx.paint()

            self.map_image = map_image_clipped
        else:
            self.map_image = ImageSurface.create_from_png(f'../images/clean/{self.file_name}.png')

        # рассчитываем координаты углов в веб-меркаоторе
        self.left_top = tuple(mercantile.xy(self.west, self.north))
        right_bottom = tuple(mercantile.xy(self.east, self.south))

        # расчитываем коэффициенты
        self.kx = self.map_image.get_width() / (right_bottom[0] - self.left_top[0])
        self.ky = self.map_image.get_height() / (right_bottom[1] - self.left_top[1])

        # сохраняем результат
        if self.create_new_empty_map:
            with open(f'../images/clean/{self.file_name}.png', 'wb') as f:
                self.map_image.write_to_png(f)
                f.close()

        self.context = Context(self.map_image)
