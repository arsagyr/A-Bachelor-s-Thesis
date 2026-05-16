import os
from flask import Flask, render_template, request, jsonify
import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2.pool import SimpleConnectionPool
from dotenv import load_dotenv
import pandas as pd
from datetime import datetime
from functools import wraps

# Загрузка переменных окружения
load_dotenv()

app = Flask(__name__)

# Конфигурация из переменных окружения
class Config:
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
            'cursor_factory': RealDictCursor
        }

# Создание пула соединений
try:
    db_params = Config.get_db_params()
    # Удаляем cursor_factory из параметров для пула
    pool_params = {k: v for k, v in db_params.items() if k != 'cursor_factory'}
    connection_pool = SimpleConnectionPool(
        Config.DB_POOL_MIN_SIZE,
        Config.DB_POOL_MAX_SIZE,
        **pool_params
    )
    print("✅ Connection pool created successfully")
except Exception as e:
    print(f"❌ Failed to create connection pool: {e}")
    connection_pool = None

def get_db_connection():
    """Получение соединения из пула"""
    if connection_pool:
        conn = connection_pool.getconn()
        # Устанавливаем cursor_factory для каждого соединения
        conn.cursor_factory = RealDictCursor
        return conn
    else:
        # Fallback к прямому соединению
        return psycopg2.connect(**Config.get_db_params())

def return_db_connection(conn):
    """Возврат соединения в пул"""
    if connection_pool and conn:
        connection_pool.putconn(conn)

def with_db_connection(f):
    """Декоратор для автоматического управления соединениями"""
    @wraps(f)
    def decorated(*args, **kwargs):
        conn = get_db_connection()
        try:
            result = f(conn, *args, **kwargs)
            return result
        finally:
            return_db_connection(conn)
    return decorated

def init_database():
    """Инициализация базы данных"""
    conn = get_db_connection()
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
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(country_id, year)
            )
        """)
        
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
        return_db_connection(conn)

@app.route('/')
def index():
    """Главная страница"""
    return render_template('index.html')

@app.route('/api/countries')
@with_db_connection
def get_countries(conn):
    """Получение списка стран"""
    cur = conn.cursor()
    cur.execute("SELECT id, name FROM countries ORDER BY name")
    countries = cur.fetchall()
    cur.close()
    return jsonify(countries)

@app.route('/api/indicators/<int:country_id>')
@with_db_connection
def get_indicators(conn, country_id):
    """Получение показателей для страны"""
    cur = conn.cursor()
    cur.execute("""
        SELECT year, export_value, import_value, gdp_value 
        FROM indicators 
        WHERE country_id = %s 
        ORDER BY year
    """, (country_id,))
    indicators = cur.fetchall()
    cur.close()
    return jsonify(indicators)

@app.route('/api/indicators/filter')
@with_db_connection
def filter_indicators(conn):
    """Фильтрация показателей по параметрам"""
    country_id = request.args.get('country_id', type=int)
    start_year = request.args.get('start_year', type=int)
    end_year = request.args.get('end_year', type=int)
    indicator_type = request.args.get('indicator_type', 'all')
    
    query = """
        SELECT i.year, i.export_value, i.import_value, i.gdp_value, c.name as country_name
        FROM indicators i
        JOIN countries c ON i.country_id = c.id
        WHERE 1=1
    """
    params = []
    
    if country_id:
        query += " AND i.country_id = %s"
        params.append(country_id)
    
    if start_year:
        query += " AND i.year >= %s"
        params.append(start_year)
    
    if end_year:
        query += " AND i.year <= %s"
        params.append(end_year)
    
    query += " ORDER BY i.year"
    
    cur = conn.cursor()
    cur.execute(query, params)
    data = cur.fetchall()
    cur.close()
    
    # Фильтрация по типу показателя
    if indicator_type != 'all':
        for row in data:
            if indicator_type == 'export':
                row['import_value'] = None
                row['gdp_value'] = None
            elif indicator_type == 'import':
                row['export_value'] = None
                row['gdp_value'] = None
            elif indicator_type == 'gdp':
                row['export_value'] = None
                row['import_value'] = None
    
    return jsonify(data)

@app.route('/api/stats/<int:country_id>')
@with_db_connection
def get_stats(conn, country_id):
    """Получение статистики по стране"""
    cur = conn.cursor()
    cur.execute("""
        SELECT 
            COUNT(*) as years_count,
            MIN(year) as min_year,
            MAX(year) as max_year,
            AVG(export_value) as avg_export,
            AVG(import_value) as avg_import,
            AVG(gdp_value) as avg_gdp,
            MAX(export_value) as max_export,
            MAX(import_value) as max_import,
            MAX(gdp_value) as max_gdp,
            MIN(export_value) as min_export,
            MIN(import_value) as min_import,
            MIN(gdp_value) as min_gdp
        FROM indicators 
        WHERE country_id = %s
    """, (country_id,))
    stats = cur.fetchone()
    cur.close()
    
    # Преобразование None в 0 для числовых значений
    if stats:
        for key in stats.keys():
            if stats[key] is None:
                stats[key] = 0
    
    return jsonify(stats)

@app.route('/api/indicators/years')
@with_db_connection
def get_available_years(conn):
    """Получение доступных годов"""
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT year FROM indicators ORDER BY year")
    years = [row['year'] for row in cur.fetchall()]
    cur.close()
    return jsonify(years)

@app.route('/api/add_country', methods=['POST'])
@with_db_connection
def add_country(conn):
    """Добавление новой страны"""
    data = request.json
    name = data.get('name')
    
    if not name:
        return jsonify({'error': 'Название страны обязательно'}), 400
    
    cur = conn.cursor()
    try:
        cur.execute(
            "INSERT INTO countries (name) VALUES (%s) RETURNING id, name, created_at",
            (name,)
        )
        new_country = cur.fetchone()
        conn.commit()
        return jsonify(new_country)
    except psycopg2.IntegrityError:
        conn.rollback()
        return jsonify({'error': 'Страна уже существует'}), 400
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        cur.close()

@app.route('/api/add_indicator', methods=['POST'])
@with_db_connection
def add_indicator(conn):
    """Добавление показателя"""
    data = request.json
    country_id = data.get('country_id')
    year = data.get('year')
    export_value = data.get('export_value')
    import_value = data.get('import_value')
    gdp_value = data.get('gdp_value')
    
    if not all([country_id, year]):
        return jsonify({'error': 'Страна и год обязательны'}), 400
    
    cur = conn.cursor()
    try:
        # Проверка существования страны
        cur.execute("SELECT id FROM countries WHERE id = %s", (country_id,))
        if not cur.fetchone():
            return jsonify({'error': 'Страна не найдена'}), 404
        
        cur.execute("""
            INSERT INTO indicators (country_id, year, export_value, import_value, gdp_value, updated_at)
            VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
            ON CONFLICT (country_id, year) DO UPDATE SET
                export_value = EXCLUDED.export_value,
                import_value = EXCLUDED.import_value,
                gdp_value = EXCLUDED.gdp_value,
                updated_at = CURRENT_TIMESTAMP
            RETURNING id
        """, (country_id, year, export_value, import_value, gdp_value))
        
        conn.commit()
        return jsonify({'message': 'Показатель успешно добавлен'})
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        cur.close()

@app.route('/api/health')
def health_check():
    """Проверка работоспособности приложения"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT 1")
        cur.close()
        return_db_connection(conn)
        
        return jsonify({
            'status': 'healthy',
            'database': 'connected',
            'pool_stats': {
                'min': Config.DB_POOL_MIN_SIZE,
                'max': Config.DB_POOL_MAX_SIZE,
                'used': connection_pool._used if connection_pool else 0,
                'available': connection_pool._pool.qsize() if connection_pool else 0
            } if connection_pool else {}
        })
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e)
        }), 500

@app.teardown_appcontext
def shutdown_session(exception=None):
    """Очистка при завершении"""
    pass

if __name__ == '__main__':
    # Инициализация базы данных
    init_database()
    
    # Запуск приложения
    app.run(
        host=Config.FLASK_HOST,
        port=Config.FLASK_PORT,
        debug=Config.FLASK_DEBUG
    )