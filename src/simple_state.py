"""
Простой менеджер состояний для телеграм-бота в памяти
Хранит состояния пользователей и их данные между сообщениями
"""
from typing import Dict, Any, Optional
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# Возможные состояния пользователя
class UserState:
    """Константы состояний пользователя"""
    IDLE = "IDLE"                           # Пользователь в главном меню
    WAITING_NAME = "WAITING_NAME"           # Ожидаем ввод имени
    WAITING_BIRTHDATE = "WAITING_BIRTHDATE" # Ожидаем ввод даты рождения
    WAITING_MAGIC_NUMBER = "WAITING_MAGIC_NUMBER"  # Ожидаем магическое число
    WAITING_PRELIMINARY_ANSWERS = "WAITING_PRELIMINARY_ANSWERS"  # Ожидаем ответы на предварительные вопросы
    WAITING_LLM_QUESTIONS = "WAITING_LLM_QUESTIONS"  # Ожидаем ответы на LLM вопросы
    PROCESSING_INTERPRETATION = "PROCESSING_INTERPRETATION"  # Генерируем интерпретацию
    WAITING_FEEDBACK = "WAITING_FEEDBACK"   # Ожидаем обратную связь
    WAITING_COMMENT = "WAITING_COMMENT"     # Ожидаем текстовый комментарий

# Глобальный словарь для хранения состояний пользователей
# Структура: {chat_id: {'state': str, 'data': dict, 'timestamp': datetime}}
_user_states: Dict[int, Dict[str, Any]] = {}


def set_state(chat_id: int, state: str, data: Optional[Dict[str, Any]] = None) -> None:
    """
    Устанавливает состояние пользователя
    
    :param chat_id: ID чата пользователя
    :param state: Новое состояние (из класса UserState)
    :param data: Дополнительные данные для сохранения (опционально)
    
    Примеры использования:
    >>> set_state(123456, UserState.WAITING_NAME)
    >>> set_state(123456, UserState.WAITING_BIRTHDATE, {'name': 'Анна'})
    >>> set_state(123456, UserState.IDLE, {'spread_type': 'celtic_cross'})
    """
    if chat_id not in _user_states:
        _user_states[chat_id] = {'state': UserState.IDLE, 'data': {}}
    
    _user_states[chat_id]['state'] = state
    
    if data:
        _user_states[chat_id]['data'].update(data)
    
    # Добавляем timestamp для отладки
    _user_states[chat_id]['timestamp'] = datetime.now()
    
    logger.info(f"Пользователь {chat_id}: состояние изменено на {state}")


def get_state(chat_id: int) -> str:
    """
    Получает текущее состояние пользователя
    
    :param chat_id: ID чата пользователя
    :return: Текущее состояние (по умолчанию IDLE)
    
    Примеры использования:
    >>> get_state(123456)
    'WAITING_NAME'
    >>> get_state(999999)  # Новый пользователь
    'IDLE'
    """
    if chat_id not in _user_states:
        # Создаём новую запись для пользователя
        _user_states[chat_id] = {
            'state': UserState.IDLE,
            'data': {},
            'timestamp': datetime.now()
        }
    
    return _user_states[chat_id]['state']


def get_user_data(chat_id: int) -> Dict[str, Any]:
    """
    Получает все данные пользователя
    
    :param chat_id: ID чата пользователя
    :return: Словарь с данными пользователя
    
    Примеры использования:
    >>> get_user_data(123456)
    {'name': 'Анна', 'birthdate': '1990-03-15', 'age': 34}
    >>> get_user_data(999999)  # Новый пользователь
    {}
    """
    if chat_id not in _user_states:
        _user_states[chat_id] = {
            'state': UserState.IDLE,
            'data': {},
            'timestamp': datetime.now()
        }
    
    return _user_states[chat_id]['data'].copy()


def update_data(chat_id: int, key: str, value: Any) -> None:
    """
    Обновляет конкретный ключ в данных пользователя
    
    :param chat_id: ID чата пользователя
    :param key: Ключ для обновления
    :param value: Новое значение
    
    Примеры использования:
    >>> update_data(123456, 'name', 'Анна')
    >>> update_data(123456, 'birthdate', '1990-03-15')
    >>> update_data(123456, 'spread_type', 'celtic_cross')
    >>> update_data(123456, 'magic_number', 777)
    """
    if chat_id not in _user_states:
        _user_states[chat_id] = {
            'state': UserState.IDLE,
            'data': {},
            'timestamp': datetime.now()
        }
    
    _user_states[chat_id]['data'][key] = value
    
    # Обновляем timestamp
    _user_states[chat_id]['timestamp'] = datetime.now()
    
    logger.info(f"Пользователь {chat_id}: обновлены данные {key} = {value}")


def clear_state(chat_id: int) -> None:
    """
    Очищает состояние и данные пользователя
    
    :param chat_id: ID чата пользователя
    
    Примеры использования:
    >>> clear_state(123456)  # Полная очистка
    """
    if chat_id in _user_states:
        del _user_states[chat_id]
        logger.info(f"Пользователь {chat_id}: состояние очищено")


def reset_to_idle(chat_id: int, keep_data: bool = False) -> None:
    """
    Сбрасывает состояние пользователя в IDLE
    
    :param chat_id: ID чата пользователя
    :param keep_data: Если True, сохраняет данные пользователя
    
    Примеры использования:
    >>> reset_to_idle(123456)  # Сброс с очисткой данных
    >>> reset_to_idle(123456, keep_data=True)  # Сброс с сохранением данных
    """
    if keep_data:
        data = get_user_data(chat_id)
        set_state(chat_id, UserState.IDLE, data)
    else:
        set_state(chat_id, UserState.IDLE, {})


def get_all_states() -> Dict[int, Dict[str, Any]]:
    """
    Получает все состояния (для отладки)
    
    :return: Словарь всех состояний пользователей
    
    Используется для отладки и мониторинга:
    >>> states = get_all_states()
    >>> print(f"Активных пользователей: {len(states)}")
    """
    return _user_states.copy()


def cleanup_old_states(max_age_hours: int = 24) -> int:
    """
    Очищает старые неактивные состояния
    
    :param max_age_hours: Максимальный возраст состояния в часах
    :return: Количество удалённых состояний
    
    Рекомендуется запускать периодически для экономии памяти:
    >>> cleanup_old_states(24)  # Удалить состояния старше 24 часов
    3
    """
    cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
    old_chat_ids = []
    
    for chat_id, state_data in _user_states.items():
        if 'timestamp' in state_data and state_data['timestamp'] < cutoff_time:
            old_chat_ids.append(chat_id)
    
    for chat_id in old_chat_ids:
        del _user_states[chat_id]
    
    if old_chat_ids:
        logger.info(f"Очищено {len(old_chat_ids)} старых состояний")
    
    return len(old_chat_ids)


# Служебные функции для тестирования
def _test_state_manager():
    """
    Тестирует функциональность менеджера состояний
    """
    print("🧪 Тестирование менеджера состояний...")
    print("=" * 50)
    
    test_chat_id = 123456
    
    # Тест 1: Начальное состояние
    print("1️⃣ Тестируем начальное состояние:")
    state = get_state(test_chat_id)
    print(f"   Начальное состояние: {state}")
    assert state == UserState.IDLE, f"Ожидали IDLE, получили {state}"
    print("   ✅ Начальное состояние корректно")
    
    # Тест 2: Установка состояния
    print("\n2️⃣ Тестируем установку состояния:")
    set_state(test_chat_id, UserState.WAITING_NAME)
    state = get_state(test_chat_id)
    print(f"   Состояние после установки: {state}")
    assert state == UserState.WAITING_NAME
    print("   ✅ Установка состояния работает")
    
    # Тест 3: Обновление данных
    print("\n3️⃣ Тестируем обновление данных:")
    update_data(test_chat_id, 'name', 'Анна')
    update_data(test_chat_id, 'age', 25)
    data = get_user_data(test_chat_id)
    print(f"   Данные пользователя: {data}")
    assert data['name'] == 'Анна'
    assert data['age'] == 25
    print("   ✅ Обновление данных работает")
    
    # Тест 4: Установка состояния с данными
    print("\n4️⃣ Тестируем установку состояния с данными:")
    set_state(test_chat_id, UserState.WAITING_BIRTHDATE, {'spread_type': 'celtic'})
    state = get_state(test_chat_id)
    data = get_user_data(test_chat_id)
    print(f"   Состояние: {state}")
    print(f"   Данные: {data}")
    assert state == UserState.WAITING_BIRTHDATE
    assert 'spread_type' in data
    assert 'name' in data  # Старые данные сохранились
    print("   ✅ Установка с данными работает")
    
    # Тест 5: Сброс в IDLE с сохранением данных
    print("\n5️⃣ Тестируем сброс в IDLE:")
    reset_to_idle(test_chat_id, keep_data=True)
    state = get_state(test_chat_id)
    data = get_user_data(test_chat_id)
    print(f"   Состояние после сброса: {state}")
    print(f"   Данные после сброса: {data}")
    assert state == UserState.IDLE
    assert len(data) > 0  # Данные сохранились
    print("   ✅ Сброс с сохранением данных работает")
    
    # Тест 6: Полная очистка
    print("\n6️⃣ Тестируем полную очистку:")
    clear_state(test_chat_id)
    state = get_state(test_chat_id)  # Должно создать новую запись
    data = get_user_data(test_chat_id)
    print(f"   Состояние после очистки: {state}")
    print(f"   Данные после очистки: {data}")
    assert state == UserState.IDLE
    assert len(data) == 0
    print("   ✅ Полная очистка работает")
    
    # Тест 7: Множественные пользователи
    print("\n7️⃣ Тестируем множественных пользователей:")
    set_state(111111, UserState.WAITING_NAME, {'test': 'user1'})
    set_state(222222, UserState.WAITING_BIRTHDATE, {'test': 'user2'})
    
    all_states = get_all_states()
    print(f"   Всего состояний: {len(all_states)}")
    assert len(all_states) >= 2
    print("   ✅ Множественные пользователи работают")
    
    print("=" * 50)
    print("🎉 Все тесты пройдены!")
    
    # Очистка тестовых данных
    clear_state(test_chat_id)
    clear_state(111111)
    clear_state(222222)


if __name__ == "__main__":
    _test_state_manager()
