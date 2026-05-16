import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2.pool import SimpleConnectionPool
from functools import wraps
from flask import g
from config import Config


class Database:
    """Класс для управления подключениями к БД"""
    
    _pool = None
    
    @classmethod
    def init_pool(cls):
        """Инициализация пула соединений"""
        if cls._pool is None:
            try:
                cls._pool = SimpleConnectionPool(
                    Config.DB_POOL_MIN_SIZE,
                    Config.DB_POOL_MAX_SIZE,
                    host=Config.DB_HOST,
                    port=Config.DB_PORT,
                    database=Config.DB_NAME,
                    user=Config.DB_USER,
                    password=Config.DB_PASSWORD,
                    sslmode=Config.DB_SSLMODE
                )
                print("✅ Connection pool created successfully")
            except Exception as e:
                print(f"❌ Failed to create connection pool: {e}")
                cls._pool = None
    
    @classmethod
    def get_connection(cls):
        """Получение соединения из пула"""
        if cls._pool:
            conn = cls._pool.getconn()
            conn.cursor_factory = RealDictCursor
            return conn
        else:
            # Fallback к прямому соединению
            return psycopg2.connect(**Config.get_db_params(), cursor_factory=RealDictCursor)
    
    @classmethod
    def return_connection(cls, conn):
        """Возврат соединения в пул"""
        if cls._pool and conn:
            cls._pool.putconn(conn)
    
    @classmethod
    def close_all_connections(cls):
        """Закрытие всех соединений в пуле"""
        if cls._pool:
            cls._pool.closeall()
    
    @classmethod
    def get_pool_stats(cls):
        """Получение статистики пула"""
        if cls._pool:
            return {
                'min': Config.DB_POOL_MIN_SIZE,
                'max': Config.DB_POOL_MAX_SIZE,
                'used': getattr(cls._pool, '_used', 0),
                'available': getattr(cls._pool, '_pool', None).qsize() if getattr(cls._pool, '_pool', None) else 0
            }
        return {}


def with_db_connection(f):
    """Декоратор для автоматического управления соединениями"""
    @wraps(f)
    def decorated(*args, **kwargs):
        conn = Database.get_connection()
        try:
            result = f(conn, *args, **kwargs)
            return result
        finally:
            Database.return_connection(conn)
    return decorated


# def init_database():
#     """Инициализация базы данных"""
#     conn = Database.get_connection()
#     cur = conn.cursor()
    
#     try:
#         # Создание таблиц
#         cur.execute("""
#             CREATE TABLE IF NOT EXISTS countries (
#                 id SERIAL PRIMARY KEY,
#                 name VARCHAR(100) NOT NULL UNIQUE,
#                 created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
#             )
#         """)
        
#         cur.execute("""
#             CREATE TABLE IF NOT EXISTS indicators (
#                 id SERIAL PRIMARY KEY,
#                 country_id INTEGER NOT NULL REFERENCES countries(id) ON DELETE CASCADE,
#                 year INTEGER NOT NULL,
#                 export_value DECIMAL(15, 2),
#                 import_value DECIMAL(15, 2),
#                 gdp_value DECIMAL(15, 2),
#                 updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
#                 UNIQUE(country_id, year)
#             )
#         """)
        
#         # Создание индексов для оптимизации
#         cur.execute("CREATE INDEX IF NOT EXISTS idx_indicators_country_year ON indicators(country_id, year)")
#         cur.execute("CREATE INDEX IF NOT EXISTS idx_indicators_year ON indicators(year)")
#         cur.execute("CREATE INDEX IF NOT EXISTS idx_countries_name ON countries(name)")
        
#         conn.commit()
#         print("✅ Database initialized successfully")
        
#         # Проверка наличия тестовых данных
#         cur.execute("SELECT COUNT(*) FROM countries")
#         count = cur.fetchone()['count']
        
#         if count == 0:
#             # Добавление тестовых данных
#             test_countries = ['Россия', 'США', 'Китай', 'Германия', 'Япония']
#             for country in test_countries:
#                 cur.execute("INSERT INTO countries (name) VALUES (%s) ON CONFLICT (name) DO NOTHING", (country,))
            
#             conn.commit()
#             print("✅ Test countries added")
            
#     except Exception as e:
#         print(f"❌ Database initialization error: {e}")
#         conn.rollback()
#     finally:
#         cur.close()
#         Database.return_connection(conn)

def init_database():
    """Инициализация базы данных"""
    conn = Database.get_connection()
    cur = conn.cursor()
    
    try:
        # Создание таблиц
        cur.execute("""
            CREATE TABLE IF NOT EXISTS countries (
                id SERIAL PRIMARY KEY,
                name VARCHAR(100) NOT NULL UNIQUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS indicators (
                id SERIAL PRIMARY KEY,
                country_id INTEGER NOT NULL REFERENCES countries(id) ON DELETE CASCADE,
                year INTEGER NOT NULL,
                export_value DECIMAL(15, 2),
                import_value DECIMAL(15, 2),
                gdp_value DECIMAL(15, 2),
                UNIQUE(country_id, year)
            )
        """)
        
        # Добавляем колонку updated_at если её нет
        try:
            cur.execute("""
                ALTER TABLE indicators 
                ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            """)
        except Exception as e:
            print(f"Note: {e}")
        
        # Создание индексов для оптимизации
        cur.execute("CREATE INDEX IF NOT EXISTS idx_indicators_country_year ON indicators(country_id, year)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_indicators_year ON indicators(year)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_countries_name ON countries(name)")
        
        conn.commit()
        print("✅ Database initialized successfully")
        
        # Проверка наличия тестовых данных
        cur.execute("SELECT COUNT(*) FROM countries")
        count = cur.fetchone()['count']
        
        if count == 0:
            # Добавление тестовых данных
            test_countries = ['Россия', 'США', 'Китай', 'Германия', 'Япония']
            for country in test_countries:
                cur.execute("INSERT INTO countries (name) VALUES (%s) ON CONFLICT (name) DO NOTHING", (country,))
            
            conn.commit()
            print("✅ Test countries added")
            
    except Exception as e:
        print(f"❌ Database initialization error: {e}")
        conn.rollback()
    finally:
        cur.close()
        Database.return_connection(conn)