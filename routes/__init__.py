from flask import Flask
from routes.countries import countries_bp
from routes.indicators import indicators_bp
from routes.main import main_bp


def register_routes(app: Flask):
    """Регистрация всех маршрутов"""
    app.register_blueprint(main_bp)
    app.register_blueprint(countries_bp)
    app.register_blueprint(indicators_bp)