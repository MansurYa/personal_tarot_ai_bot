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


def user_exists(chat_id: int) -> bool:
    """
    Проверяет существование пользователя
    
    :param chat_id: ID чата пользователя
    :return: True если пользователь существует
    
    Примеры использования:
    >>> user_exists(123456)
    False
    >>> save_user(123456, "Анна", "1990-03-15")
    >>> user_exists(123456)
    True
    """
    users = _load_users()
    return str(chat_id) in users


def save_user(chat_id: int, name: str, birthdate: str) -> bool:
    """
    Сохраняет нового пользователя
    
    :param chat_id: ID чата пользователя
    :param name: Имя пользователя
    :param birthdate: Дата рождения в формате YYYY-MM-DD
    :return: True если пользователь сохранён успешно
    
    Примеры использования:
    >>> save_user(123456, "Анна", "1990-03-15")
    True
    >>> save_user(654321, "Александр", "1985-12-25")
    True
    """
    try:
        # Проверяем инициализацию хранилища
        if not init_storage():
            logger.error("Не удалось инициализировать хранилище")
            return False
        
        users = _load_users()
        
        # Создаём данные пользователя
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        user_data = {
            "chat_id": chat_id,
            "name": name,
            "birthdate": birthdate,
            "created_at": current_time,
            "last_spread": None  # Будет установлено при первом раскладе
        }
        
        users[str(chat_id)] = user_data
        
        if _save_users(users):
            logger.info(f"Пользователь сохранён: chat_id={chat_id}, name={name}")
            return True
        else:
            return False
            
    except Exception as e:
        logger.error(f"Ошибка сохранения пользователя {chat_id}: {e}")
        return False


def get_user(chat_id: int) -> Optional[Dict[str, Any]]:
    """
    Возвращает данные пользователя
    
    :param chat_id: ID чата пользователя
    :return: Словарь с данными пользователя или None если не найден
    
    Примеры использования:
    >>> user = get_user(123456)
    >>> if user:
    ...     print(f"Имя: {user['name']}, возраст: {user['age']}")
    >>> get_user(999999)  # Несуществующий пользователь
    None
    """
    try:
        users = _load_users()
        user_data = users.get(str(chat_id))
        
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
                    logger.warning(f"Ошибка вычисления возраста для {chat_id}: {e}")
                    user_copy['age'] = None
            
            return user_copy
        
        return None
        
    except Exception as e:
        logger.error(f"Ошибка получения пользователя {chat_id}: {e}")
        return None


def update_last_spread(chat_id: int) -> bool:
    """
    Обновляет время последнего расклада пользователя
    
    :param chat_id: ID чата пользователя
    :return: True если обновление прошло успешно
    
    Примеры использования:
    >>> update_last_spread(123456)
    True
    """
    try:
        users = _load_users()
        
        if str(chat_id) not in users:
            logger.warning(f"Попытка обновить последний расклад для несуществующего пользователя: {chat_id}")
            return False
        
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        users[str(chat_id)]['last_spread'] = current_time
        
        if _save_users(users):
            logger.info(f"Обновлено время последнего расклада для пользователя {chat_id}")
            return True
        else:
            return False
            
    except Exception as e:
        logger.error(f"Ошибка обновления времени расклада для {chat_id}: {e}")
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