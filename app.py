from flask import Flask
from config import Config, config
from database import Database, init_database
from routes import register_routes


def create_app(config_name: str = 'default') -> Flask:
    app = Flask(__name__)
    
    # Загрузка конфигурации
    config_class = config.get(config_name, Config)
    app.config.from_object(config_class)
    
    # Инициализация базы данных
    Database.init_pool()
    
    # Регистрация маршрутов
    register_routes(app)
    
    return app


if __name__ == '__main__':
    # Создание приложения
    app = create_app()
    
    # Инициализация базы данных
    init_database()
    
    # Запуск приложения
    app.run(
        host=Config.FLASK_HOST,
        port=Config.FLASK_PORT,
        debug=Config.FLASK_DEBUG
    )