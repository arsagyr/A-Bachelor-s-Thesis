import pandas as pd
import io
from typing import Dict, List, Any
from database import Database
from repositories.country_repository import CountryRepository
from repositories.indicator_repository import IndicatorRepository
from repositories.statistics_repository import StatisticsRepository
from models.statistics import Statistics


class CSVImportService:

    COLUMN_MAPPING = {
        'country': {'keywords': ['country', 'страна', 'name'], 'required': True},
        'year': {'keywords': ['year', 'год'], 'required': True},
        'export': {'keywords': ['export', 'экспорт'], 'required': False},
        'import': {'keywords': ['import', 'импорт'], 'required': False},
        'gdp': {'keywords': ['gdp', 'ввп'], 'required': False},
        'population': {'keywords': ['population', 'население', 'people'], 'required': False}
    }

    @classmethod
    def detect_columns(cls, columns: List[str]) -> Dict[str, str]:
        detected = {}
        for data_type, config in cls.COLUMN_MAPPING.items():
            for col in columns:
                col_lower = col.lower()
                for keyword in config['keywords']:
                    if keyword in col_lower:
                        detected[data_type] = col
                        break
                if data_type in detected:
                    break
        return detected

    @classmethod
    def preview_csv(cls, file_content: bytes, filename: str) -> Dict[str, Any]:
        try:
            df = pd.read_csv(io.BytesIO(file_content), nrows=5, encoding='utf-8')
            column_mapping = cls.detect_columns(df.columns.tolist())
            return {
                'success': True,
                'columns': df.columns.tolist(),
                'detected_mapping': column_mapping,
                'preview': df.head(3).to_dict('records'),
                'total_rows': len(df)
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}

    @classmethod
    def import_csv(cls, file_content: bytes, filename: str,
                   custom_mapping: Dict[str, str] = None) -> Dict[str, Any]:
        results = {'success': True, 'total_rows': 0, 'imported_rows': 0, 'errors': []}
        conn = None

        try:
            conn = Database.get_connection()
            df = pd.read_csv(io.BytesIO(file_content), encoding='utf-8')
            results['total_rows'] = len(df)

            mapping = custom_mapping or cls.detect_columns(df.columns.tolist())

            country_repo = CountryRepository(conn)
            indicator_repo = IndicatorRepository(conn)
            stats_repo = StatisticsRepository(conn)

            # Получаем или создаём id для индикаторов (включая население)
            indicator_ids = {}
            for ind_name in ['export_value', 'import_value', 'gdp_value', 'population_value']:
                ind = indicator_repo.get_by_name(ind_name)
                if not ind:
                    ind = indicator_repo.create(ind_name)
                indicator_ids[ind_name] = ind.id

            for idx, row in df.iterrows():
                try:
                    country_name = str(row[mapping['country']]).strip()
                    year = int(row[mapping['year']])

                    # Страна
                    country = country_repo.get_by_name(country_name)
                    if not country:
                        country = country_repo.create(country_name)

                    # Значения
                    export_val = None
                    if mapping.get('export') and pd.notna(row[mapping['export']]):
                        export_val = float(row[mapping['export']])

                    import_val = None
                    if mapping.get('import') and pd.notna(row[mapping['import']]):
                        import_val = float(row[mapping['import']])

                    gdp_val = None
                    if mapping.get('gdp') and pd.notna(row[mapping['gdp']]):
                        gdp_val = float(row[mapping['gdp']])

                    population_val = None
                    if mapping.get('population') and pd.notna(row[mapping['population']]):
                        population_val = float(row[mapping['population']])

                    # Сохраняем каждый индикатор
                    if export_val is not None:
                        stats_repo.upsert(Statistics(country.id, year, indicator_ids['export_value'], export_val))
                    if import_val is not None:
                        stats_repo.upsert(Statistics(country.id, year, indicator_ids['import_value'], import_val))
                    if gdp_val is not None:
                        stats_repo.upsert(Statistics(country.id, year, indicator_ids['gdp_value'], gdp_val))
                    if population_val is not None:
                        stats_repo.upsert(Statistics(country.id, year, indicator_ids['population_value'], population_val))

                    results['imported_rows'] += 1

                except Exception as e:
                    results['errors'].append(f"Строка {idx+1}: {str(e)}")
                    conn.rollback()
                else:
                    conn.commit()

        except Exception as e:
            results['success'] = False
            results['errors'].append(str(e))
        finally:
            if conn:
                Database.return_connection(conn)

        return results

    @classmethod
    def generate_template(cls) -> bytes:
        df = pd.DataFrame({
            'country': ['Россия', 'США', 'Китай'],
            'year': [2020, 2020, 2020],
            'export_value': [332.5, 1430.0, 2590.0],
            'import_value': [238.0, 2400.0, 2050.0],
            'gdp_value': [1480.0, 20900.0, 14700.0],
            'population_value': [144.1, 331.0, 1411.0]   # миллионы человек
        })
        output = io.BytesIO()
        df.to_csv(output, index=False, encoding='utf-8-sig')
        output.seek(0)
        return output.getvalue()