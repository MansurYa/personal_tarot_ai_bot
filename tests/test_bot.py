"""
Тесты для проверки bot.py на синтаксические ошибки
"""
import sys
import os
import json
import tempfile
import importlib.util

# Добавляем путь к src для импорта
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


def test_bot_import():
    """
    Тестируем, что модуль bot.py импортируется без ошибок
    """
    print("🧪 Тест: импорт модуля bot.py")
    
    try:
        # Создаем временную директорию для теста
        with tempfile.TemporaryDirectory() as temp_dir:
            # Сохраняем текущую директорию
            original_dir = os.getcwd()
            
            try:
                # Переходим в временную директорию
                os.chdir(temp_dir)
                
                # Создаем временный config.json с валидным токеном для тестов
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
                
                # Создаем символическую ссылку на src
                src_path = os.path.join(os.path.dirname(__file__), '..', 'src')
                os.symlink(src_path, 'src')
                
                # Пытаемся импортировать bot модуль
                import bot
                
                print("✅ УСПЕХ: Модуль bot.py импортирован без ошибок")
                
                # Проверяем наличие основных функций
                if hasattr(bot, 'run_bot'):
                    print("✅ УСПЕХ: Функция run_bot найдена")
                else:
                    print("❌ ОШИБКА: Функция run_bot не найдена")
                    return False
                
                if hasattr(bot, 'start_command'):
                    print("✅ УСПЕХ: Функция start_command найдена")
                else:
                    print("❌ ОШИБКА: Функция start_command не найдена")
                    return False
                
                if hasattr(bot, 'help_command'):
                    print("✅ УСПЕХ: Функция help_command найдена")
                else:
                    print("❌ ОШИБКА: Функция help_command не найдена")
                    return False
                
                if hasattr(bot, 'handle_message'):
                    print("✅ УСПЕХ: Функция handle_message найдена")
                else:
                    print("❌ ОШИБКА: Функция handle_message не найдена")
                    return False
                
                return True
                
            finally:
                # Возвращаемся в исходную директорию
                os.chdir(original_dir)
                
    except ImportError as e:
        print(f"❌ ОШИБКА ИМПОРТА: {e}")
        return False
    except Exception as e:
        print(f"❌ НЕОЖИДАННАЯ ОШИБКА: {type(e).__name__}: {e}")
        return False


def test_bot_syntax():
    """
    Проверяем синтаксис файла bot.py
    """
    print("\n🧪 Тест: синтаксис bot.py")
    
    bot_file = os.path.join(os.path.dirname(__file__), '..', 'src', 'bot.py')
    
    try:
        with open(bot_file, 'r', encoding='utf-8') as f:
            source_code = f.read()
        
        # Компилируем код для проверки синтаксиса
        compile(source_code, bot_file, 'exec')
        print("✅ УСПЕХ: Синтаксис bot.py корректен")
        return True
        
    except SyntaxError as e:
        print(f"❌ СИНТАКСИЧЕСКАЯ ОШИБКА в {bot_file}:")
        print(f"   Строка {e.lineno}: {e.text.strip() if e.text else ''}")
        print(f"   Ошибка: {e.msg}")
        return False
    except Exception as e:
        print(f"❌ ОШИБКА при проверке синтаксиса: {e}")
        return False


if __name__ == "__main__":
    print("🚀 Запуск тестов для bot.py\n")
    
    tests_passed = 0
    total_tests = 2
    
    # Запускаем тесты
    if test_bot_syntax():
        tests_passed += 1
    
    if test_bot_import():
        tests_passed += 1
    
    # Выводим результаты
    print(f"\n📊 Результаты тестов: {tests_passed}/{total_tests}")
    
    if tests_passed == total_tests:
        print("🎉 Все тесты прошли успешно!")
        print("✅ Бот готов к запуску!")
    else:
        print("❌ Некоторые тесты провалились")
        sys.exit(1)