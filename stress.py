#!/usr/bin/env python3
"""
Скрипт для нагрузки Raspberry Pi и записи температуры в CSV-файл
"""

import subprocess
import time
import datetime
import csv
import os
import sys
import signal
import threading
import multiprocessing
import math

class StressTester:
    def __init__(self, filename='temperature_log.csv', interval=1.0):
        """
        Инициализация тестера
        
        Args:
            filename: имя файла для записи логов
            interval: интервал измерения температуры в секундах
        """
        self.filename = filename
        self.interval = interval
        self.running = False
        self.workers = []
        
    def get_temperature(self):
        """Получение температуры CPU"""
        try:
            # Чтение температуры из системного файла
            with open('/sys/class/thermal/thermal_zone0/temp', 'r') as f:
                temp = float(f.read().strip()) / 1000.0
            return temp
        except Exception as e:
            print(f"Ошибка чтения температуры: {e}")
            return None
    
    def cpu_stress_worker(self, worker_id):
        """Функция для создания нагрузки на CPU"""
        print(f"Запуск воркера нагрузки #{worker_id}")
        while self.running:
            # Интенсивные математические вычисления
            x = 0
            for i in range(1000000):
                x += math.sqrt(i) * math.sin(i) * math.cos(i)
    
    def memory_stress_worker(self):
        """Функция для создания нагрузки на память"""
        print("Запуск воркера памяти")
        # Выделяем и удерживаем большой объем памяти
        memory_chunks = []
        chunk_size = 50 * 1024 * 1024  # 50 MB
        
        while self.running:
            try:
                # Создаем большой массив и удерживаем его
                chunk = bytearray(chunk_size)
                memory_chunks.append(chunk)
                time.sleep(0.1)
            except MemoryError:
                # Если память закончилась, очищаем часть
                if memory_chunks:
                    memory_chunks.pop()
                time.sleep(0.5)
    
    def io_stress_worker(self, worker_id):
        """Функция для создания нагрузки на I/O"""
        print(f"Запуск I/O воркера #{worker_id}")
        temp_file = f"/tmp/stress_io_{worker_id}.tmp"
        
        while self.running:
            try:
                # Интенсивная запись в файл
                with open(temp_file, 'wb') as f:
                    # Записываем 10 MB данных
                    data = b'X' * (10 * 1024 * 1024)
                    f.write(data)
                
                # Чтение файла
                with open(temp_file, 'rb') as f:
                    _ = f.read()
                
                # Удаление файла
                os.remove(temp_file)
                time.sleep(0.1)
            except Exception as e:
                time.sleep(0.5)
    
    def start_stress(self, cpu_workers=None, memory_workers=1, io_workers=2):
        """
        Запуск нагрузки на систему
        
        Args:
            cpu_workers: количество потоков нагрузки на CPU (по умолчанию все ядра * 2)
            memory_workers: количество воркеров нагрузки на память
            io_workers: количество воркеров нагрузки на I/O
        """
        if cpu_workers is None:
            # Используем вдвое больше потоков, чем ядер
            cpu_workers = multiprocessing.cpu_count() * 2
        
        print(f"Запуск нагрузки на Raspberry Pi:")
        print(f"  - CPU воркеров: {cpu_workers}")
        print(f"  - Memory воркеров: {memory_workers}")
        print(f"  - I/O воркеров: {io_workers}")
        print(f"  - Интервал измерения: {self.interval} сек")
        print(f"  - Файл лога: {self.filename}")
        print("Для остановки нажмите Ctrl+C")
        print("-" * 50)
        
        self.running = True
        self.workers = []
        
        # Запуск CPU воркеров
        for i in range(cpu_workers):
            t = threading.Thread(target=self.cpu_stress_worker, args=(i+1,))
            t.daemon = True
            t.start()
            self.workers.append(t)
        
        # Запуск Memory воркеров
        for i in range(memory_workers):
            t = threading.Thread(target=self.memory_stress_worker)
            t.daemon = True
            t.start()
            self.workers.append(t)
        
        # Запуск I/O воркеров
        for i in range(io_workers):
            t = threading.Thread(target=self.io_stress_worker, args=(i+1,))
            t.daemon = True
            t.start()
            self.workers.append(t)
    
    def stop_stress(self):
        """Остановка нагрузки"""
        print("\nОстановка нагрузки...")
        self.running = False
        time.sleep(1)  # Даем время воркерам завершиться
    
    def log_temperature(self, duration=None):
        """
        Запись температуры в файл
        
        Args:
            duration: продолжительность записи в секундах (None - бесконечно)
        """
        start_time = time.time()
        
        # Создаем заголовок CSV файла
        with open(self.filename, 'w', newline='') as csvfile:
            csvwriter = csv.writer(csvfile)
            csvwriter.writerow(['timestamp', 'temperature_c', 'elapsed_seconds'])
        
        print("Начало записи температуры...")
        
        try:
            while self.running:
                current_time = time.time()
                elapsed = current_time - start_time
                
                # Получаем температуру
                temp = self.get_temperature()
                
                if temp is not None:
                    # Форматируем timestamp
                    timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    
                    # Записываем в CSV
                    with open(self.filename, 'a', newline='') as csvfile:
                        csvwriter = csv.writer(csvfile)
                        csvwriter.writerow([timestamp, f"{temp:.2f}", f"{elapsed:.1f}"])
                    
                    # Выводим в консоль
                    print(f"[{timestamp}] Температура: {temp:.2f}°C | Время: {elapsed:.1f}с")
                
                # Проверяем не истекло ли время
                if duration and elapsed >= duration:
                    print(f"\nДостигнута заданная продолжительность ({duration} секунд)")
                    break
                
                # Ждем указанный интервал
                time.sleep(self.interval)
                
        except KeyboardInterrupt:
            print("\nПрервано пользователем")
        except Exception as e:
            print(f"Ошибка при записи температуры: {e}")
        finally:
            self.stop_stress()
            print(f"\nЗапись завершена. Данные сохранены в {self.filename}")
            print(f"Всего записей: {self.count_records()}")

    def count_records(self):
        """Подсчет количества записей в файле"""
        try:
            with open(self.filename, 'r') as f:
                return sum(1 for line in f) - 1  # Минус заголовок
        except:
            return 0

def signal_handler(sig, frame):
    """Обработчик сигнала Ctrl+C"""
    print("\nПолучен сигнал прерывания")
    sys.exit(0)

def main():
    """Основная функция"""
    # Настройки по умолчанию
    DEFAULT_FILENAME = "temperature_log.csv"
    DEFAULT_INTERVAL = 1.0  # секунды
    DEFAULT_DURATION = None  # None = бесконечно
    
    # Регистрируем обработчик Ctrl+C
    signal.signal(signal.SIGINT, signal_handler)
    
    print("=" * 60)
    print("СТРЕСС-ТЕСТ RASPBERRY PI С ЗАПИСЬЮ ТЕМПЕРАТУРЫ")
    print("=" * 60)
    
    # Запрашиваем параметры у пользователя
    try:
        filename = input(f"Имя файла для записи [{DEFAULT_FILENAME}]: ").strip()
        if not filename:
            filename = DEFAULT_FILENAME
        
        interval_str = input(f"Инвал измерения (сек) [{DEFAULT_INTERVAL}]: ").strip()
        interval = float(interval_str) if interval_str else DEFAULT_INTERVAL
        
        duration_str = input(f"Продолжительность теста в секундах (Enter для бесконечного): ").strip()
        duration = float(duration_str) if duration_str else DEFAULT_DURATION
        
        cpu_workers_str = input(f"Количество CPU воркеров (Enter для авто): ").strip()
        cpu_workers = int(cpu_workers_str) if cpu_workers_str else None
        
    except ValueError:
        print("Ошибка ввода! Использую значения по умолчанию.")
        filename = DEFAULT_FILENAME
        interval = DEFAULT_INTERVAL
        duration = DEFAULT_DURATION
        cpu_workers = None
    
    # Создаем и запускаем тестер
    tester = StressTester(filename=filename, interval=interval)
    
    # Запускаем нагрузку
    tester.start_stress(cpu_workers=cpu_workers)
    
    # Запускаем запись температуры
    tester.log_temperature(duration=duration)

if __name__ == "__main__":
    main()