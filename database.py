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
                    password=Config.DB_PASSWORD,
                    sslmode=Config.DB_SSLMODE
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
    """Инициализация базы данных - без тестовых данных"""
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
        
        # Создание индексов
        cur.execute("CREATE INDEX IF NOT EXISTS idx_indicators_country_year ON indicators(country_id, year)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_indicators_year ON indicators(year)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_countries_name ON countries(name)")
        
        conn.commit()
        print("✅ Database initialized successfully (no test data)")
        
    except Exception as e:
        print(f"❌ Database initialization error: {e}")
        conn.rollback()
    finally:
        cur.close()
        Database.return_connection(conn)