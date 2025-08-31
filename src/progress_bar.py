"""
Визуальный прогресс-бар для генерации интерпретации
"""

import asyncio
import logging
from typing import Optional
from telegram import Message
from telegram.ext import ContextTypes
from src.simple_state import add_message_to_delete

logger = logging.getLogger(__name__)

class TarotProgressBar:
    """Визуальный прогресс-бар с таро-тематикой"""
    
    # Этапы генерации интерпретации
    STAGES = {
        0: "🎴 Раскладываю карты...",
        25: "📖 Читаю значения карт...", 
        50: "🧠 Анализирую вашу ситуацию...",
        75: "✨ Формирую интерпретацию...",
        100: "🔮 Готово!"
    }
    
    def __init__(self, message: Message):
        self.message = message
        self.current_progress = 0
        self.is_cancelled = False
    
    def _generate_progress_visual(self, progress: int) -> str:
        """Генерирует визуальный прогресс-бар"""
        # Уменьшаем количество звезд в 2 раза для мобильных
        total_stars = 10  # было 20, стало 10
        filled_stars = int((progress / 100) * total_stars)
        empty_stars = total_stars - filled_stars
        
        # Создаем бар из звезд
        filled = "⭐" * filled_stars
        empty = "☆" * empty_stars
        progress_bar = filled + empty
        
        return progress_bar
    
    def _format_progress_message(self, progress: int) -> str:
        """Форматирует сообщение прогресс-бара"""
        stage_text = self.STAGES.get(progress, "Обрабатываю...")
        progress_visual = self._generate_progress_visual(progress)
        
        message = (
            f"🔮 **Генерирую интерпретацию вашего расклада**\n\n"
            f"{progress_visual} {progress}%\n\n"
            f"{stage_text}"
        )
        
        return message
    
    async def update_progress(self, progress: int, delay: float = 0.5) -> bool:
        """
        Обновляет прогресс-бар
        
        :param progress: Процент выполнения (0-100)
        :param delay: Задержка перед обновлением
        :return: True если успешно обновлено, False если отменено
        """
        if self.is_cancelled:
            return False
            
        if delay > 0:
            await asyncio.sleep(delay)
        
        try:
            # Ограничиваем прогресс
            progress = max(0, min(100, progress))
            self.current_progress = progress
            
            # Форматируем сообщение
            message_text = self._format_progress_message(progress)
            
            # Обновляем сообщение
            await self.message.edit_text(
                text=message_text,
                parse_mode='Markdown'
            )
            
            logger.info(f"Прогресс-бар обновлен: {progress}%")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка при обновлении прогресс-бара: {e}")
            return False
    
    async def complete(self, delay: float = 1.0) -> bool:
        """
        Завершает прогресс-бар и удаляет сообщение
        
        :param delay: Время показа завершения перед удалением
        :return: True если успешно завершено
        """
        try:
            # Показываем 100%
            await self.update_progress(100, delay=0)
            
            # Ждем немного перед удалением
            if delay > 0:
                await asyncio.sleep(delay)
            
            # Удаляем сообщение
            await self.message.delete()
            logger.info("Прогресс-бар завершен и удален")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка при завершении прогресс-бара: {e}")
            return False
    
    async def cancel(self) -> bool:
        """
        Отменяет прогресс-бар и удаляет сообщение
        
        :return: True если успешно отменено
        """
        try:
            self.is_cancelled = True
            await self.message.delete()
            logger.info("Прогресс-бар отменен и удален")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка при отмене прогресс-бара: {e}")
            return False
    
    def is_complete(self) -> bool:
        """Проверяет завершен ли прогресс"""
        return self.current_progress >= 100


class InterpretationProgress:
    """Управляет прогрессом интерпретации с привязкой к реальным этапам"""
    
    def __init__(self, progress_bar: TarotProgressBar):
        self.progress_bar = progress_bar
        self.current_stage = 0
        self.update_context = None  # Для создания новых прогресс-баров
        
    async def start_image_generation(self):
        """Этап 1: 0-25% - Генерация изображения расклада"""
        await self.progress_bar.update_progress(0)
        await asyncio.sleep(0.5)
        await self.progress_bar.update_progress(15)
        self.current_stage = 1
    
    async def complete_image_generation(self):
        """Завершение генерации изображения"""
        if self.current_stage == 1:
            await self.progress_bar.update_progress(25)
            await asyncio.sleep(0.3)
            self.current_stage = 2
    
    async def start_preparation(self):
        """Начальный этап: 0% - Подготовка расклада"""
        await self.progress_bar.update_progress(0)
        self.current_stage = 0
    
    async def complete_llm_questions_generation(self):
        """Завершение генерации LLM вопросов: 25%"""
        await self.progress_bar.update_progress(25)
        self.current_stage = 2
    
    async def cancel(self):
        """Отменяет прогресс-бар"""
        await self.progress_bar.cancel()
    
    def set_update_context(self, update, context):
        """Сохраняет контекст для создания новых прогресс-баров"""
        self.update_context = (update, context)
    
    async def recreate_progress_bar(self, current_progress: int):
        """Пересоздает прогресс-бар внизу чата для лучшей видимости"""
        if not self.update_context:
            return False
            
        try:
            # Удаляем старый прогресс-бар
            await self.progress_bar.cancel()
            
            # Создаем новый внизу чата
            update, context = self.update_context
            chat_id = update.effective_chat.id
            
            # Формируем сообщение для нового прогресс-бара
            progress_visual = self.progress_bar._generate_progress_visual(current_progress)
            stage_text = self.progress_bar.STAGES.get(current_progress, "Обрабатываю...")
            
            message_text = (
                f"🔮 **Генерирую интерпретацию вашего расклада**\\n\\n"
                f"{progress_visual} {current_progress}%\\n\\n"
                f"{stage_text}"
            )
            
            progress_message = await update.message.reply_text(
                message_text,
                parse_mode='Markdown'
            )
            
            # Трекируем новое сообщение для удаления
            add_message_to_delete(chat_id, progress_message.message_id)
            
            # Обновляем прогресс-бар
            self.progress_bar = TarotProgressBar(progress_message)
            self.progress_bar.current_progress = current_progress
            
            logger.info(f"Прогресс-бар пересоздан внизу чата для {current_progress}%")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка при пересоздании прогресс-бара: {e}")
            return False
    
    async def start_context_analysis(self):
        """Этап 2: 25-50% - Промпт 04 (анализ контекста)"""
        if self.current_stage == 2:
            await self.progress_bar.update_progress(25)
            await asyncio.sleep(0.2)
            await self.progress_bar.update_progress(35)
    
    async def complete_context_analysis(self):
        """Завершение анализа контекста"""
        if self.current_stage == 2:
            # Пересоздаем прогресс-бар внизу на 50%
            recreated = await self.recreate_progress_bar(50)
            if not recreated:
                await self.progress_bar.update_progress(50)
            await asyncio.sleep(0.3)
            self.current_stage = 3
    
    async def start_synthesis(self):
        """Этап 3: 50-75% - Промпт 05 (синтез)"""
        if self.current_stage == 3:
            await self.progress_bar.update_progress(50)
            await asyncio.sleep(0.2)
            await self.progress_bar.update_progress(60)
    
    async def complete_synthesis(self):
        """Завершение синтеза"""
        if self.current_stage == 3:
            # Пересоздаем прогресс-бар внизу на 75%
            recreated = await self.recreate_progress_bar(75)
            if not recreated:
                await self.progress_bar.update_progress(75)
            await asyncio.sleep(0.3)
            self.current_stage = 4
    
    async def start_final_interpretation(self):
        """Этап 4: 75-100% - Промпт 06 (финальная интерпретация)"""
        if self.current_stage == 4:
            await self.progress_bar.update_progress(75)
            await asyncio.sleep(0.2)
            await self.progress_bar.update_progress(85)
    
    async def complete_final_interpretation(self):
        """Завершение финальной интерпретации"""
        if self.current_stage == 4:
            await self.progress_bar.update_progress(100)
            self.current_stage = 5
    
    async def finish(self, delay: float = 1.5):
        """Завершает весь процесс"""
        await self.progress_bar.complete(delay=delay)


async def create_progress_bar(update, context: ContextTypes.DEFAULT_TYPE) -> TarotProgressBar:
    """
    Создает и инициализирует прогресс-бар
    
    :param update: Telegram update
    :param context: Bot context
    :return: Экземпляр TarotProgressBar
    """
    try:
        # Создаем начальное сообщение (с уменьшенным количеством звёзд)
        initial_message = (
            f"🔮 **Генерирую интерпретацию вашего расклада**\n\n"
            f"☆☆☆☆☆☆☆☆☆☆ 0%\n\n"
            f"🔮 Подготавливаю расклад..."
        )
        
        progress_message = await update.message.reply_text(
            initial_message,
            parse_mode='Markdown'
        )
        
        # Трекируем сообщение для удаления 
        chat_id = update.effective_chat.id
        add_message_to_delete(chat_id, progress_message.message_id)
        
        # Создаем прогресс-бар
        progress_bar = TarotProgressBar(progress_message)
        
        logger.info("Прогресс-бар создан")
        return progress_bar
        
    except Exception as e:
        logger.error(f"Ошибка при создании прогресс-бара: {e}")
        raise


# Альтернативные дизайны для разных ситуаций

class CompactProgressBar:
    """Компактная версия прогресс-бара"""
    
    @staticmethod
    def generate(progress: int) -> str:
        """Генерирует компактный прогресс-бар"""
        filled = int(progress / 10)  # 10 позиций
        bar = "●" * filled + "○" * (10 - filled)
        return f"🔮 {bar} {progress}%"


class EmojiProgressBar:
    """Прогресс-бар с эмодзи-анимацией"""
    
    ANIMATION_FRAMES = ["🌑", "🌒", "🌓", "🌔", "🌕"]
    
    @staticmethod
    def generate(progress: int) -> str:
        """Генерирует анимированный прогресс-бар"""
        frame_index = (progress // 20) % len(EmojiProgressBar.ANIMATION_FRAMES)
        moon = EmojiProgressBar.ANIMATION_FRAMES[frame_index]
        
        stars = "⭐" * (progress // 5)
        empty = "☆" * (20 - progress // 5)
        
        return f"{moon} {stars}{empty} {progress}%"