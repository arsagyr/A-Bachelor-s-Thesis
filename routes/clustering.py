from flask import Blueprint, request, jsonify
from services.clustering_service import ClusteringService
from services.indicator_service import IndicatorService
import traceback

clustering_bp = Blueprint('clustering', __name__)


@clustering_bp.route('/api/clustering/analyze', methods=['GET'])
def analyze_clusters():
    """Анализ кластеризации стран"""
    try:
        year = request.args.get('year', type=int)
        result = ClusteringService.analyze_country_clusters(year)
        
        if result.get('success'):
            return jsonify(result)
        return jsonify({'error': result.get('error', 'Ошибка кластеризации')}), 400
    except Exception as e:
        print(f"Error: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@clustering_bp.route('/api/clustering/available-years', methods=['GET'])
def get_clustering_available_years():
    """Получение доступных годов для кластеризации"""
    try:
        years = IndicatorService.get_available_years()
        return jsonify({'years': years})
    except Exception as e:
        print(f"Error: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500