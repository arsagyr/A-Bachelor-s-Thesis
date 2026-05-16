```
economic_dashboard/
├── app.py                          # Главный файл приложения
├── config.py                       # Конфигурация (env)
├── database.py                     # Работа с БД и пул соединений
├── requirements.txt                # Зависимости
├── .env                           # Переменные окружения (создать самому)
├── .env.example                   # Шаблон env
├── fix_database.py                # Скрипт исправления БД
├── reset_database.py              # Скрипт сброса БД
├── test_csv_import.py             # Тест импорта CSV
├── models/                        # Модели данных
│   ├── __init__.py
│   ├── country.py
│   ├── indicator.py
│   └── stats.py
├── routes/                        # Маршруты API
│   ├── __init__.py
│   ├── countries.py
│   ├── indicators.py
│   └── main.py
├── services/                      # Бизнес-логика
│   ├── __init__.py
│   ├── country_service.py
│   ├── indicator_service.py
│   └── csv_import_service.py
├── utils/                         # Утилиты
│   ├── __init__.py
│   └── validators.py
└── templates/                     # HTML шаблоны
    └── index.html
```


New-Item -Path config.py, database.py,  models.py,   routes/__init__.py, routes/countries.py, routes/indicators.py, routes/main.py, services/__init__.py, services/country_service.py, services/indicator_service.py,  utils/__init__.py, utils/validators.py