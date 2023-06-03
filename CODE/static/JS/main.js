//Создание карты
var extent = [15522946.393668033, 5002641.018067474, 15751596.627757415, 5160979.444049783];
var projection = new ol.proj.Projection({
    code: 'xkcd-image',
    units: 'pixels',
    extent: extent,
});
var vectorLayer = new ol.layer.Vector({
    source: new ol.source.Vector(),
});

var map = new ol.Map({
    target: 'map', // ID элемента на странице, где отобразить карту
    layers: [
        new ol.layer.Tile({
            title: 'Open Street Map',
            source: new ol.source.OSM(),
            type: 'base'
        }),
        new ol.layer.Image({
            name: 'Ships',
            visible: true,
            source: new ol.source.ImageStatic({
                url: '/static/img/clasters.png', // URL PNG-изображения
                imageSize: [5893, 4143], // Размер изображения
                projection: projection,
                imageExtent: extent,
            })
        }),
    ],
    view: new ol.View({
        projection: projection,
        center: ol.extent.getCenter(extent), // Координаты центра карты
        zoom: 2, // Масштаб карты
        minZoom: 2,
        maxZoom: 5,
    }),
    controls: ol.control.defaults().extend([
        new ol.control.FullScreen(),
        // Добавление элемента управления для легенды
        new ol.control.Control({
            element: document.getElementById('legend')
        })
    ])
});
map.setView(
    new ol.View({
        center: ol.extent.getCenter(extent),
        extent: map.getView().calculateExtent(map.getSize()),
        zoom: 9.5,
        minZoom: 9.5,
        maxZoom: 14
    })
);
map.addControl(new ol.control.LayerSwitcher({
    reverse: false
}));

//Создание легенды
var legendShown = false;

function hideLegend() {
    document.getElementById('legend').className = 'hide';
    legendShown = false;
}

function showLegend() {
    document.getElementById('legend').className = 'show';
    legendShown = true;
}

var button = new ol.control.Button({
    className: 'ol-legend ol-unselectable ol-control ol-collapsed', // класс для стилизации кнопки
    title: 'Данные работы алгоритма', // всплывающая подсказка для кнопки
    handleClick: function () { // ваша функция для обработки клика на кнопке
        if (legendShown) {
            document.getElementById('legend').className = 'hide';
            legendShown = false;
        } else {
            document.getElementById('legend').className = 'show';
            legendShown = true;
        }
    },
});
map.addControl(button); // добавление кнопки на карту
var legend = document.getElementById('legend');
map.getViewport().appendChild(legend);


//Заполнение полей координат
function setPoints() {
    let startPointInput = document.getElementById("start_coords");
    let endPointInput = document.getElementById("end_coords");
    const routeBtn = document.getElementById('do_graph');
    routeBtn.addEventListener('click', () => {
        startPointInput.style.display = 'inline';
        endPointInput.style.display = 'inline';
    });
    var checkFocus = (el) => el === document.querySelector(':focus');

    window.addEventListener('click', e => {
        if (checkFocus(start_coords)) {
            var onfocus = 1;
        } else if (checkFocus(end_coords)) {
            onfocus = 2;
        }


        map.on('click', function (evt) {
            let layers = map.getLayers().getArray();
            let coords = ol.proj.toLonLat(evt.coordinate).map(coord => coord.toFixed(6));

            if (onfocus === 1) {
                startPointInput.value = coords.toString();
                var StartPointLayer = null;

                for (let i = 0; i < layers.length; i++) {
                    if (layers[i].get('name') === 'StartPoint') {
                        StartPointLayer = layers[i];
                        break;
                    }
                }

                if (StartPointLayer) {
                    map.removeLayer(StartPointLayer);
                }

                const StartPoint = new ol.layer.Vector({
                    name: 'StartPoint',
                    source: new ol.source.Vector({
                        features: [
                            new ol.Feature({
                                geometry: new ol.geom.Point(evt.coordinate),
                            })
                        ]
                    }),
                    style: new ol.style.Style({
                        image: new ol.style.Icon({
                            anchor: [0.5, 1],
                            crossOrigin: 'anonymous',
                            src: '/static/img/start_point.png',
                        })
                    })
                });

                map.addLayer(StartPoint);
                onfocus = null
            } else if (onfocus === 2) {
                endPointInput.value = coords.toString();

                var endPointLayer = null;
                for (let i = 0; i < layers.length; i++) {
                    if (layers[i].get('name') === 'EndPoint') {
                        endPointLayer = layers[i];
                        break;
                    }
                }

                if (endPointLayer) {
                    map.removeLayer(endPointLayer);
                }

                const EndPoint = new ol.layer.Vector({
                    name: 'EndPoint',
                    source: new ol.source.Vector({
                        features: [
                            new ol.Feature({
                                geometry: new ol.geom.Point(evt.coordinate),
                            })
                        ]
                    }),
                    style: new ol.style.Style({
                        image: new ol.style.Icon({
                            anchor: [0.5, 1],
                            crossOrigin: 'anonymous',
                            src: '/static/img/end_point.png',
                        })
                    })
                });

                map.addLayer(EndPoint);
                onfocus = null
            }

        });
    });
}

setPoints();

//Обработка кнопки Визуализация маршрута
function Create_graph() {
    let polyLayerExists = false;
    let allLayers = map.getLayers().getArray();
    for (let i = 0; i < allLayers.length; i++) {
        if (allLayers[i].get('name') === 'PolygonsForGraph') {
            polyLayerExists = true;
            break;
        }
    }
    if (!polyLayerExists) {
        document.querySelector('.red_text').style.cssText = 'color : green;';
        alert("Сначала необходимо кластеризовать данные");
    } else {
        // Получаем значения полей ввода
        const fields = ['distance_delta', 'angle_of_vision', 'weight_time_graph', 'weight_course_graph', 'start_coords', 'end_coords'];
        const parameters_for_graph = {};
        let allFieldsFilled = true;
        fields.forEach(field => {
            const value = document.getElementById(field).value;
            if (!value) {
                allFieldsFilled = false;
                return alert("Заполните поле " + field);
            }
            parameters_for_graph[field] = value;
        });

        // Если не все поля заполнены, выходим из функции
        if (!allFieldsFilled) return;

        $.ajax({
            type: 'POST',
            url: '/get_graphs_parameters',
            contentType: 'application/json',
            data: JSON.stringify(parameters_for_graph),
            success: function (data) {
                const GraphLayer = new ol.layer.Image({
                    name: 'Graph',
                    visible: true,
                    source: new ol.source.ImageStatic({
                        url: data, // URL PNG-изображения
                        imageSize: [5893, 4143], // Размер изображения
                        projection: projection,
                        imageExtent: extent,
                    })
                })

                let allLayers = map.getLayers().getArray();
                for (let i = 0; i < allLayers.length; i++) {
                    if (allLayers[i].get('name') === 'StartPoint') {
                        var StartPoint = allLayers[i]
                        map.removeLayer(allLayers[i]);
                        break;
                    }
                }
                for (let i = 0; i < allLayers.length; i++) {
                    if (allLayers[i].get('name') === 'EndPoint') {
                        var EndPoint = allLayers[i]
                        map.removeLayer(allLayers[i]);
                        break;
                    }
                }
                for (let i = 0; i < allLayers.length; i++) {
                    if (allLayers[i].get('name') === 'Graph') {
                        map.removeLayer(allLayers[i]);
                        break;
                    }
                }

                map.addLayer(GraphLayer);
                map.addLayer(StartPoint);
                map.addLayer(EndPoint);

                //Заполнение легенды данными из вычислительной части
                const name1 = 'Протяженность маршрута'
                const description1 = '145м'
                const name2 = 'Примерное время прохождения маршрута'
                const description2 = '145м'
                const name3 = 'Отклонение от средних курсов на маршруте'
                const description3 = '145м'
                let legend = document.getElementById('legend');

                //Перезаполнение при выборе других маршрутов
                let divsToRemove = legend.querySelectorAll('div:not(:first-child)');
                for (let i = 0; i < divsToRemove.length; i++) {
                    legend.removeChild(divsToRemove[i]);
                }

                let item = document.createElement('div');
                item.innerHTML = '<strong>' + name1 + '</strong>: ' + description1 +
                    '<br>' + '<strong>' + name2 + '</strong>: ' + description2 +
                    '<br>' + '<strong>' + name3 + '</strong>: ' + description3 + '<br>';
                legend.appendChild(item);

            }
        });
    }
}

//Обработка кнопки Кластеризовать данные
function Do_clustering() {
    document.querySelector('.red_text').style.cssText = '';
    // Получаем значения полей ввода
    const fields = ['weight_distance', 'weight_speed', 'weight_course', 'eps', 'min_samples'];
    var parameters_for_DBSCAN = {};
    let allFieldsFilled = true;
    fields.forEach(field => {
        const value = document.getElementById(field).value;
        if (!value) {
            allFieldsFilled = false;
            return alert("Заполните поле " + field);
        }
        parameters_for_DBSCAN[field] = value;
    });

    // Если не все поля заполнены, выходим из функции
    if (!allFieldsFilled) return;

    $.ajax({
        type: 'POST',
        url: '/get_DBSCAN_parameters',
        contentType: 'application/json',
        data: JSON.stringify(parameters_for_DBSCAN),
        success: function (data) {
            const ClustersLayer = new ol.layer.Image({
                name: 'Clusters',
                visible: true,
                source: new ol.source.ImageStatic({
                    url: data, // URL PNG-изображения
                    imageSize: [5893, 4143], // Размер изображения
                    projection: projection,
                    imageExtent: extent,
                })
            });
            const PolygonsLayer = new ol.layer.Image({
                name: 'Polygons',
                visible: true,
                source: new ol.source.ImageStatic({
                    url: '/static/img/polygons.png', // URL PNG-изображения
                    imageSize: [5893, 4143], // Размер изображения
                    projection: projection,
                    imageExtent: extent,
                })
            });
            const PolygonsForGraphLayer = new ol.layer.Image({
                name: 'PolygonsForGraph',
                visible: true,
                source: new ol.source.ImageStatic({
                    url: '/static/img/polygons.png', // URL PNG-изображения
                    imageSize: [5893, 4143], // Размер изображения
                    projection: projection,
                    imageExtent: extent,
                })
            });

            // Удаляем старые слои с карты
            const names = ["Clusters", "Polygons", "PolygonsForGraph", "Graph", "StartPoint", "EndPoint"];
            names.forEach(name => {
                const layers = map.getLayers().getArray();
                layers.forEach(layer => {
                    if (layer.get('name') === name) {
                        map.removeLayer(layer);
                    }
                });
            });

            map.addLayer(ClustersLayer);
            map.addLayer(PolygonsLayer);
            map.addLayer(PolygonsForGraphLayer);
            document.getElementById("start_coords").value = "";
            document.getElementById("end_coords").value = "";

            //Легенда с данными из вычислительной части
            const name1 = 'Количество кластеров'
            const name2 = 'Доля шума'
            const description1 = '120'
            const description2 = '1/5'
            let legend = document.getElementById('legend');
            legend.innerHTML = '';
            let item = document.createElement('div');
            item.innerHTML = '<strong>' + name1 + '</strong>: ' + description1 +
                '<br>' + '<strong>' + name2 + '</strong>: ' + description2;
            legend.appendChild(item);
        }
    });
}
