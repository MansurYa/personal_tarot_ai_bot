"""
Тесты для модуля config.py
"""
import sys
import os
import json
import tempfile
import shutil
from pathlib import Path

# Добавляем путь к src для импорта
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from config import load_config


def test_empty_token_error():
    """
    Тестируем, что пустой токен вызывает правильную ошибку
    """
    print("🧪 Тест: пустой токен должен вызывать ошибку")
    
    # Создаем временную директорию для теста
    with tempfile.TemporaryDirectory() as temp_dir:
        # Сохраняем текущую директорию
        original_dir = os.getcwd()
        
        try:
            # Переходим в временную директорию
            os.chdir(temp_dir)
            
            # Создаем config.json с пустым токеном
            test_config = {
                "telegram_bot_token": "",  # Пустой токен
                "openrouter_api_key": "test-key",
                "bot_username": "@test_bot",
                "model_name": "deepseek/deepseek-chat-v3-0324:free",
                "max_message_length": 4096,
                "max_response_tokens": 8000,
                "temperature": 0.3
            }
            
            with open("config.json", "w", encoding="utf-8") as f:
                json.dump(test_config, f, indent=4, ensure_ascii=False)
            
            # Пытаемся загрузить конфигурацию
            try:
                load_config()
                print("❌ ОШИБКА: Ожидалась ValueError, но функция выполнилась успешно")
                return False
            except ValueError as e:
                expected_message = "Ошибка: Добавьте токен бота в config.json"
                if str(e) == expected_message:
                    print(f"✅ УСПЕХ: Получена правильная ошибка: {e}")
                    return True
                else:
                    print(f"❌ ОШИБКА: Неправильное сообщение об ошибке:")
                    print(f"   Ожидали: {expected_message}")
                    print(f"   Получили: {e}")
                    return False
            except Exception as e:
                print(f"❌ ОШИБКА: Неожиданный тип исключения: {type(e).__name__}: {e}")
                return False
        
        finally:
            # Возвращаемся в исходную директорию
            os.chdir(original_dir)


def test_whitespace_token_error():
    """
    Тестируем, что токен из пробелов вызывает правильную ошибку
    """
    print("\n🧪 Тест: токен из пробелов должен вызывать ошибку")
    
    # Создаем временную директорию для теста
    with tempfile.TemporaryDirectory() as temp_dir:
        # Сохраняем текущую директорию
        original_dir = os.getcwd()
        
        try:
            # Переходим в временную директорию
            os.chdir(temp_dir)
            
            # Создаем config.json с токеном из пробелов
            test_config = {
                "telegram_bot_token": "   ",  # Только пробелы
                "openrouter_api_key": "test-key",
                "bot_username": "@test_bot",
                "model_name": "deepseek/deepseek-chat-v3-0324:free",
                "max_message_length": 4096,
                "max_response_tokens": 8000,
                "temperature": 0.3
            }
            
            with open("config.json", "w", encoding="utf-8") as f:
                json.dump(test_config, f, indent=4, ensure_ascii=False)
            
            # Пытаемся загрузить конфигурацию
            try:
                load_config()
                print("❌ ОШИБКА: Ожидалась ValueError, но функция выполнилась успешно")
                return False
            except ValueError as e:
                expected_message = "Ошибка: Добавьте токен бота в config.json"
                if str(e) == expected_message:
                    print(f"✅ УСПЕХ: Получена правильная ошибка: {e}")
                    return True
                else:
                    print(f"❌ ОШИБКА: Неправильное сообщение об ошибке:")
                    print(f"   Ожидали: {expected_message}")
                    print(f"   Получили: {e}")
                    return False
            except Exception as e:
                print(f"❌ ОШИБКА: Неожиданный тип исключения: {type(e).__name__}: {e}")
                return False
        
        finally:
            # Возвращаемся в исходную директорию
            os.chdir(original_dir)


def test_valid_config():
    """
    Тестируем, что валидная конфигурация загружается успешно
    """
    print("\n🧪 Тест: валидная конфигурация должна загружаться успешно")
    
    # Создаем временную директорию для теста
    with tempfile.TemporaryDirectory() as temp_dir:
        # Сохраняем текущую директорию
        original_dir = os.getcwd()
        
        try:
            # Переходим в временную директорию
            os.chdir(temp_dir)
            
            # Создаем config.json с валидными данными
            test_config = {
                "telegram_bot_token": "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11",
                "openrouter_api_key": "sk-or-v1-test-key",
                "bot_username": "@test_bot",
                "model_name": "deepseek/deepseek-chat-v3-0324:free",
                "max_message_length": 4096,
                "max_response_tokens": 8000,
                "temperature": 0.3
            }
            
            with open("config.json", "w", encoding="utf-8") as f:
                json.dump(test_config, f, indent=4, ensure_ascii=False)
            
            # Пытаемся загрузить конфигурацию
            try:
                config = load_config()
                print("✅ УСПЕХ: Конфигурация загружена успешно")
                print(f"   Токен: {config['telegram_bot_token'][:10]}...")
                print(f"   Bot username: {config['bot_username']}")
                return True
            except Exception as e:
                print(f"❌ ОШИБКА: Неожиданная ошибка: {type(e).__name__}: {e}")
                return False
        
        finally:
            # Возвращаемся в исходную директорию
            os.chdir(original_dir)


if __name__ == "__main__":
    print("🚀 Запуск тестов для config.py\n")
    
    tests_passed = 0
    total_tests = 3
    
    # Запускаем тесты
    if test_empty_token_error():
        tests_passed += 1
    
    if test_whitespace_token_error():
        tests_passed += 1
    
    if test_valid_config():
        tests_passed += 1
    
    # Выводим результаты
    print(f"\n📊 Результаты тестов: {tests_passed}/{total_tests}")
    
    if tests_passed == total_tests:
        print("🎉 Все тесты прошли успешно!")
    else:
        print("❌ Некоторые тесты провалились")
        sys.exit(1)