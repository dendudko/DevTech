import io
import urllib.request
import random

from cairo import ImageSurface, FORMAT_ARGB32, Context
import math
import mercantile
import matplotlib.colors as mcolors


def get_map(west, south, east, north, zoom, df, create_new=True):
    if create_new:
        tiles = list(mercantile.tiles(west, south, east, north, zoom))

        min_x = min([t.x for t in tiles])
        min_y = min([t.y for t in tiles])
        max_x = max([t.x for t in tiles])
        max_y = max([t.y for t in tiles])

        tile_size = (256, 256)
        # создаем пустое изображение в которое как мозайку будем вставлять тайлы
        # для начала просто попробуем отобразить все четыре тайла в строчку
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
            print(url)
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
        map_image = ImageSurface.create_from_png('../Map/map_crop.png')

    # рассчитываем координаты углов в веб-меркаоторе
    left_top = tuple(mercantile.xy(west, north))
    right_bottom = tuple(mercantile.xy(east, south))

    # расчитываем коэффициенты
    kx = map_image.get_width() / (right_bottom[0] - left_top[0])
    ky = map_image.get_height() / (right_bottom[1] - left_top[1])

    # сохраняем результат
    if create_new:
        with open("../Map/map_crop.png", "wb") as f:
            map_image.write_to_png(f)

    map_paint(map_image, df, left_top, kx, ky)


def map_paint(map_image, df, left_top, kx, ky):
    # тут создаем rgba массив цветов из CSS4, меняем [-1] элемент, чтобы шум был заданного нами цвета
    # ВРЕМЕННОЕ РЕШЕНИЕ, С ЦВЕТАМИ НАДО ЧТО-ТО ПРИДУМАТЬ
    colors = list(mcolors.CSS4_COLORS.keys())
    # Шум
    colors[-1] = 'black'
    # colors[-1] = 'red'
    colors[7] = 'yellowgreen'
    colors = mcolors.to_rgba_array(colors)

    context = Context(map_image)
    for i, row in df.iterrows():
        # gps в web-mercator
        x, y = mercantile.xy(row['lat'], row['lon'])
        # переводим x, y в координаты изображения
        x = (x - left_top[0]) * kx
        y = (y - left_top[1]) * ky
        context.arc(x, y, 4, 0 * math.pi / 180, 360 * math.pi / 180)

        if 'cluster' in df.columns:
            red = colors[int(row['cluster'])][0]
            green = colors[int(row['cluster'])][1]
            blue = colors[int(row['cluster'])][2]
            alpha = colors[int(row['cluster'])][3]
        else:
            red, green, blue, alpha = 1, 0, 0, 1

        context.set_source_rgba(red, green, blue, alpha)
        # if 'cluster' not in df.columns or row['cluster'] != -1:
        #     context.fill()
        context.fill()

    with open("../Map/map_crop_with_dots.png", "wb") as f:
        map_image.write_to_png(f)
