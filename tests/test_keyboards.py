"""
Тесты для inline-клавиатур
"""
import sys
import os

# Добавляем путь к src для импорта модулей
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.keyboards import main_menu, spreads_menu, back_button, help_menu, SPREAD_NAMES


def test_main_menu():
    """Тестирует главное меню"""
    keyboard = main_menu()
    
    # Проверяем что это InlineKeyboardMarkup
    assert hasattr(keyboard, 'inline_keyboard')
    
    # Проверяем количество кнопок
    buttons = keyboard.inline_keyboard
    assert len(buttons) == 2  # "Сделать расклад" и "Помощь"
    
    # Проверяем callback_data
    assert buttons[0][0].callback_data == "spreads_list"
    assert buttons[1][0].callback_data == "help"
    
    print("✅ test_main_menu прошёл")


def test_spreads_menu():
    """Тестирует меню раскладов"""
    keyboard = spreads_menu()
    
    # Проверяем что это InlineKeyboardMarkup
    assert hasattr(keyboard, 'inline_keyboard')
    
    # Проверяем количество кнопок (7 раскладов + кнопка "Назад")
    buttons = keyboard.inline_keyboard
    assert len(buttons) == 8
    
    # Проверяем что последняя кнопка - "Назад"
    assert buttons[-1][0].callback_data == "back_to_main"
    
    # Проверяем что все callback_data начинаются с "spread_"
    spread_callbacks = [button[0].callback_data for button in buttons[:-1]]  # Исключаем кнопку "Назад"
    for callback in spread_callbacks:
        assert callback.startswith("spread_")
    
    print("✅ test_spreads_menu прошёл")


def test_back_button():
    """Тестирует кнопку 'Назад'"""
    keyboard = back_button("test_callback")
    
    # Проверяем что это InlineKeyboardMarkup
    assert hasattr(keyboard, 'inline_keyboard')
    
    # Проверяем что есть только одна кнопка
    buttons = keyboard.inline_keyboard
    assert len(buttons) == 1
    assert len(buttons[0]) == 1
    
    # Проверяем callback_data
    assert buttons[0][0].callback_data == "test_callback"
    
    print("✅ test_back_button прошёл")


def test_help_menu():
    """Тестирует меню помощи"""
    keyboard = help_menu()
    
    # Проверяем что это InlineKeyboardMarkup
    assert hasattr(keyboard, 'inline_keyboard')
    
    # Проверяем что это кнопка "Назад" к главному меню
    buttons = keyboard.inline_keyboard
    assert len(buttons) == 1
    assert buttons[0][0].callback_data == "back_to_main"
    
    print("✅ test_help_menu прошёл")


def test_spread_names():
    """Тестирует словарь с названиями раскладов"""
    # Проверяем что все ожидаемые ключи есть
    expected_keys = [
        "spread_single", "spread_three", "spread_horseshoe", 
        "spread_love", "spread_celtic", "spread_week", "spread_year"
    ]
    
    for key in expected_keys:
        assert key in SPREAD_NAMES
        assert isinstance(SPREAD_NAMES[key], str)
        assert len(SPREAD_NAMES[key]) > 0
    
    # Проверяем что количество раскладов соответствует ожидаемому (7)
    assert len(SPREAD_NAMES) == 7
    
    print("✅ test_spread_names прошёл")


def run_all_tests():
    """Запускает все тесты"""
    print("🧪 Запуск тестов клавиатур...")
    print("=" * 50)
    
    try:
        test_main_menu()
        test_spreads_menu()
        test_back_button()
        test_help_menu()
        test_spread_names()
        
        print("=" * 50)
        print("🎉 Все тесты клавиатур прошли успешно!")
        
    except Exception as e:
        print(f"❌ Ошибка в тестах: {e}")
        raise


if __name__ == "__main__":
    run_all_tests()