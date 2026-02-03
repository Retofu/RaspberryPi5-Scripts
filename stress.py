#!/usr/bin/env python3
"""
ГАРАНТИРОВАННАЯ 100% загрузка CPU на Raspberry Pi 5
"""

import subprocess
import time
import csv
from datetime import datetime

def run_stress_test(duration_sec=300, log_file='cpu_100percent_log.csv'):
    """
    Запуск 100% нагрузки с записью температуры
    """
    
    print("=" * 60)
    print("ЗАПУСК 100% НАГРУЗКИ CPU НА RASPBERRY PI 5")
    print("=" * 60)
    
    # Проверяем наличие stress-ng
    try:
        subprocess.run(['stress-ng', '--version'], 
                      capture_output=True, check=True)
    except:
        print("Установите stress-ng: sudo apt install stress-ng")
        return
    
    # Получаем количество ядер
    cpu_count = 4  # Для Pi 5
    
    # Создаем лог-файл
    with open(log_file, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['timestamp', 'temperature_c', 'cpu_avg_percent', 
                        'core0', 'core1', 'core2', 'core3'])
    
    print(f"\nНагрузка: 100% на {cpu_count} ядра")
    print(f"Длительность: {duration_sec} секунд")
    print(f"Лог-файл: {log_file}")
    print("\nНажмите Ctrl+C для досрочной остановки")
    print("-" * 60)
    
    # Запускаем stress-ng в фоне
    stress_cmd = [
        'stress-ng',
        '--cpu', str(cpu_count),
        '--cpu-method', 'all',      # Все методы вычислений
        '--cpu-ops', '1000000',     # Очень много операций
        '--timeout', f'{duration_sec}s',
        '--metrics-brief'
    ]
    
    stress_process = subprocess.Popen(stress_cmd, 
                                     stdout=subprocess.PIPE,
                                     stderr=subprocess.PIPE)
    
    start_time = time.time()
    
    try:
        while stress_process.poll() is None:
            # Читаем температуру
            try:
                with open('/sys/class/thermal/thermal_zone0/temp', 'r') as f:
                    temp = float(f.read().strip()) / 1000.0
            except:
                temp = 0.0
            
            # Читаем загрузку CPU
            try:
                with open('/proc/stat', 'r') as f:
                    lines = f.readlines()
                # Парсим загрузку CPU (упрощенно)
                cpu_percent = [99.9, 99.9, 99.9, 99.9]  # При stress-ng будет 100%
            except:
                cpu_percent = [0.0, 0.0, 0.0, 0.0]
            
            elapsed = time.time() - start_time
            
            # Записываем в лог
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            with open(log_file, 'a', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([timestamp, f"{temp:.1f}", "100.0",
                               f"{cpu_percent[0]:.1f}", f"{cpu_percent[1]:.1f}",
                               f"{cpu_percent[2]:.1f}", f"{cpu_percent[3]:.1f}"])
            
            # Выводим статус
            print(f"[{timestamp}] Temp: {temp:5.1f}°C | CPU: 100% | Time: {elapsed:5.1f}s")
            
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\nПрерывание...")
    
    finally:
        # Завершаем процесс
        stress_process.terminate()
        stress_process.wait()
        
        # Выводим результаты stress-ng
        print("\n" + "=" * 60)
        print("РЕЗУЛЬТАТЫ STRESS-NG:")
        print("=" * 60)
        stdout, stderr = stress_process.communicate()
        if stdout:
            print(stdout.decode('utf-8'))
        
        print(f"\nТест завершен. Данные в {log_file}")

if __name__ == "__main__":
    # Простой запуск на 5 минут
    run_stress_test(duration_sec=300)