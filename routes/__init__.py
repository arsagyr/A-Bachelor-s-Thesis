from flask import Flask

# Импортируем все Blueprint'ы
from .main import main_bp
from .countries import countries_bp
from .indicators import indicators_bp
from .forecast import forecast_bp
from .regression import regression_bp
from .clustering import clustering_bp
from .csv_import import csv_bp
from .irwin import irwin_bp
from .trend import trend_bp


def register_routes(app: Flask):
    """Регистрация всех маршрутов"""
    app.register_blueprint(main_bp)
    app.register_blueprint(countries_bp)
    app.register_blueprint(indicators_bp)
    app.register_blueprint(forecast_bp)
    app.register_blueprint(regression_bp)
    app.register_blueprint(clustering_bp)
    app.register_blueprint(csv_bp)
    app.register_blueprint(irwin_bp)
    app.register_blueprint(trend_bp)