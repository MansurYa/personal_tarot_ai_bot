"""
Загрузка и управление конфигурацией проекта
"""
import json
import os


def load_config():
    """
    Загружает конфигурацию из файла config.json
    
    :return: Словарь с настройками проекта
    :raises FileNotFoundError: Если файл config.json не найден
    :raises ValueError: Если файл содержит некорректный JSON
    """
    config_path = "config.json"
    
    # Проверяем существование файла
    if not os.path.exists(config_path):
        raise FileNotFoundError(
            f"Файл конфигурации не найден: {config_path}\n"
            f"Создайте файл config.json в корне проекта"
        )
    
    try:
        with open(config_path, 'r', encoding='utf-8') as file:
            config = json.load(file)
        
        # Проверяем наличие обязательных полей
        required_fields = ['telegram_bot_token', 'openrouter_api_key', 'model_name']
        missing_fields = [field for field in required_fields if field not in config]
        
        if missing_fields:
            raise ValueError(
                f"В конфигурации отсутствуют обязательные поля: {missing_fields}"
            )
        
        # Проверяем, что telegram_bot_token не пустой
        if not config['telegram_bot_token'] or config['telegram_bot_token'].strip() == "":
            raise ValueError("Ошибка: Добавьте токен бота в config.json")
        
        print(f"✅ Конфигурация успешно загружена из {config_path}")
        return config
        
    except json.JSONDecodeError as e:
        raise ValueError(f"Ошибка парсинга JSON в файле {config_path}: {e}")
    except ValueError:
        # Пропускаем ValueError дальше (включая проверку токена)
        raise
    except Exception as e:
        raise Exception(f"Неожиданная ошибка при загрузке конфигурации: {e}")


def get_telegram_token():
    """
    Возвращает токен телеграм-бота
    
    :return: Токен бота
    """
    config = load_config()
    return config['telegram_bot_token']


def get_openrouter_config():
    """
    Возвращает настройки для OpenRouter API
    
    :return: Словарь с настройками OpenRouter
    """
    config = load_config()
    return {
        'api_key': config['openrouter_api_key'],
        'model_name': config['model_name'],
        'max_response_tokens': config.get('max_response_tokens', 4000),
        'temperature': config.get('temperature', 0.7)
    }