"""
Скрипт для полного сброса базы данных
"""

import psycopg2
from psycopg2.extras import RealDictCursor
from config import Config


def reset_database():
    """Полный сброс БД"""
    answer = input("⚠️ ВНИМАНИЕ! Это удалит ВСЕ данные. Продолжить? (yes/no): ")
    
    if answer.lower() != 'yes':
        print("Операция отменена")
        return
    
    try:
        conn = psycopg2.connect(
            host=Config.DB_HOST,
            port=Config.DB_PORT,
            database=Config.DB_NAME,
            user=Config.DB_USER,
            password=Config.DB_PASSWORD,
            cursor_factory=RealDictCursor
        )
        
        cur = conn.cursor()
        
        # Удаляем таблицы
        cur.execute("DROP TABLE IF EXISTS indicators CASCADE")
        cur.execute("DROP TABLE IF EXISTS countries CASCADE")
        
        # Создаем заново
        cur.execute("""
            CREATE TABLE countries (
                id SERIAL PRIMARY KEY,
                name VARCHAR(100) NOT NULL UNIQUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE indicators (
                id SERIAL PRIMARY KEY,
                country_id INTEGER NOT NULL REFERENCES countries(id) ON DELETE CASCADE,
                year INTEGER NOT NULL,
                export_value DECIMAL(15, 2),
                import_value DECIMAL(15, 2),
                gdp_value DECIMAL(15, 2),
                UNIQUE(country_id, year)
            )
        """)
        
        conn.commit()
        cur.close()
        conn.close()
        
        print("✅ База данных успешно пересоздана (без тестовых данных)!")
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")


if __name__ == '__main__':
    reset_database()