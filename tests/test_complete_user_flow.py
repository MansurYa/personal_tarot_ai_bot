"""
Интеграционный тест полного потока работы с пользователями:
Валидаторы + Менеджер состояний + Менеджер пользователей
"""
import sys
import os

# Добавляем путь к src для импорта модулей
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.validators import validate_name, validate_birthdate, validate_magic_number
from src.simple_state import UserState, set_state, get_state, update_data, get_user_data, clear_state
from src.user_manager import init_storage, user_exists, save_user, get_user, update_last_spread, get_user_count


def test_complete_user_registration_flow():
    """Тестирует полный поток регистрации и сохранения пользователя"""
    print("🧪 Полный тест регистрации пользователя...")
    print("=" * 70)
    
    # Инициализируем хранилище
    success = init_storage()
    assert success, "Хранилище должно инициализироваться"
    
    test_chat_id = 123456789
    
    # Этап 1: Проверка что пользователь новый
    print("1️⃣ Проверяем нового пользователя:")
    exists_in_state = get_state(test_chat_id) != UserState.IDLE
    exists_in_storage = user_exists(test_chat_id)
    print(f"   В состоянии: {exists_in_state}")
    print(f"   В хранилище: {exists_in_storage}")
    assert not exists_in_storage, "Пользователь должен быть новым"
    print("   ✅ Пользователь новый")
    
    # Этап 2: Пользователь выбирает расклад
    print("\n2️⃣ Пользователь выбирает расклад:")
    set_state(test_chat_id, UserState.WAITING_NAME, {'spread_type': 'celtic_cross'})
    current_state = get_state(test_chat_id)
    current_data = get_user_data(test_chat_id)
    print(f"   Состояние: {current_state}")
    print(f"   Данные: {current_data}")
    assert current_state == UserState.WAITING_NAME
    assert current_data['spread_type'] == 'celtic_cross'
    print("   ✅ Состояние установлено")
    
    # Этап 3: Ввод и валидация имени
    print("\n3️⃣ Ввод и валидация имени:")
    test_names = ["", "А", "Анна123", "Александр Иванович"]
    valid_name = None
    
    for name_input in test_names:
        is_valid, result = validate_name(name_input)
        print(f"   '{name_input}' → {is_valid}")
        if is_valid:
            valid_name = result
            update_data(test_chat_id, 'name', result)
            set_state(test_chat_id, UserState.WAITING_BIRTHDATE)
            print(f"   ✅ Принято имя: {result}")
            break
    
    assert valid_name is not None, "Должно быть найдено валидное имя"
    assert get_state(test_chat_id) == UserState.WAITING_BIRTHDATE
    
    # Этап 4: Ввод и валидация даты рождения
    print("\n4️⃣ Ввод и валидация даты рождения:")
    test_dates = ["abc", "32.01.1990", "15.03.2030", "15.03.1990"]
    valid_birthdate = None
    user_age = None
    
    for date_input in test_dates:
        is_valid, result = validate_birthdate(date_input)
        if is_valid:
            print(f"   '{date_input}' → валидно, возраст {result['age']}")
            valid_birthdate = result['date']
            user_age = result['age']
            update_data(test_chat_id, 'birthdate', result['date'])
            update_data(test_chat_id, 'age', result['age'])
            set_state(test_chat_id, UserState.WAITING_MAGIC_NUMBER)
            print(f"   ✅ Принята дата: {result['date']}")
            break
        else:
            print(f"   '{date_input}' → {result}")
    
    assert valid_birthdate is not None, "Должна быть найдена валидная дата"
    assert get_state(test_chat_id) == UserState.WAITING_MAGIC_NUMBER
    
    # Этап 5: Ввод и валидация магического числа
    print("\n5️⃣ Ввод и валидация магического числа:")
    test_numbers = ["abc", "0", "1000", "777"]
    valid_number = None
    
    for number_input in test_numbers:
        is_valid, result = validate_magic_number(number_input)
        if is_valid:
            print(f"   '{number_input}' → валидно")
            valid_number = result
            update_data(test_chat_id, 'magic_number', result)
            set_state(test_chat_id, UserState.IDLE)
            print(f"   ✅ Принято число: {result}")
            break
        else:
            print(f"   '{number_input}' → {result}")
    
    assert valid_number is not None, "Должно быть найдено валидное число"
    assert get_state(test_chat_id) == UserState.IDLE
    
    # Этап 6: Сохранение пользователя в хранилище
    print("\n6️⃣ Сохранение пользователя в хранилище:")
    session_data = get_user_data(test_chat_id)
    # Используем test_chat_id как user_id для тестов (в реальности это разные параметры)
    success = save_user(test_chat_id, test_chat_id, session_data['name'], session_data['birthdate'])
    print(f"   Сохранение: {'✅' if success else '❌'}")
    assert success, "Пользователь должен сохраниться"
    
    # Проверяем что пользователь теперь в хранилище
    exists = user_exists(test_chat_id)
    print(f"   Существует в хранилище: {exists}")
    assert exists, "Пользователь должен существовать в хранилище"
    print("   ✅ Пользователь сохранён")
    
    # Этап 7: Получение сохранённых данных
    print("\n7️⃣ Проверка сохранённых данных:")
    saved_user = get_user(test_chat_id)
    print(f"   Сохранённые данные: {saved_user}")
    assert saved_user is not None
    assert saved_user['name'] == valid_name
    assert saved_user['birthdate'] == valid_birthdate
    assert saved_user['age'] == user_age
    assert saved_user['chat_id'] == test_chat_id
    assert 'created_at' in saved_user
    print("   ✅ Данные сохранены корректно")
    
    # Этап 8: Симуляция завершения расклада
    print("\n8️⃣ Симуляция завершения расклада:")
    success = update_last_spread(test_chat_id)
    print(f"   Обновление времени расклада: {'✅' if success else '❌'}")
    assert success, "Время расклада должно обновиться"
    
    # Проверяем обновлённые данные
    updated_user = get_user(test_chat_id)
    print(f"   Время последнего расклада: {updated_user['last_spread']}")
    assert updated_user['last_spread'] is not None
    print("   ✅ Расклад завершён")
    
    print("=" * 70)
    print("🎉 ПОЛНЫЙ ПОТОК РЕГИСТРАЦИИ ПРОШЁЛ УСПЕШНО!")
    
    return test_chat_id


def test_returning_user_flow():
    """Тестирует поток для возвращающегося пользователя"""
    print("\n🧪 Тест возвращающегося пользователя...")
    print("=" * 70)
    
    # Используем пользователя из предыдущего теста
    test_chat_id = 123456789
    
    # Этап 1: Проверка что пользователь существует
    print("1️⃣ Проверяем существующего пользователя:")
    exists = user_exists(test_chat_id)
    print(f"   Пользователь существует: {exists}")
    assert exists, "Пользователь должен существовать"
    
    # Получаем данные пользователя
    user_data = get_user(test_chat_id)
    print(f"   Данные пользователя: {user_data['name']}, возраст {user_data['age']}")
    print("   ✅ Пользователь найден")
    
    # Этап 2: Быстрый переход к раскладу
    print("\n2️⃣ Быстрый переход к новому раскладу:")
    # Для существующего пользователя пропускаем регистрацию
    set_state(test_chat_id, UserState.WAITING_MAGIC_NUMBER, {
        'spread_type': 'love_triangle',
        'name': user_data['name'],
        'age': user_data['age']
    })
    
    current_state = get_state(test_chat_id)
    session_data = get_user_data(test_chat_id)
    print(f"   Состояние: {current_state}")
    print(f"   Данные сессии: {session_data}")
    assert current_state == UserState.WAITING_MAGIC_NUMBER
    print("   ✅ Пропущена регистрация для существующего пользователя")
    
    # Этап 3: Завершение нового расклада
    print("\n3️⃣ Завершение нового расклада:")
    is_valid, magic_number = validate_magic_number("333")
    assert is_valid
    update_data(test_chat_id, 'magic_number', magic_number)
    set_state(test_chat_id, UserState.IDLE)
    
    # Обновляем время последнего расклада
    success = update_last_spread(test_chat_id)
    assert success
    print("   ✅ Новый расклад завершён")
    
    print("=" * 70)
    print("🎉 ПОТОК ВОЗВРАЩАЮЩЕГОСЯ ПОЛЬЗОВАТЕЛЯ ПРОШЁЛ УСПЕШНО!")


def test_multiple_users_isolation():
    """Тестирует изоляцию данных между пользователями"""
    print("\n🧪 Тест изоляции множественных пользователей...")
    print("=" * 70)
    
    # Создаём трёх пользователей одновременно
    users_data = [
        (111111, "Анна", "1990-03-15", "single"),
        (222222, "Пётр", "1985-07-20", "three_cards"),
        (333333, "Мария", "1992-12-10", "celtic_cross")
    ]
    
    # Этап 1: Установка разных состояний
    print("1️⃣ Установка состояний для разных пользователей:")
    for chat_id, name, birthdate, spread_type in users_data:
        set_state(chat_id, UserState.WAITING_NAME, {'spread_type': spread_type})
        update_data(chat_id, 'temp_name', name)  # Временно сохраняем
        print(f"   Пользователь {chat_id}: {spread_type}")
    
    # Этап 2: Проверка изоляции состояний
    print("\n2️⃣ Проверка изоляции состояний:")
    for chat_id, name, birthdate, spread_type in users_data:
        state = get_state(chat_id)
        data = get_user_data(chat_id)
        print(f"   {chat_id}: состояние={state}, spread={data['spread_type']}")
        assert state == UserState.WAITING_NAME
        assert data['spread_type'] == spread_type
    print("   ✅ Изоляция состояний работает")
    
    # Этап 3: Сохранение всех пользователей
    print("\n3️⃣ Сохранение всех пользователей:")
    for chat_id, name, birthdate, spread_type in users_data:
        success = save_user(chat_id, chat_id, name, birthdate)  # chat_id используется как user_id для тестов
        assert success, f"Не удалось сохранить пользователя {name}"
        print(f"   Сохранён: {name}")
    
    # Этап 4: Проверка что все сохранились независимо
    print("\n4️⃣ Проверка независимого сохранения:")
    total_users = get_user_count()
    print(f"   Общее количество пользователей: {total_users}")
    assert total_users >= len(users_data), f"Должно быть минимум {len(users_data)} пользователей"
    
    # Проверяем каждого пользователя отдельно
    for chat_id, name, birthdate, spread_type in users_data:
        user = get_user(chat_id)
        assert user is not None, f"Пользователь {name} должен существовать"
        assert user['name'] == name
        assert user['birthdate'] == birthdate
        print(f"   Проверен: {name} (возраст {user['age']})")
    
    print("   ✅ Все пользователи сохранены и изолированы")
    
    print("=" * 70)
    print("🎉 ИЗОЛЯЦИЯ МНОЖЕСТВЕННЫХ ПОЛЬЗОВАТЕЛЕЙ РАБОТАЕТ!")


def cleanup_test_data():
    """Очищает тестовые данные"""
    print("\n🧹 Очистка тестовых данных...")
    try:
        # Очищаем состояния
        test_chat_ids = [123456789, 111111, 222222, 333333]
        for chat_id in test_chat_ids:
            clear_state(chat_id)
        
        # Удаляем файлы хранилища
        import shutil
        if os.path.exists("data"):
            shutil.rmtree("data")
        
        print("   ✅ Тестовые данные очищены")
    except Exception as e:
        print(f"   ⚠️ Частичная очистка: {e}")


def run_complete_tests():
    """Запускает все интеграционные тесты"""
    print("🚀 КОМПЛЕКСНОЕ ТЕСТИРОВАНИЕ СИСТЕМЫ ПОЛЬЗОВАТЕЛЕЙ")
    print("=" * 80)
    
    try:
        # Основные тесты
        test_chat_id = test_complete_user_registration_flow()
        test_returning_user_flow()
        test_multiple_users_isolation()
        
        print("\n" + "=" * 80)
        print("🎉 ВСЕ ИНТЕГРАЦИОННЫЕ ТЕСТЫ ПРОШЛИ УСПЕШНО!")
        print()
        print("📋 Протестированные компоненты:")
        print("   ✅ Валидация пользовательского ввода")
        print("   ✅ Управление состояниями разговора")
        print("   ✅ Сохранение и загрузка пользователей")
        print("   ✅ Изоляция данных между пользователями")
        print("   ✅ Полный поток регистрации")
        print("   ✅ Поток для возвращающихся пользователей")
        print("   ✅ Обновление времени раскладов")
        print()
        print("🎯 СИСТЕМА ГОТОВА ДЛЯ ИНТЕГРАЦИИ В TELEGRAM BOT!")
        
    except Exception as e:
        print(f"❌ Ошибка в тестах: {e}")
        raise
    finally:
        cleanup_test_data()


if __name__ == "__main__":
    run_complete_tests()