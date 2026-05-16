from flask import Blueprint, render_template, jsonify
from database import Database
from config import Config

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def index():
    """Главная страница"""
    return render_template('index.html')


@main_bp.route('/api/health', methods=['GET'])
def health_check():
    """Проверка работоспособности приложения"""
    try:
        conn = Database.get_connection()
        cur = conn.cursor()
        cur.execute("SELECT 1")
        cur.close()
        Database.return_connection(conn)
        
        return jsonify({
            'status': 'healthy',
            'database': 'connected',
            'pool_stats': Database.get_pool_stats(),
            'environment': Config.FLASK_DEBUG and 'development' or 'production'
        })
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e)
        }), 500