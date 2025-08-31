"""
Система обратной связи для раскладов Таро
"""

import logging
from typing import Optional, Dict
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from src.spread_logger import get_spread_logger
from src.simple_state import UserState, set_state, get_user_data, update_data, reset_to_idle
from src.keyboards import main_menu

logger = logging.getLogger(__name__)

class FeedbackSystem:
    """Система сбора и обработки обратной связи"""
    
    # Рейтинги с эмодзи
    RATING_EMOJIS = {
        1: "⭐",
        2: "⭐⭐", 
        3: "⭐⭐⭐",
        4: "⭐⭐⭐⭐",
        5: "⭐⭐⭐⭐⭐"
    }
    
    # Сообщения благодарности
    THANK_YOU_MESSAGES = {
        1: "😔 Очень жаль, что не понравилось! Буду работать над улучшением интерпретаций.",
        2: "😐 Спасибо за честность! Ваш отзыв поможет мне стать лучше.",
        3: "😊 Спасибо за отзыв! Рад, что интерпретация была полезной.", 
        4: "😄 Отлично! Рад, что вам понравилась интерпретация!",
        5: "🤩 Потрясающе! Очень рад, что смог дать точную интерпретацию!"
    }
    
    def create_rating_keyboard(self) -> InlineKeyboardMarkup:
        """Создает клавиатуру для оценки интерпретации"""
        keyboard = []
        
        # Первый ряд: звезды 1-3
        row1 = []
        for i in range(1, 4):
            emoji = self.RATING_EMOJIS[i]
            row1.append(InlineKeyboardButton(emoji, callback_data=f"rate_{i}"))
        keyboard.append(row1)
        
        # Второй ряд: звезды 4-5
        row2 = []
        for i in range(4, 6):
            emoji = self.RATING_EMOJIS[i] 
            row2.append(InlineKeyboardButton(emoji, callback_data=f"rate_{i}"))
        keyboard.append(row2)
        
        # Третий ряд: дополнительные опции
        keyboard.append([
            InlineKeyboardButton("💬 Оставить комментарий", callback_data="feedback_comment"),
            InlineKeyboardButton("🔄 Новый расклад", callback_data="spreads_list")
        ])
        
        # Четвертый ряд: главное меню
        keyboard.append([
            InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")
        ])
        
        return InlineKeyboardMarkup(keyboard)
    
    async def request_feedback(self, update: Update, context: ContextTypes.DEFAULT_TYPE, 
                             chat_id: int) -> None:
        """Запрашивает обратную связь от пользователя"""
        try:
            # Устанавливаем состояние ожидания обратной связи
            set_state(chat_id, UserState.WAITING_FEEDBACK)
            
            feedback_message = (
                "🌟 **Оцените интерпретацию**\n\n"
                "Ваш отзыв очень важен для меня! Это поможет улучшить качество будущих гаданий.\n\n"
                "⭐ Выберите количество звезд:"
            )
            
            keyboard = self.create_rating_keyboard()
            
            await update.message.reply_text(
                feedback_message,
                reply_markup=keyboard,
                parse_mode='Markdown'
            )
            
            logger.info(f"Запрошена обратная связь у пользователя {chat_id}")
            
        except Exception as e:
            logger.error(f"Ошибка при запросе обратной связи: {e}")
    
    def create_feedback_after_rating_keyboard(self, rating: int) -> InlineKeyboardMarkup:
        """Создает клавиатуру после выбора рейтинга"""
        keyboard = [
            [InlineKeyboardButton("💬 Оставить комментарий", callback_data="feedback_comment")],
            [InlineKeyboardButton("🔄 Новый расклад", callback_data="spreads_list")],
            [InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    async def handle_rating(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обрабатывает рейтинг от пользователя (ОСТАВЛЯЕМ КНОПКУ КОММЕНТАРИЯ)"""
        try:
            query = update.callback_query
            chat_id = query.message.chat.id
            
            # Извлекаем рейтинг из callback_data
            rating_str = query.data.replace("rate_", "")
            rating = int(rating_str)
            
            # Получаем данные сессии для логирования
            session_data = get_user_data(chat_id)
            log_filepath = session_data.get('log_filepath')
            
            # Сохраняем рейтинг в сессии
            update_data(chat_id, 'user_rating', rating)
            
            if log_filepath:
                # Сохраняем рейтинг в лог
                spread_logger = get_spread_logger()
                spread_logger.add_feedback(log_filepath, rating)
            
            # Благодарим пользователя, НО ОСТАВЛЯЕМ КОММЕНТАРИЙ
            thank_you_message = self.THANK_YOU_MESSAGES.get(rating, "Спасибо за отзыв!")
            rating_emoji = self.RATING_EMOJIS.get(rating, "⭐")
            
            response_message = (
                f"{thank_you_message}\n\n"
                f"Ваша оценка: {rating_emoji}\n\n"
                "💬 Вы можете также оставить комментарий."
            )
            
            # Проверяем, есть ли уже комментарий
            existing_comment = session_data.get('user_comment')
            if existing_comment:
                # У пользователя уже есть и рейтинг, и комментарий
                response_message += f"\n✨ Спасибо за полную оценку! Возвращайтесь за новыми раскладами!"
                await query.edit_message_text(
                    response_message,
                    reply_markup=main_menu()
                )
                # Очищаем состояние
                reset_to_idle(chat_id, keep_data=False)
            else:
                # Обновляем сообщение С КНОПКОЙ КОММЕНТАРИЯ
                await query.edit_message_text(
                    response_message,
                    reply_markup=self.create_feedback_after_rating_keyboard(rating)
                )
            
            logger.info(f"Получена оценка {rating} от пользователя {chat_id}")
            
        except Exception as e:
            logger.error(f"Ошибка при обработке рейтинга: {e}")
            await query.answer("❌ Ошибка при сохранении оценки")
    
    async def request_comment(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Запрашивает текстовый комментарий"""
        try:
            query = update.callback_query
            chat_id = query.message.chat.id
            
            # Устанавливаем состояние ожидания комментария
            set_state(chat_id, UserState.WAITING_COMMENT)
            
            comment_message = (
                "💬 **Оставьте комментарий**\n\n"
                "Расскажите, что вам понравилось или что можно улучшить?\n"
                "Ваш отзыв поможет мне стать лучше!\n\n"
                "📝 Напишите ваш комментарий:"
            )
            
            # Кнопка отмены
            cancel_keyboard = InlineKeyboardMarkup([[
                InlineKeyboardButton("❌ Отмена", callback_data="feedback_cancel")
            ]])
            
            await query.edit_message_text(
                comment_message,
                reply_markup=cancel_keyboard,
                parse_mode='Markdown'
            )
            
            logger.info(f"Запрошен комментарий у пользователя {chat_id}")
            
        except Exception as e:
            logger.error(f"Ошибка при запросе комментария: {e}")
    
    def create_feedback_after_comment_keyboard(self) -> InlineKeyboardMarkup:
        """Создаёт клавиатуру после комментария"""
        keyboard = [
            # Первый ряд: звезды 1-3
            [InlineKeyboardButton("⭐", callback_data="rate_1"),
             InlineKeyboardButton("⭐⭐", callback_data="rate_2"), 
             InlineKeyboardButton("⭐⭐⭐", callback_data="rate_3")],
            # Второй ряд: звезды 4-5
            [InlineKeyboardButton("⭐⭐⭐⭐", callback_data="rate_4"),
             InlineKeyboardButton("⭐⭐⭐⭐⭐", callback_data="rate_5")],
            # Третий ряд: навигация
            [InlineKeyboardButton("🔄 Новый расклад", callback_data="spreads_list")],
            [InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    async def handle_comment(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обрабатывает текстовый комментарий (ОСТАВЛЯЕМ КНОПКИ ОЦЕНКИ)"""
        try:
            chat_id = update.effective_chat.id
            comment = update.message.text.strip()
            
            # Получаем данные сессии
            session_data = get_user_data(chat_id)
            log_filepath = session_data.get('log_filepath')
            
            # Сохраняем комментарий в сессию
            update_data(chat_id, 'user_comment', comment)
            
            if log_filepath:
                # Сохраняем комментарий в лог (рейтинг 0 = только комментарий)
                spread_logger = get_spread_logger()
                spread_logger.add_feedback(log_filepath, 0, comment)
            
            # Благодарим за комментарий, НО ОСТАВЛЯЕМ ОЦЕНКУ
            response_message = (
                "💝 **Спасибо за подробный отзыв!**\n\n"
                "Ваш комментарий очень ценен для меня.\n\n"
                "⭐ Вы можете также поставить оценку:"
            )
            
            await update.message.reply_text(
                response_message,
                reply_markup=self.create_feedback_after_comment_keyboard(),
                parse_mode='Markdown'
            )
            
            # Проверяем, есть ли уже рейтинг
            existing_rating = session_data.get('user_rating')
            if existing_rating:
                # У пользователя уже есть и рейтинг, и комментарий
                rating_emoji = self.RATING_EMOJIS.get(existing_rating, "⭐")
                response_message += f"\nВаша оценка: {rating_emoji}\n\n✨ Спасибо за полную оценку! Возвращайтесь за новыми раскладами!"
                # Обновляем последнее сообщение (найдём его)
                # Очищаем состояние
                reset_to_idle(chat_id, keep_data=False)
            else:
                # НЕ очищаем состояние, оставляем WAITING_FEEDBACK
                set_state(chat_id, UserState.WAITING_FEEDBACK)  # возвращаемся к ожиданию обратной связи
            
            logger.info(f"Получен комментарий от пользователя {chat_id}: {comment[:50]}...")
            
        except Exception as e:
            logger.error(f"Ошибка при обработке комментария: {e}")
            await update.message.reply_text(
                "❌ Ошибка при сохранении комментария. Попробуйте позже.",
                reply_markup=main_menu()
            )
    
    async def cancel_feedback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Отменяет процесс обратной связи"""
        try:
            query = update.callback_query
            chat_id = query.message.chat.id
            
            cancel_message = (
                "✅ **Обратная связь отменена**\n\n"
                "Ничего страшного! Возвращайтесь за новыми раскладами когда захотите.\n\n"
                "🔮 Буду рад помочь вам снова!"
            )
            
            await query.edit_message_text(
                cancel_message,
                reply_markup=main_menu(),
                parse_mode='Markdown'
            )
            
            # Очищаем состояние
            reset_to_idle(chat_id, keep_data=False)
            
            logger.info(f"Отменена обратная связь пользователем {chat_id}")
            
        except Exception as e:
            logger.error(f"Ошибка при отмене обратной связи: {e}")
    
    def get_user_feedback_stats(self, chat_id: int) -> Dict:
        """Получает статистику обратной связи пользователя"""
        try:
            spread_logger = get_spread_logger()
            stats = spread_logger.get_user_stats(chat_id)
            
            feedback_stats = {
                "total_ratings": stats.get("total_feedback", 0),
                "average_rating": stats.get("average_rating", 0),
                "total_spreads": stats.get("total_spreads", 0),
                "feedback_rate": 0
            }
            
            # Процент обратной связи
            if stats.get("total_spreads", 0) > 0:
                feedback_stats["feedback_rate"] = round(
                    (stats.get("total_feedback", 0) / stats.get("total_spreads", 1)) * 100, 1
                )
            
            return feedback_stats
            
        except Exception as e:
            logger.error(f"Ошибка при получении статистики обратной связи: {e}")
            return {}


# Глобальный экземпляр системы обратной связи
_feedback_system = None

def get_feedback_system() -> FeedbackSystem:
    """Получает глобальный экземпляр системы обратной связи"""
    global _feedback_system
    if _feedback_system is None:
        _feedback_system = FeedbackSystem()
    return _feedback_system