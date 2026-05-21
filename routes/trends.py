from flask import Blueprint, render_template, request, jsonify
from services.trend_analysis_service import TrendAnalysisService
import numpy as np
from database import Database

trends_bp = Blueprint('trends', __name__)


@trends_bp.route('/trends')
def trends_page():
    """Страница трендового анализа всех стран"""
    return render_template('trends.html')


@trends_bp.route('/api/trends/all-countries', methods=['GET'])
def get_all_countries_trends():
    """Получение трендов для всех стран"""
    try:
        indicator = request.args.get('indicator', 'gdp')
        steps = request.args.get('steps', 5, type=int)
        steps = min(steps, 10)
        
        if indicator not in ['export', 'import', 'gdp']:
            return jsonify({'error': 'Неверный тип показателя'}), 400
        
        result = TrendAnalysisService.get_all_countries_trends(indicator, steps)
        
        if result.get('success'):
            return jsonify(result)
        else:
            return jsonify({'error': result.get('error', 'Ошибка анализа')}), 400
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@trends_bp.route('/api/trends/single-country/<int:country_id>/<indicator>', methods=['GET'])
def get_single_country_trend(country_id, indicator):
    """Получение трендов для одной страны"""
    try:
        steps = request.args.get('steps', 5, type=int)
        steps = min(steps, 10)
        
        if indicator not in ['export', 'import', 'gdp']:
            return jsonify({'error': 'Неверный тип показателя'}), 400
        
        conn = Database.get_connection()
        
        try:
            cur = conn.cursor()
            query = f"""
                SELECT year, {indicator}_value as value
                FROM indicators 
                WHERE country_id = %s AND {indicator}_value IS NOT NULL
                ORDER BY year
            """
            cur.execute(query, (country_id,))
            data = cur.fetchall()
            cur.close()
            
            if len(data) < 3:
                return jsonify({'error': 'Недостаточно данных'}), 400
            
            cur = conn.cursor()
            cur.execute("SELECT name FROM countries WHERE id = %s", (country_id,))
            country = cur.fetchone()
            cur.close()
            
            if not country:
                return jsonify({'error': 'Страна не найдена'}), 404
            
            years = np.array([d['year'] for d in data])
            values = np.array([float(d['value']) for d in data])
            X = np.arange(len(values))
            
            result = TrendAnalysisService.analyze_single_country(
                X, values, years.tolist(), country_id, country['name'], indicator, steps
            )
            
            return jsonify({'success': True, 'data': result})
            
        finally:
            Database.return_connection(conn)
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500