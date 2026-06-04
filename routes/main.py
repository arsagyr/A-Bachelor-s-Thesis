from flask import Blueprint, render_template
from flask import send_from_directory, current_app


main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def index():
    return render_template('index.html')

@main_bp.route('/favicon.ico', methods=['GET'])
def favicon():
    try:
        return send_from_directory(current_app.static_folder, 'favicon.ico')
    except:
        # Если файл отсутствует, возвращаем пустой ответ (204 No Content)
        return '', 204