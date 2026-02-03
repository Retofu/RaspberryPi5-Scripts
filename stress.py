#!/usr/bin/env python3
"""
Специальный скрипт для Raspberry Pi 5
С нагрузкой всех компонентов и мониторингом температуры
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
import psutil
import gpiozero
from collections import deque

class Pi5StressTester:
    def __init__(self, filename='pi5_temperature_log.csv', interval=1.0):
        """
        Инициализация тестера для Raspberry Pi 5
        
        Args:
            filename: имя файла для записи логов
            interval: интервал измерения в секундах
        """
        self.filename = filename
        self.interval = interval
        self.running = False
        self.workers = []
        self.cpu_history = deque(maxlen=5)
        self.pi5_model = self.detect_pi5()
        
        if not self.pi5_model:
            print("⚠️  Предупреждение: Не удалось определить Raspberry Pi 5")
            print("   Скрипт может работать некорректно на других моделях")
        
        # Настройки для Pi 5
        self.max_safe_temp = 85  # Максимальная безопасная температура для Pi 5
        self.throttle_temp = 80  # Температура троттлинга
        
    def detect_pi5(self):
        """Определение модели Raspberry Pi"""
        try:
            with open('/proc/device-tree/model', 'r') as f:
                model = f.read().lower()
                return 'raspberry pi 5' in model
        except:
            return False
    
    def get_temperature(self):
        """Получение температуры CPU для Pi 5"""
        try:
            # Способ 1: Основной датчик температуры
            with open('/sys/class/thermal/thermal_zone0/temp', 'r') as f:
                temp = float(f.read().strip()) / 1000.0
            
            # Способ 2: Дополнительные датчики (если есть)
            try:
                with open('/sys/class/hwmon/hwmon0/temp1_input', 'r') as f:
                    soc_temp = float(f.read().strip()) / 1000.0
                    # Берем максимальную температуру
                    temp = max(temp, soc_temp)
            except:
                pass
            
            return temp
        except Exception as e:
            print(f"Ошибка чтения температуры: {e}")
            return None
    
    def get_cpu_usage_pi5(self):
        """Расширенный мониторинг CPU для Pi 5"""
        try:
            # Базовая загрузка CPU
            cpu_percent = psutil.cpu_percent(interval=0.1, percpu=True)
            avg_percent = sum(cpu_percent) / len(cpu_percent)
            
            # Частота каждого ядра
            cpu_freqs = []
            for i in range(len(cpu_percent)):
                try:
                    with open(f'/sys/devices/system/cpu/cpu{i}/cpufreq/scaling_cur_freq', 'r') as f:
                        freq = int(f.read().strip()) / 1000  # MHz
                        cpu_freqs.append(freq)
                except:
                    cpu_freqs.append(0)
            
            # Определяем, есть ли троттлинг
            throttling = self.check_throttling()
            
            return {
                'per_core': cpu_percent,
                'average': avg_percent,
                'cores': len(cpu_percent),
                'frequencies': cpu_freqs,
                'throttling': throttling,
                'max_freq': 2400 if self.pi5_model else 1800  # MHz
            }
        except Exception as e:
            print(f"Ошибка мониторинга CPU: {e}")
            return None
    
    def check_throttling(self):
        """Проверка статуса троттлинга"""
        try:
            with open('/sys/devices/platform/soc/soc:firmware/get_throttled', 'r') as f:
                throttled = f.read().strip()
            
            status = {
                'under_voltage': bool(int(throttled, 16) & 0x1),
                'frequency_capped': bool(int(throttled, 16) & 0x2),
                'throttling': bool(int(throttled, 16) & 0x4),
                'soft_temp_limit': bool(int(throttled, 16) & 0x8)
            }
            return status
        except:
            return {}
    
    def get_gpu_usage(self):
        """Получение информации о GPU"""
        try:
            result = subprocess.run(['vcgencmd', 'get_mem', 'gpu'], 
                                  capture_output=True, text=True)
            gpu_mem = result.stdout.strip()
            
            result = subprocess.run(['vcgencmd', 'measure_clock', 'core'],
                                  capture_output=True, text=True)
            gpu_freq = result.stdout.strip()
            
            return {
                'memory': gpu_mem,
                'frequency': gpu_freq
            }
        except:
            return None
    
    def get_power_status(self):
        """Получение информации о питании"""
        try:
            # Напряжение
            result = subprocess.run(['vcgencmd', 'measure_volts', 'core'],
                                  capture_output=True, text=True)
            voltage = result.stdout.strip()
            
            # Потребление тока (если доступно)
            try:
                with open('/sys/class/hwmon/hwmon1/curr1_input', 'r') as f:
                    current = float(f.read().strip()) / 1000  # Амперы
            except:
                current = None
            
            return {
                'voltage': voltage,
                'current': current
            }
        except:
            return None
    
    def stress_cpu_pi5(self, worker_id, use_vector=False):
        """Специализированная нагрузка для CPU Pi 5"""
        print(f"Запуск CPU воркера Pi5 #{worker_id}")
        
        while self.running:
            # Используем разные типы вычислений для нагрузки
            x = 0.0
            y = 0.0
            z = 0.0
            
            # Интенсивные вычисления с плавающей точкой
            for i in range(500000):
                # Разные математические функции для нагрузки всех ALU
                x += math.sqrt(i) * math.sin(i * 0.01)
                y += math.cos(i * 0.02) * math.log(i + 1)
                z += math.tan(i * 0.005) * math.exp(-i * 0.0001)
            
            # Целочисленные вычисления
            for i in range(100000):
                x += (i * i) % 7919  # Простое число для сложных операций
            
            # Векторные операции (если требуется)
            if use_vector:
                import numpy as np
                arr = np.random.rand(10000)
                x += np.sum(np.sin(arr) * np.cos(arr))
    
    def stress_gpu_pi5(self):
        """Нагрузка на GPU Pi 5"""
        print("Запуск GPU воркера Pi5")
        
        while self.running:
            try:
                # Используем OpenGL/VideoCore команды для нагрузки GPU
                subprocess.run(['vcgencmd', 'measure_temp'], 
                             capture_output=True, text=True)
                
                # Создаем и обрабатываем изображение
                temp_image = '/tmp/gpu_test.rgb'
                size = 1024 * 768 * 3  # RGB изображение
                
                with open(temp_image, 'wb') as f:
                    f.write(os.urandom(size))
                
                # Простая обработка через ImageMagick
                subprocess.run(['convert', temp_image, '-blur', '0x2', temp_image],
                             capture_output=True)
                
                if os.path.exists(temp_image):
                    os.remove(temp_image)
                    
                time.sleep(0.5)
                
            except Exception as e:
                time.sleep(1)
    
    def stress_io_pi5(self, use_pcie=False):
        """Нагрузка на I/O с учетом PCIe на Pi 5"""
        print("Запуск I/O воркера Pi5")
        
        test_file = '/tmp/io_stress_test.bin'
        
        while self.running:
            try:
                # Большой объем данных для нагрузки (100MB)
                data_size = 100 * 1024 * 1024
                
                # Запись
                with open(test_file, 'wb') as f:
                    # Пишем большими блоками для скорости
                    for _ in range(10):
                        f.write(os.urandom(data_size // 10))
                
                # Чтение
                with open(test_file, 'rb') as f:
                    while f.read(1024 * 1024):  # Читаем по 1MB
                        pass
                
                # Удаление
                os.remove(test_file)
                
                # Дополнительная нагрузка на PCIe через рандомные операции
                if use_pcie:
                    import random
                    random_ops = random.randint(100, 1000)
                    for _ in range(random_ops):
                        temp = f'/tmp/temp_{random.randint(0, 1000)}.tmp'
                        with open(temp, 'wb') as f:
                            f.write(os.urandom(1024))
                        if os.path.exists(temp):
                            os.remove(temp)
                
                time.sleep(0.2)
                
            except Exception as e:
                time.sleep(1)
    
    def stress_memory_pi5(self, use_swap=False):
        """Нагрузка на память с учетом особенностей Pi 5"""
        print("Запуск Memory воркера Pi5")
        
        memory_chunks = []
        
        while self.running:
            try:
                # Выделяем разными блоками для нагрузки памяти
                for size_mb in [10, 50, 100]:
                    try:
                        chunk = bytearray(size_mb * 1024 * 1024)
                        memory_chunks.append(chunk)
                    except MemoryError:
                        break
                
                # Операции с памятью
                if memory_chunks:
                    for chunk in memory_chunks:
                        # Изменяем данные в памяти
                        for i in range(0, len(chunk), 4096):
                            chunk[i] = (chunk[i] + 1) % 256
                
                # Периодическая очистка для избежания OOM
                if len(memory_chunks) > 20:
                    memory_chunks = memory_chunks[-10:]
                
                time.sleep(0.3)
                
            except MemoryError:
                if memory_chunks:
                    memory_chunks.pop()
                time.sleep(0.5)
            except Exception as e:
                time.sleep(1)
    
    def start_stress_pi5(self, intensity=1.0):
        """
        Запуск комплексной нагрузки для Pi 5
        
        Args:
            intensity: общая интенсивность нагрузки (0.1 - 1.0)
        """
        print("=" * 70)
        print("RASPBERRY PI 5 - КОМПЛЕКСНЫЙ СТРЕСС-ТЕСТ")
        print("=" * 70)
        
        if self.pi5_model:
            print("✅ Обнаружен Raspberry Pi 5")
        else:
            print("⚠️  Модель не определена как Pi 5")
        
        cpu_cores = multiprocessing.cpu_count()
        
        print(f"\nНастройки нагрузки:")
        print(f"  • CPU воркеров: {cpu_cores * 2}")
        print(f"  • GPU воркеров: 1")
        print(f"  • I/O воркеров: 2")
        print(f"  • Memory воркеров: 1")
        print(f"  • Интенсивность: {intensity:.1f}")
        print(f"  • Интервал записи: {self.interval} сек")
        print(f"  • Файл лога: {self.filename}")
        print("\n⚠️  Внимание: Pi 5 может сильно нагреваться!")
        print(f"   Безопасная температура: до {self.max_safe_temp}°C")
        print(f"   Троттлинг начинается: {self.throttle_temp}°C")
        print("=" * 70)
        print("Для остановки нажмите Ctrl+C")
        print("-" * 70)
        
        self.running = True
        self.workers = []
        
        # CPU нагрузка (больше воркеров для 4 ядер)
        cpu_workers = cpu_cores * 3  # 12 воркеров для 4 ядер
        for i in range(cpu_workers):
            t = threading.Thread(target=self.stress_cpu_pi5, args=(i+1,))
            t.daemon = True
            t.start()
            self.workers.append(t)
        
        # GPU нагрузка
        t = threading.Thread(target=self.stress_gpu_pi5)
        t.daemon = True
        t.start()
        self.workers.append(t)
        
        # I/O нагрузка (2 воркера)
        for i in range(2):
            t = threading.Thread(target=self.stress_io_pi5, args=(i==0,))
            t.daemon = True
            t.start()
            self.workers.append(t)
        
        # Memory нагрузка
        t = threading.Thread(target=self.stress_memory_pi5)
        t.daemon = True
        t.start()
        self.workers.append(t)
    
    def print_pi5_status(self, temp, cpu_data, elapsed, warn_temp=70):
        """Специальный вывод статуса для Pi 5"""
        # Очистка экрана для динамического обновления
        os.system('clear' if os.name == 'posix' else 'cls')
        
        print("=" * 80)
        print("RASPBERRY PI 5 - МОНИТОРИНГ В РЕАЛЬНОМ ВРЕМЕНИ".center(80))
        print("=" * 80)
        
        # Температура с предупреждениями
        if temp >= warn_temp:
            temp_display = f"⚠️  \033[91m{temp:5.1f}°C\033[0m ⚠️"
            if temp >= self.throttle_temp:
                temp_display = f"🚨 \033[91m{temp:5.1f}°C (ТРОТТЛИНГ!)\033[0m 🚨"
        elif temp >= warn_temp - 10:
            temp_display = f"🔶 \033[93m{temp:5.1f}°C\033[0m 🔶"
        else:
            temp_display = f"✅ \033[92m{temp:5.1f}°C\033[0m"
        
        print(f"\n🌡  ТЕМПЕРАТУРА CPU: {temp_display}")
        print(f"   Безопасный предел: {self.max_safe_temp}°C | Троттлинг: {self.throttle_temp}°C")
        
        # Загрузка CPU
        if cpu_data:
            print(f"\n⚡ ЗАГРУЗКА CPU: \033[94m{cpu_data['average']:5.1f}%\033[0m")
            
            # График по ядрам
            print("   " + "─" * 60)
            for i, (percent, freq) in enumerate(zip(cpu_data['per_core'], 
                                                   cpu_data['frequencies'])):
                bar_length = 20
                filled = int(percent / 100 * bar_length)
                bar = "█" * filled + "░" * (bar_length - filled)
                
                # Цвет в зависимости от загрузки
                if percent < 50:
                    color = "\033[92m"
                elif percent < 80:
                    color = "\033[93m"
                else:
                    color = "\033[91m"
                
                freq_str = f"{freq:.0f} MHz" if freq > 0 else "N/A"
                print(f"   Ядро {i}: {color}{bar}\033[0m {percent:6.1f}% | {freq_str}")
        
        # Статус троттлинга
        if cpu_data and 'throttling' in cpu_data:
            throttle = cpu_data['throttling']
            if any(throttle.values()):
                print(f"\n⚠️  СТАТУС ТРОТТЛИНГА:")
                for key, value in throttle.items():
                    if value:
                        status = "🔴 ВКЛ" if value else "🟢 ВЫКЛ"
                        print(f"   • {key}: \033[91m{status}\033[0m")
        
        # Информация о системе
        try:
            mem = psutil.virtual_memory()
            mem_percent = mem.percent
            mem_color = "\033[92m" if mem_percent < 70 else "\033[93m" if mem_percent < 90 else "\033[91m"
            
            print(f"\n💾 ПАМЯТЬ: {mem_color}{mem_percent:5.1f}%\033[0m")
            print(f"   Использовано: {mem.used / (1024**3):.1f} GB / {mem.total / (1024**3):.1f} GB")
            
            # Информация о GPU
            gpu_info = self.get_gpu_usage()
            if gpu_info:
                print(f"\n🎮 GPU: {gpu_info['memory']} | Частота: {gpu_info['frequency']}")
            
        except:
            pass
        
        # Время и информация
        print(f"\n⏱  ВРЕМЯ РАБОТЫ: {elapsed:.1f} секунд")
        print(f"📊 ФАЙЛ ЛОГА: {self.filename}")
        print(f"🕐 ТЕКУЩЕЕ ВРЕМЯ: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("\n" + "=" * 80)
        print("Нажмите Ctrl+C для остановки".center(80))
        print("=" * 80)
    
    def log_data_pi5(self, duration=None):
        """Запись данных с расширенной информацией для Pi 5"""
        start_time = time.time()
        
        # Создание заголовка CSV
        with open(self.filename, 'w', newline='') as csvfile:
            csvwriter = csv.writer(csvfile)
            
            # Базовые колонки
            header = ['timestamp', 'temperature_c', 'cpu_avg_percent', 'elapsed_seconds']
            
            # Колонки для каждого ядра CPU
            cpu_count = psutil.cpu_count()
            for i in range(cpu_count):
                header.append(f'cpu_core_{i}_percent')
                header.append(f'cpu_core_{i}_freq_mhz')
            
            # Дополнительные колонки
            header.extend([
                'throttling_under_voltage',
                'throttling_freq_capped',
                'throttling_active',
                'throttling_soft_limit',
                'memory_percent',
                'memory_used_gb',
                'memory_total_gb',
                'gpu_memory',
                'gpu_frequency',
                'voltage',
                'current_a'
            ])
            
            csvwriter.writerow(header)
        
        print("Начало записи данных...")
        time.sleep(2)  # Даем время нагрузке начаться
        
        try:
            while self.running:
                current_time = time.time()
                elapsed = current_time - start_time
                
                # Сбор всех данных
                temp = self.get_temperature()
                cpu_data = self.get_cpu_usage_pi5()
                gpu_info = self.get_gpu_usage()
                power_info = self.get_power_status()
                
                # Получение информации о памяти
                mem = psutil.virtual_memory()
                
                if temp is not None and cpu_data is not None:
                    # Отображение в консоли
                    self.print_pi5_status(temp, cpu_data, elapsed)
                    
                    # Подготовка данных для CSV
                    timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    
                    # Базовые данные
                    row = [
                        timestamp,
                        f"{temp:.2f}",
                        f"{cpu_data['average']:.2f}",
                        f"{elapsed:.1f}"
                    ]
                    
                    # Данные по ядрам CPU
                    for percent, freq in zip(cpu_data['per_core'], 
                                           cpu_data.get('frequencies', [0]*len(cpu_data['per_core']))):
                        row.append(f"{percent:.2f}")
                        row.append(f"{freq:.0f}" if freq > 0 else "N/A")
                    
                    # Данные троттлинга
                    throttle = cpu_data.get('throttling', {})
                    row.extend([
                        "1" if throttle.get('under_voltage') else "0",
                        "1" if throttle.get('frequency_capped') else "0",
                        "1" if throttle.get('throttling') else "0",
                        "1" if throttle.get('soft_temp_limit') else "0"
                    ])
                    
                    # Данные памяти
                    row.extend([
                        f"{mem.percent:.2f}",
                        f"{mem.used / (1024**3):.2f}",
                        f"{mem.total / (1024**3):.2f}"
                    ])
                    
                    # Данные GPU
                    if gpu_info:
                        row.extend([
                            gpu_info.get('memory', 'N/A'),
                            gpu_info.get('frequency', 'N/A')
                        ])
                    else:
                        row.extend(['N/A', 'N/A'])
                    
                    # Данные питания
                    if power_info:
                        row.extend([
                            power_info.get('voltage', 'N/A'),
                            f"{power_info.get('current', 0):.3f}" if power_info.get('current') else 'N/A'
                        ])
                    else:
                        row.extend(['N/A', 'N/A'])
                    
                    # Запись в CSV
                    with open(self.filename, 'a', newline='') as csvfile:
                        csvwriter = csv.writer(csvfile)
                        csvwriter.writerow(row)
                    
                    # Проверка критической температуры
                    if temp > self.max_safe_temp:
                        print(f"\n\033[91m⚠️  КРИТИЧЕСКАЯ ТЕМПЕРАТУРА! {temp:.1f}°C > {self.max_safe_temp}°C\033[0m")
                        print("\033[91m   Рекомендуется остановить тест!\033[0m")
                
                # Проверка времени
                if duration and elapsed >= duration:
                    print(f"\n{'='*80}")
                    print(f"Достигнута заданная продолжительность ({duration:.0f} секунд)".center(80))
                    print("=" * 80)
                    break
                
                time.sleep(self.interval)
                
        except KeyboardInterrupt:
            print(f"\n\n{'='*80}")
            print("ТЕСТ ПРЕРВАН ПОЛЬЗОВАТЕЛЕМ".center(80))
            print("=" * 80)
        except Exception as e:
            print(f"\nОшибка: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self.running = False
            time.sleep(1)
            
            print(f"\n📊 ИТОГИ:")
            print(f"   • Файл данных: {self.filename}")
            print(f"   • Записей: {self.count_records()}")
            print(f"   • Общее время: {time.time() - start_time:.1f} сек")
            print(f"\n{'='*80}")
    
    def count_records(self):
        """Подсчет записей"""
        try:
            with open(self.filename, 'r') as f:
                return sum(1 for line in f) - 1
        except:
            return 0

def main():
    """Главная функция для Pi 5"""
    # Проверка зависимостей
    try:
        import psutil
    except ImportError:
        print("Установите psutil: sudo pip3 install psutil")
        sys.exit(1)
    
    print("\n" + "="*80)
    print("RASPBERRY PI 5 - СТРЕСС-ТЕСТ И МОНИТОРИНГ".center(80))
    print("="*80)
    
    # Настройки
    filename = input(f"\nИмя файла лога [pi5_stress_log.csv]: ").strip()
    if not filename:
        filename = "pi5_stress_log.csv"
    
    interval_str = input(f"Интервал записи (сек) [2.0]: ").strip()
    interval = float(interval_str) if interval_str else 2.0
    
    duration_str = input(f"Продолжительность теста в секундах (Enter - без ограничения): ").strip()
    duration = float(duration_str) if duration_str else None
    
    intensity_str = input(f"Интенсивность нагрузки (0.1-1.0) [1.0]: ").strip()
    intensity = float(intensity_str) if intensity_str else 1.0
    
    # Предупреждение
    print(f"\n{'⚠️'*40}")
    print("ВНИМАНИЕ: Raspberry Pi 5 может сильно нагреваться!")
    print("Убедитесь в наличии адекватного охлаждения!")
    print(f"{'⚠️'*40}\n")
    
    confirm = input("Продолжить? (y/N): ").strip().lower()
    if confirm != 'y':
        print("Отменено.")
        return
    
    # Запуск теста
    tester = Pi5StressTester(filename=filename, interval=interval)
    tester.start_stress_pi5(intensity=intensity)
    tester.log_data_pi5(duration=duration)

if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    main()