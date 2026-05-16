```
project/
├── app.py                 # Главный файл приложения
├── .env                   # Переменные окружения
├── .env.example          # Шаблон переменных окружения
├── requirements.txt      # Зависимости
├── config.py             # Конфигурация приложения
├── database.py           # Работа с базой данных
├── models/               # ПАКЕТ моделей данных
│   ├── __init__.py
│   ├── country.py
│   ├── indicator.py
│   └── stats.py
├── routes/               # ПАКЕТ маршрутов
│   ├── __init__.py
│   ├── countries.py
│   ├── indicators.py
│   └── main.py
├── services/             # ПАКЕТ сервисов
│   ├── __init__.py
│   ├── country_service.py
│   └── indicator_service.py
├── utils/                # ПАКЕТ утилит
│   ├── __init__.py
│   └── validators.py
└── templates/
    └── index.html
```


New-Item -Path config.py, database.py,  models.py,   routes/__init__.py, routes/countries.py, routes/indicators.py, routes/main.py, services/__init__.py, services/country_service.py, services/indicator_service.py,  utils/__init__.py, utils/validators.py