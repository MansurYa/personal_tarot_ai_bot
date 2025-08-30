"""
Модуль для работы с предварительными вопросами для раскладов Таро.
Загружает вопросы из JSON файла и предоставляет интерфейс для их использования.
"""

import json
import os
from typing import Dict, List, Optional
from dataclasses import dataclass


@dataclass
class Question:
    """Класс для представления вопроса"""
    id: int
    text: str
    hint: str
    expected_length: str


@dataclass 
class SpreadQuestions:
    """Класс для представления вопросов для конкретного расклада"""
    name: str
    estimated_time: str
    questions: List[Question]


class QuestionManager:
    """Класс для управления системой предварительных вопросов"""
    
    def __init__(self, questions_file_path: str = None):
        """
        Инициализация менеджера вопросов
        
        Args:
            questions_file_path: Путь к JSON файлу с вопросами
        """
        if questions_file_path is None:
            # Получаем путь к файлу относительно расположения этого модуля
            current_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(current_dir)
            questions_file_path = os.path.join(project_root, 'assets', 'spread_questions.json')
        
        self.questions_file_path = questions_file_path
        self.questions_data = None
        self.length_descriptions = None
        self._load_questions()
    
    def _load_questions(self) -> None:
        """Загружает вопросы из JSON файла"""
        try:
            with open(self.questions_file_path, 'r', encoding='utf-8') as file:
                data = json.load(file)
                self.questions_data = data.get('spread_questions', {})
                self.length_descriptions = data.get('length_descriptions', {})
        except FileNotFoundError:
            raise FileNotFoundError(f"Файл с вопросами не найден: {self.questions_file_path}")
        except json.JSONDecodeError:
            raise ValueError(f"Некорректный JSON файл: {self.questions_file_path}")
    
    def get_questions_for_spread(self, spread_type: str) -> Optional[SpreadQuestions]:
        """
        Получает вопросы для конкретного типа расклада
        
        Args:
            spread_type: Тип расклада (single_card, three_cards, etc.)
            
        Returns:
            SpreadQuestions или None если расклад не найден
        """
        if spread_type not in self.questions_data:
            return None
        
        spread_data = self.questions_data[spread_type]
        questions = []
        
        for q_data in spread_data.get('questions', []):
            question = Question(
                id=q_data['id'],
                text=q_data['text'],
                hint=q_data['hint'],
                expected_length=q_data['expected_length']
            )
            questions.append(question)
        
        return SpreadQuestions(
            name=spread_data['name'],
            estimated_time=spread_data['estimated_time'],
            questions=questions
        )
    
    def get_available_spreads(self) -> List[str]:
        """Возвращает список доступных типов раскладов"""
        return list(self.questions_data.keys())
    
    def get_length_description(self, length_type: str) -> Optional[str]:
        """
        Получает описание для типа длины ответа
        
        Args:
            length_type: Тип длины (short, medium, long)
            
        Returns:
            Описание или None если не найдено
        """
        return self.length_descriptions.get(length_type)
    
    def validate_spread_type(self, spread_type: str) -> bool:
        """
        Проверяет, существует ли указанный тип расклада
        
        Args:
            spread_type: Тип расклада для проверки
            
        Returns:
            True если расклад существует, False иначе
        """
        return spread_type in self.questions_data
    
    def get_question_count(self, spread_type: str) -> int:
        """
        Возвращает количество вопросов для указанного расклада
        
        Args:
            spread_type: Тип расклада
            
        Returns:
            Количество вопросов или 0 если расклад не найден
        """
        if spread_type not in self.questions_data:
            return 0
        return len(self.questions_data[spread_type].get('questions', []))


# Глобальный экземпляр для использования в других модулях
question_manager = QuestionManager()


def get_questions_for_spread(spread_type: str) -> Optional[SpreadQuestions]:
    """
    Удобная функция для получения вопросов для расклада
    
    Args:
        spread_type: Тип расклада
        
    Returns:
        SpreadQuestions или None
    """
    return question_manager.get_questions_for_spread(spread_type)


def validate_spread_type(spread_type: str) -> bool:
    """
    Удобная функция для проверки типа расклада
    
    Args:
        spread_type: Тип расклада
        
    Returns:
        True если расклад существует
    """
    return question_manager.validate_spread_type(spread_type)


# Маппинг типов раскладов для совместимости с существующим кодом
SPREAD_TYPE_MAPPING = {
    'single_card': 'single_card',
    'three_cards': 'three_cards', 
    'celtic_cross': 'celtic_cross',
    'horseshoe': 'horseshoe',
    'love_triangle': 'love_triangle',
    'week_forecast': 'week_forecast',
    'year_wheel': 'year_wheel'
}


def get_spread_type_from_callback(callback_data: str) -> Optional[str]:
    """
    Преобразует callback_data в тип расклада
    
    Args:
        callback_data: Данные из callback кнопки
        
    Returns:
        Тип расклада или None
    """
    # Извлекаем тип расклада из callback_data вида 'spread_single_card' 
    if callback_data.startswith('spread_'):
        spread_name = callback_data.replace('spread_', '')
        return SPREAD_TYPE_MAPPING.get(spread_name)
    return None


if __name__ == "__main__":
    # Тестирование модуля
    try:
        manager = QuestionManager()
        print("Доступные расклады:", manager.get_available_spreads())
        
        # Тестируем каждый расклад
        for spread_type in manager.get_available_spreads():
            questions = manager.get_questions_for_spread(spread_type)
            if questions:
                print(f"\n=== {questions.name} ===")
                print(f"Время: {questions.estimated_time}")
                print(f"Количество вопросов: {len(questions.questions)}")
                
                for question in questions.questions:
                    print(f"  {question.id}. {question.text}")
                    print(f"     Подсказка: {question.hint}")
                    print(f"     Длина ответа: {question.expected_length}")
                    
        print(f"\nОписания длины ответов:")
        for length_type, description in manager.length_descriptions.items():
            print(f"  {length_type}: {description}")
            
    except Exception as e:
        print(f"Ошибка при тестировании: {e}")