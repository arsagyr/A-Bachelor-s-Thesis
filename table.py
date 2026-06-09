import requests
import pandas as pd
from datetime import datetime
import time
import requests

def get_wb_data(indicator, country_code, start_year=2000, end_year=2026, max_retries=3):
    """
    Получение данных из World Bank API с повторными попытками.
    """
    url = f"http://api.worldbank.org/v2/country/{country_code}/indicator/{indicator}"
    params = {
        'format': 'json',
        'per_page': 100,
        'date': f'{start_year}:{end_year}'
    }
    
    for attempt in range(max_retries):
        try:
            response = requests.get(url, params=params, timeout=60)  # увеличен таймаут
            if response.status_code == 400:
                # Для 400 считаем, что данных нет (некоторые индикаторы отсутствуют для страны)
                print(f"⚠️  Данные по {indicator} для {country_code} отсутствуют (HTTP 400)")
                return {}
            response.raise_for_status()
            data = response.json()
            
            if len(data) < 2 or not data[1]:
                return {}
            
            result = {}
            for item in data[1]:
                year = item['date']
                value = item['value']
                if value is not None and value != "..":
                    try:
                        result[int(year)] = float(value)
                    except (ValueError, TypeError):
                        continue
            return result
        
        except requests.exceptions.Timeout:
            print(f"  Таймаут ({attempt+1}/{max_retries}) для {indicator} {country_code}, повтор через {2**attempt} сек...")
            time.sleep(2**attempt)
        except requests.exceptions.RequestException as e:
            print(f"  Ошибка ({attempt+1}/{max_retries}): {e}")
            if attempt == max_retries-1:
                return {}
            time.sleep(2**attempt)
    
    return {}

# Определяем страны БРИКС (оригинальный состав до 2026)
brics_countries = {
    'BRA': 'Brazil',
    'RUS': 'Russia', 
    'IND': 'India',
    'CHN': 'China',
    'ZAF': 'South Africa',
    'EGY': 'Egypt',
    'ETH': 'Ethiopia',
    'IRN': 'Iran',
    'ARE': 'UAE',
    'SAU': 'Saudi Arabia',
    'IDN': 'Indonesia'
}

# Индикаторы Всемирного банка
indicators = {
    'GDP': 'NY.GDP.MKTP.CD',           # ВВП (в текущих долларах)
    'EXPORT': 'NE.EXP.GNFS.CD',         # Экспорт товаров и услуг
    'IMPORT': 'NE.IMP.GNFS.CD',         # Импорт товаров и услуг
    'POP': 'SP.POP.TOTL'               # 👈 ДОБАВЛЕНО: общая численность населения
}

years = range(2000, 2026)
all_data = []

for country_code, country_name in brics_countries.items():
    try:
        print(f"\n📊 Загружаем данные для {country_name} ({country_code})...")
        country_data = {'Country': country_name}
        
        for indicator_name, indicator_code in indicators.items():
            print(f"  - {indicator_name}...", end=" ", flush=True)
            data = get_wb_data(indicator_code, country_code, 2000, 2026)  # ваша функция с retry
            print(f"✅ ({len(data)} лет)" if data else "⚠️ (нет данных)")
            
            for year in years:
                value = data.get(year)
                if value is not None:
                    try:
                        if indicator_name == 'GDP':
                            country_data[f"{year}_GDP_bln"] = value / 1e9
                        elif indicator_name == 'EXPORT':
                            country_data[f"{year}_EXPORT_bln"] = value / 1e9
                        elif indicator_name == 'IMPORT':
                            country_data[f"{year}_IMPORT_bln"] = value / 1e9
                        elif indicator_name == 'POP':
                            country_data[f"{year}_POP_mil"] = value / 1e6
                    except (TypeError, ValueError) as e:
                        print(f"      Ошибка преобразования года {year}: {e}")
            
            time.sleep(1)  # пауза между индикаторами
        
        all_data.append(country_data)
        print(f"  ✅ Данные для {country_name} добавлены")
        time.sleep(2)
    
    except Exception as e:
        print(f"  ❌ Критическая ошибка при обработке {country_name}: {e}")
        continue

# Диагностика перед созданием DataFrame
print(f"\n📦 Собрано данных для {len(all_data)} стран из {len(brics_countries)}")
if not all_data:
    raise RuntimeError("Нет данных ни для одной страны. Проверьте соединение и индикаторы.")

df_list = []
for country in all_data:
    country_name = country.get('Country')
    if not country_name:
        print(f"⚠️ Пропущена запись без ключа 'Country': {country}")
        continue
    for year in years:
        row = {
            'Страна': country_name,
            'Год': year,
            'ВВП_млрд': country.get(f"{year}_GDP_bln", None),
            'Экспорт_млрд': country.get(f"{year}_EXPORT_bln", None),
            'Импорт_млрд': country.get(f"{year}_IMPORT_bln", None),
            'Население_млн': country.get(f"{year}_POP_mil", None)
        }
        df_list.append(row)

df = pd.DataFrame(df_list)
print(f"📊 Итоговый DataFrame: {df.shape[0]} строк, колонки: {df.columns.tolist()}")

# Сортируем данные
df = df.sort_values(['Страна', 'Год']).reset_index(drop=True)

# Сохраняем в CSV
csv_filename = 'table.csv'
df.to_csv(csv_filename, index=False, encoding='utf-8-sig')

print("\n" + "=" * 60)
print(f"✅ Готово! Данные сохранены в файл: {csv_filename}")
print(f"📈 Всего записей: {len(df)}")
print(f"🌍 Стран: {len(brics_countries)}")
print(f"📅 Период: 2000-2026")

# Показываем статистику по полноте данных
print("\n📊 Статистика по данным:")
for indicator in ['ВВП_млрд', 'Экспорт_млрд', 'Импорт_млрд', 'Население_млн']:   # 👈 ДОБАВЛЕНО
    non_null = df[indicator].notna().sum()
    total = len(df)
    print(f"  - {indicator}: {non_null}/{total} ({non_null/total*100:.1f}%)")

# Выводим первые несколько строк для проверки
print("\n🔍 Первые 10 строк данных:")
print(df.head(10))

# Дополнительно: сводная статистика по 2026 году
print("\n📋 Данные за 2026 год:")
print(df[df['Год'] == 2026].to_string(index=False))

# Дополнительная статистика
print("\n📈 Сводная статистика за весь период:")
for country in brics_countries.values():
    country_data = df[df['Страна'] == country]
    if not country_data.empty:
        print(f"\n{country}:")
        print(f"  Средний ВВП: {country_data['ВВП_млрд'].mean():.2f} млрд USD")
        print(f"  Средний экспорт: {country_data['Экспорт_млрд'].mean():.2f} млрд USD")
        print(f"  Средний импорт: {country_data['Импорт_млрд'].mean():.2f} млрд USD")
        print(f"  Среднее население: {country_data['Население_млн'].mean():.2f} млн чел.")   # 👈 ДОБАВЛЕНО