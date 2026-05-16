# Установка и запуск
```
# Создайте .env файл с вашими настройками
cp .env.example .env

# Отредактируйте .env под вашу конфигурацию
nano .env

# Установите зависимости
pip install -r requirements.txt

# Запустите приложение
python app.py
```

## Импорт данных из CSV/Excel

### Формат CSV файла

Система автоматически определяет колонки по ключевым словам:

- **Страна**: country, страна, country_name, nation
- **Год**: year, год, date, период  
- **Экспорт**: export, экспорт, exports
- **Импорт**: import, импорт, imports
- **ВВП**: gdp, ввп, gross domestic product

### Пример CSV файла

```csv
country,year,export_value,import_value,gdp_value
Россия,2020,332.5,238.0,1480.0
США,2020,1430.0,2400.0,20900.0
Китай,2020,2590.0,2050.0,14700.0