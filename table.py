import requests
import pandas as pd
from datetime import datetime
import time

def get_wb_data(indicator, country_code, start_year=2000, end_year=2023):
    """
    Получение данных из World Bank API
    
    Parameters:
    - indicator: код индикатора Всемирного банка
    - country_code: код страны (BRA, RUS, IND, CHN, ZAF)
    - start_year: начальный год
    - end_year: конечный год
    """
    url = f"http://api.worldbank.org/v2/country/{country_code}/indicator/{indicator}"
    params = {
        'format': 'json',
        'per_page': 100,
        'date': f'{start_year}:{end_year}'
    }
    
    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        if len(data) < 2 or not data[1]:
            return {}
        
        # Парсим данные
        result = {}
        for item in data[1]:
            year = item['date']
            value = item['value']
            if value is not None:
                result[int(year)] = float(value)
        
        return result
    
    except Exception as e:
        print(f"Ошибка при загрузке {indicator} для {country_code}: {e}")
        return {}

# Определяем страны БРИКС (оригинальный состав до 2024)
brics_countries = {
    'BRA': 'Brazil',
    'RUS': 'Russia', 
    'IND': 'India',
    'CHN': 'China',
    'ZAF': 'South Africa'
}

# Индикаторы Всемирного банка
indicators = {
    'GDP': 'NY.GDP.MKTP.CD',           # ВВП (в текущих долларах)
    'EXPORT': 'NE.EXP.GNFS.CD',         # Экспорт товаров и услуг
    'IMPORT': 'NE.IMP.GNFS.CD'          # Импорт товаров и услуг
}

years = range(2000, 2024)
all_data = []

print("🚀 Начинаем сбор данных из World Bank API...")
print("-" * 60)

# Собираем данные для каждой страны
for country_code, country_name in brics_countries.items():
    print(f"\n📊 Загружаем данные для {country_name} ({country_code})...")
    
    country_data = {'Country': country_name}
    
    for indicator_name, indicator_code in indicators.items():
        print(f"  - {indicator_name}...", end=" ")
        data = get_wb_data(indicator_code, country_code, 2000, 2023)
        print(f"✅ ({len(data)} лет)")
        
        # Сохраняем данные для каждого года
        for year in years:
            value = data.get(year, None)
            if value is not None:
                # Конвертируем в миллиарды для всех показателей
                if indicator_name == 'GDP':
                    country_data[f"{year}_GDP_bln"] = value / 1e9   # млрд USD
                elif indicator_name == 'EXPORT':
                    country_data[f"{year}_EXPORT_bln"] = value / 1e9   # млрд USD
                else:  # IMPORT
                    country_data[f"{year}_IMPORT_bln"] = value / 1e9   # млрд USD
    
    all_data.append(country_data)
    time.sleep(0.5)  # Небольшая пауза между запросами

# Создаем DataFrame
df_list = []
for country in all_data:
    country_name = country['Country']
    
    # Извлекаем данные по годам
    for year in years:
        row = {
            'Страна': country_name,
            'Год': year,
            'ВВП_млрд': country.get(f"{year}_GDP_bln", None),
            'Экспорт_млрд': country.get(f"{year}_EXPORT_bln", None),
            'Импорт_млрд': country.get(f"{year}_IMPORT_bln", None)
        }
        df_list.append(row)

df = pd.DataFrame(df_list)

# Сортируем данные
df = df.sort_values(['Страна', 'Год']).reset_index(drop=True)

# Сохраняем в CSV
csv_filename = 'brics_trade_gdp_2000_2023.csv'
df.to_csv(csv_filename, index=False, encoding='utf-8-sig')

print("\n" + "=" * 60)
print(f"✅ Готово! Данные сохранены в файл: {csv_filename}")
print(f"📈 Всего записей: {len(df)}")
print(f"🌍 Стран: {len(brics_countries)}")
print(f"📅 Период: 2000-2023")

# Показываем статистику по полноте данных
print("\n📊 Статистика по данным (в млрд USD):")
for indicator in ['ВВП_млрд', 'Экспорт_млрд', 'Импорт_млрд']:
    non_null = df[indicator].notna().sum()
    total = len(df)
    print(f"  - {indicator}: {non_null}/{total} ({non_null/total*100:.1f}%)")

# Выводим первые несколько строк для проверки
print("\n🔍 Первые 10 строк данных:")
print(df.head(10))

# Дополнительно: сводная статистика по 2023 году
print("\n📋 Данные за 2023 год (в млрд USD):")
df_2023 = df[df['Год'] == 2023]
print(df_2023.to_string(index=False))

# Дополнительная статистика
print("\n📈 Сводная статистика за весь период:")
for country in brics_countries.values():
    country_data = df[df['Страна'] == country]
    if not country_data.empty:
        print(f"\n{country}:")
        print(f"  Средний ВВП: {country_data['ВВП_млрд'].mean():.2f} млрд USD")
        print(f"  Средний экспорт: {country_data['Экспорт_млрд'].mean():.2f} млрд USD")
        print(f"  Средний импорт: {country_data['Импорт_млрд'].mean():.2f} млрд USD")