"""
Валидаторы для проверки пользовательского ввода
"""
import re
from datetime import datetime, date
from typing import Tuple, Union, Dict, Any


def validate_name(text: str) -> Tuple[bool, Union[str, str]]:
    """
    Проверяет корректность имени пользователя
    
    Правила валидации:
    - Не пустое
    - От 2 до 50 символов
    - Только буквы (любые языки), пробелы, дефисы
    - Убирает лишние пробелы
    
    :param text: Введённое имя
    :return: (True, очищенное_имя) или (False, сообщение_ошибки)
    
    Примеры использования:
    >>> validate_name("Анна")
    (True, "Анна")
    >>> validate_name("  Мария-Елена  ")
    (True, "Мария-Елена")
    >>> validate_name("John Smith")
    (True, "John Smith")
    >>> validate_name("")
    (False, "Имя не может быть пустым")
    >>> validate_name("123")
    (False, "Имя должно содержать только буквы, пробелы и дефисы")
    """
    if not text or not text.strip():
        return False, "Имя не может быть пустым"
    
    # Убираем лишние пробелы
    cleaned_name = text.strip()
    
    # Проверяем длину
    if len(cleaned_name) < 2:
        return False, "Имя должно содержать минимум 2 символа"
    
    if len(cleaned_name) > 50:
        return False, "Имя не должно быть длиннее 50 символов"
    
    # Проверяем допустимые символы: буквы любых языков, пробелы, дефисы
    # Используем простую проверку на буквы, пробелы и дефисы
    pattern = r'^[a-zA-Zа-яА-ЯёЁ\s\-]+$'
    if not re.match(pattern, cleaned_name):
        return False, "Имя должно содержать только буквы, пробелы и дефисы"
    
    # Проверяем что есть хотя бы одна буква
    if not re.search(r'[a-zA-Zа-яА-ЯёЁ]', cleaned_name):
        return False, "Имя должно содержать хотя бы одну букву"
    
    return True, cleaned_name


def validate_birthdate(text: str) -> Tuple[bool, Union[Dict[str, Any], str]]:
    """
    Проверяет корректность даты рождения
    
    Правила валидации:
    - Формат ДД.ММ.ГГГГ (например: 15.03.1990)
    - Дата должна быть в прошлом
    - Возраст от 6 до 120 лет
    
    :param text: Введённая дата
    :return: (True, {'date': 'YYYY-MM-DD', 'age': int}) или (False, сообщение_ошибки)
    
    Примеры использования:
    >>> validate_birthdate("15.03.1990")
    (True, {'date': '1990-03-15', 'age': 34})
    >>> validate_birthdate("29.02.2000")
    (True, {'date': '2000-02-29', 'age': 24})
    >>> validate_birthdate("32.01.1990")
    (False, "Некорректная дата. Проверьте день и месяц")
    >>> validate_birthdate("15.03.2030")
    (False, "Дата рождения не может быть в будущем")
    """
    if not text or not text.strip():
        return False, "Дата рождения не может быть пустой"
    
    text = text.strip()
    
    # Проверяем формат ДД.ММ.ГГГГ
    pattern = r'^(\d{1,2})\.(\d{1,2})\.(\d{4})$'
    match = re.match(pattern, text)
    
    if not match:
        return False, "Неверный формат даты. Используйте ДД.ММ.ГГГГ (например: 15.03.1990)"
    
    day, month, year = map(int, match.groups())
    
    # Проверяем что это валидная дата
    try:
        birth_date = date(year, month, day)
    except ValueError:
        return False, "Некорректная дата. Проверьте день и месяц"
    
    # Проверяем что дата в прошлом
    today = date.today()
    if birth_date >= today:
        return False, "Дата рождения не может быть в будущем"
    
    # Вычисляем возраст
    age = today.year - birth_date.year
    if (today.month, today.day) < (birth_date.month, birth_date.day):
        age -= 1
    
    # Проверяем разумные границы возраста
    if age < 6:
        return False, "Минимальный возраст для использования бота: 6 лет"
    
    if age > 120:
        return False, "Максимальный возраст: 120 лет. Проверьте правильность даты"
    
    # Возвращаем дату в формате ISO и возраст
    result = {
        'date': birth_date.isoformat(),  # 'YYYY-MM-DD'
        'age': age
    }
    
    return True, result


def validate_magic_number(text: str) -> Tuple[bool, Union[int, str]]:
    """
    Проверяет корректность магического числа
    
    Правила валидации:
    - Целое число от 1 до 999
    - Убирает лишние пробелы
    
    :param text: Введённое число
    :return: (True, число) или (False, сообщение_ошибки)
    
    Примеры использования:
    >>> validate_magic_number("777")
    (True, 777)
    >>> validate_magic_number("  42  ")
    (True, 42)
    >>> validate_magic_number("1")
    (True, 1)
    >>> validate_magic_number("999")
    (True, 999)
    >>> validate_magic_number("0")
    (False, "Число должно быть от 1 до 999")
    >>> validate_magic_number("1000")
    (False, "Число должно быть от 1 до 999")
    >>> validate_magic_number("abc")
    (False, "Введите целое число")
    """
    if not text or not text.strip():
        return False, "Магическое число не может быть пустым"
    
    text = text.strip()
    
    # Проверяем что это число
    if not text.isdigit():
        return False, "Введите целое число"
    
    try:
        number = int(text)
    except ValueError:
        return False, "Введите целое число"
    
    # Проверяем диапазон
    if number < 1:
        return False, "Число должно быть от 1 до 999"
    
    if number > 999:
        return False, "Число должно быть от 1 до 999"
    
    return True, number


# Вспомогательные функции для тестирования
def test_validators():
    """
    Тестирует все валидаторы с различными входными данными
    """
    print("🧪 Тестирование валидаторов...")
    print("=" * 50)
    
    # Тесты validate_name
    print("1️⃣ Тестируем validate_name:")
    name_tests = [
        ("Анна", True),
        ("Мария-Елена", True),
        ("John Smith", True),
        ("  Александр  ", True),
        ("", False),
        ("А", False),
        ("123", False),
        ("Очень длинное имя которое превышает лимит в пятьдесят символов", False),
        ("---", False)
    ]
    
    for test_input, expected_valid in name_tests:
        is_valid, result = validate_name(test_input)
        status = "✅" if is_valid == expected_valid else "❌"
        print(f"   {status} '{test_input}' → {is_valid}, {result}")
    
    print()
    
    # Тесты validate_birthdate
    print("2️⃣ Тестируем validate_birthdate:")
    date_tests = [
        ("15.03.1990", True),
        ("01.01.2000", True),
        ("29.02.2000", True),  # Високосный год
        ("", False),
        ("32.01.1990", False),  # Неверный день
        ("15.13.1990", False),  # Неверный месяц
        ("15.03.2030", False),  # Будущее
        ("15.03.1900", False),  # Слишком старый
        ("abc", False),
        ("15-03-1990", False)   # Неверный формат
    ]
    
    for test_input, expected_valid in date_tests:
        is_valid, result = validate_birthdate(test_input)
        status = "✅" if is_valid == expected_valid else "❌"
        print(f"   {status} '{test_input}' → {is_valid}, {result}")
    
    print()
    
    # Тесты validate_magic_number
    print("3️⃣ Тестируем validate_magic_number:")
    number_tests = [
        ("777", True),
        ("1", True),
        ("999", True),
        ("  42  ", True),
        ("0", False),
        ("1000", False),
        ("", False),
        ("abc", False),
        ("-5", False),
        ("7.5", False)
    ]
    
    for test_input, expected_valid in number_tests:
        is_valid, result = validate_magic_number(test_input)
        status = "✅" if is_valid == expected_valid else "❌"
        print(f"   {status} '{test_input}' → {is_valid}, {result}")
    
    print("=" * 50)
    print("🎉 Тестирование завершено!")


if __name__ == "__main__":
    test_validators()