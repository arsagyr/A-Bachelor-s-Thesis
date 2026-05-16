"""
Скрипт для очистки тестовых данных из БД
"""

import psycopg2
from psycopg2.extras import RealDictCursor
from config import Config


def clear_test_data():
    """Очистка тестовых данных"""
    try:
        conn = psycopg2.connect(
            host=Config.DB_HOST,
            port=Config.DB_PORT,
            database=Config.DB_NAME,
            user=Config.DB_USER,
            password=Config.DB_PASSWORD,
            cursor_factory=RealDictCursor
        )
        
        cur = conn.cursor()
        
        # Удаляем тестовые страны (если они есть)
        test_countries = ['Россия', 'США', 'Китай', 'Германия', 'Япония']
        
        for country in test_countries:
            cur.execute("DELETE FROM countries WHERE name = %s", (country,))
        
        conn.commit()
        
        deleted = cur.rowcount
        cur.close()
        conn.close()
        
        if deleted > 0:
            print(f"✅ Удалено {deleted} тестовых стран")
        else:
            print("ℹ️ Тестовых данных не найдено")
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")


if __name__ == '__main__':
    answer = input("⚠️ Это удалит тестовые страны (Россия, США, Китай, Германия, Япония). Продолжить? (yes/no): ")
    if answer.lower() == 'yes':
        clear_test_data()
    else:
        print("Операция отменена")