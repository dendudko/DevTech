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


# def get_colors():
#     # тут создаем rgba массив цветов из CSS4 и перемешиваем
#     # ВРЕМЕННОЕ РЕШЕНИЕ, С ЦВЕТАМИ НАДО ЧТО-ТО ПРИДУМАТЬ
#     # Удаляю черный
#     css4_colors = list(mcolors.CSS4_COLORS.keys())
#     random.shuffle(css4_colors)
#     css4_colors.remove('black')
#     print(css4_colors)
#     css4_colors = mcolors.to_rgba_array(css4_colors)
#     return css4_colors
#
#
# colors = get_colors()
# print(colors)

# ChatGPT выдал прекрасную генерацию цветов
def generate_colors(num_colors):
    colors = []

    # Golden ratio
    golden_ratio_conjugate = 0.618033988749895
    h = 0.0

    for i in range(num_colors):
        r, g, b = 0, 0, 0

        # HSL to RGB conversion
        h += golden_ratio_conjugate
        h %= 1

        hue = 360 * h
        saturation = 0.6
        lightness = 0.6

        c = (1 - abs(2 * lightness - 1)) * saturation
        x = c * (1 - abs((hue / 60) % 2 - 1))
        m = lightness - c / 2

        if hue < 60:
            r = c
            g = x
        elif hue < 120:
            r = x
            g = c
        elif hue < 180:
            g = c
            b = x
        elif hue < 240:
            g = x
            b = c
        elif hue < 300:
            r = x
            b = c
        else:
            r = c
            b = x

        r, g, b = r + m, g + m, b + m
        colors.append([r, g, b, 1])

    return colors


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

        self.df_points_on_image = pandas.DataFrame(columns=['x', 'y', 'speed', 'course', 'cluster'])
        self.polygons = {}
        self.polygon_bounds = {}
        self.intersections = {}
        self.intersection_bounds = {}
        self.intersection_points = {}
        self.average_directions = {}
        self.average_speeds = {}

        self.cluster_count = max(df['cluster']) + 1
        self.colors = generate_colors(self.cluster_count)

        self.visible_points = []
        self.visited_points = []
        self.routes_counter = 0

    def delete_noise(self):
        # Удаление шума, спорное решение
        self.df = self.df.loc[(self.df['cluster'] != -1)].dropna(axis=0).reset_index(drop=True)

    def calculate_points_on_image(self):
        if len(self.df_points_on_image) == 0:
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
                red = self.colors[int(row[4])][0]
                green = self.colors[int(row[4])][1]
                blue = self.colors[int(row[4])][2]
                alpha = 1
                r = 2
            self.context.arc(row[0], row[1], r, 0 * math.pi / 180, 360 * math.pi / 180)
            self.context.set_source_rgba(red, green, blue, alpha)
            self.context.fill()

            # Рисуем линии, отображающие направление, стрелки перегружают картинку, будут просто линии)
            self.context.set_line_width(1.5)
            self.context.move_to(row[0], row[1])
            # Курс отсчитывается по часовой стрелке от направления на север, движение правостороннее
            angle = math.radians(row[3] - 90)
            line_length = row[2] / 10
            self.context.line_to(row[0] + line_length * math.cos(angle), row[1] + line_length * math.sin(angle))
            self.context.stroke()

    def show_polygons(self):
        # Создаем и добавляем полигоны
        if len(self.polygons) == 0 or len(self.polygon_bounds) == 0:
            for i in range(self.cluster_count):
                self.polygons[i] = self.df_points_on_image.where(self.df_points_on_image['cluster'] == i).dropna(
                    how='any')
                polygon_geom = shapely.Polygon(
                    zip(self.polygons[i]['x'].values.tolist(), self.polygons[i]['y'].values.tolist()))
                # polygon_geom2 = shapely.convex_hull(polygon_geom)
                # TODO: Минимальная вогнутая оболочка - выглядит правдоподобнее
                polygon_geom2 = shapely.concave_hull(polygon_geom, ratio=0.5)
                # Проверка класса polygon_geom2, без этого код может падать из-за Linestring вместо Polygon
                if isinstance(polygon_geom2, shapely.Polygon):
                    a, b = polygon_geom2.exterior.coords.xy
                    self.polygon_bounds[i] = tuple(list(zip(a, b)))

        for key, polygon_bound in self.polygon_bounds.items():
            red = self.colors[key][0]
            green = self.colors[key][1]
            blue = self.colors[key][2]
            alpha = 0.25
            self.context.set_source_rgba(red, green, blue, alpha)
            for dot in polygon_bound:
                self.context.line_to(dot[0], dot[1])
            self.context.fill_preserve()
            # Дополнительно выделяю границу полигона
            self.context.set_line_width(1.5)
            self.context.set_source_rgba(red, green, blue, 1)
            self.context.stroke()

    def show_intersections(self):
        # Ищем и отображаем пересечения полигонов
        if len(self.intersections) == 0 or len(self.intersection_bounds) == 0:
            keys = list(self.polygon_bounds.keys())
            for i in range(len(keys)):
                key_i = keys[i]
                for j in range(i + 1, len(keys)):
                    key_j = keys[j]
                    if shapely.intersects(shapely.Polygon(self.polygon_bounds[key_i]),
                                          shapely.Polygon(self.polygon_bounds[key_j])):
                        self.intersections[key_i, key_j] = (
                            shapely.intersection(shapely.Polygon(self.polygon_bounds[key_i]),
                                                 shapely.Polygon(self.polygon_bounds[key_j])))

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

    def show_intersection_points(self):
        self.intersection_points = {}
        # Расстояние между точками границы пересечения
        distance_delta = 50
        # Если не добавляем точки внутрь пересечений
        # distance_delta = 5
        # Накидываем точки на границу пересечения полигонов
        if len(self.intersection_points) == 0:
            for key, intersection_bound in self.intersection_bounds.items():
                distances = np.arange(0, shapely.LineString(intersection_bound).length, distance_delta)
                self.intersection_points[key] = (
                    [shapely.LineString(intersection_bound).interpolate(distance) for distance in distances])

            # Добавляем точки внутрь полигонов
            for key in self.intersection_bounds.keys():
                x_min, y_min, x_max, y_max = self.intersections[key].bounds
                # min_num_points = 10
                # delta = min((x_max - x_min) / min_num_points, (y_max - y_min) / min_num_points)

                current_y = y_min - distance_delta
                calculated_points = []
                while current_y <= y_max:
                    current_y += distance_delta
                    current_x = x_min - distance_delta
                    while current_x <= x_max:
                        current_x += distance_delta
                        calculated_points.append(shapely.Point(current_x, current_y))
                # for i in range(100):
                #     calculated_points.append(shapely.Point(random.randint(int(x_min), int(x_max)), random.randint(int(y_min), int(y_max))))
                calculated_multi_point = shapely.MultiPoint(calculated_points)
                actual_multi_point = self.intersections[key].intersection(calculated_multi_point)
                if isinstance(actual_multi_point, shapely.MultiPoint):
                    actual_multi_point = actual_multi_point.geoms
                    self.intersection_points[key] += actual_multi_point

        for key, intersection_bound in self.intersection_bounds.items():
            for dot in self.intersection_points[key]:
                self.context.arc(dot.x, dot.y, 2, 0 * math.pi / 180, 360 * math.pi / 180)
                self.context.set_source_rgba(255, 0, 0, 1)
                self.context.fill()

    def show_average_directions(self):
        if len(self.average_directions) == 0 or len(self.average_speeds) == 0:
            for i in range(self.cluster_count):
                self.average_directions[i] = np.mean(self.df_points_on_image['course'].where(
                    self.df_points_on_image['cluster'] == i).dropna(how='any').values)
                self.average_speeds[i] = np.mean(self.df_points_on_image['speed'].where(
                    self.df_points_on_image['cluster'] == i).dropna(how='any').values)

        for key, polygon_bound in self.polygon_bounds.items():
            center = shapely.centroid(shapely.Polygon(polygon_bound))

            arrow_length = self.average_speeds[key]
            arrow_angle = math.radians(self.average_directions[key] - 90)
            arrowhead_angle = math.pi / 12
            arrowhead_length = 30

            self.context.move_to(center.x, center.y)  # move to center of polygon
            self.context.rel_move_to(-arrow_length * math.cos(arrow_angle) / 2,
                                     -arrow_length * math.sin(arrow_angle) / 2)
            self.context.rel_line_to(arrow_length * math.cos(arrow_angle), arrow_length * math.sin(arrow_angle))
            self.context.rel_move_to(-arrowhead_length * math.cos(arrow_angle - arrowhead_angle),
                                     -arrowhead_length * math.sin(arrow_angle - arrowhead_angle))
            self.context.rel_line_to(arrowhead_length * math.cos(arrow_angle - arrowhead_angle),
                                     arrowhead_length * math.sin(arrow_angle - arrowhead_angle))
            self.context.rel_line_to(-arrowhead_length * math.cos(arrow_angle + arrowhead_angle),
                                     -arrowhead_length * math.sin(arrow_angle + arrowhead_angle))

            red = self.colors[key][0]
            green = self.colors[key][1]
            blue = self.colors[key][2]
            self.context.set_source_rgba(red, green, blue, 1)
            self.context.set_line_width(10)
            self.context.stroke()

    def save_clustered_image(self):
        if self.save_count != -1:
            file_name = self.file_name + '_' + str(self.save_count)
            with open(f'../images/clustered/clustered_{file_name}.png', 'wb') as f:
                self.map_image.write_to_png(f)
        else:
            with open(f'../images/clustered/clustered_{self.file_name}.png', 'wb') as f:
                self.map_image.write_to_png(f)
        f.close()

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

            # i = 0
            # print(len(tiles))
            # Не знаю, как оптимизировать
            for t in tiles:
                server = random.choice(['a', 'b', 'c'])  # у OSM три сервера, распределяем нагрузку
                url = 'http://{server}.tile.openstreetmap.org/{zoom}/{x}/{y}.png'.format(
                    server=server,
                    zoom=t.z,
                    x=t.x,
                    y=t.y
                )
                # i += 1
                # print(i, url)
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

    # TODO: как-то оптимизировать эту функцию...
    def build_graph(self, current_point=None, end_point=None):
        polygon_buffers = {key: shapely.Polygon(polygon_bound).buffer(1e-9) for key, polygon_bound in
                           self.polygon_bounds.items()}
        # Угол обзора в градусах
        angle_of_vision = 2

        # Ищем точки с прямым доступом в точку Б
        interesting_points = []
        interesting_directions = {}
        really_interesting_points = []
        for key in self.polygon_bounds.keys():
            if shapely.intersects(polygon_buffers[key], end_point):
                interesting_directions[key] = self.average_directions[key]
        # Здесь добавляем в interesting_points все возможные точки из пересечений, чтобы ничего не пропустить...
        for key_intersection, intersection_bound_points in self.intersection_points.items():
            interesting_points.extend(intersection_bound_points)

        angles = {}
        # Определяем углы до точек
        for point in interesting_points:
            dx, dy = point.x - end_point.x, point.y - end_point.y
            angles[point] = (math.atan2(dy, dx) + 2 * math.pi) % (math.pi * 2)

        for key, direction in interesting_directions.items():
            angle_center = (direction - 90 - 180 + 360) % 360
            # Определяем границы видимости
            angle_left = angle_center - angle_of_vision / 2
            angle_right = angle_center + angle_of_vision / 2
            # Конвертируем углы в радианы
            angle_left_rad = math.radians(angle_left)
            angle_right_rad = math.radians(angle_right)

            # Отрисовка границ угла обзора
            self.context.set_source_rgba(255, 255, 255, 1)
            self.context.set_line_width(2)
            self.context.move_to(end_point.x, end_point.y)
            self.context.line_to(end_point.x + math.cos(angle_left_rad) * 1000,
                                 end_point.y + math.sin(angle_left_rad) * 1000)
            self.context.move_to(end_point.x, end_point.y)
            self.context.line_to(end_point.x + math.cos(angle_right_rad) * 1000,
                                 end_point.y + math.sin(angle_right_rad) * 1000)
            self.context.stroke()

            for point, angle in angles.items():
                if shapely.intersects(polygon_buffers[key], point):
                    if angle_left_rad <= angle <= angle_right_rad:
                        really_interesting_points.append(point)

        for point in really_interesting_points:
            self.context.arc(point.x, point.y, 5, 0 * math.pi / 180, 360 * math.pi / 180)
            self.context.set_source_rgba(0, 255, 255, 1)
            self.context.fill()
        print('Всего завершающих точек:', len(really_interesting_points))

        # Ищем видимые точки для текущей
        # for i in range(1):
        len_really_interesting_points = len(really_interesting_points)
        while len(self.visited_points) < 200:
            available_points = []
            available_directions = {}
            for key in self.polygon_bounds.keys():
                if shapely.intersects(polygon_buffers[key], current_point):
                    available_directions[key] = self.average_directions[key]
                    if shapely.intersects(polygon_buffers[key], end_point):
                        available_points.append(end_point)
            # Здесь добавляем в available_points все возможные точки из пересечений, чтобы ничего не пропустить...
            # Если delta большая - работает достаточно быстро
            for key_intersection, intersection_bound_points in self.intersection_points.items():
                available_points.extend(intersection_bound_points)

            visible_points_local = []
            # Точка обзора
            x0, y0 = current_point.x, current_point.y
            angles = {}
            # Определяем углы до точек
            for point in available_points:
                dx, dy = point.x - x0, point.y - y0
                angles[point] = (math.atan2(dy, dx) + 2 * math.pi) % (math.pi * 2)

            # diff_angles = {}
            for key, direction in available_directions.items():
                angle_center = (direction - 90 + 360) % 360
                # Определяем границы видимости
                angle_left = angle_center - angle_of_vision / 2
                angle_right = angle_center + angle_of_vision / 2
                # Конвертируем углы в радианы
                # angle_center_rad = math.radians(angle_center)
                angle_left_rad = math.radians(angle_left)
                angle_right_rad = math.radians(angle_right)

                # # Отрисовка границ угла обзора
                # self.context.set_source_rgba(255, 255, 255, 1)
                # self.context.set_line_width(2)
                # self.context.move_to(current_point.x, current_point.y)
                # self.context.line_to(current_point.x + math.cos(angle_left_rad) * 1000,
                #                      current_point.y + math.sin(angle_left_rad) * 1000)
                # self.context.move_to(current_point.x, current_point.y)
                # self.context.line_to(current_point.x + math.cos(angle_right_rad) * 1000,
                #                      current_point.y + math.sin(angle_right_rad) * 1000)
                # self.context.stroke()

                for point, angle in angles.items():
                    if shapely.intersects(polygon_buffers[key], point):
                        if angle_left_rad <= angle <= angle_right_rad:
                            visible_points_local.append(point)
                            # diff_angles[key] = {}
                            # diff_angles[key][point] = abs(abs(angle_center_rad) - abs(angle))

            # # Берем лучшие точки
            # diff_angles = {k: {v: v1} for k, v, v1 in sorted(diff_angles.items(), key=lambda item: item[1])}
            # visible_points_local = list(diff_angles.keys())[:50]

            for visible_point in visible_points_local:
                self.context.set_source_rgba(255, 255, 255, 1)
                self.context.set_line_width(0.3)
                self.context.move_to(current_point.x, current_point.y)
                self.context.line_to(visible_point.x, visible_point.y)
                self.context.stroke()

            if end_point in visible_points_local:
                self.routes_counter += 1
                print('Попали!))))))')
                self.context.set_source_rgba(0, 255, 0, 1)
                self.context.set_line_width(2)
                self.context.move_to(current_point.x, current_point.y)
                self.context.line_to(end_point.x, end_point.y)
                self.context.stroke()

            self.visible_points.extend(visible_points_local)
            without_visited_points = set(self.visible_points)
            without_visited_points.difference_update(set(self.visited_points))
            self.visible_points = list(without_visited_points)
            if len(self.visible_points) != 0:
                # Рандомайзер значительно сокращает время поиска конечных маршрутов
                # Даю приоритет точкам, лежащим в одном из полигонов конечной точки
                really_interesting_points_local = list(set(really_interesting_points).intersection(self.visible_points))
                if len(really_interesting_points_local) != 0:
                    current_point = really_interesting_points_local.pop(
                        random.randrange(len(really_interesting_points_local)))
                    self.visible_points.remove(current_point)
                    really_interesting_points.remove(current_point)
                    print(really_interesting_points)
                else:
                    current_point = self.visible_points.pop(random.randrange(len(self.visible_points)))
                # current_point = self.visible_points.pop(0)
                self.visited_points.append(current_point)
                print(len(self.visible_points))
                print(len(self.visited_points))
                if len(self.visible_points) == 0:
                    self.routes_counter = 404040404

    # Возможно стоит убрать мелкие кластеры...
    def create_clustered_map(self):
        self.create_empty_map()
        # Удаляю шум, не уверен, стоит ли
        # self.delete_noise()
        self.calculate_points_on_image()
        self.show_polygons()
        self.show_intersections()
        self.show_intersection_points()
        # frac - можно выбрать, какую долю объектов нанести на карту
        self.show_points(frac=1)
        self.show_average_directions()

        self.visible_points = []
        self.visited_points = []
        self.routes_counter = 0
        self.build_graph(shapely.Point(4500, 1450), shapely.Point(3700, 1200))
        for point in self.visited_points:
            self.context.arc(point.x, point.y, 5, 0 * math.pi / 180, 360 * math.pi / 180)
            self.context.set_source_rgba(0, 255, 0, 1)
            self.context.fill()
        self.context.set_source_rgba(0, 0, 0, 1)
        self.context.arc(4500, 1450, 10, 0 * math.pi / 180, 360 * math.pi / 180)
        self.context.arc(3700, 1200, 10, 0 * math.pi / 180, 360 * math.pi / 180)
        self.context.fill()
        print(self.routes_counter)
        # Задаем номер сохраняемого файла, нужно пока что для отладки
        # self.save_count = 2
        self.save_clustered_image()

        # print(self.polygons.keys())
        # print(self.polygon_bounds.keys())
        # print(self.intersections.keys())
        # print(self.intersection_bounds.keys())
        # print(self.intersection_bounds_points.keys())
        # print(self.average_speeds.keys())
        # print(self.average_directions.keys())
