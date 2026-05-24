"""
Сервис для регрессионного анализа (API слой)
"""

import numpy as np
import pandas as pd
from typing import Dict, Any
from decimal import Decimal
from database import with_db_connection
from calculations.regression_calc import predict_gdp_by_regression


class RegressionService:
    """Сервис для регрессионного анализа ВВП"""
    
    @staticmethod
    @with_db_connection
    def get_gdp_forecast(conn, country_id: int, steps: int = 5, model_type: str = 'linear', **kwargs) -> Dict[str, Any]:
        """Прогноз ВВП на основе экспорта и импорта"""
        cur = conn.cursor()
        cur.execute("""
            SELECT year, export_value, import_value, gdp_value
            FROM indicators 
            WHERE country_id = %s 
              AND export_value IS NOT NULL 
              AND import_value IS NOT NULL 
              AND gdp_value IS NOT NULL
            ORDER BY year
        """, (country_id,))
        data = cur.fetchall()
        cur.close()
        
        if len(data) < 4:
            return {'success': False, 'error': f'Недостаточно данных: {len(data)} точек'}
        
        cur = conn.cursor()
        cur.execute("SELECT name FROM countries WHERE id = %s", (country_id,))
        country = cur.fetchone()
        cur.close()
        
        rows = []
        for row in data:
            rows.append({
                'year': row['year'],
                'export': float(row['export_value']) if row['export_value'] else 0.0,
                'import': float(row['import_value']) if row['import_value'] else 0.0,
                'gdp': float(row['gdp_value']) if row['gdp_value'] else 0.0
            })
        
        df = pd.DataFrame(rows)
        
        historical_years = df['year'].tolist()
        historical_export = df['export'].tolist()
        historical_import = df['import'].tolist()
        historical_gdp = df['gdp'].tolist()
        last_year = historical_years[-1]
        forecast_years = [last_year + i + 1 for i in range(steps)]
        
        result = predict_gdp_by_regression(df, steps, model_type, **kwargs)
        
        if not result.get('success'):
            return {'success': False, 'error': result.get('error', 'Ошибка регрессии')}
        
        # Извлекаем метрики
        metrics = result.get('metrics', {})
        
        coefficients = result.get('coefficients', [])
        intercept = result.get('intercept', 0)
        export_forecast = result.get('export_forecast', [])
        import_forecast = result.get('import_forecast', [])
        gdp_forecast = result.get('forecast', [])
        
        # Строим модельную линию
        n = len(historical_years)
        total_points = n + steps
        model_predictions = []
        
        for i in range(total_points):
            if i < n:
                pred_export = historical_export[i]
                pred_import = historical_import[i]
            else:
                idx = i - n
                pred_export = export_forecast[idx] if idx < len(export_forecast) else historical_export[-1]
                pred_import = import_forecast[idx] if idx < len(import_forecast) else historical_import[-1]
            
            features = np.array([
                pred_export, pred_import,
                pred_export * pred_import,
                pred_export ** 2,
                pred_import ** 2,
                pred_export - pred_import,
                pred_export + pred_import
            ], dtype=float)
            
            coeffs = np.array(coefficients, dtype=float)
            pred_gdp = intercept + np.sum(coeffs * features)
            model_predictions.append(float(pred_gdp))
        
        # Формула
        formula_parts = [f"{intercept:.4f}"]
        names = ['Э', 'И', 'Э×И', 'Э²', 'И²', 'Сальдо', 'Оборот']
        for i, (coef, name) in enumerate(zip(coefficients[:7], names[:7])):
            if abs(coef) > 1e-10:
                sign = '+' if coef > 0 else '-'
                formula_parts.append(f" {sign} {abs(coef):.4f}·{name}")
        
        formula = "ВВП = " + ''.join(formula_parts)
        
        return {
            'success': True,
            'country_name': country['name'],
            'model_type': model_type,
            'historical': {
                'years': historical_years,
                'export': historical_export,
                'import': historical_import,
                'gdp': historical_gdp
            },
            'forecast_years': forecast_years,
            'forecast': {
                'export': export_forecast,
                'import': import_forecast,
                'gdp': gdp_forecast
            },
            'model_predictions': model_predictions,
            'metrics': {
                'r2': metrics.get('r2', 0),
                'rmse': metrics.get('rmse', 0),
                'mae': metrics.get('mae', 0),
                'mape': metrics.get('mape', 0)
            },
            'coefficients': coefficients,
            'intercept': intercept,
            'formula': formula
        }