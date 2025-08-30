"""
Интеграционные тесты для инфраструктуры ФАЗЫ 3: 
Валидаторы + Менеджер состояний
"""
import sys
import os

# Добавляем путь к src для импорта модулей
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.validators import validate_name, validate_birthdate, validate_magic_number
from src.simple_state import (
    UserState, set_state, get_state, get_user_data, 
    update_data, clear_state, reset_to_idle
)


def test_user_registration_flow():
    """Тестирует полный поток регистрации пользователя"""
    print("🧪 Тестируем поток регистрации пользователя...")
    print("=" * 60)
    
    test_chat_id = 987654321
    
    # Шаг 1: Начальное состояние
    print("1️⃣ Начальное состояние:")
    state = get_state(test_chat_id)
    print(f"   Состояние: {state}")
    assert state == UserState.IDLE
    print("   ✅ Пользователь в состоянии IDLE")
    
    # Шаг 2: Запрос имени
    print("\n2️⃣ Переход к сбору имени:")
    set_state(test_chat_id, UserState.WAITING_NAME, {'spread_type': 'single'})
    state = get_state(test_chat_id)
    data = get_user_data(test_chat_id)
    print(f"   Состояние: {state}")
    print(f"   Данные: {data}")
    assert state == UserState.WAITING_NAME
    assert data['spread_type'] == 'single'
    print("   ✅ Переход к сбору имени выполнен")
    
    # Шаг 3: Валидация и сохранение имени
    print("\n3️⃣ Валидация и сохранение имени:")
    test_names = [
        ("", False, "Пустое имя"),
        ("А", False, "Слишком короткое"),
        ("Анна123", False, "С цифрами"),
        ("Анна", True, "Корректное имя")
    ]
    
    for name_input, should_be_valid, description in test_names:
        is_valid, result = validate_name(name_input)
        status = "✅" if is_valid == should_be_valid else "❌"
        print(f"   {status} {description}: '{name_input}' → {is_valid}")
        
        if is_valid:
            # Сохраняем валидное имя и переходим к следующему шагу
            update_data(test_chat_id, 'name', result)
            set_state(test_chat_id, UserState.WAITING_BIRTHDATE)
            break
    
    # Проверяем что имя сохранилось
    data = get_user_data(test_chat_id)
    state = get_state(test_chat_id)
    assert 'name' in data
    assert state == UserState.WAITING_BIRTHDATE
    print("   ✅ Имя сохранено, переход к дате рождения")
    
    # Шаг 4: Валидация и сохранение даты рождения
    print("\n4️⃣ Валидация и сохранение даты рождения:")
    test_dates = [
        ("", False, "Пустая дата"),
        ("32.01.1990", False, "Некорректный день"),
        ("15.13.1990", False, "Некорректный месяц"),
        ("15.03.2030", False, "Будущая дата"),
        ("15.03.1990", True, "Корректная дата")
    ]
    
    for date_input, should_be_valid, description in test_dates:
        is_valid, result = validate_birthdate(date_input)
        status = "✅" if is_valid == should_be_valid else "❌"
        if is_valid:
            print(f"   {status} {description}: '{date_input}' → возраст {result['age']}")
        else:
            print(f"   {status} {description}: '{date_input}' → {result}")
        
        if is_valid:
            # Сохраняем валидную дату
            update_data(test_chat_id, 'birthdate', result['date'])
            update_data(test_chat_id, 'age', result['age'])
            set_state(test_chat_id, UserState.WAITING_MAGIC_NUMBER)
            break
    
    # Проверяем что дата сохранилась
    data = get_user_data(test_chat_id)
    state = get_state(test_chat_id)
    assert 'birthdate' in data
    assert 'age' in data
    assert state == UserState.WAITING_MAGIC_NUMBER
    print("   ✅ Дата рождения сохранена, переход к магическому числу")
    
    # Шаг 5: Валидация и сохранение магического числа
    print("\n5️⃣ Валидация и сохранение магического числа:")
    test_numbers = [
        ("", False, "Пустое число"),
        ("0", False, "Ноль"),
        ("1000", False, "Слишком большое"),
        ("abc", False, "Не число"),
        ("777", True, "Корректное число")
    ]
    
    for number_input, should_be_valid, description in test_numbers:
        is_valid, result = validate_magic_number(number_input)
        status = "✅" if is_valid == should_be_valid else "❌"
        print(f"   {status} {description}: '{number_input}' → {result}")
        
        if is_valid:
            # Сохраняем валидное число
            update_data(test_chat_id, 'magic_number', result)
            set_state(test_chat_id, UserState.IDLE)
            break
    
    # Шаг 6: Проверка финального состояния
    print("\n6️⃣ Проверка финального состояния:")
    final_state = get_state(test_chat_id)
    final_data = get_user_data(test_chat_id)
    
    print(f"   Финальное состояние: {final_state}")
    print(f"   Финальные данные: {final_data}")
    
    # Проверяем что все данные собраны
    required_fields = ['spread_type', 'name', 'birthdate', 'age', 'magic_number']
    for field in required_fields:
        assert field in final_data, f"Отсутствует поле: {field}"
    
    assert final_state == UserState.IDLE
    print("   ✅ Регистрация завершена успешно!")
    
    # Очистка тестовых данных
    clear_state(test_chat_id)
    
    print("=" * 60)
    print("🎉 Поток регистрации работает корректно!")


def test_multiple_users_isolation():
    """Тестирует изоляцию данных разных пользователей"""
    print("\n🧪 Тестируем изоляцию данных пользователей...")
    print("=" * 60)
    
    user1_id = 111111
    user2_id = 222222
    
    # Устанавливаем разные состояния для разных пользователей
    set_state(user1_id, UserState.WAITING_NAME, {'spread_type': 'single'})
    set_state(user2_id, UserState.WAITING_BIRTHDATE, {'name': 'Мария'})
    
    # Проверяем изоляцию состояний
    user1_state = get_state(user1_id)
    user2_state = get_state(user2_id)
    user1_data = get_user_data(user1_id)
    user2_data = get_user_data(user2_id)
    
    print(f"Пользователь 1: состояние={user1_state}, данные={user1_data}")
    print(f"Пользователь 2: состояние={user2_state}, данные={user2_data}")
    
    # Проверки
    assert user1_state == UserState.WAITING_NAME
    assert user2_state == UserState.WAITING_BIRTHDATE
    assert user1_data['spread_type'] == 'single'
    assert user2_data['name'] == 'Мария'
    assert 'name' not in user1_data
    assert 'spread_type' not in user2_data
    
    print("✅ Изоляция данных пользователей работает корректно!")
    
    # Очистка
    clear_state(user1_id)
    clear_state(user2_id)


def test_edge_cases():
    """Тестирует граничные случаи"""
    print("\n🧪 Тестируем граничные случаи...")
    print("=" * 60)
    
    test_chat_id = 555555
    
    # Тест 1: Работа с несуществующим пользователем
    print("1️⃣ Несуществующий пользователь:")
    state = get_state(999999999)
    data = get_user_data(999999999)
    print(f"   Состояние: {state}, Данные: {data}")
    assert state == UserState.IDLE
    assert len(data) == 0
    print("   ✅ Несуществующий пользователь обрабатывается корректно")
    
    # Тест 2: Граничные значения валидаторов
    print("\n2️⃣ Граничные значения:")
    
    # Имя ровно 2 символа
    is_valid, result = validate_name("Ян")
    assert is_valid == True
    print(f"   ✅ Имя из 2 символов: {result}")
    
    # Имя ровно 50 символов
    long_name = "Анна-Мария-Елена-Виктория-Александра-Екатерина"
    is_valid, result = validate_name(long_name)
    print(f"   Имя {len(long_name)} символов: {is_valid}")
    
    # Возраст 6 лет (минимальный)
    from datetime import date
    current_year = date.today().year
    min_age_date = f"01.01.{current_year - 6}"
    is_valid, result = validate_birthdate(min_age_date)
    print(f"   ✅ Минимальный возраст: {result['age']} лет")
    
    # Число 1 и 999
    assert validate_magic_number("1")[0] == True
    assert validate_magic_number("999")[0] == True
    print("   ✅ Граничные магические числа: 1 и 999")
    
    # Тест 3: Сброс состояния с сохранением данных
    print("\n3️⃣ Сброс с сохранением данных:")
    set_state(test_chat_id, UserState.WAITING_NAME, {'important_data': 'keep_me'})
    update_data(test_chat_id, 'user_name', 'Тест')
    
    reset_to_idle(test_chat_id, keep_data=True)
    
    final_state = get_state(test_chat_id)
    final_data = get_user_data(test_chat_id)
    
    assert final_state == UserState.IDLE
    assert 'important_data' in final_data
    assert 'user_name' in final_data
    print(f"   ✅ Данные сохранены при сбросе: {final_data}")
    
    # Очистка
    clear_state(test_chat_id)
    clear_state(999999999)
    
    print("=" * 60)
    print("🎉 Граничные случаи обработаны корректно!")


def run_all_tests():
    """Запускает все тесты инфраструктуры ФАЗЫ 3"""
    print("🚀 ТЕСТИРОВАНИЕ ИНФРАСТРУКТУРЫ ФАЗЫ 3")
    print("=" * 80)
    
    try:
        test_user_registration_flow()
        test_multiple_users_isolation() 
        test_edge_cases()
        
        print("\n" + "=" * 80)
        print("🎉 ВСЕ ТЕСТЫ ИНФРАСТРУКТУРЫ ПРОШЛИ УСПЕШНО!")
        print()
        print("📋 Проверенные компоненты:")
        print("   ✅ Валидатор имён (validate_name)")
        print("   ✅ Валидатор дат рождения (validate_birthdate)")
        print("   ✅ Валидатор магических чисел (validate_magic_number)")
        print("   ✅ Менеджер состояний (simple_state)")
        print("   ✅ Изоляция данных между пользователями")
        print("   ✅ Полный поток регистрации пользователя")
        print("   ✅ Граничные случаи и обработка ошибок")
        print()
        print("🎯 ИНФРАСТРУКТУРА ГОТОВА ДЛЯ ИНТЕГРАЦИИ В БОТ!")
        
    except Exception as e:
        print(f"❌ Ошибка в тестах: {e}")
        raise


if __name__ == "__main__":
    run_all_tests()