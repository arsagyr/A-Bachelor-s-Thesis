#!/usr/bin/env python3
"""
Запуск тестов с измерением нефункциональных метрик:
- время выполнения (wall‑clock)
- процессорное время (CPU time)
- пиковое потребление памяти (tracemalloc)
"""

import unittest
import time
import tracemalloc
import sys
import os

# Добавляем корень проекта в PYTHONPATH
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


class MetricsTestResult(unittest.TextTestResult):
    """Собирает метрики для каждого теста."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.test_metrics = []

    def startTest(self, test):
        # Запускаем измерения перед тестом
        tracemalloc.start()
        self._start_wall = time.perf_counter()
        self._start_cpu = time.process_time()
        super().startTest(test)

    def stopTest(self, test):
        # Собираем метрики после теста
        end_cpu = time.process_time()
        end_wall = time.perf_counter()
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        wall_time = end_wall - self._start_wall
        cpu_time = end_cpu - self._start_cpu
        peak_mb = peak / (1024 * 1024)
        current_mb = current / (1024 * 1024)

        self.test_metrics.append({
            'test_id': test.id(),
            'wall_time': wall_time,
            'cpu_time': cpu_time,
            'peak_memory_mb': peak_mb,
            'current_memory_mb': current_mb,
        })
        super().stopTest(test)


class MetricsTestRunner(unittest.TextTestRunner):
    """Использует MetricsTestResult."""
    def _makeResult(self):
        return MetricsTestResult(self.stream, self.descriptions, self.verbosity)


def run_tests_with_metrics():
    """Запускает все тесты и выводит таблицу метрик."""
    tests_dir = os.path.join(os.path.dirname(__file__), 'tests')
    if not os.path.isdir(tests_dir):
        print(f"Ошибка: папка с тестами '{tests_dir}' не найдена.")
        return False

    loader = unittest.TestLoader()
    suite = loader.discover(start_dir=tests_dir, pattern='test_*.py')
    runner = MetricsTestRunner(verbosity=2)
    result = runner.run(suite)

    # Вывод таблицы метрик
    print("\n" + "=" * 80)
    print("НЕФУНКЦИОНАЛЬНЫЕ МЕТРИКИ ПО ТЕСТАМ")
    print("=" * 80)
    print(f"{'Тест':<60} {'Wall (s)':<10} {'CPU (s)':<10} {'Peak Mem (MB)':<15}")
    print("-" * 95)

    total_wall = 0.0
    total_cpu = 0.0
    peak_mems = []
    for m in result.test_metrics:
        short_name = m['test_id'].split('.')[-1] + "()"
        wall = m['wall_time']
        cpu = m['cpu_time']
        peak = m['peak_memory_mb']
        total_wall += wall
        total_cpu += cpu
        peak_mems.append(peak)
        print(f"{short_name:<60} {wall:<10.4f} {cpu:<10.4f} {peak:<15.2f}")

    print("-" * 95)
    avg_peak = sum(peak_mems) / len(peak_mems) if peak_mems else 0
    print(f"{'ИТОГО / СРЕДНЕЕ':<60} {total_wall:<10.4f} {total_cpu:<10.4f} {avg_peak:<15.2f}")

    return result.wasSuccessful()


if __name__ == '__main__':
    print("=" * 60)
    print("ЗАПУСК ТЕСТОВ ПРОЕКТА economic_dashboard (с метриками)")
    print("=" * 60)
    success = run_tests_with_metrics()
    sys.exit(0 if success else 1)