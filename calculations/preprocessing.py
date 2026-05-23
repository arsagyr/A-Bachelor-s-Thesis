"""
Предобработка данных для регрессионного анализа
"""

import numpy as np
from decimal import Decimal


def decimal_to_float(value):
    """Преобразование Decimal в float"""
    if isinstance(value, Decimal):
        return float(value)
    return value


def convert_data_to_float(data):
    """Преобразование всех Decimal значений в float в списке словарей"""
    converted = []
    for row in data:
        new_row = {}
        for key, val in row.items():
            if isinstance(val, Decimal):
                new_row[key] = float(val)
            else:
                new_row[key] = val
        converted.append(new_row)
    return converted


def prepare_regression_features(export_values, import_values):
    """
    Подготовка признаков для регрессии ВВП от экспорта и импорта
    
    Args:
        export_values: список значений экспорта
        import_values: список значений импорта
    
    Returns:
        features: матрица признаков (7 столбцов)
        feature_names: названия признаков
    """
    export = np.array([float(x) for x in export_values])
    import_val = np.array([float(x) for x in import_values])
    
    # Создаем признаки
    features = np.column_stack([
        export,                    # 1. Экспорт
        import_val,                # 2. Импорт
        export * import_val,       # 3. Взаимодействие экспорта и импорта
        export ** 2,               # 4. Квадрат экспорта
        import_val ** 2,           # 5. Квадрат импорта
        export - import_val,       # 6. Торговое сальдо
        export + import_val        # 7. Торговый оборот
    ])
    
    feature_names = [
        'экспорт', 
        'импорт', 
        'экспорт×импорт', 
        'экспорт²', 
        'импорт²', 
        'торговое сальдо', 
        'торговый оборот'
    ]
    
    return features, feature_names


def prepare_time_series_features(series):
    """Подготовка признаков для прогнозирования временных рядов"""
    X = np.arange(len(series)).reshape(-1, 1)
    y = np.array([float(x) for x in series])
    return X, y


def normalize_features(features):
    """Нормализация признаков (StandardScaler)"""
    from sklearn.preprocessing import StandardScaler
    scaler = StandardScaler()
    features_scaled = scaler.fit_transform(features)
    return features_scaled, scaler