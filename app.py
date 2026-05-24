from flask import Flask
from config import Config
from database import Database, init_database
from routes import register_routes


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    
    app.static_folder = 'static'
    app.static_url_path = '/static'
    
    Database.init_pool()
    register_routes(app)
    
    # Вывод всех маршрутов для отладки
    print("\n" + "="*50)
    print("ЗАРЕГИСТРИРОВАННЫЕ МАРШРУТЫ:")
    for rule in app.url_map.iter_rules():
        print(f"  {rule}")
    print("="*50 + "\n")
    
    return app


if __name__ == '__main__':
    app = create_app()
    init_database()
    app.run(
        host=Config.FLASK_HOST,
        port=Config.FLASK_PORT,
        debug=Config.FLASK_DEBUG
    )