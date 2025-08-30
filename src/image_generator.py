"""
Движок генерации изображений раскладов Таро
"""
import os
from typing import List, Dict, Optional, Tuple
from PIL import Image, ImageDraw
import io


class ImageCache:
    """Кэш для изображений карт и фонов"""
    
    def __init__(self):
        self._backgrounds = {}
        self._cards = {}
    
    def get_background(self, background_id: int) -> Optional[Image.Image]:
        """Получить фон из кэша"""
        return self._backgrounds.get(background_id)
    
    def cache_background(self, background_id: int, image: Image.Image):
        """Сохранить фон в кэш"""
        self._backgrounds[background_id] = image
    
    def get_card(self, card_path: str) -> Optional[Image.Image]:
        """Получить карту из кэша"""
        return self._cards.get(card_path)
    
    def cache_card(self, card_path: str, image: Image.Image):
        """Сохранить карту в кэш"""
        self._cards[card_path] = image
    
    def clear(self):
        """Очистить кэш"""
        self._backgrounds.clear()
        self._cards.clear()


# Глобальный кэш изображений
_image_cache = ImageCache()


def load_background(background_id: int, backgrounds_dir: str = None) -> Image.Image:
    """
    Загрузка фона для расклада
    
    :param background_id: Номер фона (1-7)
    :param backgrounds_dir: Папка с фонами
    :return: PIL Image объект фона
    """
    if not 1 <= background_id <= 7:
        raise ValueError(f"background_id должен быть от 1 до 7, получен: {background_id}")
    
    # Проверяем кэш
    cached = _image_cache.get_background(background_id)
    if cached is not None:
        return cached.copy()
    
    if backgrounds_dir is None:
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        backgrounds_dir = os.path.join(project_root, 'assets', 'backgrounds for spreads')
    
    background_file = f"back{background_id}.png"
    background_path = os.path.join(backgrounds_dir, background_file)
    
    if not os.path.exists(background_path):
        raise FileNotFoundError(f"Фон не найден: {background_path}")
    
    try:
        background = Image.open(background_path)
        
        # Проверяем размер фона
        if background.size != (1024, 1024):
            print(f"⚠️ Предупреждение: размер фона {background.size}, ожидался (1024, 1024)")
        
        # Кэшируем и возвращаем копию
        _image_cache.cache_background(background_id, background.copy())
        return background
        
    except Exception as e:
        raise RuntimeError(f"Ошибка загрузки фона {background_file}: {e}")


def load_card_image(card_path: str) -> Image.Image:
    """
    Загрузка изображения карты
    
    :param card_path: Полный путь к изображению карты
    :return: PIL Image объект карты
    """
    # Проверяем кэш
    cached = _image_cache.get_card(card_path)
    if cached is not None:
        return cached.copy()
    
    if not os.path.exists(card_path):
        raise FileNotFoundError(f"Изображение карты не найдено: {card_path}")
    
    try:
        card = Image.open(card_path)
        
        # Проверяем размер карты
        if card.size != (350, 600):
            print(f"⚠️ Предупреждение: размер карты {card.size}, ожидался (350, 600)")
        
        # Кэшируем и возвращаем копию
        _image_cache.cache_card(card_path, card.copy())
        return card
        
    except Exception as e:
        raise RuntimeError(f"Ошибка загрузки карты {os.path.basename(card_path)}: {e}")


def scale_image(image: Image.Image, scale_factor: float) -> Image.Image:
    """
    Масштабирование изображения
    
    :param image: PIL Image для масштабирования
    :param scale_factor: Коэффициент масштабирования
    :return: Масштабированное изображение
    """
    if scale_factor <= 0:
        raise ValueError(f"Коэффициент масштабирования должен быть > 0, получен: {scale_factor}")
    
    original_width, original_height = image.size
    new_width = int(original_width * scale_factor)
    new_height = int(original_height * scale_factor)
    
    if new_width <= 0 or new_height <= 0:
        raise ValueError(f"Результирующий размер некорректен: {new_width}x{new_height}")
    
    return image.resize((new_width, new_height), Image.LANCZOS)


def rotate_image(image: Image.Image, rotation: float) -> Image.Image:
    """
    Поворот изображения с прозрачным фоном
    
    :param image: PIL Image для поворота
    :param rotation: Угол поворота в градусах (по часовой стрелке)
    :return: Повёрнутое изображение с прозрачным фоном
    """
    if rotation == 0:
        return image
    
    # Конвертируем в RGBA если нужно для поддержки прозрачности
    if image.mode != 'RGBA':
        image = image.convert('RGBA')
    
    # Поворачиваем изображение с прозрачным фоном
    # fillcolor=(0,0,0,0) = полностью прозрачный
    rotated = image.rotate(-rotation, expand=True, fillcolor=(0, 0, 0, 0))
    
    return rotated


def place_card_on_background(
    background: Image.Image,
    card: Image.Image,
    x: int,
    y: int,
    rotation: float = 0,
    scale: float = 1.0
) -> Image.Image:
    """
    Размещение карты на фоне
    
    :param background: Фоновое изображение
    :param card: Изображение карты
    :param x: X координата центра карты (в рабочей области)
    :param y: Y координата центра карты (в рабочей области)
    :param rotation: Угол поворота карты в градусах
    :param scale: Коэффициент масштабирования
    :return: Фон с размещённой картой
    """
    # Создаём копию фона для работы
    result = background.copy()
    
    # Масштабируем карту
    if scale != 1.0:
        card = scale_image(card, scale)
    
    # Поворачиваем карту если нужно
    if rotation != 0:
        card = rotate_image(card, rotation)
    
    # Преобразуем координаты из рабочей области в абсолютные координаты фона
    # Рабочая область 512x512 начинается с (256, 256) на фоне 1024x1024
    abs_x = x + 256  # Сдвиг на начало рабочей области по X
    abs_y = y + 256  # Сдвиг на начало рабочей области по Y
    
    # Вычисляем позицию для вставки (левый верхний угол карты)
    card_width, card_height = card.size
    paste_x = abs_x - card_width // 2   # x - это центр карты
    paste_y = abs_y - card_height // 2  # y - это центр карты
    
    # Размещаем карту на фоне
    try:
        # Проверяем, что карта умещается на фоне
        if paste_x < 0 or paste_y < 0 or paste_x + card_width > 1024 or paste_y + card_height > 1024:
            print(f"⚠️ Предупреждение: карта частично выходит за границы фона")
            print(f"   Позиция: ({paste_x}, {paste_y}), размер карты: {card_width}x{card_height}")
        
        # Если у карты есть прозрачность (альфа-канал), используем её для корректного наложения
        if card.mode in ('RGBA', 'LA') or 'transparency' in card.info:
            result.paste(card, (paste_x, paste_y), card)
        else:
            result.paste(card, (paste_x, paste_y))
            
    except Exception as e:
        raise RuntimeError(f"Ошибка размещения карты на позиции ({paste_x}, {paste_y}): {e}")
    
    return result


def generate_spread_image(
    background_id: int,
    cards: List[Dict],
    layout_config: Dict
) -> Image.Image:
    """
    Основная функция генерации изображения расклада
    
    :param background_id: Номер фона (1-7)
    :param cards: Список карт от card_manager
    :param layout_config: Конфигурация расклада с позициями
    :return: PIL Image объект готового расклада
    """
    if not cards:
        raise ValueError("Список карт не может быть пустым")
    
    if not layout_config:
        raise ValueError("Конфигурация расклада не может быть пустой")
    
    # Получаем параметры из конфигурации
    positions = layout_config.get('positions', [])
    scale_factor = layout_config.get('scale', 1.0)
    
    if len(cards) != len(positions):
        raise ValueError(f"Количество карт ({len(cards)}) не совпадает с количеством позиций ({len(positions)})")
    
    print(f"🎨 Генерируем расклад: {len(cards)} карт, фон {background_id}, scale {scale_factor}")
    
    # Загружаем фон
    try:
        background = load_background(background_id)
    except Exception as e:
        raise RuntimeError(f"Ошибка загрузки фона: {e}")
    
    # Размещаем карты на фоне
    result = background
    
    for i, (card, position) in enumerate(zip(cards, positions)):
        try:
            # Получаем путь к изображению карты
            try:
                from .card_manager import TarotDeck
            except ImportError:
                from card_manager import TarotDeck
            deck = TarotDeck()  # Временное решение для получения пути к карте
            card_path = deck.get_card_image_path(card)
            
            # Загружаем изображение карты
            card_image = load_card_image(card_path)
            
            # Получаем позицию и параметры
            x = position.get('x', 256)
            y = position.get('y', 256)
            rotation = position.get('rotation', 0)
            
            print(f"   Размещаем карту {i+1}: {card['name']} на ({x}, {y}), поворот {rotation}°")
            
            # Размещаем карту на фоне
            result = place_card_on_background(
                result, card_image, x, y, rotation, scale_factor
            )
            
        except Exception as e:
            raise RuntimeError(f"Ошибка размещения карты {i+1} ({card.get('name', 'unknown')}): {e}")
    
    print(f"✅ Расклад сгенерирован успешно!")
    return result


def save_image_optimized(image: Image.Image, file_path: str, max_size_mb: float = 2.0) -> int:
    """
    Сохранение изображения с оптимизацией размера файла
    
    :param image: PIL Image для сохранения
    :param file_path: Путь для сохранения
    :param max_size_mb: Максимальный размер файла в МБ
    :return: Размер сохранённого файла в байтах
    """
    # Пробуем разные уровни качества для достижения нужного размера
    quality_levels = [95, 90, 85, 80, 75, 70]
    
    for quality in quality_levels:
        # Создаём буфер для тестирования размера
        buffer = io.BytesIO()
        
        # Конвертируем в RGB если нужно (для JPEG сохранения)
        save_image = image
        if image.mode in ('RGBA', 'P'):
            # Создаём белый фон для прозрачных изображений
            background = Image.new('RGB', image.size, (255, 255, 255))
            if image.mode == 'P':
                image = image.convert('RGBA')
            background.paste(image, mask=image.split()[-1] if image.mode == 'RGBA' else None)
            save_image = background
        
        # Определяем формат по расширению
        format_type = 'PNG' if file_path.lower().endswith('.png') else 'JPEG'
        
        if format_type == 'PNG':
            save_image.save(buffer, format='PNG', optimize=True)
        else:
            save_image.save(buffer, format='JPEG', quality=quality, optimize=True)
        
        file_size = buffer.tell()
        max_bytes = max_size_mb * 1024 * 1024
        
        if file_size <= max_bytes or quality == quality_levels[-1]:
            # Сохраняем файл
            buffer.seek(0)
            with open(file_path, 'wb') as f:
                f.write(buffer.getvalue())
            
            size_mb = file_size / (1024 * 1024)
            print(f"💾 Изображение сохранено: {file_path}")
            print(f"📊 Размер файла: {size_mb:.2f} МБ (качество: {quality if format_type == 'JPEG' else 'PNG'})")
            return file_size
        
        buffer.close()
    
    return 0


# Тестовые функции
def test_single_card():
    """Тестовая генерация расклада с одной картой"""
    print("🧪 Генерация тестового изображения с одной картой...")
    
    try:
        # Импортируем необходимые модули
        try:
            from .card_manager import TarotDeck
        except ImportError:
            from card_manager import TarotDeck
        
        # Загружаем колоду и получаем The Fool
        deck = TarotDeck()
        all_cards = deck.cards
        
        # Ищем The Fool
        the_fool = None
        for card in all_cards:
            if card['name'] == 'The Fool':
                the_fool = card
                break
        
        if the_fool is None:
            raise ValueError("Карта 'The Fool' не найдена в колоде")
        
        # Конфигурация тестового расклада
        test_layout = {
            'scale': 0.4,
            'positions': [
                {'x': 256, 'y': 256, 'rotation': 0}  # Центр рабочей области
            ]
        }
        
        # Генерируем изображение
        result_image = generate_spread_image(
            background_id=1,
            cards=[the_fool],
            layout_config=test_layout
        )
        
        # Сохраняем результат
        output_path = "test_single_card.png"
        file_size = save_image_optimized(result_image, output_path)
        
        return output_path, file_size
        
    except Exception as e:
        print(f"❌ Ошибка генерации тестового изображения: {e}")
        raise


def clear_image_cache():
    """Очистка кэша изображений"""
    global _image_cache
    _image_cache.clear()
    print("🧹 Кэш изображений очищен")


class ImageGenerator:
    """
    Класс для генерации изображений раскладов Таро
    Обертка над функцией generate_spread_image для удобства использования
    """
    
    def __init__(self):
        """Инициализация генератора изображений"""
        pass
    
    def generate_spread_image(self, background_id: int, cards: List[Dict], 
                            positions: List[Dict], scale: float) -> bytes:
        """
        Генерирует изображение расклада и возвращает его как байты
        
        :param background_id: Номер фона (1-7)
        :param cards: Список карт от card_manager
        :param positions: Список позиций карт
        :param scale: Масштаб карт
        :return: Байты PNG изображения
        """
        # Формируем конфигурацию в ожидаемом формате
        layout_config = {
            'positions': positions,
            'scale': scale
        }
        
        # Генерируем изображение
        image = generate_spread_image(background_id, cards, layout_config)
        
        # Конвертируем в байты PNG
        buffer = io.BytesIO()
        
        # Убеждаемся что изображение в RGB для корректного сохранения
        if image.mode in ('RGBA', 'P'):
            # Создаём белый фон для прозрачных изображений  
            background = Image.new('RGB', image.size, (255, 255, 255))
            if image.mode == 'P':
                image = image.convert('RGBA')
            background.paste(image, mask=image.split()[-1] if image.mode == 'RGBA' else None)
            image = background
        
        # Сохраняем как PNG с оптимизацией
        image.save(buffer, format='PNG', optimize=True)
        
        return buffer.getvalue()


# Тестирование модуля
if __name__ == "__main__":
    print("🎨 Тестирование модуля image_generator.py")
    print("=" * 50)
    
    try:
        # Тестируем загрузку фона
        print("\n1️⃣ Тестирование загрузки фона...")
        bg = load_background(1)
        print(f"   ✅ Фон загружен: {bg.size}, режим: {bg.mode}")
        
        # Тестируем загрузку карты
        print("\n2️⃣ Тестирование загрузки карты...")
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        card_path = os.path.join(project_root, 'assets', 'cards', 'm00.jpg')
        card = load_card_image(card_path)
        print(f"   ✅ Карта загружена: {card.size}, режим: {card.mode}")
        
        # Тестируем масштабирование
        print("\n3️⃣ Тестирование масштабирования...")
        scaled = scale_image(card, 0.5)
        print(f"   ✅ Карта масштабирована: {card.size} → {scaled.size}")
        
        # Тестируем поворот
        print("\n4️⃣ Тестирование поворота...")
        rotated = rotate_image(card, 45)
        print(f"   ✅ Карта повёрнута на 45°: {card.size} → {rotated.size}")
        
        # Генерируем тестовое изображение
        print("\n5️⃣ Генерация тестового изображения...")
        test_path, test_size = test_single_card()
        
        print(f"\n✅ Все тесты завершены успешно!")
        print(f"📁 Тестовое изображение: {test_path}")
        print(f"📊 Размер файла: {test_size / 1024:.1f} КБ")
        
    except Exception as e:
        print(f"\n❌ Ошибка при тестировании: {e}")
        import traceback
        traceback.print_exc()