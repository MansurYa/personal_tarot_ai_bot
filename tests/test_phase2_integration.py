"""
Интеграционный тест для ФАЗЫ 2: Inline-меню и навигация
"""
import sys
import os

# Добавляем путь к src для импорта модулей
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.keyboards import main_menu, spreads_menu, SPREAD_NAMES
from src.config import load_config


def test_phase2_integration():
    """
    Проверяет что все компоненты ФАЗЫ 2 готовы к работе
    """
    print("🧪 Интеграционный тест ФАЗЫ 2...")
    print("=" * 50)
    
    # 1. Проверяем конфигурацию
    print("1️⃣ Проверяем конфигурацию...")
    config = load_config()
    assert 'telegram_bot_token' in config
    assert 'openrouter_api_key' in config
    assert 'model_name' in config
    print("   ✅ Конфигурация загружается корректно")
    
    # 2. Проверяем главное меню
    print("2️⃣ Проверяем главное меню...")
    menu = main_menu()
    assert len(menu.inline_keyboard) == 2
    print("   ✅ Главное меню создается корректно")
    
    # 3. Проверяем меню раскладов
    print("3️⃣ Проверяем меню раскладов...")
    spreads = spreads_menu()
    assert len(spreads.inline_keyboard) == 8  # 7 раскладов + кнопка "Назад"
    print("   ✅ Меню раскладов создается корректно")
    
    # 4. Проверяем словарь раскладов
    print("4️⃣ Проверяем словарь раскладов...")
    assert len(SPREAD_NAMES) == 7
    expected_spreads = ["spread_single", "spread_three", "spread_horseshoe", 
                       "spread_love", "spread_celtic", "spread_week", "spread_year"]
    for spread in expected_spreads:
        assert spread in SPREAD_NAMES
    print("   ✅ Все 7 раскладов определены корректно")
    
    # 5. Проверяем импорты модулей
    print("5️⃣ Проверяем импорты...")
    try:
        from src.handlers import handle_callback_query
        from src.bot import start_command, help_command
        print("   ✅ Все модули импортируются без ошибок")
    except ImportError as e:
        raise AssertionError(f"Ошибка импорта: {e}")
    
    print("=" * 50)
    print("🎉 ФАЗА 2 готова к работе!")
    print()
    print("📋 Что реализовано:")
    print("   • Inline-клавиатуры для навигации")
    print("   • Главное меню с кнопками")
    print("   • Список всех 7 раскладов")
    print("   • Кнопки 'Назад' для навигации")
    print("   • Callback-обработчики для всех кнопок")
    print("   • Интеграция с основным ботом")
    print()
    print("🚀 Следующий шаг: Сбор данных пользователя и ConversationHandler")


if __name__ == "__main__":
    test_phase2_integration()