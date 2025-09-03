"""
ИСПРАВЛЕННАЯ LLM сессия с правильным накоплением контекста
"""

import re
import json
import logging
from typing import Dict, List, Optional, Tuple
from .openrouter_client import MessageContext
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


class FixedLLMSession:
    """
    ИСПРАВЛЕННАЯ LLM сессия с правильной архитектурой:
    - Все промпты добавляются в единый контекст
    - ОДИН финальный запрос в конце
    - LLM видит всю историю включая все инструкции
    """
    
    def __init__(self, prompt_manager: PromptManager, model_name: str = None):
        self.prompt_manager = prompt_manager
        self.config = load_config()
        
        # Создаем MessageContext с mode=2 (критически важно!)
        self.context = MessageContext(task_prompt=None)
        
        # Используем переданную модель или берем из конфига
        if model_name is None:
            model_name = self.config.get("model_name", "deepseek/deepseek-chat-v3-0324:free")
        
        # Параметры для запроса
        self.model_name = model_name
        self.api_key = self.config.get("openrouter_api_key")
        self.max_tokens = self.config.get("max_response_tokens", 8000)
        self.temperature = self.config.get("temperature", 0.3)
        
        # Состояние сессии
        self.current_stage = None
        self.user_data = {}
        self.spread_data = {}
        self.generated_questions = []
        
    def setup_spread(self, spread_type: str, selected_cards: List[Dict], 
                    spread_config: Dict, user_name: str, user_age: int, 
                    magic_number: int):
        """Настройка данных расклада"""
        self.spread_data = {
            'spread_type': spread_type,
            'selected_cards': selected_cards,
            'spread_config': spread_config,
            'user_name': user_name,
            'user_age': user_age,
            'magic_number': magic_number
        }
        
        self.user_data = {
            'name': user_name,
            'age': user_age,
            'magic_number': magic_number
        }
    
    def add_spread_context(self, spread_type: str):
        """Добавляет контекст расклада в сессию"""
        context_prompt = self.prompt_manager.get_spread_context_prompt(spread_type)
        self.context.add_user_message(context_prompt)
        self.current_stage = InterpretationStage.SPREAD_CONTEXT
        logger.info(f"Добавлен контекст расклада: {spread_type}")
    
    def build_complete_context(self, preliminary_answers: List[str], 
                              additional_answers: List[str] = None) -> bool:
        """
        КЛЮЧЕВОЙ МЕТОД: Строит полный контекст со ВСЕМИ промптами
        Это и есть правильная реализация по LLM_algorithm.md!
        """
        try:
            # 1. Системная персона (01_system_persona.md)
            system_prompt = self.prompt_manager.get_system_persona(
                name=self.user_data['name'],
                age=self.user_data['age']
            )
            self.context = MessageContext(task_prompt=system_prompt)
            logger.info("1️⃣ Добавлен системный промпт")
            
            # 2. Контекст расклада (02_*_context.md)
            spread_type = self.spread_data.get('spread_type', '')
            spread_prompt = self.prompt_manager.get_spread_context(
                spread_type=spread_type,
                selected_cards=self.spread_data['selected_cards'],
                positions=self.spread_data['spread_config'].get('card_meanings', [])
            )
            self.context.add_user_message(spread_prompt)
            logger.info(f"2️⃣ Добавлен контекст расклада: {spread_type}")
            
            # Добавляем предварительные ответы
            if preliminary_answers:
                answers_text = "\\n".join([f"{i+1}. {answer}" for i, answer in enumerate(preliminary_answers)])
                self.context.add_user_message(f"ПРЕДВАРИТЕЛЬНЫЕ ОТВЕТЫ ПОЛЬЗОВАТЕЛЯ:\\n{answers_text}")
                logger.info("📝 Добавлены предварительные ответы")
            
            # 3. Психологический анализ и вопросы (03_psychological_analysis_questions.md) 
            analysis_prompt = self.prompt_manager.get_psychological_analysis_prompt(
                user_answers=preliminary_answers or []
            )
            self.context.add_user_message(analysis_prompt)
            logger.info("3️⃣ Добавлен промпт психологического анализа")
            
            # Добавляем дополнительные ответы если есть
            if additional_answers:
                additional_text = "\\n".join([f"{i+1}. {answer}" for i, answer in enumerate(additional_answers)])
                self.context.add_user_message(f"ДОПОЛНИТЕЛЬНЫЕ ОТВЕТЫ НА УТОЧНЯЮЩИЕ ВОПРОСЫ:\\n{additional_text}")
                logger.info("📝 Добавлены дополнительные ответы")
            
            # 4. Анализ контекста и карт (04_context_analysis_and_card_interpretation.md)
            context_analysis_prompt = self.prompt_manager.get_context_analysis_prompt()
            self.context.add_user_message(context_analysis_prompt)
            logger.info("4️⃣ Добавлен промпт анализа контекста")
            
            # 5. Глубокий синтез (05_deep_synthesis_and_story_planning.md)
            synthesis_prompt = self.prompt_manager.get_synthesis_prompt()
            self.context.add_user_message(synthesis_prompt)
            logger.info("5️⃣ Добавлен промпт синтеза")
            
            # 6. Финальный ответ (06_final_user_response.md)
            final_prompt = self.prompt_manager.get_final_response_prompt()
            self.context.add_user_message(final_prompt)
            logger.info("6️⃣ Добавлен промпт финального ответа")
            
            return True
            
        except Exception as e:
            logger.error(f"Ошибка при построении контекста: {e}")
            return False
    
    async def generate_complete_interpretation(self) -> Optional[str]:
        """
        ЕДИНСТВЕННЫЙ запрос к LLM с полным контекстом!
        Это правильная реализация - LLM видит ВСЕ промпты включая требования к краткости!
        """
        try:
            messages = self.context.get_message_history()
            
            # Логируем для отладки 
            logger.info(f"Отправляем запрос с {len(messages)} сообщениями в контексте")
            
            # Проверяем что требование к краткости присутствует
            full_context = "\\n".join([msg['content'][0]['text'] for msg in messages])
            has_brevity = "Требование к краткости" in full_context
            logger.info(f"Требование к краткости в контексте: {has_brevity}")
            
            from .openrouter_client import send_request
            response = await send_request(
                messages=messages,
                model=self.model_name,
                api_key=self.api_key,
                max_tokens=self.max_tokens,
                temperature=self.temperature
            )
            
            self.current_stage = InterpretationStage.FINAL_RESPONSE
            logger.info("🎯 Полная интерпретация сгенерирована за ОДИН запрос!")
            
            # Извлекаем финальную интерпретацию
            cleaned_response = self._extract_final_interpretation(response)
            return cleaned_response
            
        except Exception as e:
            logger.error(f"Ошибка при генерации полной интерпретации: {e}")
            return None
    
    def _extract_final_interpretation(self, response: str) -> str:
        """Извлекает финальную интерпретацию из ответа LLM"""
        try:
            # Способ 1: Ищем маркеры [INTERPRETATION_START] и [INTERPRETATION_END]
            interpretation_match = re.search(r'\\[INTERPRETATION_START\\](.*?)\\[INTERPRETATION_END\\]', 
                                           response, re.DOTALL | re.IGNORECASE)
            if interpretation_match:
                cleaned = interpretation_match.group(1).strip()
                logger.info("✅ Интерпретация извлечена по маркерам")
                return cleaned
            
            # Способ 2: Ищем последний блок после финального промпта
            lines = response.split('\\n')
            interpretation_lines = []
            capturing = False
            
            for line in lines:
                if 'INTERPRETATION_START' in line or capturing:
                    capturing = True
                    if 'INTERPRETATION_END' in line:
                        break
                    interpretation_lines.append(line)
            
            if interpretation_lines:
                result = '\\n'.join(interpretation_lines).strip()
                # Очищаем от возможных маркеров
                result = re.sub(r'\\[INTERPRETATION_(START|END)\\]', '', result).strip()
                logger.info("✅ Интерпретация извлечена по блокам")
                return result
            
            # Способ 3: Берем последние 1000-2000 символов как интерпретацию
            if len(response) > 1000:
                result = response[-2000:].strip()
                logger.info("⚠️ Интерпретация взята как последний блок")
                return result
            
            # Способ 4: Возвращаем весь ответ
            logger.warning("⚠️ Не удалось выделить интерпретацию, возвращаем полный ответ")
            return response.strip()
            
        except Exception as e:
            logger.error(f"Ошибка при извлечении интерпретации: {e}")
            return response.strip()
    
    def get_context_debug_info(self) -> Dict:
        """Возвращает отладочную информацию о контексте"""
        messages = self.context.get_message_history()
        full_context = "\\n".join([msg['content'][0]['text'] for msg in messages])
        
        return {
            'message_count': len(messages),
            'total_length': len(full_context),
            'has_brevity_instruction': 'Требование к краткости' in full_context,
            'has_system_persona': '01_system_persona' in full_context,
            'has_spread_context': '02_' in full_context and '_context' in full_context,
            'context_preview': full_context[:500] + '...' if len(full_context) > 500 else full_context
        }