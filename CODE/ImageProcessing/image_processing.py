from PIL import Image
import numpy as np
from selenium import webdriver
import os
import time


def crop_image_help(img, xmin, ymin, xmax, ymax):
    im = Image.open(img)
    padding = 20
    im_crop = im.crop((xmin - padding, ymin - padding, xmax + padding, ymax + padding))
    im_crop.save('../ImageProcessing/map_crop.png', quality=100)


def crop_image_by_marker_color(img, r=0, g=0, b=0):
    color = (r, g, b)
    image = Image.open(img)
    rgb_image = image.convert('RGB')
    found_pixels_x = []
    found_pixels_y = []
    for x in range(rgb_image.size[0]):
        for y in range(rgb_image.size[1]):
            r, g, b = rgb_image.getpixel((x, y))
            if (r, g, b) == color:
                found_pixels_x.append(x)
                found_pixels_y.append(y)
    min_x = np.min(found_pixels_x)
    max_x = np.max(found_pixels_x)
    min_y = np.min(found_pixels_y)
    max_y = np.max(found_pixels_y)
    crop_image_help(img, min_x, min_y, max_x, max_y)


def create_screenshot():
    map_url = 'file://{0}/{1}'.format(os.getcwd(), '../App/index.html')
    driver = webdriver.Chrome()
    driver.get(map_url)
    driver.maximize_window()
    # wait for 1 second for the maps and other assets to be loaded in the browser
    time.sleep(1)
    driver.save_screenshot('../ImageProcessing/full_map.png')
    driver.quit()
    # # Кроп работает корректно, но пахнет костылем...
    crop_image_by_marker_color('../ImageProcessing/full_map.png', r=255)
