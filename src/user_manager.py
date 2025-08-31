"""
Система хранения и управления пользователями
Использует JSON файл для простого хранения данных пользователей
"""
import json
import os
import threading
from datetime import datetime
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

# Путь к папке с данными
DATA_DIR = "data"
USERS_FILE = os.path.join(DATA_DIR, "users.json")

# Блокировка для потокобезопасного доступа к файлу
_file_lock = threading.Lock()


def init_storage() -> bool:
    """
    Инициализирует хранилище пользователей
    Создаёт папку data/ и файл users.json если они не существуют
    
    :return: True если инициализация прошла успешно
    
    Примеры использования:
    >>> init_storage()
    True
    """
    try:
        # Создаём папку data/ если не существует
        if not os.path.exists(DATA_DIR):
            os.makedirs(DATA_DIR)
            logger.info(f"Создана папка для данных: {DATA_DIR}")
        
        # Создаём файл users.json если не существует
        if not os.path.exists(USERS_FILE):
            with open(USERS_FILE, 'w', encoding='utf-8') as f:
                json.dump({}, f, ensure_ascii=False, indent=2)
            logger.info(f"Создан файл пользователей: {USERS_FILE}")
        
        # Проверяем что файл читается корректно
        with open(USERS_FILE, 'r', encoding='utf-8') as f:
            json.load(f)
        
        logger.info("Хранилище пользователей инициализировано успешно")
        return True
        
    except Exception as e:
        logger.error(f"Ошибка инициализации хранилища: {e}")
        return False


def _load_users() -> Dict[str, Dict[str, Any]]:
    """
    Загружает всех пользователей из файла
    Внутренняя функция с блокировкой файла
    
    :return: Словарь пользователей {chat_id_str: user_data}
    """
    try:
        with _file_lock:
            if not os.path.exists(USERS_FILE):
                return {}
            
            with open(USERS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
                
    except (json.JSONDecodeError, FileNotFoundError) as e:
        logger.error(f"Ошибка загрузки пользователей: {e}")
        return {}
    except Exception as e:
        logger.error(f"Неожиданная ошибка при загрузке: {e}")
        return {}


def _save_users(users: Dict[str, Dict[str, Any]]) -> bool:
    """
    Сохраняет всех пользователей в файл
    Внутренняя функция с блокировкой файла
    
    :param users: Словарь пользователей для сохранения
    :return: True если сохранение прошло успешно
    """
    try:
        with _file_lock:
            # Создаём резервную копию перед записью
            if os.path.exists(USERS_FILE):
                backup_file = USERS_FILE + '.backup'
                with open(USERS_FILE, 'r', encoding='utf-8') as src, \
                     open(backup_file, 'w', encoding='utf-8') as dst:
                    dst.write(src.read())
            
            # Записываем новые данные
            with open(USERS_FILE, 'w', encoding='utf-8') as f:
                json.dump(users, f, ensure_ascii=False, indent=2)
            
            return True
            
    except Exception as e:
        logger.error(f"Ошибка сохранения пользователей: {e}")
        return False


def user_exists(user_id: int = None, chat_id: int = None) -> bool:
    """
    Проверяет существование пользователя (теперь по user_id в первую очередь)
    
    :param user_id: ID пользователя Telegram (приоритетный)
    :param chat_id: ID чата пользователя (для совместимости)
    :return: True если пользователь существует
    
    Примеры использования:
    >>> user_exists(user_id=987654)
    False
    >>> user_exists(chat_id=123456)  # Поиск по старому chat_id для совместимости
    False
    """
    users = _load_users()
    
    # Приоритет - поиск по user_id
    if user_id is not None:
        return str(user_id) in users
    
    # Совместимость - поиск по chat_id в данных пользователей
    if chat_id is not None:
        for user_data in users.values():
            if user_data.get('chat_id') == chat_id:
                return True
    
    return False


def save_user(chat_id: int, user_id: int, name: str, birthdate: str, 
               telegram_username: str = None, telegram_first_name: str = None, 
               telegram_last_name: str = None) -> bool:
    """
    Сохраняет нового пользователя (теперь по user_id для защиты от обхода через удаление чата)
    
    :param chat_id: ID чата пользователя (для совместимости)
    :param user_id: ID пользователя Telegram (основной ключ)
    :param name: Имя пользователя (введенное при регистрации)
    :param birthdate: Дата рождения в формате YYYY-MM-DD
    :param telegram_username: @username пользователя в Telegram
    :param telegram_first_name: Имя из профиля Telegram
    :param telegram_last_name: Фамилия из профиля Telegram
    :return: True если пользователь сохранён успешно
    
    Примеры использования:
    >>> save_user(123456, 987654, "Анна", "1990-03-15", "anna_user")
    True
    """
    try:
        # Проверяем инициализацию хранилища
        if not init_storage():
            logger.error("Не удалось инициализировать хранилище")
            return False
        
        users = _load_users()
        
        # Получаем начальные лимиты из конфигурации
        from src.config import load_config
        config = load_config()
        tariff_plans = config.get('tariff_plans', {})
        
        initial_credits = {
            'beginner': tariff_plans.get('beginner', {}).get('initial_credits', 3),
            'expert': tariff_plans.get('expert', {}).get('initial_credits', 1)
        }
        
        # Создаём данные пользователя (используем user_id как основной ключ)
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        user_data = {
            "chat_id": chat_id,  # Оставляем для совместимости
            "user_id": user_id,  # Основной идентификатор
            "name": name,
            "birthdate": birthdate,
            "telegram_username": telegram_username,
            "telegram_first_name": telegram_first_name,
            "telegram_last_name": telegram_last_name,
            "created_at": current_time,
            "last_spread": None,
            "credits": initial_credits.copy()  # Количество доступных раскладов по тарифам
        }
        
        users[str(user_id)] = user_data  # Сохраняем по user_id вместо chat_id
        
        if _save_users(users):
            logger.info(f"Пользователь сохранён: user_id={user_id}, name={name}, credits={initial_credits}")
            return True
        else:
            return False
            
    except Exception as e:
        logger.error(f"Ошибка сохранения пользователя {user_id}: {e}")
        return False


def get_user(user_id: int = None, chat_id: int = None) -> Optional[Dict[str, Any]]:
    """
    Возвращает данные пользователя (теперь по user_id в первую очередь)
    
    :param user_id: ID пользователя Telegram (приоритетный)
    :param chat_id: ID чата пользователя (для совместимости)
    :return: Словарь с данными пользователя или None если не найден
    
    Примеры использования:
    >>> user = get_user(user_id=987654)
    >>> if user:
    ...     print(f"Имя: {user['name']}, возраст: {user['age']}")
    """
    try:
        users = _load_users()
        user_data = None
        
        # Приоритет - поиск по user_id
        if user_id is not None:
            user_data = users.get(str(user_id))
        
        # Совместимость - поиск по chat_id в данных пользователей
        if user_data is None and chat_id is not None:
            for uid, data in users.items():
                if data.get('chat_id') == chat_id:
                    user_data = data
                    break
        
        if user_data:
            # Добавляем вычисленный возраст
            user_copy = user_data.copy()
            if 'birthdate' in user_copy:
                try:
                    from datetime import date
                    birth_date = date.fromisoformat(user_copy['birthdate'])
                    today = date.today()
                    age = today.year - birth_date.year
                    if (today.month, today.day) < (birth_date.month, birth_date.day):
                        age -= 1
                    user_copy['age'] = age
                except Exception as e:
                    logger.warning(f"Ошибка вычисления возраста для user_id={user_id}, chat_id={chat_id}: {e}")
                    user_copy['age'] = None
            
            return user_copy
        
        return None
        
    except Exception as e:
        logger.error(f"Ошибка получения пользователя user_id={user_id}, chat_id={chat_id}: {e}")
        return None


def get_user_credits(user_id: int) -> Optional[Dict[str, int]]:
    """
    Возвращает количество кредитов пользователя по тарифам
    
    :param user_id: ID пользователя Telegram
    :return: Словарь с количеством кредитов {'beginner': int, 'expert': int} или None
    """
    try:
        user_data = get_user(user_id=user_id)
        if user_data:
            return user_data.get('credits', {'beginner': 0, 'expert': 0})
        return None
    except Exception as e:
        logger.error(f"Ошибка получения кредитов пользователя {user_id}: {e}")
        return None


def use_credit(user_id: int, tariff: str) -> bool:
    """
    Списывает один кредит с указанного тарифа пользователя
    
    :param user_id: ID пользователя Telegram
    :param tariff: Тариф ('beginner' или 'expert')
    :return: True если кредит успешно списан
    """
    try:
        users = _load_users()
        user_key = str(user_id)
        
        if user_key not in users:
            logger.warning(f"Попытка списать кредит для несуществующего пользователя: {user_id}")
            return False
        
        user_data = users[user_key]
        credits = user_data.get('credits', {'beginner': 0, 'expert': 0})
        
        if tariff not in credits:
            logger.warning(f"Неизвестный тариф: {tariff}")
            return False
        
        if credits[tariff] <= 0:
            logger.warning(f"Недостаточно кредитов на тарифе {tariff} для пользователя {user_id}")
            return False
        
        # Списываем кредит
        credits[tariff] -= 1
        users[user_key]['credits'] = credits
        
        if _save_users(users):
            logger.info(f"Списан кредит с тарифа {tariff} для пользователя {user_id}. Осталось: {credits[tariff]}")
            return True
        else:
            return False
            
    except Exception as e:
        logger.error(f"Ошибка списания кредита для пользователя {user_id}: {e}")
        return False


def has_credits(user_id: int, tariff: str) -> bool:
    """
    Проверяет наличие кредитов на указанном тарифе
    
    :param user_id: ID пользователя Telegram
    :param tariff: Тариф ('beginner' или 'expert')
    :return: True если есть кредиты
    """
    credits = get_user_credits(user_id)
    if credits and tariff in credits:
        return credits[tariff] > 0
    return False


def update_last_spread(user_id: int = None, chat_id: int = None) -> bool:
    """
    Обновляет время последнего расклада пользователя (теперь по user_id в первую очередь)
    
    :param user_id: ID пользователя Telegram (приоритетный)
    :param chat_id: ID чата пользователя (для совместимости)
    :return: True если обновление прошло успешно
    
    Примеры использования:
    >>> update_last_spread(user_id=987654)
    True
    """
    try:
        users = _load_users()
        user_key = None
        
        # Приоритет - поиск по user_id
        if user_id is not None:
            user_key = str(user_id)
            if user_key not in users:
                logger.warning(f"Попытка обновить последний расклад для несуществующего user_id: {user_id}")
                return False
        
        # Совместимость - поиск по chat_id
        elif chat_id is not None:
            for uid, data in users.items():
                if data.get('chat_id') == chat_id:
                    user_key = uid
                    break
            
            if user_key is None:
                logger.warning(f"Попытка обновить последний расклад для несуществующего chat_id: {chat_id}")
                return False
        
        if user_key is None:
            logger.warning("Не указан ни user_id, ни chat_id для обновления времени расклада")
            return False
        
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        users[user_key]['last_spread'] = current_time
        
        if _save_users(users):
            logger.info(f"Обновлено время последнего расклада для пользователя {user_key}")
            return True
        else:
            return False
            
    except Exception as e:
        logger.error(f"Ошибка обновления времени расклада для user_id={user_id}, chat_id={chat_id}: {e}")
        return False


def get_user_count() -> int:
    """
    Возвращает общее количество пользователей
    
    :return: Количество зарегистрированных пользователей
    
    Примеры использования:
    >>> count = get_user_count()
    >>> print(f"Всего пользователей: {count}")
    """
    try:
        users = _load_users()
        return len(users)
    except Exception as e:
        logger.error(f"Ошибка подсчёта пользователей: {e}")
        return 0


def get_recent_users(days: int = 7) -> list:
    """
    Возвращает пользователей, активных за последние N дней
    
    :param days: Количество дней для поиска активных пользователей
    :return: Список пользователей с активностью за указанный период
    """
    try:
        from datetime import timedelta
        
        users = _load_users()
        cutoff_date = datetime.now() - timedelta(days=days)
        recent_users = []
        
        for user_data in users.values():
            if user_data.get('last_spread'):
                try:
                    last_spread = datetime.strptime(user_data['last_spread'], "%Y-%m-%d %H:%M:%S")
                    if last_spread >= cutoff_date:
                        recent_users.append(user_data)
                except ValueError:
                    continue
        
        return recent_users
        
    except Exception as e:
        logger.error(f"Ошибка получения активных пользователей: {e}")
        return []


# Функции для тестирования
def _test_user_manager():
    """
    Тестирует функциональность менеджера пользователей
    """
    print("🧪 Тестирование менеджера пользователей...")
    print("=" * 50)
    
    # Тест 1: Инициализация
    print("1️⃣ Тестируем инициализацию:")
    success = init_storage()
    print(f"   Инициализация: {'✅' if success else '❌'}")
    assert success, "Инициализация должна быть успешной"
    
    # Тест 2: Проверка несуществующего пользователя
    print("\n2️⃣ Проверяем несуществующего пользователя:")
    test_chat_id = 999999999
    exists = user_exists(test_chat_id)
    print(f"   Пользователь {test_chat_id} существует: {exists}")
    assert not exists, "Новый пользователь не должен существовать"
    print("   ✅ Проверка несуществующего пользователя прошла")
    
    # Тест 3: Создание нового пользователя
    print("\n3️⃣ Создаём нового пользователя:")
    success = save_user(test_chat_id, "Тестовый Пользователь", "1990-01-01")
    print(f"   Сохранение пользователя: {'✅' if success else '❌'}")
    assert success, "Сохранение должно быть успешным"
    
    # Проверяем что пользователь теперь существует
    exists = user_exists(test_chat_id)
    print(f"   Пользователь теперь существует: {exists}")
    assert exists, "Пользователь должен существовать после сохранения"
    print("   ✅ Создание пользователя прошло успешно")
    
    # Тест 4: Получение данных пользователя
    print("\n4️⃣ Получаем данные пользователя:")
    user_data = get_user(test_chat_id)
    print(f"   Данные пользователя: {user_data}")
    assert user_data is not None, "Данные пользователя должны существовать"
    assert user_data['name'] == "Тестовый Пользователь"
    assert user_data['birthdate'] == "1990-01-01"
    assert 'age' in user_data
    assert 'created_at' in user_data
    print("   ✅ Получение данных пользователя прошло успешно")
    
    # Тест 5: Обновление времени расклада
    print("\n5️⃣ Обновляем время последнего расклада:")
    success = update_last_spread(test_chat_id)
    print(f"   Обновление времени расклада: {'✅' if success else '❌'}")
    assert success, "Обновление должно быть успешным"
    
    # Проверяем что время обновилось
    updated_user = get_user(test_chat_id)
    print(f"   Время последнего расклада: {updated_user['last_spread']}")
    assert updated_user['last_spread'] is not None
    print("   ✅ Обновление времени расклада прошло успешно")
    
    # Тест 6: Статистика
    print("\n6️⃣ Проверяем статистику:")
    user_count = get_user_count()
    print(f"   Общее количество пользователей: {user_count}")
    assert user_count >= 1, "Должен быть хотя бы один пользователь"
    
    recent_users = get_recent_users(7)
    print(f"   Активных пользователей за 7 дней: {len(recent_users)}")
    print("   ✅ Статистика работает")
    
    # Тест 7: Множественные пользователи
    print("\n7️⃣ Тестируем множественных пользователей:")
    test_users = [
        (111111, "Анна", "1985-05-15"),
        (222222, "Пётр", "1992-10-20"),
        (333333, "Мария", "1988-03-08")
    ]
    
    for chat_id, name, birthdate in test_users:
        success = save_user(chat_id, name, birthdate)
        assert success, f"Не удалось сохранить пользователя {name}"
    
    final_count = get_user_count()
    print(f"   Финальное количество пользователей: {final_count}")
    assert final_count >= 4, "Должно быть минимум 4 пользователя"
    print("   ✅ Множественные пользователи работают")
    
    print("=" * 50)
    print("🎉 Все тесты менеджера пользователей прошли!")
    
    # Очистка тестовых данных
    print("\n🧹 Очищаем тестовые данные...")
    try:
        if os.path.exists(USERS_FILE):
            os.remove(USERS_FILE)
        if os.path.exists(DATA_DIR):
            os.rmdir(DATA_DIR)
        print("   ✅ Тестовые данные очищены")
    except Exception as e:
        print(f"   ⚠️ Не удалось полностью очистить тестовые данные: {e}")


if __name__ == "__main__":
    _test_user_manager()