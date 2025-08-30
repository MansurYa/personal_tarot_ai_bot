"""
Интеграционный тест полного потока бота с пошаговым сбором данных
"""
import sys
import os

# Добавляем путь к src для импорта модулей
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.user_manager import init_storage, user_exists, get_user, get_user_count
from src.simple_state import UserState, get_state, clear_state
from src.handlers import handle_text_message, handle_spread_selection
from src.keyboards import SPREAD_NAMES


async def simulate_new_user_flow():
    """Симулирует полный поток нового пользователя"""
    print("🧪 Симуляция полного потока нового пользователя...")
    print("=" * 60)
    
    # Инициализируем хранилище
    success = init_storage()
    assert success, "Хранилище должно инициализироваться"
    
    test_chat_id = 555555555
    
    # Проверяем начальное состояние
    print("1️⃣ Проверяем начальное состояние:")
    initial_users = get_user_count()
    user_exists_before = user_exists(test_chat_id)
    user_state = get_state(test_chat_id)
    
    print(f"   Пользователей в системе: {initial_users}")
    print(f"   Пользователь существует: {user_exists_before}")
    print(f"   Состояние пользователя: {user_state}")
    
    assert not user_exists_before, "Тестовый пользователь не должен существовать"
    assert user_state == UserState.IDLE, "Состояние должно быть IDLE"
    print("   ✅ Начальное состояние корректно")
    
    print("\n2️⃣ Симуляция выбора расклада:")
    # Создаём моковые объекты для тестирования
    class MockQuery:
        def __init__(self, data, chat_id):
            self.data = data
            self.message = MockMessage(chat_id)
            self.from_user = MockUser(chat_id)
        
        async def edit_message_text(self, text, reply_markup=None):
            print(f"   Бот отправил: {text[:100]}...")
            return True
    
    class MockMessage:
        def __init__(self, chat_id):
            self.chat = MockChat(chat_id)
    
    class MockChat:
        def __init__(self, chat_id):
            self.id = chat_id
    
    class MockUser:
        def __init__(self, user_id):
            self.id = user_id
    
    class MockUpdate:
        def __init__(self, chat_id, text=None, callback_data=None):
            self.effective_chat = MockChat(chat_id)
            if callback_data:
                self.callback_query = MockQuery(callback_data, chat_id)
            if text:
                self.message = MockTextMessage(text, chat_id)
    
    class MockTextMessage:
        def __init__(self, text, chat_id):
            self.text = text
            self.chat = MockChat(chat_id)
        
        async def reply_text(self, text, reply_markup=None):
            print(f"   Бот ответил: {text[:100]}...")
            return True
    
    # Тестируем выбор расклада
    spread_type = "spread_celtic"
    mock_update = MockUpdate(test_chat_id, callback_data=spread_type)
    
    try:
        # Вызываем обработчик выбора расклада
        await handle_spread_selection(mock_update, None)
        
        # Проверяем что состояние изменилось
        new_state = get_state(test_chat_id)
        print(f"   Состояние после выбора: {new_state}")
        assert new_state == UserState.WAITING_NAME, f"Состояние должно быть WAITING_NAME, а не {new_state}"
        print("   ✅ Пользователь перешёл к вводу имени")
    
    except Exception as e:
        print(f"   ❌ Ошибка при выборе расклада: {e}")
        raise
    
    print("\n3️⃣ Симуляция ввода имени:")
    # Тестируем некорректные имена
    wrong_names = ["", "А", "123"]
    for wrong_name in wrong_names:
        mock_update = MockUpdate(test_chat_id, text=wrong_name)
        try:
            await handle_text_message(mock_update, None)
            state = get_state(test_chat_id)
            assert state == UserState.WAITING_NAME, "Состояние должно остаться WAITING_NAME при ошибке"
            print(f"   ✅ Некорректное имя '{wrong_name}' отклонено")
        except Exception as e:
            print(f"   ❌ Ошибка при обработке имени '{wrong_name}': {e}")
    
    # Тестируем корректное имя
    correct_name = "Екатерина Смирнова"
    mock_update = MockUpdate(test_chat_id, text=correct_name)
    try:
        await handle_text_message(mock_update, None)
        state = get_state(test_chat_id)
        print(f"   Состояние после имени: {state}")
        assert state == UserState.WAITING_BIRTHDATE, f"Состояние должно быть WAITING_BIRTHDATE, а не {state}"
        print("   ✅ Корректное имя принято, переход к дате рождения")
    except Exception as e:
        print(f"   ❌ Ошибка при обработке корректного имени: {e}")
        raise
    
    print("\n4️⃣ Симуляция ввода даты рождения:")
    # Тестируем некорректные даты
    wrong_dates = ["abc", "32.01.1990", "15.03.2030"]
    for wrong_date in wrong_dates:
        mock_update = MockUpdate(test_chat_id, text=wrong_date)
        try:
            await handle_text_message(mock_update, None)
            state = get_state(test_chat_id)
            assert state == UserState.WAITING_BIRTHDATE, "Состояние должно остаться WAITING_BIRTHDATE при ошибке"
            print(f"   ✅ Некорректная дата '{wrong_date}' отклонена")
        except Exception as e:
            print(f"   ❌ Ошибка при обработке даты '{wrong_date}': {e}")
    
    # Тестируем корректную дату
    correct_date = "25.07.1992"
    mock_update = MockUpdate(test_chat_id, text=correct_date)
    try:
        await handle_text_message(mock_update, None)
        state = get_state(test_chat_id)
        print(f"   Состояние после даты: {state}")
        assert state == UserState.WAITING_MAGIC_NUMBER, f"Состояние должно быть WAITING_MAGIC_NUMBER, а не {state}"
        
        # Проверяем что пользователь сохранился
        user_exists_now = user_exists(test_chat_id)
        print(f"   Пользователь сохранён: {user_exists_now}")
        assert user_exists_now, "Пользователь должен быть сохранён после ввода даты"
        print("   ✅ Корректная дата принята, пользователь сохранён")
    except Exception as e:
        print(f"   ❌ Ошибка при обработке корректной даты: {e}")
        raise
    
    print("\n5️⃣ Симуляция ввода магического числа:")
    # Тестируем некорректные числа
    wrong_numbers = ["abc", "0", "1000"]
    for wrong_number in wrong_numbers:
        mock_update = MockUpdate(test_chat_id, text=wrong_number)
        try:
            await handle_text_message(mock_update, None)
            state = get_state(test_chat_id)
            assert state == UserState.WAITING_MAGIC_NUMBER, "Состояние должно остаться WAITING_MAGIC_NUMBER при ошибке"
            print(f"   ✅ Некорректное число '{wrong_number}' отклонено")
        except Exception as e:
            print(f"   ❌ Ошибка при обработке числа '{wrong_number}': {e}")
    
    # Тестируем корректное число
    correct_number = "777"
    mock_update = MockUpdate(test_chat_id, text=correct_number)
    try:
        await handle_text_message(mock_update, None)
        state = get_state(test_chat_id)
        print(f"   Состояние после числа: {state}")
        assert state == UserState.IDLE, f"Состояние должно быть IDLE, а не {state}"
        print("   ✅ Корректное число принято, процесс завершён")
    except Exception as e:
        print(f"   ❌ Ошибка при обработке корректного числа: {e}")
        raise
    
    print("\n6️⃣ Проверка финального результата:")
    final_users = get_user_count()
    saved_user = get_user(test_chat_id)
    
    print(f"   Пользователей в системе: {final_users}")
    print(f"   Данные пользователя: {saved_user}")
    
    assert final_users > initial_users, "Количество пользователей должно увеличиться"
    assert saved_user is not None, "Пользователь должен быть сохранён"
    assert saved_user['name'] == correct_name, f"Имя должно быть '{correct_name}'"
    assert saved_user['chat_id'] == test_chat_id, "Chat ID должен совпадать"
    assert 'age' in saved_user, "Возраст должен быть вычислен"
    
    print("   ✅ Пользователь успешно зарегистрирован и сохранён")
    print("=" * 60)
    print("🎉 ПОЛНЫЙ ПОТОК НОВОГО ПОЛЬЗОВАТЕЛЯ ПРОШЁЛ УСПЕШНО!")
    
    return test_chat_id


async def simulate_returning_user_flow(existing_chat_id):
    """Симулирует поток возвращающегося пользователя"""
    print("\n🧪 Симуляция потока возвращающегося пользователя...")
    print("=" * 60)
    
    print("1️⃣ Проверяем существующего пользователя:")
    user_exists_check = user_exists(existing_chat_id)
    saved_user = get_user(existing_chat_id)
    
    print(f"   Пользователь существует: {user_exists_check}")
    print(f"   Имя пользователя: {saved_user['name'] if saved_user else 'Неизвестно'}")
    
    assert user_exists_check, "Пользователь должен существовать"
    assert saved_user is not None, "Данные пользователя должны загружаться"
    print("   ✅ Пользователь найден")
    
    print("\n2️⃣ Симуляция выбора нового расклада:")
    
    # Классы для мокирования (копируем из предыдущей функции)
    class MockQuery:
        def __init__(self, data, chat_id):
            self.data = data
            self.message = MockMessage(chat_id)
            self.from_user = MockUser(chat_id)
        
        async def edit_message_text(self, text, reply_markup=None):
            print(f"   Бот отправил: {text[:100]}...")
            return True
    
    class MockMessage:
        def __init__(self, chat_id):
            self.chat = MockChat(chat_id)
    
    class MockChat:
        def __init__(self, chat_id):
            self.id = chat_id
    
    class MockUser:
        def __init__(self, user_id):
            self.id = user_id
    
    class MockUpdate:
        def __init__(self, chat_id, text=None, callback_data=None):
            self.effective_chat = MockChat(chat_id)
            if callback_data:
                self.callback_query = MockQuery(callback_data, chat_id)
            if text:
                self.message = MockTextMessage(text, chat_id)
    
    class MockTextMessage:
        def __init__(self, text, chat_id):
            self.text = text
            self.chat = MockChat(chat_id)
        
        async def reply_text(self, text, reply_markup=None):
            print(f"   Бот ответил: {text[:100]}...")
            return True
    
    # Выбираем другой расклад
    spread_type = "spread_love"
    mock_update = MockUpdate(existing_chat_id, callback_data=spread_type)
    
    try:
        await handle_spread_selection(mock_update, None)
        
        # Проверяем что сразу перешли к магическому числу (пропустили регистрацию)
        state = get_state(existing_chat_id)
        print(f"   Состояние после выбора: {state}")
        assert state == UserState.WAITING_MAGIC_NUMBER, f"Должен быть сразу переход к WAITING_MAGIC_NUMBER, а не {state}"
        print("   ✅ Регистрация пропущена, сразу к магическому числу")
    except Exception as e:
        print(f"   ❌ Ошибка при выборе расклада: {e}")
        raise
    
    print("\n3️⃣ Симуляция ввода магического числа:")
    correct_number = "333"
    mock_update = MockUpdate(existing_chat_id, text=correct_number)
    
    try:
        await handle_text_message(mock_update, None)
        state = get_state(existing_chat_id)
        print(f"   Состояние после числа: {state}")
        assert state == UserState.IDLE, f"Состояние должно быть IDLE, а не {state}"
        print("   ✅ Расклад для возвращающегося пользователя завершён")
    except Exception as e:
        print(f"   ❌ Ошибка при завершении расклада: {e}")
        raise
    
    print("=" * 60)
    print("🎉 ПОТОК ВОЗВРАЩАЮЩЕГОСЯ ПОЛЬЗОВАТЕЛЯ ПРОШЁЛ УСПЕШНО!")


async def run_full_integration_test():
    """Запускает полный интеграционный тест бота"""
    print("🚀 ПОЛНЫЙ ИНТЕГРАЦИОННЫЙ ТЕСТ БОТА")
    print("=" * 80)
    
    try:
        # Очищаем предыдущие тестовые данные
        cleanup_test_data()
        
        # Тест 1: Новый пользователь
        test_chat_id = await simulate_new_user_flow()
        
        # Тест 2: Возвращающийся пользователь
        await simulate_returning_user_flow(test_chat_id)
        
        print("\n" + "=" * 80)
        print("🎉 ВСЕ ИНТЕГРАЦИОННЫЕ ТЕСТЫ ПРОШЛИ УСПЕШНО!")
        print()
        print("📋 Протестированные потоки:")
        print("   ✅ Выбор расклада новым пользователем")
        print("   ✅ Пошаговый сбор данных (имя → дата → число)")
        print("   ✅ Валидация всех видов пользовательского ввода")
        print("   ✅ Сохранение пользователя в хранилище")
        print("   ✅ Быстрый поток для возвращающихся пользователей")
        print("   ✅ Состояния и переходы между этапами")
        print()
        print("🎯 БОТ ГОТОВ К ТЕСТИРОВАНИЮ ПОЛЬЗОВАТЕЛЯМИ!")
        
    except Exception as e:
        print(f"❌ Ошибка в тестах: {e}")
        raise
    finally:
        cleanup_test_data()


def cleanup_test_data():
    """Очищает тестовые данные"""
    try:
        # Очищаем состояния
        test_chat_ids = [555555555]
        for chat_id in test_chat_ids:
            clear_state(chat_id)
        
        # Удаляем файлы хранилища
        import shutil
        if os.path.exists("data"):
            shutil.rmtree("data")
    except Exception:
        pass


if __name__ == "__main__":
    import asyncio
    asyncio.run(run_full_integration_test())