"""
Менеджер карт Таро - загрузка, выбор и управление колодой
"""
import json
import random
import os
from typing import List, Dict, Optional


class TarotDeck:
    """Класс для работы с колодой карт Таро"""
    
    def __init__(self, cards_file_path: str = None):
        """
        Инициализация колоды Таро
        
        :param cards_file_path: Путь к файлу с данными карт
        """
        if cards_file_path is None:
            # Путь по умолчанию относительно корня проекта
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            cards_file_path = os.path.join(project_root, 'assets', 'tarot-cards-images-info-ru.json')
        
        self.cards_file_path = cards_file_path
        self._cards = []
        self._load_cards()
    
    def _load_cards(self):
        """Загрузка данных карт из JSON файла"""
        try:
            if not os.path.exists(self.cards_file_path):
                raise FileNotFoundError(f"Файл с картами не найден: {self.cards_file_path}")
            
            with open(self.cards_file_path, 'r', encoding='utf-8') as file:
                data = json.load(file)
            
            # Валидация структуры JSON
            if not isinstance(data, dict):
                raise ValueError("JSON файл должен содержать объект")
            
            if 'cards' not in data:
                raise ValueError("JSON файл должен содержать массив 'cards'")
            
            if not isinstance(data['cards'], list):
                raise ValueError("Поле 'cards' должно быть массивом")
            
            self._cards = data['cards']
            
            # Проверяем что загружено правильное количество карт
            if len(self._cards) != 78:
                print(f"Предупреждение: загружено {len(self._cards)} карт вместо ожидаемых 78")
            
            # Валидация обязательных полей в каждой карте
            required_fields = ['name', 'number', 'arcana', 'suit', 'img']
            for i, card in enumerate(self._cards):
                for field in required_fields:
                    if field not in card:
                        raise ValueError(f"Карта {i}: отсутствует обязательное поле '{field}'")
            
            print(f"✅ Успешно загружено {len(self._cards)} карт Таро")
            
        except FileNotFoundError as e:
            raise FileNotFoundError(f"Не удалось найти файл с картами: {e}")
        except json.JSONDecodeError as e:
            raise ValueError(f"Ошибка чтения JSON файла: {e}")
        except Exception as e:
            raise RuntimeError(f"Ошибка загрузки карт: {e}")
    
    @property
    def cards(self) -> List[Dict]:
        """Получить список всех карт"""
        return self._cards.copy()  # Возвращаем копию для безопасности
    
    def get_card_by_index(self, index: int) -> Optional[Dict]:
        """
        Получить карту по индексу
        
        :param index: Индекс карты (0-77)
        :return: Словарь с данными карты или None если индекс неверный
        """
        if 0 <= index < len(self._cards):
            return self._cards[index].copy()
        return None
    
    def get_card_image_path(self, card: Dict, images_dir: str = None) -> str:
        """
        Получить путь к изображению карты
        
        :param card: Словарь с данными карты
        :param images_dir: Папка с изображениями (по умолчанию assets/cards)
        :return: Полный путь к файлу изображения
        """
        if images_dir is None:
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            images_dir = os.path.join(project_root, 'assets', 'cards')
        
        image_filename = card.get('img')
        if not image_filename:
            raise ValueError(f"У карты '{card.get('name', 'unknown')}' отсутствует поле 'img'")
        
        image_path = os.path.join(images_dir, image_filename)
        
        # Проверяем существование файла изображения
        if not os.path.exists(image_path):
            print(f"⚠️  Предупреждение: изображение не найдено: {image_path}")
        
        return image_path
    
    def get_cards_count(self) -> int:
        """Получить общее количество карт в колоде"""
        return len(self._cards)
    
    def get_major_arcana(self) -> List[Dict]:
        """Получить только карты Старших Арканов"""
        return [card for card in self._cards if card.get('arcana') == 'Major Arcana']
    
    def get_minor_arcana(self) -> List[Dict]:
        """Получить только карты Младших Арканов"""
        return [card for card in self._cards if card.get('arcana') == 'Minor Arcana']


def select_cards(deck: TarotDeck, count: int, magic_number: int, user_age: int = None, timestamp: int = None) -> List[Dict]:
    """
    Выбор случайных карт из колоды с использованием сложного seed
    
    :param deck: Экземпляр TarotDeck
    :param count: Количество карт для выбора
    :param magic_number: Магическое число от пользователя
    :param user_age: Возраст пользователя (опционально)
    :param timestamp: Временная метка в секундах (опционально)
    :return: Список выбранных карт (без повторений)
    """
    if not isinstance(deck, TarotDeck):
        raise TypeError("Параметр deck должен быть экземпляром TarotDeck")
    
    if count <= 0:
        raise ValueError("Количество карт должно быть больше 0")
    
    if count > deck.get_cards_count():
        raise ValueError(f"Нельзя выбрать {count} карт из колоды в {deck.get_cards_count()} карт")
    
    if not isinstance(magic_number, int):
        raise TypeError("Магическое число должно быть целым числом")
    
    # Формируем сложный seed
    if user_age is not None:
        # Seed: магическое число + возраст (без времени для стабильности)
        complex_seed = magic_number + user_age
        print(f"🎴 Выбрано {count} карт с комплексным seed: {magic_number} + {user_age} = {complex_seed}")
    else:
        # Простой seed только из магического числа (для обратной совместимости)
        complex_seed = magic_number
        print(f"🎴 Выбрано {count} карт с магическим числом {magic_number}")
    
    # Устанавливаем seed для воспроизводимости
    random.seed(complex_seed)
    
    # Получаем все карты и выбираем случайные без повторений
    all_cards = deck.cards
    selected_cards = random.sample(all_cards, count)
    
    return selected_cards


def format_card_info(card: Dict) -> str:
    """
    Форматирование информации о карте для отображения
    
    :param card: Словарь с данными карты
    :return: Отформатированная строка с названием и арканой
    """
    if not isinstance(card, dict):
        raise TypeError("Карта должна быть словарём")
    
    name = card.get('name', 'Unknown Card')
    arcana = card.get('arcana', 'Unknown Arcana')
    
    return f"{name} ({arcana})"


def validate_card_images(deck: TarotDeck, images_dir: str = None) -> Dict:
    """
    Проверка существования всех файлов изображений карт
    
    :param deck: Экземпляр TarotDeck
    :param images_dir: Папка с изображениями
    :return: Словарь с результатами проверки
    """
    if images_dir is None:
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        images_dir = os.path.join(project_root, 'assets', 'cards')
    
    results = {
        'total_cards': deck.get_cards_count(),
        'existing_images': 0,
        'missing_images': 0,
        'missing_files': []
    }
    
    for card in deck.cards:
        image_path = deck.get_card_image_path(card, images_dir)
        if os.path.exists(image_path):
            results['existing_images'] += 1
        else:
            results['missing_images'] += 1
            results['missing_files'].append({
                'card': card.get('name'),
                'file': card.get('img'),
                'path': image_path
            })
    
    return results


# Тестирование модуля
if __name__ == "__main__":
    print("🔮 Тестирование модуля card_manager.py")
    print("=" * 50)
    
    try:
        # 1. Загрузка колоды
        print("\n1️⃣ Загрузка колоды...")
        deck = TarotDeck()
        print(f"   Загружено карт: {deck.get_cards_count()}")
        
        # Проверяем разделение на арканы
        major_arcana = deck.get_major_arcana()
        minor_arcana = deck.get_minor_arcana()
        print(f"   Старшие арканы: {len(major_arcana)}")
        print(f"   Младшие арканы: {len(minor_arcana)}")
        
        # 2. Выбор карт с magic_number=777
        print("\n2️⃣ Выбор 3 карт с магическим числом 777...")
        selected_cards_1 = select_cards(deck, 3, 777)
        
        print("   Выбранные карты:")
        for i, card in enumerate(selected_cards_1, 1):
            formatted = format_card_info(card)
            image_path = deck.get_card_image_path(card)
            print(f"   {i}. {formatted}")
            print(f"      Изображение: {os.path.basename(image_path)}")
        
        # 3. Проверка воспроизводимости
        print("\n3️⃣ Проверка воспроизводимости (тот же magic_number)...")
        selected_cards_2 = select_cards(deck, 3, 777)
        
        same_cards = True
        for card1, card2 in zip(selected_cards_1, selected_cards_2):
            if card1['name'] != card2['name']:
                same_cards = False
                break
        
        if same_cards:
            print("   ✅ При одинаковом магическом числе выбираются те же карты")
        else:
            print("   ❌ При одинаковом магическом числе выбираются разные карты")
        
        # 4. Проверка уникальности карт в раскладе
        print("\n4️⃣ Проверка уникальности карт в раскладе...")
        test_cards = select_cards(deck, 10, 123)  # Тестируем с 10 картами
        card_names = [card['name'] for card in test_cards]
        unique_names = set(card_names)
        
        if len(card_names) == len(unique_names):
            print("   ✅ Все карты в раскладе уникальны")
        else:
            duplicates = len(card_names) - len(unique_names)
            print(f"   ❌ Найдено {duplicates} повторяющихся карт")
        
        # 5. Тест получения карты по индексу
        print("\n5️⃣ Тест получения карты по индексу...")
        first_card = deck.get_card_by_index(0)
        last_card = deck.get_card_by_index(77)
        invalid_card = deck.get_card_by_index(100)
        
        print(f"   Первая карта (индекс 0): {format_card_info(first_card)}")
        print(f"   Последняя карта (индекс 77): {format_card_info(last_card)}")
        print(f"   Несуществующий индекс: {invalid_card}")
        
        # 6. Проверка изображений (выборочно)
        print("\n6️⃣ Проверка изображений карт...")
        image_results = validate_card_images(deck)
        print(f"   Всего карт: {image_results['total_cards']}")
        print(f"   Изображения найдены: {image_results['existing_images']}")
        print(f"   Изображения отсутствуют: {image_results['missing_images']}")
        
        if image_results['missing_images'] > 0:
            print("   Отсутствующие файлы:")
            for missing in image_results['missing_files'][:5]:  # Показываем первые 5
                print(f"     - {missing['card']}: {missing['file']}")
            if len(image_results['missing_files']) > 5:
                print(f"     ... и ещё {len(image_results['missing_files']) - 5}")
        
        print("\n🎉 Все тесты завершены!")
        
    except Exception as e:
        print(f"\n❌ Ошибка при тестировании: {e}")
        import traceback
        traceback.print_exc()