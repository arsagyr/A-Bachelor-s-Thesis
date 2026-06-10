from flask import Blueprint, request, jsonify, send_file
from services.csv_import_service import CSVImportService
import io
import traceback

csv_bp = Blueprint('csv', __name__)


@csv_bp.route('/api/csv/preview', methods=['POST'])
def preview_csv():
    """Предпросмотр CSV файла"""
    if 'file' not in request.files:
        return jsonify({'error': 'Файл не загружен'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'Файл не выбран'}), 400
    try:
        result = CSVImportService.preview_csv(file.read(), file.filename)
        return jsonify(result) if result.get('success') else jsonify({'error': result.get('error')}), 400
    except Exception as e:
        print(f"Error: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@csv_bp.route('/api/csv/import', methods=['POST'])
def import_csv():
    """Импорт CSV файла"""
    if 'file' not in request.files:
        return jsonify({'error': 'Файл не загружен'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'Файл не выбран'}), 400
    try:
        result = CSVImportService.import_csv(file.read(), file.filename)
        return jsonify(result)
    except Exception as e:
        print(f"Error: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@csv_bp.route('/api/csv/template', methods=['GET'])
def download_template():
    """Скачивание шаблона CSV"""
    try:
        content = CSVImportService.generate_template()
        return send_file(
            io.BytesIO(content),
            mimetype='text/csv',
            as_attachment=True,
            download_name='import_template.csv'
        )
    except Exception as e:
        print(f"Error: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500