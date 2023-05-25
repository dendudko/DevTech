# # TODO: как-то оптимизировать эту функцию...
# def build_graph(self, current_point=None, end_point=None):
#     for i in range(5):
#         # while self.routes_counter < 5:
#         a_point = current_point
#         b_point = end_point
#
#         visible_points_local = []
#         available_directions = {}
#         available_intersections = {}
#         for key, polygon_bounds in self.polygon_bounds.items():
#             if shapely.intersects(shapely.Polygon(polygon_bounds).buffer(1e-9), a_point):
#                 available_directions[key] = self.average_directions[key]
#                 for key_intersection, intersection in self.intersections.items():
#                     if key in key_intersection:
#                         available_intersections[key_intersection] = intersection
#
#         # Угол обзора в градусах и его ширина
#         angle_of_vision = 5
#
#         for key_direction, direction in available_directions.items():
#             angle_center = direction - 90
#             # Определяем границы видимости
#             angle_left = angle_center - angle_of_vision / 2
#             angle_right = angle_center + angle_of_vision / 2
#             # Конвертируем углы в радианы
#             angle_left_rad = math.radians(angle_left)
#             angle_right_rad = math.radians(angle_right)
#             # Точка обзора
#             x0, y0 = a_point.x, a_point.y
#             # Определяем, какие точки видимы при заданном угле обзора
#             rays = shapely.Polygon(
#                 [[x0, y0],
#                  [x0 + math.cos(angle_left_rad) * (self.map_image.get_width() + self.map_image.get_height()),
#                   y0 + math.sin(angle_left_rad) * (self.map_image.get_width() + self.map_image.get_height())],
#                  [x0 + math.cos(angle_right_rad) * (self.map_image.get_width() + self.map_image.get_height()),
#                   y0 + math.sin(angle_right_rad) * (self.map_image.get_width() + self.map_image.get_height())]])
#
#             for key_polygon_intersection, polygon_intersection in available_intersections.items():
#                 if key_direction in key_polygon_intersection:
#                     print(key_direction, key_polygon_intersection)
#                     if polygon_intersection.intersects(rays):
#                         # visible_areas - это list из-за возможности получить GeometryCollection
#                         visible_areas = [polygon_intersection.intersection(rays)]
#                         if isinstance(visible_areas[0], shapely.GeometryCollection):
#                             visible_areas = list(visible_areas[0].geoms)
#
#                         for visible_area in visible_areas:
#                             for key, intersection in available_intersections.items():
#                                 if shapely.intersects(visible_area, intersection):
#                                     print(shapely.intersection(shapely.LineString(self.intersection_points[key]), visible_area))
#                             if isinstance(visible_area, shapely.Point):
#                                 visible_points_local.append(visible_area)
#
#                         for visible_point in visible_points_local:
#                             self.context.set_source_rgba(255, 255, 255, 1)
#                             self.context.set_line_width(1)
#                             self.context.move_to(a_point.x, a_point.y)
#                             self.context.line_to(visible_point.x, visible_point.y)
#                             self.context.stroke()
#
#                         if shapely.intersects(rays, b_point):
#                             self.routes_counter += 1
#                             print('Попали!))))))')
#                             self.context.set_source_rgba(0, 255, 0, 1)
#                             self.context.set_line_width(2)
#                             self.context.move_to(a_point.x, a_point.y)
#                             self.context.line_to(b_point.x, b_point.y)
#                             self.context.stroke()
#
#                         self.visible_points += [point_i for point_i in visible_points_local]
#
#         if len(self.visible_points) != 0:
#             # Рандомайзер значительно сокращает время поиска конечных маршрутов
#             current_point = self.visible_points.pop(random.randrange(len(self.visible_points)))
#             # current_point = self.visible_points.pop(0)
#             self.visited_points.append(current_point)
#             print(len(self.visible_points))
#             print(len(self.visited_points))
#
# # Возможно стоит убрать мелкие кластеры...
# def create_clustered_map(self):
#     self.create_empty_map()
#     # Удаляю шум, не уверен, стоит ли
#     # self.delete_noise()
#     self.calculate_points_on_image()
#     self.show_polygons()
#     self.show_intersections()
#     self.show_intersection_points()
#     # frac - можно выбрать, какую долю объектов нанести на карту
#     self.show_points(frac=1)
#     self.show_average_directions()
#
#     self.visible_points = []
#     self.visited_points = []
#     self.routes_counter = 0
#     self.build_graph(shapely.Point(4500, 1450), shapely.Point(3700, 1200))
#     for point in self.visited_points:
#         self.context.arc(point.x, point.y, 5, 0 * math.pi / 180, 360 * math.pi / 180)
#         self.context.set_source_rgba(0, 255, 0, 1)
#         self.context.fill()
#     self.context.set_source_rgba(0, 0, 0, 1)
#     self.context.arc(4500, 1450, 10, 0 * math.pi / 180, 360 * math.pi / 180)
#     self.context.arc(3700, 1200, 10, 0 * math.pi / 180, 360 * math.pi / 180)
#     self.context.fill()
#     print(self.routes_counter)
#     # Задаем номер сохраняемого файла, нужно пока что для отладки
#     # self.save_count = 2
#     self.save_clustered_image()
#
#     # print(self.polygons.keys())
#     # print(self.polygon_bounds.keys())
#     # print(self.intersections.keys())
#     # print(self.intersection_bounds.keys())
#     # print(self.intersection_bounds_points.keys())
#     # print(self.average_speeds.keys())
#     # print(self.average_directions.keys())
