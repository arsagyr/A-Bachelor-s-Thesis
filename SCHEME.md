economic_dashboard/
├── app.py
├── config.py
├── database.py
├── requirements.txt
├── .env
├── .env.example
├── models/
│   ├── __init__.py
│   ├── country.py
│   ├── indicator.py
│   └── stats.py
├── services/
│   ├── __init__.py
│   ├── country_service.py
│   ├── indicator_service.py
│   ├── csv_import_service.py
│   ├── forecast_service.py
│   ├── regression_service.py
│   └── trend_service.py
├── calculations/
│   ├── __init__.py
│   ├── auto_regression.py
│   ├── metrics.py
│   ├── preprocessing.py
│   └── regression.py
├── routes/
│   ├── __init__.py
│   ├── countries.py
│   ├── indicators.py
│   ├── main.py
│   └── trends.py
├── utils/
│   ├── __init__.py
│   └── validators.py
├── static/
│   ├── css/
│   │   └── style.css
│   └── js/
│       └── main.js
└── templates/
    ├── index.html
    └── trends.html