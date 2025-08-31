"""
Система логирования раскладов для анализа и обратной связи
"""

import json
import os
import time
from datetime import datetime
from typing import Dict, List, Optional, Any
import logging

logger = logging.getLogger(__name__)

class SpreadLogger:
    """Логирует все данные расклада для анализа и обратной связи"""
    
    def __init__(self, logs_dir: str = "logs/spreads"):
        self.logs_dir = logs_dir
        self._ensure_logs_directory()
    
    def _ensure_logs_directory(self):
        """Создает директорию для логов если не существует"""
        if not os.path.exists(self.logs_dir):
            os.makedirs(self.logs_dir, exist_ok=True)
            logger.info(f"Создана директория для логов: {self.logs_dir}")
    
    def _generate_filename(self, chat_id: int, spread_type: str) -> str:
        """Генерирует имя файла для лога"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_{chat_id}_{spread_type}.json"
        return os.path.join(self.logs_dir, filename)
    
    def create_spread_log(self, 
                         chat_id: int,
                         user_data: Dict,
                         spread_type: str,
                         spread_name: str,
                         magic_number: int,
                         selected_cards: List[Dict],
                         positions: List[str],
                         telegram_username: str = None,
                         telegram_first_name: str = None,
                         telegram_last_name: str = None,
                         user_id: int = None) -> str:
        """
        Создает начальный лог расклада
        
        :param chat_id: ID чата пользователя
        :param user_data: Данные пользователя (имя, возраст)
        :param spread_type: Тип расклада
        :param spread_name: Название расклада
        :param magic_number: Магическое число
        :param selected_cards: Выбранные карты
        :param positions: Позиции карт
        :param telegram_username: Telegram username пользователя
        :param telegram_first_name: Имя в Telegram
        :param telegram_last_name: Фамилия в Telegram
        :param user_id: Telegram user ID
        :return: Путь к файлу лога
        """
        try:
            log_data = {
                "metadata": {
                    "chat_id": chat_id,
                    "timestamp": datetime.now().isoformat(),
                    "start_time": time.time(),
                    "status": "started"
                },
                "user": {
                    "name": user_data.get("name"),
                    "age": user_data.get("age"),
                    "chat_id": chat_id,
                    "user_id": user_id,
                    "telegram": {
                        "username": telegram_username,
                        "first_name": telegram_first_name,
                        "last_name": telegram_last_name
                    }
                },
                "spread": {
                    "type": spread_type,
                    "name": spread_name,
                    "magic_number": magic_number,
                    "cards": selected_cards,
                    "positions": positions
                },
                "questions": {
                    "preliminary": [],
                    "preliminary_answers": [],
                    "llm_generated": [],
                    "llm_answers": []
                },
                "llm_processing": {
                    "model": None,
                    "prompts_used": [],
                    "generation_start": None,
                    "generation_end": None,
                    "generation_time_seconds": None,
                    "errors": []
                },
                "interpretation": {
                    "text": None,
                    "length": 0,
                    "delivery_time": None
                },
                "feedback": {
                    "rating": None,
                    "comment": None,
                    "feedback_time": None
                }
            }
            
            filepath = self._generate_filename(chat_id, spread_type)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(log_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Создан лог расклада: {filepath}")
            return filepath
            
        except Exception as e:
            logger.error(f"Ошибка при создании лога расклада: {e}")
            return ""
    
    def update_preliminary_questions(self, filepath: str, questions: List[str], answers: List[str]):
        """Обновляет предварительные вопросы и ответы"""
        try:
            self._update_log_section(filepath, {
                "questions.preliminary": questions,
                "questions.preliminary_answers": answers
            })
            logger.info(f"Обновлены предварительные вопросы в {filepath}")
            
        except Exception as e:
            logger.error(f"Ошибка при обновлении предварительных вопросов: {e}")
    
    def update_llm_questions(self, filepath: str, questions: List[str], answers: List[str]):
        """Обновляет LLM вопросы и ответы"""
        try:
            self._update_log_section(filepath, {
                "questions.llm_generated": questions,
                "questions.llm_answers": answers
            })
            logger.info(f"Обновлены LLM вопросы в {filepath}")
            
        except Exception as e:
            logger.error(f"Ошибка при обновлении LLM вопросов: {e}")
    
    def start_llm_processing(self, filepath: str, model_name: str):
        """Отмечает начало LLM обработки"""
        try:
            self._update_log_section(filepath, {
                "llm_processing.model": model_name,
                "llm_processing.generation_start": time.time(),
                "metadata.status": "llm_processing"
            })
            logger.info(f"Начата LLM обработка в {filepath}")
            
        except Exception as e:
            logger.error(f"Ошибка при начале LLM обработки: {e}")
    
    def log_llm_error(self, filepath: str, error_message: str, stage: str):
        """Логирует ошибку LLM"""
        try:
            log_data = self._load_log(filepath)
            if log_data:
                error_entry = {
                    "timestamp": datetime.now().isoformat(),
                    "stage": stage,
                    "error": str(error_message)
                }
                log_data["llm_processing"]["errors"].append(error_entry)
                log_data["metadata"]["status"] = "error"
                
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(log_data, f, ensure_ascii=False, indent=2)
                    
                logger.error(f"Логирована ошибка LLM в {filepath}: {error_message}")
            
        except Exception as e:
            logger.error(f"Ошибка при логировании LLM ошибки: {e}")
    
    def complete_interpretation(self, filepath: str, interpretation: str):
        """Завершает интерпретацию"""
        try:
            end_time = time.time()
            
            log_data = self._load_log(filepath)
            if log_data:
                start_time = log_data.get("llm_processing", {}).get("generation_start", end_time)
                generation_time = end_time - start_time
                
                updates = {
                    "llm_processing.generation_end": end_time,
                    "llm_processing.generation_time_seconds": round(generation_time, 2),
                    "interpretation.text": interpretation,
                    "interpretation.length": len(interpretation),
                    "interpretation.delivery_time": datetime.now().isoformat(),
                    "metadata.status": "completed"
                }
                
                self._update_log_section(filepath, updates)
                logger.info(f"Завершена интерпретация в {filepath} за {generation_time:.2f} сек")
            
        except Exception as e:
            logger.error(f"Ошибка при завершении интерпретации: {e}")
    
    def add_feedback(self, filepath: str, rating: int, comment: str = None):
        """Добавляет обратную связь"""
        try:
            updates = {
                "feedback.rating": rating,
                "feedback.comment": comment,
                "feedback.feedback_time": datetime.now().isoformat(),
                "metadata.status": "feedback_received"
            }
            
            self._update_log_section(filepath, updates)
            logger.info(f"Добавлена обратная связь в {filepath}: {rating} звезд")
            
        except Exception as e:
            logger.error(f"Ошибка при добавлении обратной связи: {e}")
    
    def _update_log_section(self, filepath: str, updates: Dict[str, Any]):
        """Обновляет секции в логе"""
        if not os.path.exists(filepath):
            logger.warning(f"Файл лога не найден: {filepath}")
            return
        
        log_data = self._load_log(filepath)
        if not log_data:
            return
        
        # Обновляем значения по ключам с точками (например, "questions.preliminary")
        for key, value in updates.items():
            keys = key.split('.')
            current = log_data
            
            # Навигация по nested dictionary
            for k in keys[:-1]:
                if k not in current:
                    current[k] = {}
                current = current[k]
            
            # Установка финального значения
            current[keys[-1]] = value
        
        # Сохранение обновленных данных
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(log_data, f, ensure_ascii=False, indent=2)
    
    def _load_log(self, filepath: str) -> Optional[Dict]:
        """Загружает данные лога"""
        try:
            if not os.path.exists(filepath):
                return None
                
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
                
        except Exception as e:
            logger.error(f"Ошибка при загрузке лога {filepath}: {e}")
            return None
    
    def get_user_stats(self, chat_id: int) -> Dict:
        """Получает статистику пользователя"""
        try:
            stats = {
                "total_spreads": 0,
                "favorite_spread": None,
                "average_rating": 0,
                "total_feedback": 0,
                "recent_spreads": []
            }
            
            # Ищем все логи пользователя
            user_logs = []
            for filename in os.listdir(self.logs_dir):
                if filename.endswith('.json') and f"_{chat_id}_" in filename:
                    filepath = os.path.join(self.logs_dir, filename)
                    log_data = self._load_log(filepath)
                    if log_data:
                        user_logs.append(log_data)
            
            if not user_logs:
                return stats
            
            # Подсчет статистики
            spread_types = {}
            ratings = []
            
            for log in user_logs:
                stats["total_spreads"] += 1
                
                # Подсчет типов раскладов
                spread_type = log.get("spread", {}).get("type")
                if spread_type:
                    spread_types[spread_type] = spread_types.get(spread_type, 0) + 1
                
                # Подсчет рейтингов
                rating = log.get("feedback", {}).get("rating")
                if rating:
                    ratings.append(rating)
                    stats["total_feedback"] += 1
                
                # Последние расклады
                if len(stats["recent_spreads"]) < 5:
                    stats["recent_spreads"].append({
                        "type": spread_type,
                        "timestamp": log.get("metadata", {}).get("timestamp"),
                        "rating": rating
                    })
            
            # Любимый тип расклада
            if spread_types:
                stats["favorite_spread"] = max(spread_types, key=spread_types.get)
            
            # Средний рейтинг
            if ratings:
                stats["average_rating"] = round(sum(ratings) / len(ratings), 1)
            
            return stats
            
        except Exception as e:
            logger.error(f"Ошибка при получении статистики пользователя {chat_id}: {e}")
            return {}
    
    def cleanup_old_logs(self, days: int = 30):
        """Очищает старые логи"""
        try:
            cutoff_time = time.time() - (days * 24 * 3600)
            removed_count = 0
            
            for filename in os.listdir(self.logs_dir):
                if filename.endswith('.json'):
                    filepath = os.path.join(self.logs_dir, filename)
                    file_time = os.path.getctime(filepath)
                    
                    if file_time < cutoff_time:
                        os.remove(filepath)
                        removed_count += 1
            
            if removed_count > 0:
                logger.info(f"Удалено {removed_count} старых логов (старше {days} дней)")
                
        except Exception as e:
            logger.error(f"Ошибка при очистке старых логов: {e}")


# Глобальный экземпляр логгера
_spread_logger = None

def get_spread_logger() -> SpreadLogger:
    """Получает глобальный экземпляр логгера"""
    global _spread_logger
    if _spread_logger is None:
        _spread_logger = SpreadLogger()
    return _spread_logger