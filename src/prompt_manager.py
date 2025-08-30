"""
Менеджер промптов для LLM интерпретации раскладов Таро
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Optional

class PromptManager:
    """Менеджер для загрузки и форматирования промптов"""
    
    def __init__(self, prompts_dir: str, tarot_cards_file: str):
        self.prompts_dir = prompts_dir
        self.tarot_cards_file = tarot_cards_file
        self._prompt_cache = {}
        self._cards_data = None
    
    def _load_prompt(self, filename: str) -> str:
        """Загружает промпт из файла с кешированием"""
        if filename not in self._prompt_cache:
            filepath = os.path.join(self.prompts_dir, filename)
            with open(filepath, 'r', encoding='utf-8') as f:
                self._prompt_cache[filename] = f.read()
        return self._prompt_cache[filename]
    
    def _load_cards_data(self):
        """Загружает данные о картах"""
        if self._cards_data is None:
            with open(self.tarot_cards_file, 'r', encoding='utf-8') as f:
                self._cards_data = json.load(f)
    
    def get_system_persona(self, name: str, age: int) -> str:
        """Загружает системный промпт с подстановкой данных пользователя"""
        prompt = self._load_prompt('01_system_persona.md')
        current_date = datetime.now().strftime("%d %B %Y года")
        
        # Подставляем данные пользователя
        formatted_prompt = f"""Имя пользователя: {name}
Возраст: {age} лет
Текущая дата: {current_date}

{prompt}"""
        
        return formatted_prompt
    
    def get_spread_context(self, spread_type: str, selected_cards: List[Dict], positions: List[str]) -> str:
        """Загружает контекст конкретного расклада с картами"""
        filename = f"02_{spread_type}_context.md"
        prompt = self._load_prompt(filename)
        
        # Форматируем информацию о картах
        cards_info = self._format_cards_for_prompt(selected_cards, positions)
        
        formatted_prompt = f"""{prompt}

## ВЫПАВШИЕ КАРТЫ В ВАШЕМ РАСКЛАДЕ

{cards_info}"""
        
        return formatted_prompt
    
    def _format_cards_for_prompt(self, selected_cards: List[Dict], positions: List[str]) -> str:
        """Форматирует карты для промпта"""
        self._load_cards_data()
        cards_info = []
        
        for i, card in enumerate(selected_cards):
            position = positions[i] if i < len(positions) else f"Позиция {i+1}"
            
            # Находим полную информацию о карте
            card_data = self._find_card_by_name(card['name'])
            if not card_data:
                continue
                
            fortune_telling = " • ".join(card_data.get('fortune_telling', []))
            keywords = ", ".join(card_data.get('keywords', []))
            
            # Выбираем несколько значений из meanings для контекста
            light_meanings = card_data.get('meanings', {}).get('light', [])[:3]
            shadow_meanings = card_data.get('meanings', {}).get('shadow', [])[:3]
            
            card_info = f"""**{position}: {card['name']}**
• Предсказания: {fortune_telling}
• Ключевые слова: {keywords}
• Светлые аспекты: {" • ".join(light_meanings)}
• Теневые аспекты: {" • ".join(shadow_meanings)}"""
            
            cards_info.append(card_info)
        
        return "\n\n".join(cards_info)
    
    def _find_card_by_name(self, name: str) -> Optional[Dict]:
        """Находит карту по имени в данных"""
        if not self._cards_data:
            return None
            
        for card in self._cards_data.get('cards', []):
            if card.get('name') == name:
                return card
        return None
    
    def get_psychological_analysis_prompt(self, user_answers: List[str]) -> str:
        """Загружает промпт для психологического анализа с ответами пользователя"""
        prompt = self._load_prompt('03_psychological_analysis_questions.md')
        
        # Добавляем ответы пользователя
        if user_answers:
            answers_text = ""
            for i, answer in enumerate(user_answers, 1):
                answers_text += f"\nВопрос {i}: {answer}"
            
            formatted_prompt = f"""{prompt}

## ОТВЕТЫ ПОЛЬЗОВАТЕЛЯ НА ПРЕДВАРИТЕЛЬНЫЕ ВОПРОСЫ
{answers_text}

Используйте эти ответы для глубокого понимания ситуации пользователя."""
        else:
            formatted_prompt = prompt
        
        return formatted_prompt
    
    def get_context_analysis_prompt(self) -> str:
        """Загружает промпт для анализа контекста и интерпретации карт"""
        return self._load_prompt('04_context_analysis_and_card_interpretation.md')
    
    def get_synthesis_prompt(self) -> str:
        """Загружает промпт для глубокого синтеза и планирования рассказа"""
        return self._load_prompt('05_deep_synthesis_and_story_planning.md')
    
    def get_final_response_prompt(self) -> str:
        """Загружает промпт для финального ответа пользователю"""
        return self._load_prompt('06_final_user_response.md')
    
    def format_user_answers(self, questions: List[str], answers: List[str]) -> str:
        """Форматирует вопросы и ответы пользователя"""
        formatted = []
        for i, (question, answer) in enumerate(zip(questions, answers), 1):
            formatted.append(f"Вопрос {i}: {question}")
            formatted.append(f"Ответ: {answer}")
            formatted.append("")
        
        return "\n".join(formatted)