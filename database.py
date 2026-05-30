import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2.pool import SimpleConnectionPool
from functools import wraps
from config import Config


class Database:
    _pool = None
    
    @classmethod
    def init_pool(cls):
        if cls._pool is None:
            try:
                cls._pool = SimpleConnectionPool(
                    Config.DB_POOL_MIN_SIZE,
                    Config.DB_POOL_MAX_SIZE,
                    host=Config.DB_HOST,
                    port=Config.DB_PORT,
                    database=Config.DB_NAME,
                    user=Config.DB_USER,
                    password=Config.DB_PASSWORD
                )
                print("✅ Connection pool created")
            except Exception as e:
                print(f"❌ Failed to create pool: {e}")
                cls._pool = None
    
    @classmethod
    def get_connection(cls):
        if cls._pool:
            conn = cls._pool.getconn()
            conn.cursor_factory = RealDictCursor
            return conn
        return psycopg2.connect(**Config.get_db_params(), cursor_factory=RealDictCursor)
    
    @classmethod
    def return_connection(cls, conn):
        if cls._pool and conn:
            cls._pool.putconn(conn)


def with_db_connection(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        conn = Database.get_connection()
        try:
            result = f(conn, *args, **kwargs)
            return result
        finally:
            Database.return_connection(conn)
    return decorated


def init_database():
    """Инициализация базы данных по новой схеме: countries, indicators, statistics."""
    conn = Database.get_connection()
    cur = conn.cursor()
    
    try:
        # Таблица стран (без поля created_at)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS countries (
                id SERIAL PRIMARY KEY,
                name VARCHAR(100) NOT NULL UNIQUE
            )
        """)
        
        # Справочник показателей
        cur.execute("""
            CREATE TABLE IF NOT EXISTS indicators (
                id SERIAL PRIMARY KEY,
                name VARCHAR(100) NOT NULL UNIQUE
            )
        """)
        
        # Таблица значений показателей
        cur.execute("""
            CREATE TABLE IF NOT EXISTS statistics (
                country_id INTEGER NOT NULL REFERENCES countries(id) ON DELETE CASCADE,
                year INTEGER NOT NULL,
                indicator_id INTEGER NOT NULL REFERENCES indicators(id) ON DELETE CASCADE,
                value NUMERIC(20,2) NOT NULL,
                PRIMARY KEY (country_id, year, indicator_id)
            )
        """)
        
        # Индексы для ускорения запросов
        cur.execute("CREATE INDEX IF NOT EXISTS idx_statistics_country ON statistics(country_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_statistics_year ON statistics(year)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_statistics_indicator ON statistics(indicator_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_countries_name ON countries(name)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_indicators_name ON indicators(name)")
        
        # Добавляем базовые показатели (если таблица indicators пуста)
        cur.execute("SELECT COUNT(*) FROM indicators")
        count = cur.fetchone()['count']
        if count == 0:
            cur.execute("""
                INSERT INTO indicators (name) VALUES
                ('export_value'),
                ('import_value'),
                ('gdp_value')
                ON CONFLICT (name) DO NOTHING
            """)
            print("✅ Basic indicators added")
        
        conn.commit()
        print("✅ Database initialized with new schema (countries, indicators, statistics)")
    except Exception as e:
        print(f"❌ Error: {e}")
        conn.rollback()
    finally:
        cur.close()
        Database.return_connection(conn)