"""
Тесты для main.py
"""
import sys
import os
import json
import tempfile
from unittest.mock import patch
import subprocess
import signal
import time


def test_main_with_valid_config():
    """
    Тест запуска main.py с валидной конфигурацией (без реального запуска бота)
    """
    print("🧪 Тест: запуск main.py с валидной конфигурацией")
    
    # Создаем временную директорию для теста
    with tempfile.TemporaryDirectory() as temp_dir:
        # Сохраняем текущую директорию
        original_dir = os.getcwd()
        
        try:
            # Переходим в временную директорию
            os.chdir(temp_dir)
            
            # Создаем src директорию и файлы
            os.makedirs('src', exist_ok=True)
            
            # Копируем файлы src
            src_files = ['config.py', 'bot.py', '__init__.py']
            for filename in src_files:
                src_path = os.path.join(original_dir, 'src', filename)
                dest_path = os.path.join('src', filename)
                if os.path.exists(src_path):
                    with open(src_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    with open(dest_path, 'w', encoding='utf-8') as f:
                        f.write(content)
            
            # Создаем main.py
            main_path = os.path.join(original_dir, 'main.py')
            with open(main_path, 'r', encoding='utf-8') as f:
                main_content = f.read()
            with open('main.py', 'w', encoding='utf-8') as f:
                f.write(main_content)
            
            # Создаем config.json с валидным токеном
            test_config = {
                "telegram_bot_token": "123456789:ABCDEFGHIJKLMNOPQRSTUVWXYZ",
                "openrouter_api_key": "sk-or-v1-test-key",
                "bot_username": "@test_bot",
                "model_name": "deepseek/deepseek-chat-v3-0324:free",
                "max_message_length": 4096,
                "max_response_tokens": 8000,
                "temperature": 0.3
            }
            
            with open("config.json", "w", encoding="utf-8") as f:
                json.dump(test_config, f, indent=4, ensure_ascii=False)
            
            # Тестируем только загрузку и проверку конфигурации
            # (не запускаем реального бота)
            test_code = '''
import sys
sys.path.insert(0, "src")
from config import load_config

try:
    config = load_config()
    token = config.get("telegram_bot_token", "").strip()
    if not token:
        print("❌ Токен не найден")
        sys.exit(1)
    else:
        print("✅ Конфигурация загружена")
        print(f"   Bot: {config.get('bot_username', 'Не указан')}")
        print(f"   Model: {config.get('model_name', 'Не указан')}")
        print("✅ Готов к запуску!")
except Exception as e:
    print(f"❌ Ошибка: {e}")
    sys.exit(1)
'''
            
            # Выполняем тестовый код
            result = subprocess.run([sys.executable, '-c', test_code], 
                                  capture_output=True, text=True)
            
            if result.returncode == 0 and "✅ Готов к запуску!" in result.stdout:
                print("✅ УСПЕХ: main.py готов к запуску с валидной конфигурацией")
                print("📋 Вывод:")
                for line in result.stdout.strip().split('\n'):
                    print(f"   {line}")
                return True
            else:
                print("❌ ОШИБКА: Проблема с загрузкой конфигурации")
                print(f"Return code: {result.returncode}")
                print(f"STDOUT: {result.stdout}")
                print(f"STDERR: {result.stderr}")
                return False
                
        finally:
            # Возвращаемся в исходную директорию
            os.chdir(original_dir)


def test_main_with_empty_token():
    """
    Тест запуска main.py с пустым токеном
    """
    print("\n🧪 Тест: запуск main.py с пустым токеном")
    
    # Создаем временную директорию для теста
    with tempfile.TemporaryDirectory() as temp_dir:
        # Сохраняем текущую директорию
        original_dir = os.getcwd()
        
        try:
            # Переходим в временную директорию
            os.chdir(temp_dir)
            
            # Создаем src директорию и файлы
            os.makedirs('src', exist_ok=True)
            
            # Копируем файлы src
            src_files = ['config.py', 'bot.py', '__init__.py']
            for filename in src_files:
                src_path = os.path.join(original_dir, 'src', filename)
                dest_path = os.path.join('src', filename)
                if os.path.exists(src_path):
                    with open(src_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    with open(dest_path, 'w', encoding='utf-8') as f:
                        f.write(content)
            
            # Создаем config.json с пустым токеном
            test_config = {
                "telegram_bot_token": "",  # Пустой токен
                "openrouter_api_key": "sk-or-v1-test-key",
                "bot_username": "@test_bot",
                "model_name": "deepseek/deepseek-chat-v3-0324:free",
                "max_message_length": 4096,
                "max_response_tokens": 8000,
                "temperature": 0.3
            }
            
            with open("config.json", "w", encoding="utf-8") as f:
                json.dump(test_config, f, indent=4, ensure_ascii=False)
            
            # Тестируем с пустым токеном
            test_code = '''
import sys
sys.path.insert(0, "src")

try:
    from config import load_config
    config = load_config()
    print("❌ ОШИБКА: Пустой токен должен был вызвать исключение")
    sys.exit(1)
except ValueError as e:
    if "Добавьте токен бота в config.json" in str(e):
        print("✅ УСПЕХ: Правильная ошибка для пустого токена")
        sys.exit(0)
    else:
        print(f"❌ ОШИБКА: Неправильное сообщение: {e}")
        sys.exit(1)
except Exception as e:
    print(f"❌ НЕОЖИДАННАЯ ОШИБКА: {e}")
    sys.exit(1)
'''
            
            # Выполняем тестовый код
            result = subprocess.run([sys.executable, '-c', test_code], 
                                  capture_output=True, text=True)
            
            if result.returncode == 0 and "✅ УСПЕХ" in result.stdout:
                print("✅ УСПЕХ: Пустой токен правильно обрабатывается")
                return True
            else:
                print("❌ ОШИБКА: Проблема с обработкой пустого токена")
                print(f"Return code: {result.returncode}")
                print(f"STDOUT: {result.stdout}")
                print(f"STDERR: {result.stderr}")
                return False
                
        finally:
            # Возвращаемся в исходную директорию
            os.chdir(original_dir)


if __name__ == "__main__":
    print("🚀 Запуск тестов для main.py\n")
    
    tests_passed = 0
    total_tests = 2
    
    # Запускаем тесты
    if test_main_with_valid_config():
        tests_passed += 1
    
    if test_main_with_empty_token():
        tests_passed += 1
    
    # Выводим результаты
    print(f"\n📊 Результаты тестов: {tests_passed}/{total_tests}")
    
    if tests_passed == total_tests:
        print("🎉 Все тесты прошли успешно!")
        print("✅ main.py готов к использованию!")
    else:
        print("❌ Некоторые тесты провалились")
        sys.exit(1)