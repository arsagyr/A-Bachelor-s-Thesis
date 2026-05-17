import pandas as pd
import numpy as np
import io
from typing import Dict, List, Any
from database import Database


class CSVImportService:
    
    COLUMN_MAPPING = {
        'country': {'keywords': ['country', 'страна', 'name'], 'required': True},
        'year': {'keywords': ['year', 'год'], 'required': True},
        'export': {'keywords': ['export', 'экспорт'], 'required': False},
        'import': {'keywords': ['import', 'импорт'], 'required': False},
        'gdp': {'keywords': ['gdp', 'ввп'], 'required': False}
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
        cur = None
        
        try:
            conn = Database.get_connection()
            df = pd.read_csv(io.BytesIO(file_content), encoding='utf-8')
            results['total_rows'] = len(df)
            
            mapping = custom_mapping or cls.detect_columns(df.columns.tolist())
            
            for idx, row in df.iterrows():
                try:
                    country_name = str(row[mapping['country']]).strip()
                    
                    cur = conn.cursor()
                    cur.execute("SELECT id FROM countries WHERE name = %s", (country_name,))
                    country = cur.fetchone()
                    cur.close()
                    cur = None
                    
                    if country:
                        country_id = country['id']
                    else:
                        cur = conn.cursor()
                        cur.execute("INSERT INTO countries (name) VALUES (%s) RETURNING id", (country_name,))
                        country_id = cur.fetchone()['id']
                        cur.close()
                        cur = None
                    
                    cur = conn.cursor()
                    cur.execute("""
                        INSERT INTO indicators (country_id, year, export_value, import_value, gdp_value)
                        VALUES (%s, %s, %s, %s, %s)
                        ON CONFLICT (country_id, year) DO UPDATE SET
                            export_value = EXCLUDED.export_value,
                            import_value = EXCLUDED.import_value,
                            gdp_value = EXCLUDED.gdp_value
                    """, (
                        country_id,
                        int(row[mapping['year']]),
                        float(row[mapping['export']]) if mapping.get('export') and pd.notna(row[mapping['export']]) else None,
                        float(row[mapping['import']]) if mapping.get('import') and pd.notna(row[mapping['import']]) else None,
                        float(row[mapping['gdp']]) if mapping.get('gdp') and pd.notna(row[mapping['gdp']]) else None
                    ))
                    cur.close()
                    cur = None
                    conn.commit()
                    results['imported_rows'] += 1
                    
                except Exception as e:
                    results['errors'].append(f"Строка {idx + 1}: {str(e)}")
                    conn.rollback()
            
        except Exception as e:
            results['success'] = False
            results['errors'].append(str(e))
        finally:
            if cur:
                cur.close()
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
            'gdp_value': [1480.0, 20900.0, 14700.0]
        })
        output = io.BytesIO()
        df.to_csv(output, index=False, encoding='utf-8-sig')
        output.seek(0)
        return output.getvalue()