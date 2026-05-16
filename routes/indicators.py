from flask import Blueprint, request, jsonify
from services.indicator_service import IndicatorService
from flask import Blueprint, request, jsonify, send_file
from services.csv_import_service import CSVImportService
import io
import json

indicators_bp = Blueprint('indicators', __name__)




@indicators_bp.route('/api/indicators/<int:country_id>', methods=['GET'])
def get_indicators(country_id):
    """Получение показателей для страны"""
    indicators = IndicatorService.get_indicators_by_country(country_id)
    return jsonify(indicators)


@indicators_bp.route('/api/indicators/filter', methods=['GET'])
def filter_indicators():
    """Фильтрация показателей"""
    country_id = request.args.get('country_id', type=int)
    start_year = request.args.get('start_year', type=int)
    end_year = request.args.get('end_year', type=int)
    indicator_type = request.args.get('indicator_type', 'all')
    
    data = IndicatorService.filter_indicators(
        country_id=country_id,
        start_year=start_year,
        end_year=end_year,
        indicator_type=indicator_type
    )
    
    return jsonify(data)


@indicators_bp.route('/api/stats/<int:country_id>', methods=['GET'])
def get_stats(country_id):
    """Получение статистики по стране"""
    stats = IndicatorService.get_country_stats(country_id)
    if stats:
        return jsonify(stats)
    return jsonify({'error': 'Статистика не найдена'}), 404


@indicators_bp.route('/api/indicators/years', methods=['GET'])
def get_available_years():
    """Получение доступных годов"""
    years = IndicatorService.get_available_years()
    return jsonify(years)


@indicators_bp.route('/api/add_indicator', methods=['POST'])
def add_indicator():
    """Добавление показателя"""
    data = request.json
    country_id = data.get('country_id')
    year = data.get('year')
    export_value = data.get('export_value')
    import_value = data.get('import_value')
    gdp_value = data.get('gdp_value')
    
    if not all([country_id, year]):
        return jsonify({'error': 'Страна и год обязательны'}), 400
    
    success, message = IndicatorService.add_or_update_indicator(
        country_id=country_id,
        year=year,
        export_value=export_value,
        import_value=import_value,
        gdp_value=gdp_value
    )
    
    if success:
        return jsonify({'message': message})
    
    return jsonify({'error': message}), 400


@indicators_bp.route('/api/indicators/<int:indicator_id>', methods=['DELETE'])
def delete_indicator(indicator_id):
    """Удаление показателя"""
    success, message = IndicatorService.delete_indicator(indicator_id)
    if success:
        return jsonify({'message': message})
    return jsonify({'error': message}), 404


# @indicators_bp.route('/api/csv/preview', methods=['POST'])
# def preview_csv():
#     """
#     Предпросмотр CSV файла
#     """
#     if 'file' not in request.files:
#         return jsonify({'error': 'Файл не загружен'}), 400
    
#     file = request.files['file']
#     if file.filename == '':
#         return jsonify({'error': 'Файл не выбран'}), 400
    
#     if not (file.filename.endswith('.csv') or file.filename.endswith('.xlsx')):
#         return jsonify({'error': 'Поддерживаются только CSV и Excel файлы'}), 400
    
#     try:
#         file_content = file.read()
#         preview_result = CSVImportService.preview_csv(file_content, file.filename)
        
#         if preview_result['success']:
#             return jsonify(preview_result)
#         else:
#             return jsonify({'error': preview_result['error']}), 400
            
#     except Exception as e:
#         return jsonify({'error': f'Ошибка при обработке файла: {str(e)}'}), 500


# @indicators_bp.route('/api/csv/import', methods=['POST'])
# def import_csv():
#     """
#     Импорт CSV файла в базу данных
#     """
#     if 'file' not in request.files:
#         return jsonify({'error': 'Файл не загружен'}), 400
    
#     file = request.files['file']
#     if file.filename == '':
#         return jsonify({'error': 'Файл не выбран'}), 400
    
#     if not (file.filename.endswith('.csv') or file.filename.endswith('.xlsx')):
#         return jsonify({'error': 'Поддерживаются только CSV и Excel файлы'}), 400
    
#     # Получаем пользовательский маппинг если есть
#     custom_mapping = request.form.get('mapping')
#     if custom_mapping:
#         import json
#         custom_mapping = json.loads(custom_mapping)
    
#     try:
#         file_content = file.read()
#         import_result = CSVImportService.import_csv(
#             file_content, 
#             file.filename, 
#             custom_mapping
#         )
        
#         return jsonify(import_result)
        
#     except Exception as e:
#         return jsonify({'error': f'Ошибка при импорте: {str(e)}'}), 500


# @indicators_bp.route('/api/csv/template', methods=['GET'])
# def download_template():
#     """
#     Скачивание шаблона CSV файла
#     """
#     template_content = CSVImportService.generate_template()
    
#     return send_file(
#         io.BytesIO(template_content),
#         mimetype='text/csv',
#         as_attachment=True,
#         download_name='import_template.csv'
#     )


# @indicators_bp.route('/api/csv/mapping-options', methods=['GET'])
# def get_mapping_options():
#     """
#     Получение вариантов маппинга колонок
#     """
#     return jsonify({
#         'available_mappings': list(CSVImportService.COLUMN_MAPPING.keys()),
#         'column_keywords': CSVImportService.COLUMN_MAPPING
#     })


# ... существующие маршруты ...


@indicators_bp.route('/api/csv/preview', methods=['POST'])
def preview_csv():
    """Предпросмотр CSV файла"""
    if 'file' not in request.files:
        return jsonify({'error': 'Файл не загружен'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'Файл не выбран'}), 400
    
    if not (file.filename.endswith('.csv') or file.filename.endswith('.xlsx')):
        return jsonify({'error': 'Поддерживаются только CSV и Excel файлы'}), 400
    
    try:
        file_content = file.read()
        preview_result = CSVImportService.preview_csv(file_content, file.filename)
        
        if preview_result['success']:
            return jsonify(preview_result)
        else:
            return jsonify({'error': preview_result['error']}), 400
            
    except Exception as e:
        return jsonify({'error': f'Ошибка при обработке файла: {str(e)}'}), 500


@indicators_bp.route('/api/csv/import', methods=['POST'])
def import_csv():
    """Импорт CSV файла в базу данных"""
    if 'file' not in request.files:
        return jsonify({'error': 'Файл не загружен'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'Файл не выбран'}), 400
    
    if not (file.filename.endswith('.csv') or file.filename.endswith('.xlsx')):
        return jsonify({'error': 'Поддерживаются только CSV и Excel файлы'}), 400
    
    # Получаем пользовательский маппинг если есть
    custom_mapping = request.form.get('mapping')
    if custom_mapping:
        try:
            custom_mapping = json.loads(custom_mapping)
        except:
            pass
    
    try:
        file_content = file.read()
        import_result = CSVImportService.import_csv(
            file_content, 
            file.filename, 
            custom_mapping
        )
        
        return jsonify(import_result)
        
    except Exception as e:
        return jsonify({'error': f'Ошибка при импорте: {str(e)}'}), 500


@indicators_bp.route('/api/csv/template', methods=['GET'])
def download_template():
    """Скачивание шаблона CSV файла"""
    try:
        template_content = CSVImportService.generate_template()
        
        return send_file(
            io.BytesIO(template_content),
            mimetype='text/csv',
            as_attachment=True,
            download_name='import_template.csv'
        )
    except Exception as e:
        return jsonify({'error': f'Ошибка при создании шаблона: {str(e)}'}), 500


@indicators_bp.route('/api/csv/mapping-options', methods=['GET'])
def get_mapping_options():
    """Получение вариантов маппинга колонок"""
    return jsonify({
        'available_mappings': list(CSVImportService.COLUMN_MAPPING.keys()),
        'column_keywords': CSVImportService.COLUMN_MAPPING
    })