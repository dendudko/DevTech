import io
import urllib.request
import random

import pandas
from cairo import ImageSurface, FORMAT_ARGB32, Context, LINE_JOIN_ROUND, LINE_CAP_ROUND, LinearGradient
import math
import mercantile
import shapely
import numpy as np

from shapely.ops import nearest_points
import networkx


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
        self.save_mode = save_count

        self.clustering_params = None
        self.graph_params = None

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

        try:
            self.noise_count = self.df['cluster'].value_counts()[-1]
        except KeyError:
            self.noise_count = 0
        self.total_count = len(self.df)
        self.cluster_count = max(self.df['cluster']) + 1
        self.colors = generate_colors(self.cluster_count)

        self.graph = networkx.DiGraph()

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
        # Расстояние между точками в пересечении
        if self.graph_params is not None:
            distance_delta = self.graph_params['distance_delta']
        else:
            distance_delta = 100
        # Накидываем точки на границу пересечения полигонов
        if len(self.intersection_points) == 0:
            for key, intersection_bound in self.intersection_bounds.items():
                distances = np.arange(0, shapely.LineString(intersection_bound).length, distance_delta)
                self.intersection_points[key] = (
                    [shapely.LineString(intersection_bound).interpolate(distance) for distance in distances])

            # Добавляем точки внутрь полигонов
            for key in self.intersection_bounds.keys():
                x_min, y_min, x_max, y_max = self.intersections[key].bounds

                current_y = y_min - distance_delta
                calculated_points = []
                while current_y <= y_max:
                    current_y += distance_delta
                    current_x = x_min - distance_delta
                    while current_x <= x_max:
                        current_x += distance_delta
                        calculated_points.append(shapely.Point(current_x, current_y))
                calculated_multi_point = shapely.MultiPoint(calculated_points)
                actual_multi_point = self.intersections[key].intersection(calculated_multi_point)
                if isinstance(actual_multi_point, shapely.MultiPoint):
                    actual_multi_point = actual_multi_point.geoms
                    self.intersection_points[key] += actual_multi_point

        for key in self.intersection_bounds.keys():
            for dot in self.intersection_points[key]:
                self.context.set_line_width(1.5)
                self.context.arc(dot.x, dot.y, 2, 0 * math.pi / 180, 360 * math.pi / 180)
                self.context.set_source_rgba(0, 255, 255, 1)
                self.context.stroke()

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
        file_name = self.file_name + '_' + str(self.save_mode)
        with open(f'../images/clustered/clustered_{file_name}.png', 'wb') as f:
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

        # Сохраняем результат
        if self.create_new_empty_map:
            with open(f'../images/clean/{self.file_name}.png', 'wb') as f:
                self.map_image.write_to_png(f)
                f.close()

        self.context = Context(self.map_image)
        if self.create_new_empty_map:
            # Отображаем точки
            for row in self.df_points_on_image.itertuples(index=False):
                self.context.arc(row[0], row[1], 2, 0 * math.pi / 180, 360 * math.pi / 180)
                self.context.set_source_rgba(255, 0, 0, 0.7)
                self.context.fill()
                # Рисуем линии, отображающие направление, стрелки перегружают картинку, будут просто линии)
                self.context.set_line_width(1.5)
                self.context.move_to(row[0], row[1])
                # Курс отсчитывается по часовой стрелке от направления на север, движение правостороннее
                angle = math.radians(row[3] - 90)
                line_length = row[2] / 10
                self.context.line_to(row[0] + line_length * math.cos(angle), row[1] + line_length * math.sin(angle))
                self.context.stroke()
            # Сохраняем результат
            with open(f'../images/clean/{self.file_name}_with_points.png', 'wb') as f:
                self.map_image.write_to_png(f)

        self.context = Context(self.map_image)

    def build_graph(self, start_point=None, end_point=None, create_new_graph=False):
        end_point_saved = None
        if len(self.graph.edges) == 0:
            create_new_graph = True
        if create_new_graph:
            self.graph = networkx.DiGraph()

        # Здесь добавляем в available_points все возможные точки из пересечений, чтобы ничего не пропустить...
        # Если delta большая - работает достаточно быстро
        available_points = []
        for key_intersection, intersection_bound_points in self.intersection_points.items():
            available_points.extend(intersection_bound_points)

        polygon_buffers = {key: shapely.Polygon(polygon_bound).buffer(1e-9) for key, polygon_bound in
                           self.polygon_bounds.items()}

        # Костыльная обработка случая, когда точка А или Б не попала в полигон
        end_point_in_poly = False
        start_point_in_poly = False
        for key in self.polygon_bounds.keys():
            if shapely.intersects(polygon_buffers[key], end_point):
                end_point_in_poly = True
            if shapely.intersects(polygon_buffers[key], start_point):
                start_point_in_poly = True

        if not start_point_in_poly:
            nearest_point = nearest_points(shapely.MultiPoint(available_points), start_point)[0]
            self.graph.add_edge(start_point, nearest_point, weight=0, color=[1, 0, 0, 1])
            current_point = nearest_point
        else:
            current_point = start_point

        if not end_point_in_poly:
            nearest_point = nearest_points(shapely.MultiPoint(available_points), end_point)[0]
            self.graph.add_edge(nearest_point, end_point, weight=0, color=[1, 0, 0, 1])
            end_point_saved = end_point
            end_point = nearest_point

        available_points.append(start_point)
        available_points.append(end_point)
        self.graph.add_node(start_point)
        self.graph.add_node(end_point)

        # Угол обзора в градусах
        angle_of_vision = self.graph_params['angle_of_vision']

        # Ищем точки с прямым доступом в точку Б
        interesting_directions = {}
        really_interesting_points = []
        for key in self.polygon_bounds.keys():
            if shapely.intersects(polygon_buffers[key], end_point):
                interesting_directions[key] = self.average_directions[key]

        # Определяем углы до точек
        angles = {point: (math.atan2(point.y - end_point.y, point.x - end_point.x)
                          + 2 * math.pi) % (math.pi * 2) for point in available_points}

        for key, direction in interesting_directions.items():
            angle_center = (direction - 90 - 180 + 360) % 360
            # Определяем границы видимости
            angle_left = angle_center - angle_of_vision / 2
            angle_right = angle_center + angle_of_vision / 2
            # Конвертируем углы в радианы
            angle_left_rad = math.radians(angle_left)
            angle_center_rad = math.radians(angle_center)
            angle_right_rad = math.radians(angle_right)

            # # Отрисовка границ угла обзора
            # self.context.set_source_rgba(255, 255, 255, 1)
            # self.context.set_line_width(2)
            # self.context.move_to(end_point.x, end_point.y)
            # self.context.line_to(end_point.x + math.cos(angle_left_rad) * 1000,
            #                      end_point.y + math.sin(angle_left_rad) * 1000)
            # self.context.move_to(end_point.x, end_point.y)
            # self.context.line_to(end_point.x + math.cos(angle_right_rad) * 1000,
            #                      end_point.y + math.sin(angle_right_rad) * 1000)
            # self.context.stroke()
            try:
                current_angles_keys_multipoint = shapely.intersection(
                    polygon_buffers[key], shapely.MultiPoint(list(angles.keys()))).geoms
                current_angles_keys = []
                for point in current_angles_keys_multipoint:
                    if shapely.contains(polygon_buffers[key], shapely.LineString([end_point, point])):
                        current_angles_keys.append(point)
            except AttributeError:
                continue
            for point in current_angles_keys:
                if angle_left_rad <= angles[point] <= angle_right_rad:
                    really_interesting_points.append(point)
                    # Вес = sqrt(((расстояние в пикселях / скорость (в узлах * 10)) * вес времени) ** 2 +
                    # + (разница направлений * вес направления) ** 2)
                    weight = math.sqrt(
                        ((math.hypot(point.x - end_point.x, point.y - end_point.y) /
                          self.average_speeds[key]) * self.graph_params['weight_time_graph']) ** 2 +
                        (abs(angles[point] - angle_center_rad) * self.graph_params['weight_course_graph']) ** 2)
                    self.graph.add_edge(point, end_point, weight=weight, color=self.colors[key])

        # Отображение завершающих точек
        # for point in really_interesting_points:
        #     self.context.arc(point.x, point.y, 5, 0 * math.pi / 180, 360 * math.pi / 180)
        #     self.context.set_source_rgba(0, 255, 255, 1)
        #     self.context.fill()
        print('Всего завершающих узлов:', len(really_interesting_points))

        visited_points = 0

        if len(really_interesting_points) != 0:
            while True:
                available_directions = {}
                for key in self.polygon_bounds.keys():
                    if shapely.intersects(polygon_buffers[key], current_point):
                        available_directions[key] = self.average_directions[key]

                # Определяем углы до точек
                angles = {point: (math.atan2(point.y - current_point.y, point.x - current_point.x)
                                  + 2 * math.pi) % (math.pi * 2) for point in available_points}
                for key, direction in available_directions.items():
                    angle_center = (direction - 90 + 360) % 360
                    # Определяем границы видимости
                    angle_left = angle_center - angle_of_vision / 2
                    angle_right = angle_center + angle_of_vision / 2
                    # Конвертируем углы в радианы
                    angle_left_rad = math.radians(angle_left)
                    angle_center_rad = math.radians(angle_center)
                    angle_right_rad = math.radians(angle_right)

                    # Оптимизирован поиск пересечения множества точек и текущего полигона,
                    # вычислительная эффективность увеличилась примерно в 2.5 раза
                    try:
                        current_angles_keys_multipoint = shapely.intersection(
                            polygon_buffers[key], shapely.MultiPoint(list(angles.keys()))).geoms
                        current_angles_keys = []
                        for point in current_angles_keys_multipoint:
                            if shapely.contains(polygon_buffers[key], shapely.LineString([current_point, point])):
                                current_angles_keys.append(point)
                    except AttributeError:
                        continue
                    for point in current_angles_keys:
                        if angle_left_rad <= angles[point] <= angle_right_rad:
                            # Вес = sqrt(((расстояние в пикселях / скорость (в узлах * 10) * вес времени) ** 2 +
                            # + (разница направлений * вес направления) ** 2)
                            weight = math.sqrt(
                                ((math.hypot(current_point.x - point.x, current_point.y - point.y) /
                                  self.average_speeds[key]) * self.graph_params['weight_time_graph']) ** 2 +
                                (abs(angles[point] - angle_center_rad) * self.graph_params['weight_course_graph']) ** 2)
                            self.graph.add_edge(current_point, point, weight=weight, color=self.colors[key])

                if not create_new_graph:
                    break
                if len(available_points) != 0:
                    current_point = available_points.pop()
                    visited_points += 1
                    print(len(available_points))
                    print(visited_points)
                    if len(available_points) == 0:
                        break
                else:
                    print('Нет видимых точек :(')
                    break

            if end_point_saved:
                end_point = end_point_saved

        else:
            print('Конечная точка недостижима :(')
            if create_new_graph:
                self.graph = networkx.DiGraph()

        # Отрисовка графа
        # self.context.set_line_width(0.5)
        # self.context.set_source_rgba(255, 255, 255, 1)
        # for edge in self.graph.edges:
        #     self.context.move_to(edge[0].x, edge[0].y)
        #     self.context.line_to(edge[1].x, edge[1].y)
        # self.context.stroke()

        # Вызов A* и отрисовка пути
        try:
            path = networkx.astar_path(self.graph, start_point, end_point)
            # Отрисовка черной линии
            self.context.set_line_join(LINE_JOIN_ROUND)
            self.context.set_line_width(18)
            self.context.set_source_rgba(0, 0, 0, 1)
            for node in path:
                self.context.line_to(node.x, node.y)
            self.context.stroke()
            # Отрисовка на черной линии зеленой
            self.context.set_line_width(10)
            self.context.set_line_cap(LINE_CAP_ROUND)
            for i in range(len(path) - 2):
                ln_gradient = LinearGradient(path[i].x, path[i].y, path[i + 1].x, path[i + 1].y)
                color1 = self.graph.get_edge_data(path[i], path[i + 1])['color']
                color2 = self.graph.get_edge_data(path[i + 1], path[i + 2])['color']
                line_length = shapely.LineString([path[i], path[i + 1]]).length
                if line_length > 15:
                    color_stop1 = (line_length - 15) / line_length
                    color_stop2 = (line_length - 5) / line_length
                    ln_gradient.add_color_stop_rgba(color_stop1, color1[0], color1[1], color1[2], color1[3])
                    ln_gradient.add_color_stop_rgba(color_stop2, color2[0], color2[1], color2[2], color2[3])
                else:
                    ln_gradient.add_color_stop_rgba(0, color1[0], color1[1], color1[2], color1[3])
                self.context.set_source(ln_gradient)
                self.context.move_to(path[i].x, path[i].y)
                self.context.line_to(path[i + 1].x, path[i + 1].y)
                self.context.stroke()
            color = self.graph.get_edge_data(path[-2], path[-1])['color']
            self.context.set_source_rgba(color[0], color[1], color[2], color[3])
            self.context.move_to(path[-2].x, path[-2].y)
            self.context.line_to(path[-1].x, path[-1].y)
            self.context.stroke()
            print('Маршрут успешно построен :)')
        except networkx.exception.NetworkXNoPath:
            print('Маршрут найти не удалось :(')
            if create_new_graph:
                self.graph = networkx.DiGraph()
        except networkx.exception.NodeNotFound:
            print('Для начальной точки нет доступных узлов :(')
            if create_new_graph:
                self.graph = networkx.DiGraph()

        # Выделение точек начала и конца
        self.context.set_line_width(0)
        self.context.set_source_rgba(255, 255, 255, 1)
        self.context.arc(start_point.x, start_point.y, 9, 0 * math.pi / 180, 360 * math.pi / 180)
        self.context.arc(end_point.x, end_point.y, 9, 0 * math.pi / 180, 360 * math.pi / 180)
        self.context.fill()
        self.context.set_source_rgba(255, 0, 0, 1)
        self.context.arc(start_point.x, start_point.y, 6, 0 * math.pi / 180, 360 * math.pi / 180)
        self.context.fill()
        self.context.set_source_rgba(0, 0, 0, 1)
        self.context.arc(end_point.x, end_point.y, 6, 0 * math.pi / 180, 360 * math.pi / 180)
        self.context.fill()
        # Удаляем начальный и конечный узлы, чтобы в графе не копился мусор
        self.graph.remove_node(start_point)
        self.graph.remove_node(end_point)
        # Отображение букв для начальной и конечной точек
        self.context.set_source_rgba(0, 0, 0, 1)
        self.context.set_font_size(50)
        self.context.move_to(start_point.x - 15, start_point.y - 15)
        self.context.show_text('A')
        self.context.move_to(end_point.x - 15, end_point.y - 15)
        self.context.show_text('B')

    # Возможно стоит убрать мелкие кластеры...
    def create_clustered_map(self):
        # Удаляю шум, не уверен, стоит ли
        # self.delete_noise()
        for save_mode in 'clusters', 'polygons':
            self.create_empty_map()
            self.calculate_points_on_image()
            self.show_polygons()
            self.show_intersections()
            # frac - можно выбрать, какую долю объектов нанести на карту
            if save_mode == 'clusters':
                self.show_points(frac=1)
            if save_mode == 'polygons':
                self.show_average_directions()
                self.show_intersection_points()
            self.save_mode = save_mode
            self.save_clustered_image()

        log = 'Всего кластеров: ' + str(self.cluster_count) + '\n'
        log += 'Доля шума: ' + str(self.noise_count) + ' / ' + str(self.total_count) + '\n'
        print(log)

        # Перевод координат изображения в координаты веб-меркатора
        # lat = self.left_top[0] + 3500 / self.kx
        # lon = self.left_top[1] + 1450 / self.ky
        # print(lon, lat)

    def find_path(self, x_start, y_start, x_end, y_end, create_new_graph):
        self.create_empty_map()
        self.calculate_points_on_image()
        self.show_polygons()
        self.show_intersections()
        self.show_average_directions()
        self.intersection_points = {}
        self.show_intersection_points()
        self.build_graph(shapely.Point(x_start, y_start), shapely.Point(x_end, y_end),
                         create_new_graph=create_new_graph)
        self.save_mode = 'path'
        self.save_clustered_image()
