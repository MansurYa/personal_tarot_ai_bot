"""
Inline-клавиатуры для телеграм-бота "Личный Таролог ✨🔮✨"
"""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def main_menu() -> InlineKeyboardMarkup:
    """
    Главное меню бота
    
    :return: Inline-клавиатура с основными опциями
    """
    keyboard = [
        [InlineKeyboardButton("🎯 Сделать расклад", callback_data="spreads_list")],
        [InlineKeyboardButton("❓ Помощь", callback_data="help")]
    ]
    return InlineKeyboardMarkup(keyboard)


def spreads_menu() -> InlineKeyboardMarkup:
    """
    Меню выбора типа расклада таро
    
    :return: Inline-клавиатура со всеми 7 типами раскладов
    """
    keyboard = [
        [InlineKeyboardButton("1️⃣ На одну карту", callback_data="spread_single")],
        [InlineKeyboardButton("3️⃣ На три карты", callback_data="spread_three")],
        [InlineKeyboardButton("🍀 Подкова", callback_data="spread_horseshoe")],
        [InlineKeyboardButton("❤️ Любовный треугольник", callback_data="spread_love")],
        [InlineKeyboardButton("✝️ Кельтский крест", callback_data="spread_celtic")],
        [InlineKeyboardButton("📅 Прогноз на неделю", callback_data="spread_week")],
        [InlineKeyboardButton("🎡 Колесо года", callback_data="spread_year")],
        [InlineKeyboardButton("◀️ Назад", callback_data="back_to_main")]
    ]
    return InlineKeyboardMarkup(keyboard)


def back_button(callback_data: str) -> InlineKeyboardMarkup:
    """
    Создает клавиатуру с одной кнопкой "Назад"
    
    :param callback_data: Callback данные для возврата (например: "back_to_main", "back_to_spreads")
    :return: Inline-клавиатура с кнопкой "Назад"
    """
    keyboard = [
        [InlineKeyboardButton("◀️ Назад", callback_data=callback_data)]
    ]
    return InlineKeyboardMarkup(keyboard)


def help_menu() -> InlineKeyboardMarkup:
    """
    Меню помощи с кнопкой возврата
    
    :return: Inline-клавиатура для экрана помощи
    """
    return back_button("back_to_main")


# Словарь с названиями раскладов для удобства
SPREAD_NAMES = {
    "spread_single": "На одну карту",
    "spread_three": "На три карты", 
    "spread_horseshoe": "Подкова",
    "spread_love": "Любовный треугольник",
    "spread_celtic": "Кельтский крест",
    "spread_week": "Прогноз на неделю",
    "spread_year": "Колесо года"
}