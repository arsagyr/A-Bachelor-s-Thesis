"""
Скрипт для проверки корректности всех импортов
Запустите для тестирования: python check_imports.py
"""

def test_imports():
    """Тестирование всех импортов"""
    try:
        print("Testing imports...")
        
        # Тестирование config
        from config import Config
        print("✓ Config imported")
        
        # Тестирование database
        from database import Database, with_db_connection, init_database
        print("✓ Database imported")
        
        # Тестирование models
        from models import Country, Indicator, CountryStats
        print("✓ Models imported")
        
        # Тестирование utils
        from utils import Validators
        print("✓ Utils imported")
        
        # Тестирование services
        from services import CountryService, IndicatorService
        print("✓ Services imported")
        
        # Тестирование routes
        from routes import register_routes, countries_bp, indicators_bp, main_bp
        print("✓ Routes imported")
        
        # Тестирование app
        from app import create_app
        print("✓ App factory imported")
        
        print("\n✅ All imports successful!")
        return True
        
    except ImportError as e:
        print(f"\n❌ Import error: {e}")
        return False


if __name__ == '__main__':
    test_imports()