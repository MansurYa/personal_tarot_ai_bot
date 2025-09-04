import os
import copy
import base64
import aiohttp
import asyncio
import json
from typing import List, Dict, Any, Optional
from tenacity import retry, stop_after_attempt, wait_random_exponential, retry_if_exception_type


class OpenRouterError(Exception):
    """Ошибка при работе с OpenRouter API"""
    pass


class MessageContext:
    """
    Упрощенный класс MessageContext для управления контекстом сообщений
    Поддерживает только режим 2 (сохраняет контекст между запросами)
    """
    
    def __init__(self, task_prompt: str = None):
        """
        Инициализирует MessageContext в режиме 2
        
        :param task_prompt: Системный промпт, добавляемый в начало контекста
        """
        self.task_prompt = task_prompt
        self.messages = []
    
    def add_user_message(self, text: str):
        """
        Добавляет пользовательское сообщение
        
        :param text: Текст сообщения
        """
        # Если сообщений еще нет и task_prompt задан, добавляем его первым
        if self.task_prompt and len(self.messages) == 0:
            self.messages.append({
                "role": "system", 
                "content": [{"type": "text", "text": self.task_prompt}]
            })
        
        # Добавляем пользовательское сообщение
        self.messages.append({
            "role": "user",
            "content": [{"type": "text", "text": text}]
        })
    
    def add_assistant_message(self, text: str):
        """
        Добавляет сообщение ассистента
        
        :param text: Текст ответа ассистента
        """
        self.messages.append({
            "role": "assistant",
            "content": [{"type": "text", "text": text}]
        })
    
    def add_system_message(self, text: str):
        """
        Добавляет системное сообщение
        
        :param text: Текст системного сообщения
        """
        self.messages.append({
            "role": "system",
            "content": [{"type": "text", "text": text}]
        })
    
    def get_message_history(self) -> List[Dict[str, Any]]:
        """
        Возвращает копию списка сообщений
        
        :return: Список сообщений
        """
        return self.messages.copy()
    
    def clear(self):
        """Очищает историю сообщений"""
        self.messages.clear()
    
    def update_task_prompt(self, new_task_prompt: str):
        """
        Обновляет системный промпт
        
        :param new_task_prompt: Новый системный промпт
        """
        self.task_prompt = new_task_prompt
        # Добавляем новый промпт как системное сообщение
        if len(self.messages) > 0:
            self.messages.append({
                "role": "system",
                "content": [{"type": "text", "text": self.task_prompt}]
            })


def _convert_messages(messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Конвертирует сообщения в простой текстовый формат для API
    
    :param messages: Список сообщений
    :return: Сконвертированные сообщения
    """
    converted = []
    
    for idx, msg in enumerate(messages):
        if 'role' not in msg or 'content' not in msg:
            raise ValueError(f"Некорректное сообщение в позиции {idx}")
        
        content = msg["content"]
        
        # Если контент - список (сложный формат), извлекаем текст
        if isinstance(content, list):
            text_parts = []
            for item in content:
                if isinstance(item, dict) and item.get("type") == "text":
                    text_parts.append(item.get("text", ""))
            content = "\n".join(text_parts)
        
        # Убеждаемся что контент - строка
        if not isinstance(content, str):
            content = str(content)
        
        converted.append({
            "role": msg["role"],
            "content": content
        })
    
    return converted


@retry(
    wait=wait_random_exponential(min=1, max=300),
    stop=stop_after_attempt(5),
    retry=retry_if_exception_type((OpenRouterError, aiohttp.ClientError, asyncio.TimeoutError)),
    reraise=True
)
async def send_request(
    messages: List[Dict[str, Any]], 
    model: str, 
    api_key: str,
    max_retries: int = 5,
    max_tokens: int = 4000,
    temperature: float = 0.3
) -> str:
    """
    Отправляет запрос к OpenRouter API с повторными попытками
    
    :param messages: Список сообщений [{"role": "user/system/assistant", "content": "текст"}]
    :param model: Название модели (например: 'deepseek/deepseek-chat-v3-0324:free')
    :param api_key: API ключ OpenRouter
    :param max_retries: Максимальное количество повторов (не используется, управляется @retry)
    :param max_tokens: Максимальное количество токенов в ответе
    :param temperature: Температура генерации (0.0-1.0)
    :return: Текст ответа от модели
    :raises OpenRouterError: При ошибках API или пустом ответе
    """
    
    if not api_key:
        raise ValueError("API ключ обязателен")
    
    if not model or '/' not in model:
        raise ValueError(f"Некорректное название модели: {model}")
    
    if not messages:
        raise ValueError("Список сообщений не может быть пустым")
    
    # Конвертируем сообщения
    converted_messages = _convert_messages(messages)
    
    # Подготовка данных
    payload = {
        "model": model,
        "messages": converted_messages,
        "max_tokens": max_tokens,
        "temperature": temperature
    }
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://tarot-bot.com",
        "X-Title": "Personal Tarot Bot"
    }
    
    timeout = aiohttp.ClientTimeout(total=300)
    
    async with aiohttp.ClientSession(timeout=timeout) as session:
        try:
            async with session.post(
                "https://openrouter.ai/api/v1/chat/completions",
                json=payload,
                headers=headers
            ) as response:
                
                if response.status != 200:
                    error_text = await response.text()
                    raise OpenRouterError(f"HTTP {response.status}: {error_text}")
                
                try:
                    data = await response.json()
                except json.JSONDecodeError as e:
                    raise OpenRouterError(f"Ошибка парсинга JSON: {e}")
                
                # Проверяем структуру ответа
                if not data.get('choices') or len(data['choices']) == 0:
                    raise OpenRouterError("Пустой ответ от API - отсутствуют choices")
                
                # Извлекаем контент
                content = data['choices'][0].get('message', {}).get('content')
                
                # КРИТИЧЕСКАЯ ПРОВЕРКА: контент не должен быть пустым
                if content is None or (isinstance(content, str) and content.strip() == ""):
                    provider = data.get('provider', 'unknown')
                    usage = data.get('usage', {})
                    usage_info = f", tokens: {usage.get('completion_tokens', 0)}/{usage.get('prompt_tokens', 0)}"
                    error_msg = f"Получен пустой ответ от провайдера {provider}{usage_info}"
                    raise OpenRouterError(error_msg)
                
                return content.strip()
                
        except aiohttp.ClientError as e:
            raise OpenRouterError(f"Ошибка соединения: {e}")
        except asyncio.TimeoutError:
            raise OpenRouterError("Превышен таймаут запроса")


def send_request_sync(
    messages: List[Dict[str, Any]], 
    model: str, 
    api_key: str,
    max_retries: int = 10,
    max_tokens: int = 8000,
    temperature: float = 0.3
) -> str:
    """
    Синхронная обертка для асинхронного вызова
    
    :param messages: Список сообщений
    :param model: Название модели  
    :param api_key: API ключ
    :param max_retries: Максимальное количество повторов
    :param max_tokens: Максимальное количество токенов
    :param temperature: Температура генерации
    :return: Текст ответа от модели
    """
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    return loop.run_until_complete(
        send_request(messages, model, api_key, max_retries, max_tokens, temperature)
    )


class TarotLLMAgent:
    """
    Упрощенный агент для работы с OpenRouter API для таро-бота
    Извлечено из ChatLLMAgent, оставлен только необходимый функционал
    """
    
    def __init__(self, model_name: str, api_key: str, task_prompt: str = None, 
                 max_tokens: int = 4000, temperature: float = 0.7):
        """
        Инициализирует агент для работы с таро
        
        :param model_name: Название модели OpenRouter (например: 'deepseek/deepseek-chat-v3-0324:free')
        :param api_key: API ключ OpenRouter
        :param task_prompt: Системный промпт (например: "Ты опытный таролог...")
        :param max_tokens: Максимальное количество токенов в ответе
        :param temperature: Температура генерации
        """
        # Пропускаем валидацию для тестовых моделей
        if not model_name.startswith("test-") and '/' not in model_name:
            raise ValueError(f"Некорректное название модели OpenRouter: {model_name}")
        
        if not model_name.startswith("test-") and not api_key:
            raise ValueError("API ключ OpenRouter обязателен")
        
        self.model_name = model_name
        self.api_key = api_key
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.context = MessageContext(task_prompt)
    
    def response_from_LLM(self, user_message: str) -> str:
        """
        Добавляет сообщение пользователя, получает ответ от LLM и добавляет его в контекст
        Упрощенная версия из ChatLLMAgent
        
        :param user_message: Сообщение пользователя
        :return: Ответ ассистента
        """
        # Добавляем сообщение пользователя в контекст
        self.context.add_user_message(user_message)
        
        # Получаем историю сообщений
        messages = self.context.get_message_history()
        
        try:
            # Отправляем запрос к OpenRouter
            assistant_response = send_request_sync(
                messages=messages,
                model=self.model_name,
                api_key=self.api_key,
                max_tokens=self.max_tokens,
                temperature=self.temperature
            )
            
            # Добавляем ответ ассистента в контекст
            self.context.add_assistant_message(assistant_response)
            
            return assistant_response
            
        except Exception as e:
            error_msg = f"Ошибка при получении ответа от LLM: {str(e)}"
            print(error_msg)
            return error_msg
    
    def clear_context(self):
        """Очищает контекст сообщений"""
        self.context.clear()
    
    def update_task_prompt(self, new_task_prompt: str):
        """
        Обновляет системный промпт
        
        :param new_task_prompt: Новый системный промпт
        """
        self.context.update_task_prompt(new_task_prompt)
    
    def get_message_count(self) -> int:
        """
        Возвращает количество сообщений в контексте
        
        :return: Количество сообщений
        """
        return len(self.context.messages)
    
    async def send_request(self, context: MessageContext) -> str:
        """
        НОВЫЙ АСИНХРОННЫЙ МЕТОД для совместимости с MultiStageLLMSession
        Отправляет запрос используя переданный контекст
        
        :param context: MessageContext с историей сообщений
        :return: Ответ от LLM
        """
        try:
            # Для тестовых моделей возвращаем мок-ответ
            if self.model_name.startswith("test-"):
                messages = context.get_message_history()
                return f"Mock LLM response for {len(messages)} messages"
            
            # Используем глобальную асинхронную функцию send_request
            from src.openrouter_client import send_request as async_send_request
            
            messages = context.get_message_history()
            
            response = await async_send_request(
                messages=messages,
                model=self.model_name,
                api_key=self.api_key,
                max_tokens=self.max_tokens,
                temperature=self.temperature
            )
            
            return response
            
        except Exception as e:
            error_msg = f"Ошибка при получении ответа от LLM: {str(e)}"
            raise OpenRouterError(error_msg)
