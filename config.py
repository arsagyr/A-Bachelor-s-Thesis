import os
from dotenv import load_dotenv

# Загрузка переменных окружения
load_dotenv()


class Config:
    """Основная конфигурация приложения"""
    
    # Database config
    DB_HOST = os.getenv('DB_HOST', 'localhost')
    DB_PORT = int(os.getenv('DB_PORT', 5432))
    DB_NAME = os.getenv('DB_NAME', 'postgres')
    DB_USER = os.getenv('DB_USER', 'postgres')
    DB_PASSWORD = os.getenv('DB_PASSWORD', '')
    DB_SSLMODE = os.getenv('DB_SSLMODE', 'prefer')
    
    # Pool settings
    DB_POOL_MIN_SIZE = int(os.getenv('DB_POOL_MIN_SIZE', 1))
    DB_POOL_MAX_SIZE = int(os.getenv('DB_POOL_MAX_SIZE', 10))
    
    # Flask config
    FLASK_HOST = os.getenv('FLASK_HOST', '0.0.0.0')
    FLASK_PORT = int(os.getenv('FLASK_PORT', 5000))
    FLASK_DEBUG = os.getenv('FLASK_DEBUG', 'True').lower() == 'true'
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    
    @classmethod
    def get_db_params(cls):
        """Получение параметров подключения к БД"""
        return {
            'host': cls.DB_HOST,
            'port': cls.DB_PORT,
            'database': cls.DB_NAME,
            'user': cls.DB_USER,
            'password': cls.DB_PASSWORD,
            'sslmode': cls.DB_SSLMODE,
        }


class DevelopmentConfig(Config):
    """Конфигурация для разработки"""
    FLASK_DEBUG = True
    DB_POOL_MIN_SIZE = 1
    DB_POOL_MAX_SIZE = 5


class ProductionConfig(Config):
    """Конфигурация для продакшена"""
    FLASK_DEBUG = False
    DB_POOL_MIN_SIZE = 5
    DB_POOL_MAX_SIZE = 20


class TestingConfig(Config):
    """Конфигурация для тестирования"""
    TESTING = True
    DB_NAME = os.getenv('TEST_DB_NAME', 'test_db')


# Словарь конфигураций
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}