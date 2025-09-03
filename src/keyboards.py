"""
Inline-клавиатуры для телеграм-бота "Личный Таролог ✨🔮✨"
"""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from typing import Dict, Any


def main_menu() -> InlineKeyboardMarkup:
    """
    Главное меню бота
    
    :return: Inline-клавиатура с основными опциями
    """
    keyboard = [
        [InlineKeyboardButton("🎯 Сделать расклад", callback_data="spreads_list")],
        [InlineKeyboardButton("💰 Мои расклады", callback_data="my_credits")],
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
        [InlineKeyboardButton("🤔 Какой расклад выбрать?", callback_data="spread_guide")],
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


def tariff_selection_menu(spread_type: str, credits: Dict[str, int], config: Dict[str, Any]) -> InlineKeyboardMarkup:
    """
    Меню выбора тарифа таролога (после выбора расклада)
    
    :param spread_type: Тип выбранного расклада (например: "spread_celtic")
    :param credits: Словарь с количеством кредитов {'beginner': int, 'expert': int}
    :param config: Конфигурация с информацией о тарифах
    :return: Inline-клавиатура с выбором тарифов
    """
    tariff_plans = config.get('tariff_plans', {})
    limitations = config.get('limitations', {})
    
    keyboard = []
    
    # Кнопки для каждого тарифа
    for tariff_key, plan_info in tariff_plans.items():
        name = plan_info.get('name', tariff_key)
        icon = plan_info.get('icon', '🔮')
        available = credits.get(tariff_key, 0)
        
        if available > 0:
            button_text = f"{icon} {name} (осталось: {available})"
            callback_data = f"tariff_{tariff_key}_{spread_type}"
        else:
            button_text = f"{icon} {name} (недоступно)"
            callback_data = f"tariff_empty_{tariff_key}"
        
        keyboard.append([InlineKeyboardButton(button_text, callback_data=callback_data)])
    
    # Предупреждение о пополнении
    if not limitations.get('refill_available', False):
        keyboard.append([InlineKeyboardButton("ℹ️ О пополнении", callback_data="refill_info")])
    
    # Кнопка назад
    keyboard.append([InlineKeyboardButton("◀️ Назад к раскладам", callback_data="spreads_list")])
    
    return InlineKeyboardMarkup(keyboard)


def credits_info_menu() -> InlineKeyboardMarkup:
    """
    Меню просмотра информации о кредитах с кнопкой возврата
    
    :return: Inline-клавиатура для экрана с информацией о кредитах
    """
    return back_button("back_to_main")


def spread_guide_navigation(step: int = 1) -> InlineKeyboardMarkup:
    """
    Навигация для гида по раскладам с кнопками "Далее", "Назад" и "К раскладам"
    
    :param step: Номер текущего шага (1-5)
    :return: Inline-клавиатура для навигации по гиду
    """
    keyboard = []
    
    # Создаём кнопки "Назад" и "Далее" в одной строке если это не первый/последний шаг
    navigation_row = []
    
    if step > 1:
        navigation_row.append(InlineKeyboardButton("⬅️ Назад", callback_data=f"guide_step_{step - 1}"))
    
    if step < 5:
        navigation_row.append(InlineKeyboardButton("Далее ➡️", callback_data=f"guide_step_{step + 1}"))
    
    if navigation_row:
        keyboard.append(navigation_row)
    
    # Всегда добавляем кнопку возврата к раскладам
    keyboard.append([InlineKeyboardButton("◀️ К раскладам", callback_data="spreads_list")])
    
    return InlineKeyboardMarkup(keyboard)


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