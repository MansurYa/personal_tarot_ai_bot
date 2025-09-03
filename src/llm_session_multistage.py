"""
Многоэтапная LLM сессия для правильного алгоритма интерпретации таро
"""

import re
import logging
import asyncio
from typing import List, Dict, Optional, Any, Tuple
from enum import Enum

from src.openrouter_client import TarotLLMAgent, MessageContext
from src.prompt_manager import PromptManager

logger = logging.getLogger(__name__)

class InterpretationStage(Enum):
    """Этапы интерпретации согласно LLM_algorithm.md"""
    QUESTIONS_GENERATION = 1      # Этап 1: Генерация дополнительных вопросов
    CONTEXT_ANALYSIS = 2          # Этап 2: Анализ контекста и карт (25% → 50%)
    DEEP_SYNTHESIS = 3            # Этап 3: Глубокий синтез (50% → 75%)
    FINAL_RESPONSE = 4            # Этап 4: Финальная интерпретация (75% → 100%)

class MultiStageLLMSession:
    """
    Многоэтапная LLM сессия, которая правильно реализует алгоритм из LLM_algorithm.md
    
    Ключевая идея: каждый этап - это отдельный LLM запрос с накапливающимся контекстом
    """
    
    def __init__(self, prompt_manager: PromptManager, model_name: str = "deepseek/deepseek-chat-v3-0324:free"):
        self.prompt_manager = prompt_manager
        self.agent = TarotLLMAgent(model_name=model_name)
        self.context = MessageContext()
        
        # Данные сессии
        self.spread_type = None
        self.selected_cards = []
        self.spread_config = {}
        self.user_name = ""
        self.user_age = 0
        self.magic_number = 1
        self.preliminary_answers = []
        self.llm_questions = []
        self.llm_answers = []
        
        # Текущий этап
        self.current_stage = InterpretationStage.QUESTIONS_GENERATION
        
        logger.info(f"Инициализирована многоэтапная LLM сессия с моделью {model_name}")

    def setup_spread(self, spread_type: str, selected_cards: List[Dict], 
                    spread_config: Dict, user_name: str, user_age: int, magic_number: int):
        """Настройка данных расклада"""
        self.spread_type = spread_type
        self.selected_cards = selected_cards
        self.spread_config = spread_config
        self.user_name = user_name
        self.user_age = user_age
        self.magic_number = magic_number
        
        logger.info(f"Настроена сессия для расклада {spread_type}, пользователь {user_name}")

    # ==================== ЭТАП 1: ГЕНЕРАЦИЯ ВОПРОСОВ ====================

    async def stage_1_generate_questions(self, preliminary_answers: List[str]) -> List[str]:
        """
        Этап 1: Генерация дополнительных уточняющих вопросов
        
        :param preliminary_answers: Предварительные ответы пользователя
        :return: Список сгенерированных LLM вопросов
        """
        logger.info("=== ЭТАП 1: Генерация дополнительных вопросов ===")
        
        self.preliminary_answers = preliminary_answers
        self.current_stage = InterpretationStage.QUESTIONS_GENERATION
        
        # Очищаем контекст и начинаем с первых 3 промптов
        self.context.clear()
        
        # Промпт 1: Системная персона
        system_prompt = self.prompt_manager.get_system_persona()
        self.context.add_system_message(system_prompt)
        
        # Промпт 2: Контекст конкретного расклада
        spread_context = self.prompt_manager.get_spread_context(self.spread_type)
        formatted_spread_context = self._format_spread_context(spread_context)
        self.context.add_user_message(formatted_spread_context)
        
        # Добавляем предварительные ответы в контекст
        preliminary_context = self._format_preliminary_answers()
        self.context.add_user_message(preliminary_context)
        
        # Промпт 3: Запрос на психологический анализ и генерацию вопросов
        analysis_prompt = self.prompt_manager.get_psychological_analysis_prompt()
        self.context.add_user_message(analysis_prompt)
        
        # Делаем LLM запрос для генерации вопросов
        logger.info("Отправляем запрос на генерацию дополнительных вопросов...")
        response = await self.agent.send_request(self.context)
        
        # Парсим сгенерированные вопросы
        questions = self._extract_questions_from_response(response)
        self.llm_questions = questions
        
        logger.info(f"Сгенерировано {len(questions)} дополнительных вопросов")
        
        # ВАЖНО: Добавляем ответ LLM в контекст для следующих этапов
        self.context.add_assistant_message(response)
        
        return questions

    # ==================== ЭТАП 2: АНАЛИЗ КОНТЕКСТА ====================

    async def stage_2_context_analysis(self, user_answers: List[str]) -> str:
        """
        Этап 2: Анализ контекста и интерпретация карт (25% → 50%)
        
        :param user_answers: Ответы пользователя на дополнительные вопросы
        :return: Результат анализа контекста
        """
        logger.info("=== ЭТАП 2: Анализ контекста и интерпретация карт ===")
        
        self.llm_answers = user_answers
        self.current_stage = InterpretationStage.CONTEXT_ANALYSIS
        
        # Добавляем ответы пользователя в контекст
        answers_context = self._format_user_answers()
        self.context.add_user_message(answers_context)
        
        # Промпт 4: Анализ контекста и интерпретация карт
        context_analysis_prompt = self.prompt_manager.get_context_analysis_prompt()
        formatted_analysis = self._format_context_analysis_prompt(context_analysis_prompt)
        self.context.add_user_message(formatted_analysis)
        
        # Делаем ОТДЕЛЬНЫЙ LLM запрос для анализа
        logger.info("Отправляем запрос на анализ контекста...")
        response = await self.agent.send_request(self.context)
        
        # ВАЖНО: Добавляем ответ в контекст для следующего этапа
        self.context.add_assistant_message(response)
        
        logger.info("Этап 2 завершен: анализ контекста выполнен")
        return response

    # ==================== ЭТАП 3: ГЛУБОКИЙ СИНТЕЗ ====================

    async def stage_3_deep_synthesis(self) -> str:
        """
        Этап 3: Глубокий синтез и планирование рассказа (50% → 75%)
        
        :return: Результат глубокого синтеза
        """
        logger.info("=== ЭТАП 3: Глубокий синтез и планирование рассказа ===")
        
        self.current_stage = InterpretationStage.DEEP_SYNTHESIS
        
        # Промпт 5: Глубокий синтез
        synthesis_prompt = self.prompt_manager.get_synthesis_prompt()
        self.context.add_user_message(synthesis_prompt)
        
        # Делаем ОТДЕЛЬНЫЙ LLM запрос для синтеза
        logger.info("Отправляем запрос на глубокий синтез...")
        response = await self.agent.send_request(self.context)
        
        # ВАЖНО: Добавляем ответ в контекст для финального этапа
        self.context.add_assistant_message(response)
        
        logger.info("Этап 3 завершен: глубокий синтез выполнен")
        return response

    # ==================== ЭТАП 4: ФИНАЛЬНАЯ ИНТЕРПРЕТАЦИЯ ====================

    async def stage_4_final_response(self) -> str:
        """
        Этап 4: Генерация финальной интерпретации для пользователя (75% → 100%)
        
        :return: Финальная интерпретация в формате для пользователя
        """
        logger.info("=== ЭТАП 4: Генерация финальной интерпретации ===")
        
        self.current_stage = InterpretationStage.FINAL_RESPONSE
        
        # Промпт 6: Финальный ответ пользователю
        final_prompt = self.prompt_manager.get_final_response_prompt()
        self.context.add_user_message(final_prompt)
        
        # Делаем ФИНАЛЬНЫЙ LLM запрос
        logger.info("Отправляем запрос на генерацию финального ответа...")
        response = await self.agent.send_request(self.context)
        
        # Парсим финальную интерпретацию
        final_interpretation = self._parse_final_interpretation(response)
        
        logger.info("Этап 4 завершен: финальная интерпретация готова")
        return final_interpretation

    # ==================== ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ ====================

    def _format_spread_context(self, spread_context: str) -> str:
        """Форматирует контекст расклада с данными карт"""
        # Добавляем информацию о выбранных картах
        cards_info = ""
        for i, card in enumerate(self.selected_cards, 1):
            cards_info += f"\n**Позиция {i}: {card['name']}**\n"
            cards_info += f"Архив: {card.get('arcana', 'Не указано')}\n"
            cards_info += f"Значения: {card.get('fortune_telling', ['Не указано'])}\n"
        
        return spread_context.replace("{cards_data}", cards_info)

    def _format_preliminary_answers(self) -> str:
        """Форматирует предварительные ответы пользователя"""
        answers_text = f"**Предварительные ответы пользователя {self.user_name}:**\n\n"
        for i, answer in enumerate(self.preliminary_answers, 1):
            if isinstance(answer, dict):
                answers_text += f"{i}. {answer.get('question_text', 'Вопрос')}: {answer.get('answer', 'Нет ответа')}\n"
            else:
                answers_text += f"{i}. {answer}\n"
        
        return answers_text

    def _format_user_answers(self) -> str:
        """Форматирует ответы пользователя на дополнительные вопросы"""
        answers_text = f"**Ответы пользователя на дополнительные вопросы:**\n\n"
        for i, (question, answer) in enumerate(zip(self.llm_questions, self.llm_answers), 1):
            answers_text += f"**Вопрос {i}:** {question}\n"
            answers_text += f"**Ответ:** {answer}\n\n"
        
        return answers_text

    def _format_context_analysis_prompt(self, prompt: str) -> str:
        """Форматирует промпт анализа контекста с данными карт"""
        cards_detailed = ""
        for card in self.selected_cards:
            cards_detailed += f"**{card['name']}:**\n"
            cards_detailed += f"- Значения: {card.get('fortune_telling', [])}\n"
            cards_detailed += f"- Ключевые слова: {card.get('keywords', [])}\n"
            if 'meanings' in card:
                cards_detailed += f"- Светлые значения: {card['meanings'].get('light', [])}\n"
                cards_detailed += f"- Теневые значения: {card['meanings'].get('shadow', [])}\n"
            cards_detailed += "\n"
        
        return prompt.replace("{detailed_cards_info}", cards_detailed)

    def _extract_questions_from_response(self, response: str) -> List[str]:
        """Извлекает вопросы из ответа LLM"""
        questions = []
        
        # Способ 1: Маркеры [QUESTIONS_START] и [QUESTIONS_END]
        questions_match = re.search(r'\[QUESTIONS_START\](.*?)\[QUESTIONS_END\]', response, re.DOTALL | re.IGNORECASE)
        if questions_match:
            questions_block = questions_match.group(1).strip()
            q_matches = re.findall(r'Q\d+:\s*(.+?)(?=Q\d+:|$)', questions_block, re.DOTALL)
            questions.extend([q.strip() for q in q_matches if self._validate_question(q.strip())])
        
        # Способ 2: Нумерованный список
        if not questions:
            lines = response.split('\n')
            for line in lines:
                line = line.strip()
                if re.match(r'^\d+\.', line) and '?' in line:
                    question = re.sub(r'^\d+\.\s*', '', line)
                    if self._validate_question(question):
                        questions.append(question)
        
        # Ограничиваем количество вопросов по типу расклада
        max_questions = {
            'single_card': 2,
            'three_cards': 3,
            'horseshoe': 4,
            'love_triangle': 5,
            'celtic_cross': 6,
            'week_forecast': 4,
            'year_wheel': 5
        }
        
        limit = max_questions.get(self.spread_type, 3)
        return questions[:limit]

    def _validate_question(self, question: str) -> bool:
        """Валидирует отдельный вопрос"""
        if not question or len(question.strip()) < 10:
            return False
        if len(question) > 500:
            return False
        if '?' not in question:
            return False
        return True

    def _parse_final_interpretation(self, response: str) -> str:
        """Парсит финальную интерпретацию из ответа"""
        # Ищем интерпретацию между маркерами
        interpretation_match = re.search(
            r'\[INTERPRETATION_START\](.*?)\[INTERPRETATION_END\]', 
            response, 
            re.DOTALL | re.IGNORECASE
        )
        
        if interpretation_match:
            return interpretation_match.group(1).strip()
        else:
            # Если маркеры не найдены, возвращаем весь ответ
            logger.warning("⚠️ Не удалось выделить интерпретацию, возвращаем полный ответ")
            return response.strip()

    def get_context_debug_info(self) -> Dict[str, Any]:
        """Возвращает отладочную информацию о контексте"""
        return {
            'current_stage': self.current_stage.name,
            'message_count': len(self.context.messages),
            'total_length': sum(len(msg.get('content', '')) for msg in self.context.messages),
            'has_questions': len(self.llm_questions) > 0,
            'has_answers': len(self.llm_answers) > 0
        }

    # ==================== АДАПТЕРЫ ДЛЯ ОБРАТНОЙ СОВМЕСТИМОСТИ ====================

    async def run_full_interpretation(self, user_data: Dict, spread_data: Dict, 
                                    preliminary_answers: List[str]) -> Tuple[List[str], Optional[str]]:
        """
        Адаптер для совместимости со старым интерфейсом
        Возвращает (вопросы, None) если нужны уточнения, или ([], интерпретация) если готово
        """
        # Настраиваем данные
        self.setup_spread(
            spread_type=spread_data['spread_type'],
            selected_cards=spread_data['cards'],
            spread_config={'card_meanings': ['Позиция расклада']},
            user_name=user_data['name'],
            user_age=user_data['age'],
            magic_number=1
        )
        
        # Выполняем только этап 1 - генерацию вопросов
        questions = await self.stage_1_generate_questions(preliminary_answers)
        
        return questions, None  # Возвращаем вопросы, интерпретация пока None

    async def continue_interpretation(self, user_answers: List[str]) -> str:
        """
        Продолжает интерпретацию после получения ответов пользователя
        Выполняет этапы 2, 3, 4 последовательно
        """
        logger.info("Продолжаем многоэтапную интерпретацию...")
        
        # Этап 2: Анализ контекста (25% → 50%)
        await self.stage_2_context_analysis(user_answers)
        
        # Этап 3: Глубокий синтез (50% → 75%) 
        await self.stage_3_deep_synthesis()
        
        # Этап 4: Финальная интерпретация (75% → 100%)
        final_interpretation = await self.stage_4_final_response()
        
        logger.info("🎯 Многоэтапная интерпретация завершена!")
        return final_interpretation

    # Остальные методы для совместимости
    async def add_question_answers(self, answers: List[str]):
        """Добавляет ответы пользователя (совместимость)"""
        self.llm_answers = answers

    async def generate_context_analysis(self):
        """Заглушка для совместимости"""
        pass

    async def generate_synthesis(self):
        """Заглушка для совместимости"""
        pass

    async def generate_final_interpretation(self) -> str:
        """Заглушка для совместимости"""
        return "Интерпретация готова"