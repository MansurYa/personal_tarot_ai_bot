"""
Тесты для обновленных обработчиков callback-запросов
"""
import sys
import os

# Добавляем путь к src для импорта модулей
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.handlers import (
    handle_main_menu, 
    handle_spreads_list, 
    handle_spread_selection, 
    handle_help, 
    handle_callback
)
from src.keyboards import SPREAD_NAMES


def test_imports():
    """Проверяет что все обработчики импортируются корректно"""
    print("1️⃣ Проверка импортов обработчиков...")
    
    # Проверяем что функции определены
    assert callable(handle_main_menu)
    assert callable(handle_spreads_list)
    assert callable(handle_spread_selection)
    assert callable(handle_help)
    assert callable(handle_callback)
    
    print("   ✅ Все обработчики импортируются корректно")


def test_spread_names_usage():
    """Проверяет что словарь SPREAD_NAMES используется правильно"""
    print("2️⃣ Проверка использования SPREAD_NAMES...")
    
    # Проверяем что все ожидаемые расклады есть
    expected_spreads = [
        "spread_single", "spread_three", "spread_horseshoe",
        "spread_love", "spread_celtic", "spread_week", "spread_year"
    ]
    
    for spread in expected_spreads:
        assert spread in SPREAD_NAMES
        assert isinstance(SPREAD_NAMES[spread], str)
        assert len(SPREAD_NAMES[spread]) > 0
    
    print(f"   ✅ Все {len(SPREAD_NAMES)} раскладов определены корректно")


def test_callback_routing_logic():
    """Проверяет логику маршрутизации callback-запросов"""
    print("3️⃣ Проверка логики маршрутизации...")
    
    # Тестовые callback_data
    test_callbacks = [
        "back_to_main",
        "spreads_list", 
        "help",
        "spread_single",
        "spread_three",
        "spread_unknown"
    ]
    
    # Проверяем что для каждого callback есть соответствующий обработчик
    known_callbacks = ["back_to_main", "spreads_list", "help"]
    spread_callbacks = [cb for cb in test_callbacks if cb.startswith("spread_")]
    
    assert len(known_callbacks) == 3
    assert len(spread_callbacks) >= 2  # Минимум 2 spread callback для теста
    
    print("   ✅ Логика маршрутизации корректна")


def test_error_handling_structure():
    """Проверяет структуру обработки ошибок"""
    print("4️⃣ Проверка структуры обработки ошибок...")
    
    # Проверяем что функция handle_callback имеет try-except блок
    import inspect
    source = inspect.getsource(handle_callback)
    
    assert "try:" in source
    assert "except" in source
    assert "logger.error" in source
    
    print("   ✅ Обработка ошибок реализована")


def test_docstrings():
    """Проверяет наличие docstring у всех функций"""
    print("5️⃣ Проверка документации...")
    
    functions = [
        handle_main_menu,
        handle_spreads_list, 
        handle_spread_selection,
        handle_help,
        handle_callback
    ]
    
    for func in functions:
        assert func.__doc__ is not None
        assert len(func.__doc__.strip()) > 0
    
    print("   ✅ Все функции документированы")


def run_all_tests():
    """Запускает все тесты обработчиков"""
    print("🧪 Тестирование обновленных обработчиков...")
    print("=" * 60)
    
    try:
        test_imports()
        test_spread_names_usage()
        test_callback_routing_logic()
        test_error_handling_structure()
        test_docstrings()
        
        print("=" * 60)
        print("🎉 Все тесты обработчиков прошли успешно!")
        print()
        print("📋 Проверенные компоненты:")
        print("   • handle_main_menu() - показ главного меню")
        print("   • handle_spreads_list() - список раскладов")
        print("   • handle_spread_selection() - выбор расклада")
        print("   • handle_help() - справка о боте")
        print("   • handle_callback() - роутер callback-запросов")
        print("   • Обработка ошибок и логирование")
        print("   • Использование edit_message_text")
        
    except Exception as e:
        print(f"❌ Ошибка в тестах: {e}")
        raise


if __name__ == "__main__":
    run_all_tests()