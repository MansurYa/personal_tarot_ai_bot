"""
LLM сессия для многоэтапной генерации интерпретации раскладов
"""

import re
import json
import logging
from typing import Dict, List, Optional, Tuple
from .openrouter_client import TarotLLMAgent, MessageContext
from .prompt_manager import PromptManager
from .config import load_config

logger = logging.getLogger(__name__)


class InterpretationStage:
    """Этапы интерпретации"""
    SYSTEM = "system"
    SPREAD_CONTEXT = "spread_context"
    PSYCHOLOGICAL_ANALYSIS = "psychological_analysis"
    CONTEXT_ANALYSIS = "context_analysis"
    SYNTHESIS = "synthesis"
    FINAL_RESPONSE = "final_response"


class LLMSession:
    """Класс для управления многоэтапной генерацией интерпретации"""
    
    def __init__(self, prompt_manager: PromptManager):
        self.prompt_manager = prompt_manager
        self.config = load_config()
        
        # Создаем MessageContext с mode=2 (критически важно!)
        self.context = MessageContext(task_prompt=None)
        
        # Создаем TarotLLMAgent
        self.agent = TarotLLMAgent(
            model_name=self.config.get("model_name", "deepseek/deepseek-chat-v3-0324:free"),
            api_key=self.config.get("openrouter_api_key"),
            max_tokens=self.config.get("max_response_tokens", 8000),
            temperature=self.config.get("temperature", 0.3)
        )
        
        # Состояние сессии
        self.current_stage = None
        self.user_data = {}
        self.spread_data = {}
        self.generated_questions = []
        self.question_answers = []
        
    async def initialize_session(self, user_data: Dict, spread_data: Dict):
        """Инициализирует сессию с данными пользователя и расклада"""
        self.user_data = user_data
        self.spread_data = spread_data
        
        # Этап 1: Системный промпт (01_system_persona.md)
        system_prompt = self.prompt_manager.get_system_persona(
            name=user_data.get('name', 'Друг'),
            age=user_data.get('age', 25)
        )
        
        # Добавляем системный промпт в контекст
        self.context.add_user_message(system_prompt)
        self.current_stage = InterpretationStage.SYSTEM
        
        logger.info("LLM сессия инициализирована")
        
    async def add_spread_context(self):
        """Этап 2: Добавляет контекст расклада с картами"""
        if not self.spread_data:
            raise ValueError("Spread data not provided")
            
        # Получаем контекст расклада
        spread_context = self.prompt_manager.get_spread_context(
            spread_type=self.spread_data.get('spread_type'),
            selected_cards=self.spread_data.get('cards', []),
            positions=self.spread_data.get('positions', [])
        )
        
        # Добавляем в контекст
        self.context.add_user_message(spread_context)
        self.current_stage = InterpretationStage.SPREAD_CONTEXT
        
        logger.info("Контекст расклада добавлен")
    
    async def add_preliminary_answers(self, answers: List[str]):
        """Добавляет предварительные ответы пользователя в контекст"""
        if answers:
            answers_text = self.prompt_manager.format_user_answers(
                questions=self.spread_data.get('questions', []),
                answers=answers
            )
            self.context.add_user_message(f"ПРЕДВАРИТЕЛЬНЫЕ ОТВЕТЫ ПОЛЬЗОВАТЕЛЯ:\n{answers_text}")
    
    async def generate_psychological_analysis(self, preliminary_answers: List[str] = None) -> List[str]:
        """
        Этап 3: Генерирует психологический анализ и уточняющие вопросы
        Возвращает список сгенерированных вопросов
        """
        if preliminary_answers:
            await self.add_preliminary_answers(preliminary_answers)
        
        # Получаем промпт для анализа
        analysis_prompt = self.prompt_manager.get_psychological_analysis_prompt(
            user_answers=preliminary_answers or []
        )
        
        # Добавляем промпт и генерируем
        self.context.add_user_message(analysis_prompt)
        
        try:
            # Получаем сообщения из контекста  
            messages = self.context.get_message_history()
            
            # Используем асинхронную функцию send_request
            from .openrouter_client import send_request
            response = await send_request(
                messages=messages,
                model=self.agent.model_name,
                api_key=self.agent.api_key,
                max_tokens=self.agent.max_tokens,
                temperature=self.agent.temperature
            )
            
            # Добавляем ответ в контекст для сохранения истории
            self.context.add_assistant_message(response)
            
            # Извлекаем вопросы из ответа
            questions = self._extract_questions_from_response(response)
            self.generated_questions = questions
            
            self.current_stage = InterpretationStage.PSYCHOLOGICAL_ANALYSIS
            logger.info(f"Сгенерировано {len(questions)} уточняющих вопросов")
            
            return questions
            
        except Exception as e:
            logger.error(f"Ошибка при генерации психологического анализа: {e}")
            return []
    
    def _extract_questions_from_response(self, response: str) -> List[str]:
        """Извлекает вопросы из ответа LLM с улучшенным парсингом"""
        try:
            questions = []
            
            # Способ 1: Ищем маркеры [QUESTIONS_START] и [QUESTIONS_END]
            questions_match = re.search(r'\[QUESTIONS_START\](.*?)\[QUESTIONS_END\]', response, re.DOTALL | re.IGNORECASE)
            if questions_match:
                questions_block = questions_match.group(1).strip()
                # Парсим Q1:, Q2: формат
                q_matches = re.findall(r'Q\d+:\s*(.+?)(?=Q\d+:|$)', questions_block, re.DOTALL)
                questions.extend([q.strip() for q in q_matches if self._validate_question(q.strip())])
            
            # Способ 2: Ищем старый формат <QUESTIONS>
            if not questions:
                questions_match = re.search(r'<QUESTIONS>(.*?)</QUESTIONS>', response, re.DOTALL)
                if questions_match:
                    questions_block = questions_match.group(1).strip()
                    # Извлекаем пронумерованные вопросы
                    for line in questions_block.split('\n'):
                        line = line.strip()
                        if re.match(r'^\d+\.', line):  # Строки вида "1. Вопрос"
                            question = re.sub(r'^\d+\.\s*', '', line)
                            if self._validate_question(question):
                                questions.append(question)
            
            # Способ 3: Ищем альтернативные форматы в основном тексте
            if not questions:
                # Ищем "Вопрос 1:", "Вопрос 2:" и т.д.
                question_patterns = [
                    r'Вопрос\s+\d+:\s*(.+?)(?=Вопрос\s+\d+:|$)',
                    r'\d+\.\s*(.+?\?)(?=\d+\.|$)',  # Нумерованный список с вопросительными знаками
                    r'[-•]\s*(.+?\?)(?=[-•]|$)'      # Список с маркерами
                ]
                
                for pattern in question_patterns:
                    matches = re.findall(pattern, response, re.DOTALL | re.IGNORECASE)
                    if matches:
                        questions.extend([q.strip() for q in matches if self._validate_question(q.strip())])
                        break
            
            # Валидируем общее количество вопросов
            if questions:
                questions = self._validate_questions_count(questions)
                logger.info(f"Извлечено {len(questions)} валидных вопросов")
            else:
                logger.warning("Не удалось извлечь вопросы из ответа LLM")
            
            return questions
            
        except Exception as e:
            logger.error(f"Ошибка при извлечении вопросов: {e}")
            return []
    
    def _validate_question(self, question: str) -> bool:
        """Валидирует отдельный вопрос"""
        if not question or len(question.strip()) < 10:
            return False
        if len(question) > 500:
            return False
        # Проверяем наличие вопросительного знака
        if '?' not in question:
            return False
        return True
    
    def _validate_questions_count(self, questions: List[str]) -> List[str]:
        """Валидирует количество вопросов согласно типу расклада"""
        spread_type = self.spread_data.get('spread_type', '')
        
        # Ограничения по количеству вопросов для разных раскладов
        max_questions = {
            'single_card': 2,
            'three_cards': 3, 
            'horseshoe': 4,
            'love_triangle': 5,
            'celtic_cross': 7,
            'week_forecast': 4,
            'year_wheel': 5
        }
        
        limit = max_questions.get(spread_type, 5)  # По умолчанию максимум 5
        
        if len(questions) > limit:
            logger.warning(f"Слишком много вопросов ({len(questions)}) для расклада {spread_type}, обрезаем до {limit}")
            return questions[:limit]
        
        return questions
    
    async def add_question_answers(self, answers: List[str]):
        """Добавляет ответы на уточняющие вопросы в контекст"""
        if not answers or not self.generated_questions:
            return
            
        self.question_answers = answers
        
        # Форматируем ответы
        answers_text = self.prompt_manager.format_user_answers(
            questions=self.generated_questions,
            answers=answers
        )
        
        # Добавляем в контекст
        self.context.add_user_message(f"ОТВЕТЫ НА УТОЧНЯЮЩИЕ ВОПРОСЫ:\n{answers_text}")
        logger.info(f"Добавлено {len(answers)} ответов на уточняющие вопросы")
    
    async def generate_context_analysis(self) -> bool:
        """Этап 4: Генерирует анализ контекста и интерпретацию карт"""
        analysis_prompt = self.prompt_manager.get_context_analysis_prompt()
        self.context.add_user_message(analysis_prompt)
        
        try:
            messages = self.context.get_message_history()
            from .openrouter_client import send_request
            response = await send_request(
                messages=messages,
                model=self.agent.model_name,
                api_key=self.agent.api_key,
                max_tokens=self.agent.max_tokens,
                temperature=self.agent.temperature
            )
            self.context.add_assistant_message(response)
            
            self.current_stage = InterpretationStage.CONTEXT_ANALYSIS
            logger.info("Анализ контекста и карт завершен")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка при анализе контекста: {e}")
            return False
    
    async def generate_synthesis(self) -> bool:
        """Этап 5: Генерирует глубокий синтез и планирование рассказа"""
        synthesis_prompt = self.prompt_manager.get_synthesis_prompt()
        self.context.add_user_message(synthesis_prompt)
        
        try:
            messages = self.context.get_message_history()
            from .openrouter_client import send_request
            response = await send_request(
                messages=messages,
                model=self.agent.model_name,
                api_key=self.agent.api_key,
                max_tokens=self.agent.max_tokens,
                temperature=self.agent.temperature
            )
            self.context.add_assistant_message(response)
            
            self.current_stage = InterpretationStage.SYNTHESIS
            logger.info("Синтез и планирование рассказа завершены")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка при синтезе: {e}")
            return False
    
    async def generate_final_interpretation(self) -> Optional[str]:
        """Этап 6: Генерирует финальную интерпретацию для пользователя"""
        final_prompt = self.prompt_manager.get_final_response_prompt()
        self.context.add_user_message(final_prompt)
        
        try:
            messages = self.context.get_message_history()
            from .openrouter_client import send_request
            response = await send_request(
                messages=messages,
                model=self.agent.model_name,
                api_key=self.agent.api_key,
                max_tokens=self.agent.max_tokens,
                temperature=self.agent.temperature
            )
            
            # НЕ добавляем финальный ответ в контекст - он для пользователя
            self.current_stage = InterpretationStage.FINAL_RESPONSE
            logger.info("Финальная интерпретация сгенерирована")
            
            # Очищаем от возможных XML тегов
            cleaned_response = self._clean_final_response(response)
            return cleaned_response
            
        except Exception as e:
            logger.error(f"Ошибка при генерации финальной интерпретации: {e}")
            return None
    
    def _clean_final_response(self, response: str) -> str:
        """Очищает и извлекает финальную интерпретацию из ответа LLM"""
        try:
            # Способ 1: Ищем маркеры [INTERPRETATION_START] и [INTERPRETATION_END]
            interpretation_match = re.search(r'\[INTERPRETATION_START\](.*?)\[INTERPRETATION_END\]', 
                                           response, re.DOTALL | re.IGNORECASE)
            if interpretation_match:
                cleaned = interpretation_match.group(1).strip()
                logger.info("Интерпретация извлечена по маркерам INTERPRETATION")
            else:
                # Способ 2: Удаляем XML теги если есть
                cleaned = re.sub(r'<[^>]+>', '', response)
                logger.info("Использован весь ответ LLM как интерпретация")
            
            # Убираем лишние пробелы и переносы
            cleaned = re.sub(r'\n\s*\n', '\n\n', cleaned.strip())
            
            # Валидируем интерпретацию
            if self._validate_interpretation(cleaned):
                return cleaned
            else:
                logger.warning("Интерпретация не прошла валидацию, используем fallback")
                return self._get_fallback_interpretation()
                
        except Exception as e:
            logger.error(f"Ошибка при очистке финальной интерпретации: {e}")
            return self._get_fallback_interpretation()
    
    def _validate_interpretation(self, interpretation: str) -> bool:
        """Валидирует интерпретацию"""
        if not interpretation or len(interpretation.strip()) < 50:
            return False
        
        # Проверяем упоминание карт (хотя бы одна из карт должна быть упомянута)
        cards = self.spread_data.get('cards', [])
        cards_mentioned = False
        for card in cards:
            card_name = card.get('name', '').lower()
            if any(word in interpretation.lower() for word in card_name.split()):
                cards_mentioned = True
                break
        
        if not cards_mentioned:
            logger.warning("В интерпретации не упоминаются выпавшие карты")
        
        # Проверяем наличие эмодзи (желательно, но не критично)
        has_emoji = any(ord(char) > 127 for char in interpretation)
        if not has_emoji:
            logger.info("В интерпретации нет эмодзи")
        
        # Проверяем связность (не слишком много повторений)
        words = interpretation.lower().split()
        unique_words = set(words)
        word_ratio = len(unique_words) / len(words) if words else 0
        
        if word_ratio < 0.3:  # Слишком много повторений
            logger.warning("Интерпретация содержит слишком много повторений")
            return False
            
        return True
    
    def _get_fallback_interpretation(self) -> str:
        """Возвращает fallback интерпретацию при ошибках LLM"""
        cards = self.spread_data.get('cards', [])
        spread_type = self.spread_data.get('spread_type', 'расклад')
        user_name = self.user_data.get('name', 'Друг')
        
        if not cards:
            return "🔮 К сожалению, не удалось сгенерировать интерпретацию для вашего расклада. Попробуйте еще раз."
        
        # Создаем базовую интерпретацию
        interpretation = f"🔮 **{user_name}, ваш {spread_type} готов!**\n\n"
        
        for i, card in enumerate(cards[:3], 1):  # Максимум 3 карты для fallback
            name = card.get('name', f'Карта {i}')
            interpretation += f"🎴 **{name}** — эта карта символизирует важные изменения в вашей жизни.\n"
        
        interpretation += "\n✨ Карты показывают период роста и новых возможностей. Доверьтесь интуиции и будьте открыты переменам!"
        
        return interpretation
    
    async def run_full_interpretation(self, user_data: Dict, spread_data: Dict, 
                                    preliminary_answers: List[str] = None) -> Tuple[List[str], Optional[str]]:
        """
        Запускает полный процесс интерпретации
        Возвращает (уточняющие_вопросы, финальная_интерпретация)
        """
        try:
            # Инициализация
            await self.initialize_session(user_data, spread_data)
            await self.add_spread_context()
            
            # Генерируем уточняющие вопросы
            questions = await self.generate_psychological_analysis(preliminary_answers)
            
            return questions, None  # Возвращаем только вопросы на первом этапе
            
        except Exception as e:
            logger.error(f"Ошибка при запуске интерпретации: {e}")
            return [], None
    
    async def complete_interpretation(self, question_answers: List[str]) -> Optional[str]:
        """
        Завершает интерпретацию после получения ответов на уточняющие вопросы
        Возвращает финальную интерпретацию
        """
        try:
            # Добавляем ответы на вопросы
            await self.add_question_answers(question_answers)
            
            # Последовательно выполняем этапы 4, 5, 6
            success = await self.generate_context_analysis()
            if not success:
                return None
                
            success = await self.generate_synthesis()
            if not success:
                return None
                
            final_interpretation = await self.generate_final_interpretation()
            return final_interpretation
            
        except Exception as e:
            logger.error(f"Ошибка при завершении интерпретации: {e}")
            return None
    
    def get_session_info(self) -> Dict:
        """Возвращает информацию о текущей сессии"""
        return {
            'current_stage': self.current_stage,
            'user_name': self.user_data.get('name'),
            'spread_type': self.spread_data.get('spread_type'),
            'questions_generated': len(self.generated_questions),
            'answers_received': len(self.question_answers),
            'context_messages': len(self.context.get_message_history())
        }