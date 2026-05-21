```
economic_dashboard/
├── app.py                 # Точка входа, создание Flask-приложения
├── config.py             # Конфигурация (переменные окружения)
├── database.py           # Работа с PostgreSQL (пул соединений)
├── models/               # Модели данных (Country, Indicator, Stats)
├── routes/               # API маршруты
│   ├── countries.py      # /api/countries
│   ├── indicators.py     # /api/indicators, /api/forecast, /api/regression
│   ├── main.py           # Главная страница /
│   └── trends.py         # Страница трендового анализа /trends
├── services/             # Бизнес-логика
│   ├── country_service.py
│   ├── indicator_service.py
│   ├── csv_import_service.py
│   ├── forecast_service.py
│   ├── regression_service.py
│   ├── clustering_service.py
│   └── trend_analysis_service.py
├── utils/                # Вспомогательные функции
│   └── validators.py     # Валидаторы
├── static/               # Статические файлы
│   ├── css/style.css
│   └── js/main.js
└── templates/            # HTML шаблоны
    ├── index.html
    └── trends.html
```


New-Item -Path config.py, database.py,  models.py,   routes/__init__.py, routes/countries.py, routes/indicators.py, routes/main.py, services/__init__.py, services/country_service.py, services/indicator_service.py,  utils/__init__.py, utils/validators.py


 | Метод | URL | Описание | Сервис |
|-------|-----|----------|--------|
| GET | `/` | Главная страница | - |
| GET | `/trends` | Страница трендового анализа | - |
| GET | `/api/countries` | Список стран | CountryService |
| GET | `/api/indicators/filter` | Фильтрация показателей | IndicatorService |
| GET | `/api/stats/<id>` | Статистика по стране | IndicatorService |
| POST | `/api/csv/import` | Импорт CSV | CSVImportService |
| GET | `/api/csv/template` | Скачать шаблон | CSVImportService |
| GET | `/api/forecast/<id>/<indicator>` | Прогноз показателя | ForecastService |
| GET | `/api/forecast/gdp-from-trade/<id>` | Прогноз ВВП | RegressionService |
| GET | `/api/regression/country/<id>` | Регрессионный анализ | RegressionService |
| POST | `/api/regression/predict` | Прогноз ВВП по значениям | RegressionService |
| GET | `/api/clustering/analyze` | Кластеризация стран | ClusteringService |
| DELETE | `/api/indicators/<id>` | Удаление показателя | IndicatorService |
| DELETE | `/api/countries/<id>` | Удаление страны | CountryService |
