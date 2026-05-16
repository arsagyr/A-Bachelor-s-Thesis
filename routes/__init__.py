from flask import Flask
from routes.countries import countries_bp
from routes.indicators import indicators_bp
from routes.main import main_bp


def register_routes(app: Flask) -> None:
    """
    Регистрация всех маршрутов в приложении
    
    Args:
        app: Экземпляр Flask приложения
    """
    app.register_blueprint(main_bp)
    app.register_blueprint(countries_bp)
    app.register_blueprint(indicators_bp)


__all__ = [
    'register_routes',
    'countries_bp',
    'indicators_bp',
    'main_bp'
]