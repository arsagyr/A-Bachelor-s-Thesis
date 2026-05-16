from flask import Blueprint, request, jsonify, send_file
from services.indicator_service import IndicatorService
from services.csv_import_service import CSVImportService
import io

indicators_bp = Blueprint('indicators', __name__)


@indicators_bp.route('/api/indicators/filter')
def filter_indicators():
    data = IndicatorService.filter_indicators(
        country_id=request.args.get('country_id', type=int),
        start_year=request.args.get('start_year', type=int),
        end_year=request.args.get('end_year', type=int),
        indicator_type=request.args.get('indicator_type', 'all')
    )
    return jsonify(data)


@indicators_bp.route('/api/stats/<int:country_id>')
def get_stats(country_id):
    stats = IndicatorService.get_country_stats(country_id)
    return jsonify(stats or {})


@indicators_bp.route('/api/add_indicator', methods=['POST'])
def add_indicator():
    data = request.json
    success, message = IndicatorService.add_or_update_indicator(
        country_id=data.get('country_id'),
        year=data.get('year'),
        export_value=data.get('export_value'),
        import_value=data.get('import_value'),
        gdp_value=data.get('gdp_value')
    )
    if success:
        return jsonify({'message': message})
    return jsonify({'error': message}), 400


@indicators_bp.route('/api/csv/preview', methods=['POST'])
def preview_csv():
    file = request.files['file']
    result = CSVImportService.preview_csv(file.read(), file.filename)
    if result['success']:
        return jsonify(result)
    return jsonify({'error': result['error']}), 400


@indicators_bp.route('/api/csv/import', methods=['POST'])
def import_csv():
    file = request.files['file']
    result = CSVImportService.import_csv(file.read(), file.filename)
    return jsonify(result)


@indicators_bp.route('/api/csv/template')
def download_template():
    return send_file(
        io.BytesIO(CSVImportService.generate_template()),
        mimetype='text/csv',
        as_attachment=True,
        download_name='import_template.csv'
    )