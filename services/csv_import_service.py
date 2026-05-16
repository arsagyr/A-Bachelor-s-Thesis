"""
Сервис для импорта данных из CSV файлов
С автоматическим определением колонок
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Any, Optional
import io
from database import with_db_connection
from services.indicator_service import IndicatorService
from services.country_service import CountryService


class CSVImportService:
    """Сервис для импорта данных из CSV"""
    
    # Словарь соответствий ключевых слов для определения колонок
    COLUMN_MAPPING = {
        'country': {
            'keywords': ['country', 'страна', 'country_name', 'nation', 'государство', 'страны', 'name'],
            'required': True
        },
        'year': {
            'keywords': ['year', 'год', 'г', 'year_of', 'date', 'период'],
            'required': True
        },
        'export': {
            'keywords': ['export', 'экспорт', 'exports', 'эксп', 'вывоз', 'export_value', 'export_usd'],
            'required': False
        },
        'import': {
            'keywords': ['import', 'импорт', 'imports', 'имп', 'ввоз', 'import_value', 'import_usd'],
            'required': False
        },
        'gdp': {
            'keywords': ['gdp', 'ввп', 'gross domestic product', 'валовый', 'gdp_value', 'gdp_usd'],
            'required': False
        }
    }
    
    @classmethod
    def detect_columns(cls, df_columns: List[str]) -> Dict[str, Optional[str]]:
        """
        Автоматическое определение колонок на основе ключевых слов
        
        Args:
            df_columns: Список названий колонок из CSV
        
        Returns:
            Dict с соответствием типов данных и названий колонок
        """
        detected = {}
        
        for data_type, config in cls.COLUMN_MAPPING.items():
            detected_column = None
            
            for col in df_columns:
                col_lower = col.lower().strip()
                
                # Проверяем совпадение с ключевыми словами
                for keyword in config['keywords']:
                    if keyword in col_lower:
                        detected_column = col
                        break
                
                # Если нашли, выходим из цикла
                if detected_column:
                    break
            
            detected[data_type] = detected_column
        
        # Проверка обязательных колонок
        missing_required = []
        for data_type, config in cls.COLUMN_MAPPING.items():
            if config['required'] and not detected.get(data_type):
                missing_required.append(data_type)
        
        if missing_required:
            raise ValueError(f"Не найдены обязательные колонки: {', '.join(missing_required)}")
        
        return detected
    
    # @classmethod
    # def validate_and_clean_data(cls, df: pd.DataFrame, column_mapping: Dict[str, str]) -> pd.DataFrame:
    #     """
    #     Валидация и очистка данных
        
    #     Args:
    #         df: DataFrame с данными
    #         column_mapping: Маппинг колонок
        
    #     Returns:
    #         Очищенный DataFrame
    #     """
    #     # Создаем копию
    #     cleaned_df = pd.DataFrame()
        
    #     # Переименовываем колонки в стандартные
    #     for data_type, col_name in column_mapping.items():
    #         if col_name and col_name in df.columns:
    #             cleaned_df[data_type] = df[col_name]
        
    #     # Если нет данных, возвращаем пустой DataFrame
    #     if cleaned_df.empty:
    #         return cleaned_df
        
    #     # Очистка данных
    #     # 1. Удаляем пустые строки
    #     cleaned_df.dropna(subset=['country', 'year'], inplace=True)
        
    #     if cleaned_df.empty:
    #         return cleaned_df
        
    #     # 2. Приводим год к целому числу
    #     cleaned_df['year'] = pd.to_numeric(cleaned_df['year'], errors='coerce')
    #     cleaned_df.dropna(subset=['year'], inplace=True)
    #     cleaned_df['year'] = cleaned_df['year'].astype(int)
        
    #     # 3. Очистка числовых значений
    #     for col in ['export', 'import', 'gdp']:
    #         if col in cleaned_df.columns:
    #             # Конвертируем в строку и очищаем
    #             cleaned_df[col] = cleaned_df[col].astype(str).str.replace(r'[^\d\-\.]', '', regex=True)
    #             cleaned_df[col] = pd.to_numeric(cleaned_df[col], errors='coerce')
                
    #             # Заменяем бесконечные значения на None
    #             cleaned_df[col] = cleaned_df[col].replace([np.inf, -np.inf], np.nan)
        
    #     # 4. Удаляем дубликаты по стране и году
    #     cleaned_df.drop_duplicates(subset=['country', 'year'], keep='last', inplace=True)
        
    #     # 5. Очистка названий стран
    #     cleaned_df['country'] = cleaned_df['country'].astype(str).str.strip()
        
    #     # 6. Удаляем строки с пустыми названиями стран
    #     cleaned_df = cleaned_df[cleaned_df['country'] != '']
    #     cleaned_df = cleaned_df[cleaned_df['country'] != 'nan']
        
    #     return cleaned_df
    
    @classmethod
    def preview_csv(cls, file_content: bytes, filename: str) -> Dict[str, Any]:
        """
        Предпросмотр CSV файла и определение колонок
        
        Args:
            file_content: Содержимое файла в байтах
            filename: Имя файла
        
        Returns:
            Dict с информацией о файле
        """
        try:
            # Определяем формат файла
            if filename.endswith('.xlsx'):
                df = pd.read_excel(io.BytesIO(file_content), nrows=10)
            else:
                # Пробуем разные разделители и кодировки
                for encoding in ['utf-8', 'cp1251', 'latin1']:
                    try:
                        df = pd.read_csv(io.BytesIO(file_content), encoding=encoding, nrows=10)
                        break
                    except:
                        continue
                else:
                    # Если не получилось, пробуем с auto-detection
                    df = pd.read_csv(io.BytesIO(file_content), encoding='utf-8', nrows=10, sep=None, engine='python')
            
            if df.empty:
                return {
                    'success': False,
                    'error': 'Файл пуст'
                }
            
            # Определяем колонки
            column_mapping = cls.detect_columns(df.columns.tolist())
            
            # Формируем информацию для предпросмотра
            preview_data = df.head(5).to_dict('records')
            
            # Конвертируем NaN в None для JSON
            for row in preview_data:
                for key, value in row.items():
                    if pd.isna(value):
                        row[key] = None
                    elif isinstance(value, (np.integer, np.floating)):
                        row[key] = float(value) if not pd.isna(value) else None
            
            return {
                'success': True,
                'columns': df.columns.tolist(),
                'detected_mapping': column_mapping,
                'preview': preview_data,
                'total_rows': len(df),
                'filename': filename
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Ошибка при чтении файла: {str(e)}'
            }
    
    @classmethod
    def import_csv(cls, file_content: bytes, filename: str, 
                   custom_mapping: Dict[str, str] = None) -> Dict[str, Any]:
        """
        Импорт CSV файла в базу данных (без декоратора, используем прямое соединение)
        
        Args:
            file_content: Содержимое файла
            filename: Имя файла
            custom_mapping: Пользовательский маппинг колонок
        
        Returns:
            Dict с результатами импорта
        """
        from database import Database
        
        results = {
            'success': True,
            'total_rows': 0,
            'imported_rows': 0,
            'skipped_rows': 0,
            'errors': [],
            'warnings': []
        }
        
        conn = None
        try:
            # Получаем соединение вручную
            conn = Database.get_connection()
            
            # Читаем весь файл
            if filename.endswith('.xlsx'):
                df = pd.read_excel(io.BytesIO(file_content))
            else:
                # Пробуем разные разделители и кодировки
                for encoding in ['utf-8', 'cp1251', 'latin1']:
                    try:
                        df = pd.read_csv(io.BytesIO(file_content), encoding=encoding)
                        break
                    except:
                        continue
                else:
                    # Если не получилось, пробуем с auto-detection
                    df = pd.read_csv(io.BytesIO(file_content), encoding='utf-8', sep=None, engine='python')
            
            results['total_rows'] = len(df)
            
            if df.empty:
                results['success'] = False
                results['errors'].append('Файл пуст')
                return results
            
            # Определяем колонки
            if custom_mapping:
                column_mapping = custom_mapping
            else:
                column_mapping = cls.detect_columns(df.columns.tolist())
            
            # Очищаем данные
            cleaned_df = cls.validate_and_clean_data(df, column_mapping)
            
            if cleaned_df.empty:
                results['warnings'].append('Нет валидных данных для импорта')
                return results
            
            # Импортируем данные
            for idx, row in cleaned_df.iterrows():
                try:
                    # Получаем или создаем страну
                    country_name = row['country']
                    
                    # Ищем страну через прямое SQL
                    cur = conn.cursor()
                    cur.execute("SELECT id FROM countries WHERE name ILIKE %s", (country_name,))
                    country = cur.fetchone()
                    cur.close()
                    
                    if country:
                        country_id = country['id']
                    else:
                        # Создаем новую страну
                        cur = conn.cursor()
                        cur.execute(
                            "INSERT INTO countries (name) VALUES (%s) ON CONFLICT (name) DO NOTHING RETURNING id",
                            (country_name,)
                        )
                        result = cur.fetchone()
                        if result:
                            country_id = result['id']
                        else:
                            # Если не получилось, пробуем получить существующую
                            cur.execute("SELECT id FROM countries WHERE name = %s", (country_name,))
                            country = cur.fetchone()
                            if country:
                                country_id = country['id']
                            else:
                                raise ValueError(f"Не удалось создать или найти страну: {country_name}")
                        cur.close()
                    
                    # Подготавливаем данные показателя
                    export_value = float(row['export']) if 'export' in row and pd.notna(row['export']) else None
                    import_value = float(row['import']) if 'import' in row and pd.notna(row['import']) else None
                    gdp_value = float(row['gdp']) if 'gdp' in row and pd.notna(row['gdp']) else None
                    
                    # Сохраняем показатель через прямое SQL
                    cur = conn.cursor()
                    cur.execute("""
                        INSERT INTO indicators (country_id, year, export_value, import_value, gdp_value, updated_at)
                        VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                        ON CONFLICT (country_id, year) DO UPDATE SET
                            export_value = EXCLUDED.export_value,
                            import_value = EXCLUDED.import_value,
                            gdp_value = EXCLUDED.gdp_value,
                            updated_at = CURRENT_TIMESTAMP
                    """, (country_id, int(row['year']), export_value, import_value, gdp_value))
                    cur.close()
                    
                    results['imported_rows'] += 1
                    
                except Exception as e:
                    results['warnings'].append(f"Строка {idx + 1} ({country_name if 'country_name' in locals() else '?'}, {row.get('year', '?')}): {str(e)}")
                    results['skipped_rows'] += 1
            
            # Коммитим транзакцию
            conn.commit()
            
        except Exception as e:
            if conn:
                conn.rollback()
            results['success'] = False
            results['errors'].append(f"Ошибка при импорте: {str(e)}")
        finally:
            if conn:
                Database.return_connection(conn)
        
        return results
    
    @classmethod
    def generate_template(cls) -> bytes:
        """
        Генерация шаблона CSV файла
        
        Returns:
            bytes: Содержимое шаблона CSV
        """
        template_data = {
            'country': ['Россия', 'США', 'Китай', 'Германия', 'Япония'],
            'year': [2020, 2020, 2020, 2020, 2020],
            'export_value': [332.5, 1430.0, 2590.0, 1370.0, 640.0],
            'import_value': [238.0, 2400.0, 2050.0, 1150.0, 635.0],
            'gdp_value': [1480.0, 20900.0, 14700.0, 3800.0, 5050.0]
        }
        
        df = pd.DataFrame(template_data)
        
        # Сохраняем в CSV
        output = io.BytesIO()
        df.to_csv(output, index=False, encoding='utf-8-sig')
        output.seek(0)
        
        return output.getvalue()
    
@classmethod
def import_csv(cls, file_content: bytes, filename: str, 
               custom_mapping: Dict[str, str] = None) -> Dict[str, Any]:
    """
    Импорт CSV файла в базу данных
    """
    from database import Database
    
    results = {
        'success': True,
        'total_rows': 0,
        'imported_rows': 0,
        'skipped_rows': 0,
        'errors': [],
        'warnings': []
    }
    
    conn = None
    try:
        # Получаем соединение вручную
        conn = Database.get_connection()
        
        # Читаем весь файл
        if filename.endswith('.xlsx'):
            df = pd.read_excel(io.BytesIO(file_content))
        else:
            # Пробуем разные разделители и кодировки
            df = None
            for encoding in ['utf-8', 'cp1251', 'latin1']:
                try:
                    df = pd.read_csv(io.BytesIO(file_content), encoding=encoding)
                    break
                except:
                    continue
            
            if df is None:
                # Если не получилось, пробуем с auto-detection
                df = pd.read_csv(io.BytesIO(file_content), encoding='utf-8', sep=None, engine='python')
        
        results['total_rows'] = len(df)
        
        if df.empty:
            results['success'] = False
            results['errors'].append('Файл пуст')
            return results
        
        # Определяем колонки
        if custom_mapping:
            column_mapping = custom_mapping
        else:
            column_mapping = cls.detect_columns(df.columns.tolist())
        
        # Очищаем данные
        cleaned_df = cls.validate_and_clean_data(df, column_mapping)
        
        if cleaned_df.empty:
            results['warnings'].append('Нет валидных данных для импорта')
            return results
        
        # Импортируем данные
        for idx, row in cleaned_df.iterrows():
            try:
                # Получаем или создаем страну
                country_name = row['country']
                
                # Ищем страну
                cur = conn.cursor()
                cur.execute("SELECT id FROM countries WHERE name ILIKE %s", (country_name,))
                country = cur.fetchone()
                cur.close()
                
                if country:
                    country_id = country['id']
                else:
                    # Создаем новую страну
                    cur = conn.cursor()
                    cur.execute(
                        "INSERT INTO countries (name) VALUES (%s) ON CONFLICT (name) DO NOTHING RETURNING id",
                        (country_name,)
                    )
                    result = cur.fetchone()
                    if result:
                        country_id = result['id']
                        conn.commit()
                    else:
                        # Если не получилось, пробуем получить существующую
                        cur.execute("SELECT id FROM countries WHERE name = %s", (country_name,))
                        country = cur.fetchone()
                        if country:
                            country_id = country['id']
                        else:
                            raise ValueError(f"Не удалось создать или найти страну: {country_name}")
                    cur.close()
                
                # Подготавливаем данные показателя
                export_value = float(row['export']) if 'export' in row and pd.notna(row['export']) else None
                import_value = float(row['import']) if 'import' in row and pd.notna(row['import']) else None
                gdp_value = float(row['gdp']) if 'gdp' in row and pd.notna(row['gdp']) else None
                
                # Сохраняем показатель (без updated_at)
                cur = conn.cursor()
                cur.execute("""
                    INSERT INTO indicators (country_id, year, export_value, import_value, gdp_value)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (country_id, year) DO UPDATE SET
                        export_value = EXCLUDED.export_value,
                        import_value = EXCLUDED.import_value,
                        gdp_value = EXCLUDED.gdp_value
                """, (country_id, int(row['year']), export_value, import_value, gdp_value))
                cur.close()
                
                results['imported_rows'] += 1
                conn.commit()
                
            except Exception as e:
                results['warnings'].append(f"Строка {idx + 1} ({row.get('country', '?')}, {row.get('year', '?')}): {str(e)}")
                results['skipped_rows'] += 1
                conn.rollback()
                continue
        
    except Exception as e:
        if conn:
            conn.rollback()
        results['success'] = False
        results['errors'].append(f"Ошибка при импорте: {str(e)}")
    finally:
        if conn:
            Database.return_connection(conn)
    
    return results

@classmethod
def validate_and_clean_data(cls, df: pd.DataFrame, column_mapping: Dict[str, str]) -> pd.DataFrame:
    """
    Валидация и очистка данных
    """
    # Создаем копию
    cleaned_df = pd.DataFrame()
    
    # Переименовываем колонки в стандартные
    for data_type, col_name in column_mapping.items():
        if col_name and col_name in df.columns:
            cleaned_df[data_type] = df[col_name]
    
    # Если нет данных, возвращаем пустой DataFrame
    if cleaned_df.empty:
        return cleaned_df
    
    # Очистка данных
    # 1. Удаляем пустые строки
    cleaned_df.dropna(subset=['country', 'year'], inplace=True)
    
    if cleaned_df.empty:
        return cleaned_df
    
    # 2. Приводим год к целому числу
    cleaned_df['year'] = pd.to_numeric(cleaned_df['year'], errors='coerce')
    cleaned_df.dropna(subset=['year'], inplace=True)
    cleaned_df['year'] = cleaned_df['year'].astype(int)
    
    # 3. Очистка числовых значений
    for col in ['export', 'import', 'gdp']:
        if col in cleaned_df.columns:
            # Конвертируем в строку и очищаем
            cleaned_df[col] = cleaned_df[col].astype(str).str.replace(r'[^\d\-\.]', '', regex=True)
            cleaned_df[col] = pd.to_numeric(cleaned_df[col], errors='coerce')
            
            # Заменяем бесконечные значения на None
            cleaned_df[col] = cleaned_df[col].replace([np.inf, -np.inf], np.nan)
    
    # 4. Удаляем дубликаты по стране и году (оставляем последний)
    cleaned_df = cleaned_df.sort_values(['country', 'year'])
    cleaned_df.drop_duplicates(subset=['country', 'year'], keep='last', inplace=True)
    
    # 5. Очистка названий стран
    cleaned_df['country'] = cleaned_df['country'].astype(str).str.strip().str.upper()
    
    # 6. Удаляем строки с пустыми названиями стран
    cleaned_df = cleaned_df[cleaned_df['country'] != '']
    cleaned_df = cleaned_df[cleaned_df['country'] != 'NAN']
    cleaned_df = cleaned_df[cleaned_df['country'] != 'NONE']
    
    # 7. Валидация годов
    cleaned_df = cleaned_df[(cleaned_df['year'] >= 1900) & (cleaned_df['year'] <= 2100)]
    
    return cleaned_df