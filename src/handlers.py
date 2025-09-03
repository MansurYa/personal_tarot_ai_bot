"""
Обработчики callback-запросов для inline-кнопок и пошаговый сбор данных
"""
import logging
import io
import time
import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from src.keyboards import main_menu, spreads_menu, back_button, SPREAD_NAMES, tariff_selection_menu, credits_info_menu, spread_guide_navigation
from src.simple_state import UserState, get_state, set_state, update_data, get_user_data, reset_to_idle, add_message_to_delete
from src.validators import validate_name, validate_birthdate, validate_magic_number
from src.user_manager import user_exists, save_user, get_user, update_last_spread, get_user_credits, use_credit, has_credits
from src.config import load_config
from src.spread_configs import get_spread_config
from src.card_manager import TarotDeck, select_cards
from src.image_generator import ImageGenerator
from src.spread_questions import get_questions_for_spread, get_spread_type_from_callback
from src.llm_integration import start_llm_interpretation, process_llm_questions

from src.feedback_system import get_feedback_system
from PIL import Image

def generate_random_magic_number(user_id: int) -> int:
    """
    Генерирует случайное магическое число для пользователя при отключенных магических числах
    
    Использует комбинированный seed из нескольких источников энтропии:
    - Текущее время с микросекундами  
    - Уникальный идентификатор пользователя
    - Дополнительный случайный компонент
    
    :param user_id: ID пользователя Telegram
    :return: Случайное число от 1 до 999
    """
    # Комбинированный seed из multiple источников энтропии
    base_seed = int(time.time() * 1000000)  # Микросекунды для высокой точности
    user_seed = hash(str(user_id)) % 10000   # Уникальность пользователя  
    random_component = random.randint(1, 999) # Дополнительная случайность
    
    # Комбинируем все источники энтропии
    combined_seed = (base_seed + user_seed + random_component) % 999 + 1
    
    return combined_seed

def is_magic_numbers_enabled() -> bool:
    """Проверяет, включены ли магические числа в конфигурации"""
    config = load_config()
    return config.get('features', {}).get('use_magic_numbers', True)

async def proceed_to_questions_or_magic_number(update: Update, context: ContextTypes.DEFAULT_TYPE, 
                                              chat_id: int, success_message: str) -> None:
    """
    Переходит либо к магическому числу, либо сразу к вопросам (в зависимости от настройки)
    
    :param update: Объект обновления от Telegram
    :param context: Контекст бота
    :param chat_id: ID чата
    :param success_message: Сообщение для отправки пользователю
    """
    if is_magic_numbers_enabled():
        # Стандартный поток - просим магическое число
        set_state(chat_id, UserState.WAITING_MAGIC_NUMBER)
        success_msg = await update.message.reply_text(success_message)
        add_message_to_delete(chat_id, success_msg.message_id)
    else:
        # Пропускаем магическое число - переходим сразу к вопросам
        session_data = get_user_data(chat_id)
        user_id = session_data.get('user_id', update.effective_user.id)
        magic_number = generate_random_magic_number(user_id)  # Генерируем случайное число
        
        # Обновляем данные сессии
        update_data(chat_id, 'magic_number', magic_number)
        
        # Переходим сразу к предварительным вопросам
        await start_preliminary_questions(update, context, chat_id)

async def start_preliminary_questions(update: Update, context: ContextTypes.DEFAULT_TYPE, chat_id: int) -> None:
    """
    Начинает процесс предварительных вопросов для расклада
    
    :param update: Объект обновления от Telegram
    :param context: Контекст бота
    :param chat_id: ID чата
    """
    try:
        session_data = get_user_data(chat_id)
        spread_type = session_data.get('spread_type')
        # Если magic_number не установлен, генерируем случайный
        magic_number = session_data.get('magic_number')
        if magic_number is None:
            user_id = session_data.get('user_id', update.effective_user.id) 
            magic_number = generate_random_magic_number(user_id)
        
        # Получаем предварительные вопросы для расклада
        spread_config_type = SPREAD_MAPPING.get(spread_type, spread_type)
        questions = get_questions_for_spread(spread_config_type)
        
        if questions and len(questions.questions) > 0:
            # Есть предварительные вопросы - начинаем их задавать
            update_data(chat_id, 'questions', questions)
            update_data(chat_id, 'current_question', 0)
            update_data(chat_id, 'preliminary_answers', [])
            set_state(chat_id, UserState.WAITING_PRELIMINARY_ANSWERS)
            
            first_question = questions.questions[0]
            
            if is_magic_numbers_enabled():
                # Стандартное сообщение с магическим числом
                intro_text = f"✅ Магическое число {magic_number} принято!\n\n"
            else:
                # Сообщение без упоминания магического числа
                intro_text = "✅ Приступаем к анализу!\n\n"
            
            await update.message.reply_text(
                f"{intro_text}"
                f"🎴 {questions.name}\n"
                f"Рекомендуемое время: {questions.estimated_time}\n\n"
                "Для более точной интерпретации ответьте на несколько вопросов:\n\n"
                f"**{first_question.text}**\n\n"
                f"💡 {first_question.hint}",
                parse_mode='Markdown'
            )
            
            logger.info(f"Начат процесс предварительных вопросов для пользователя {chat_id}, расклад {spread_type}")
        else:
            # Нет вопросов - сразу к LLM интерпретации
            tariff = session_data.get('tariff', 'beginner')
            await start_llm_interpretation(update, context, chat_id, session_data, tariff)
            
    except Exception as e:
        logger.error(f"Ошибка при запуске предварительных вопросов для пользователя {chat_id}: {e}")
        await update.message.reply_text(
            "❌ Произошла ошибка при подготовке расклада. Попробуйте позже."
        )

logger = logging.getLogger(__name__)

# ВСЕ 7 раскладов теперь готовы! (соответствуют callback_data из keyboards.py)
IMPLEMENTED_SPREADS = {
    'spread_single',     # На одну карту
    'spread_three',      # На три карты  
    'spread_horseshoe',  # Подкова
    'spread_love',       # Любовный треугольник
    'spread_celtic',     # Кельтский крест
    'spread_week',       # Прогноз на неделю
    'spread_year'        # Колесо года
}

# Mapping между callback_data и конфигурациями
SPREAD_MAPPING = {
    'spread_single': 'single_card',
    'spread_three': 'three_cards', 
    'spread_horseshoe': 'horseshoe',
    'spread_love': 'love_triangle',
    'spread_celtic': 'celtic_cross',
    'spread_week': 'week_forecast',
    'spread_year': 'year_wheel'
}


async def perform_spread(update, context, spread_type, magic_number, tariff='beginner'):
    """
    Выполняет полный цикл генерации расклада:
    1. Списывание кредита с выбранного тарифа
    2. Загрузка конфигурации
    3. Выбор карт  
    4. Генерация изображения
    5. Отправка пользователю
    6. Обработка ошибок
    
    :param update: Объект обновления от Telegram
    :param context: Контекст бота
    :param spread_type: Тип расклада (например, 'single_card')
    :param magic_number: Магическое число для генерации
    :param tariff: Выбранный тариф таролога ('beginner' или 'expert')
    """
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    session_data = get_user_data(chat_id)
    
    # Списываем кредит с выбранного тарифа
    if not use_credit(user_id, tariff):
        error_msg = await update.message.reply_text(
            f"❌ Не удалось списать кредит с тарифа {tariff}. У вас недостаточно раскладов.",
            reply_markup=main_menu()
        )
        logger.error(f"Не удалось списать кредит с тарифа {tariff} для пользователя {user_id}")
        return
    
    try:
        # 1. Загрузка конфигурации расклада (используем mapping)
        config_key = SPREAD_MAPPING.get(spread_type, spread_type)
        logger.info(f"Загрузка конфигурации для расклада {spread_type} -> {config_key}")
        config = get_spread_config(config_key)
        
        # 2. Выбор карт через card_manager с комплексным seed
        logger.info(f"Выбор {config['card_count']} карт с магическим числом {magic_number}")
        deck = TarotDeck()
        
        # Получаем возраст пользователя и текущее время
        user_age = session_data.get('age', 0)
        current_timestamp = int(time.time())  # Время в секундах с эпохи Unix
        
        # Выбираем карты с комплексным seed
        selected_cards = select_cards(deck, config['card_count'], magic_number, user_age, current_timestamp)
        
        # 3. Генерация изображения
        logger.info(f"Генерация изображения для расклада {spread_type}")
        generator = ImageGenerator()
        
        # Отправляем сообщение о генерации
        processing_msg = await update.message.reply_text(
            "🎨 Генерирую ваш расклад...\n⏳ Это может занять несколько секунд"
        )
        
        image_bytes = generator.generate_spread_image(
            background_id=config['background_id'],
            cards=selected_cards,
            positions=config['positions'],
            scale=config['scale']
        )
        
        # 4. Отправка изображения пользователю
        logger.info(f"Отправка изображения расклада пользователю {chat_id}")
        
        # Отправляем изображение БЕЗ кнопки
        image_io = io.BytesIO(image_bytes)
        image_io.name = f"{spread_type}_spread.png"
        
        await context.bot.send_photo(
            chat_id=chat_id,
            photo=image_io,
            caption=f"🎴 Ваш расклад \"{config['name']}\" готов!"
        )
        
        # Удаляем сообщение о генерации
        try:
            await processing_msg.delete()
        except:
            pass
        
        # 5. Отправляем список выпавших карт текстом
        cards_text = f"🎴 Ваш расклад \"{config['name']}\":\n\n"
        
        for i, card in enumerate(selected_cards, 1):
            card_meaning = config.get('card_meanings', [f'Карта {i}'])[i-1] if i <= len(config.get('card_meanings', [])) else f'Карта {i}'
            cards_text += f"{i}. **{card['name']}** — {card_meaning}\n"
        
        cards_text += "\n🔮 Интерпретация расклада появится в следующей версии."
        
        # Создаем кнопку "Новый расклад" для текстового сообщения
        keyboard = [[InlineKeyboardButton("🔄 Новый расклад", callback_data="spreads_list")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            cards_text,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        
        logger.info(f"Расклад {spread_type} успешно сгенерирован и отправлен пользователю {chat_id}")
        
    except Exception as e:
        logger.error(f"Ошибка генерации расклада {spread_type} для пользователя {chat_id}: {e}")
        
        # Отправляем fallback - список карт текстом
        try:
            # Удаляем сообщение о генерации если есть
            try:
                await processing_msg.delete()
            except:
                pass
            
            config_key = SPREAD_MAPPING.get(spread_type, spread_type)
            config = get_spread_config(config_key)
            deck = TarotDeck()
            
            # Используем тот же комплексный seed что и в основной функции
            user_age = session_data.get('age', 0)
            current_timestamp = int(time.time())
            selected_cards = select_cards(deck, config['card_count'], magic_number, user_age, current_timestamp)
            
            fallback_text = f"❌ Не удалось создать изображение расклада.\n\n"
            fallback_text += f"🎴 Ваши карты \"{config['name']}\":\n\n"
            
            for i, card in enumerate(selected_cards, 1):
                card_meaning = config.get('card_meanings', [f'Карта {i}'])[i-1] if i <= len(config.get('card_meanings', [])) else f'Карта {i}'
                fallback_text += f"{i}. **{card['name']}** — {card_meaning}\n"
            
            fallback_text += "\n🔮 Интерпретация расклада появится в следующей версии."
            
            keyboard = [[InlineKeyboardButton("🔄 Новый расклад", callback_data="spreads_list")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                fallback_text,
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
            
        except Exception as fallback_error:
            logger.error(f"Критическая ошибка fallback для {chat_id}: {fallback_error}")
            await update.message.reply_text(
                "❌ Произошла критическая ошибка при генерации расклада.\n"
                "Попробуйте позже или выберите другой расклад:",
                reply_markup=main_menu()
            )


async def handle_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Показывает главное меню
    
    :param update: Объект обновления от Telegram
    :param context: Контекст бота
    """
    welcome_text = (
        "🔮 Добро пожаловать в мир Таро!\n\n"
        "Я ваш личный таролог, готовый приоткрыть завесу будущего.\n\n"
        "✨ Выберите действие:"
    )
    
    query = update.callback_query
    await query.edit_message_text(
        text=welcome_text,
        reply_markup=main_menu()
    )


async def handle_spreads_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Показывает список 7 раскладов
    
    :param update: Объект обновления от Telegram
    :param context: Контекст бота
    """
    spreads_text = "📚 Выберите расклад для гадания:"
    
    query = update.callback_query
    await query.edit_message_text(
        text=spreads_text,
        reply_markup=spreads_menu()
    )


async def handle_spread_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Обрабатывает выбор конкретного расклада - теперь показывает выбор тарифа таролога
    
    :param update: Объект обновления от Telegram
    :param context: Контекст бота
    """
    try:
        query = update.callback_query
        user_id = query.from_user.id
        spread_type = query.data
        
        # Определяем название выбранного расклада
        spread_name = SPREAD_NAMES.get(spread_type, "Неизвестный расклад")
        
        logger.info(f"Пользователь {user_id} выбрал расклад: {spread_name}")
        
        # Получаем кредиты пользователя для показа в меню выбора тарифа
        credits = get_user_credits(user_id)
        if credits is None:
            # Новый пользователь - устанавливаем начальные кредиты из конфигурации
            config = load_config()
            tariff_plans = config.get('tariff_plans', {})
            credits = {
                'beginner': tariff_plans.get('beginner', {}).get('initial_credits', 3),
                'expert': tariff_plans.get('expert', {}).get('initial_credits', 1)
            }
        
        # Показываем меню выбора тарифа
        config = load_config()
        await query.edit_message_text(
            f"🎴 **{spread_name}**\n\n"
            "🔮 Выберите уровень таролога:\n\n"
            "_Различные тарологи дают разные по глубине и стилю интерпретации._",
            reply_markup=tariff_selection_menu(spread_type, credits, config),
            parse_mode='Markdown'
        )
        
        logger.info(f"Пользователю {user_id} показано меню выбора тарифа для расклада {spread_name}")
        
    except Exception as e:
        logger.error(f"Ошибка в handle_spread_selection для пользователя {update.callback_query.from_user.id}: {e}")
        try:
            await update.callback_query.edit_message_text(
                "❌ Произошла ошибка при выборе расклада.\nПопробуйте начать заново:",
                reply_markup=main_menu()
            )
        except Exception:
            pass


async def handle_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Показывает справку о боте
    
    :param update: Объект обновления от Telegram
    :param context: Контекст бота
    """
    help_text = (
        "📖 Справка по боту 'Личный Таролог':\n\n"
        "🔮 Бот умеет делать расклады карт Таро с помощью ИИ\n"
        "✨ Доступно 7 различных типов раскладов\n"
        "🎯 Каждый расклад персонализирован под ваш вопрос\n\n"
        "💫 Как это работает:\n"
        "1. Выберите тип расклада\n"
        "2. Ответьте на вопросы\n"
        "3. Введите магическое число\n"
        "4. Получите расклад с интерпретацией\n\n"
        "🌟 Все интерпретации генерируются ИИ на основе\n"
        "классических значений карт Таро."
    )
    
    query = update.callback_query
    await query.edit_message_text(
        text=help_text,
        reply_markup=back_button("back_to_main")
    )


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Главный роутер для всех callback-запросов
    
    :param update: Объект обновления от Telegram
    :param context: Контекст бота
    """
    try:
        query = update.callback_query
        # Обязательно отвечаем на callback
        await query.answer()
        
        callback_data = query.data
        
        # Маршрутизация по callback_data
        if callback_data == "back_to_main" or callback_data == "main_menu":
            await handle_main_menu(update, context)
        elif callback_data == "spreads_list":
            await handle_spreads_list(update, context)
        elif callback_data == "help":
            await handle_help(update, context)
        elif callback_data == "spread_guide":
            # Гид по раскладам - показываем первый шаг (ВАЖНО: проверяем ДО общего spread_)
            await handle_spread_guide(update, context, step=1)
        elif callback_data.startswith("spread_"):
            await handle_spread_selection(update, context)
        elif callback_data.startswith("rate_"):
            # Обрабатываем рейтинги (rate_1, rate_2, etc.)
            feedback_system = get_feedback_system()
            await feedback_system.handle_rating(update, context)
        elif callback_data == "feedback_comment":
            # Запрос на комментарий
            feedback_system = get_feedback_system()
            await feedback_system.request_comment(update, context)
        elif callback_data == "feedback_cancel":
            # Отмена обратной связи
            feedback_system = get_feedback_system()
            await feedback_system.cancel_feedback(update, context)
        elif callback_data.startswith("feedback_"):
            await handle_feedback(update, context)
        elif callback_data == "my_credits":
            # Просмотр кредитов пользователя
            await handle_my_credits(update, context)
        elif callback_data.startswith("tariff_"):
            # Выбор тарифа для расклада
            await handle_tariff_selection(update, context)
        elif callback_data == "refill_info":
            # Информация о пополнении
            await handle_refill_info(update, context)
        elif callback_data.startswith("guide_step_"):
            # Навигация по шагам гида
            try:
                step = int(callback_data.split("_")[-1])
                await handle_spread_guide(update, context, step=step)
            except (ValueError, IndexError):
                await query.edit_message_text(
                    text="❌ Ошибка навигации",
                    reply_markup=back_button("spreads_list")
                )
        else:
            # Неизвестный callback
            await query.edit_message_text(
                text="❌ Неизвестная команда",
                reply_markup=back_button("back_to_main")
            )
            
    except Exception as e:
        logger.error(f"Ошибка в handle_callback: {e}")
        try:
            query = update.callback_query
            await query.edit_message_text(
                text="❌ Произошла ошибка. Попробуйте /start",
                reply_markup=back_button("back_to_main")
            )
        except Exception:
            pass


# Обработчики текстовых сообщений для сбора данных
async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Обработчик всех текстовых сообщений
    Направляет пользователя к нужному этапу сбора данных в зависимости от состояния
    
    :param update: Объект обновления от Telegram
    :param context: Контекст бота
    """
    try:
        chat_id = update.effective_chat.id
        current_state = get_state(chat_id)
        
        # Направляем к нужному обработчику в зависимости от состояния
        if current_state == UserState.WAITING_NAME:
            await process_name(update, context)
        elif current_state == UserState.WAITING_BIRTHDATE:
            await process_birthdate(update, context)
        elif current_state == UserState.WAITING_MAGIC_NUMBER:
            await process_magic_number(update, context)
        elif current_state == UserState.WAITING_PRELIMINARY_ANSWERS:
            await process_preliminary_answers(update, context)
        elif current_state == UserState.WAITING_LLM_QUESTIONS:
            await process_llm_questions(update, context)
        elif current_state == UserState.WAITING_COMMENT:
            feedback_system = get_feedback_system()
            await feedback_system.handle_comment(update, context)
        else:
            # Пользователь в состоянии IDLE или неизвестном состоянии
            await update.message.reply_text(
                "✨ Используйте кнопки для навигации или команды:\n\n"
                "/start - Главное меню\n"
                "/help - Справка\n\n"
                "🔮 Выберите действие:",
                reply_markup=main_menu()
            )
            logger.info(f"Пользователь {chat_id} отправил сообщение в состоянии {current_state}")
        
    except Exception as e:
        logger.error(f"Ошибка в handle_text_message: {e}")
        await update.message.reply_text(
            "❌ Произошла ошибка. Используйте /start для начала.",
            reply_markup=main_menu()
        )


async def process_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Обрабатывает ввод имени пользователя
    
    :param update: Объект обновления от Telegram
    :param context: Контекст бота
    """
    try:
        chat_id = update.effective_chat.id
        user_input = update.message.text.strip()
        
        logger.info(f"Пользователь {chat_id} ввёл имя: {user_input}")
        
        # Валидируем имя
        is_valid, result = validate_name(user_input)
        
        if not is_valid:
            # Имя некорректно - показываем ошибку и просим ввести заново
            error_msg = await update.message.reply_text(
                f"❌ {result}\n\n"
                "👤 Попробуйте ещё раз. Как вас зовут?"
            )
            add_message_to_delete(chat_id, error_msg.message_id)
            logger.info(f"Некорректное имя от пользователя {chat_id}: {result}")
            return
        
        # Имя корректно - сохраняем и переходим к дате рождения
        update_data(chat_id, 'name', result)
        
        # Сохраняем Telegram информацию пользователя для логов
        user = update.effective_user
        update_data(chat_id, 'user_id', user.id)
        update_data(chat_id, 'telegram_username', user.username)
        update_data(chat_id, 'telegram_first_name', user.first_name)
        update_data(chat_id, 'telegram_last_name', user.last_name)
        
        set_state(chat_id, UserState.WAITING_BIRTHDATE)
        
        success_msg = await update.message.reply_text(
            f"✅ Приятно познакомиться, {result}!\n\n"
            "📅 Введите дату рождения в формате ДД.ММ.ГГГГ\n"
            "(например: 15.03.1990):"
        )
        add_message_to_delete(chat_id, success_msg.message_id)
        
        logger.info(f"Имя сохранено для пользователя {chat_id}: {result}")
        
    except Exception as e:
        logger.error(f"Ошибка в process_name для пользователя {update.effective_chat.id}: {e}")
        await update.message.reply_text(
            "❌ Произошла ошибка при обработке имени. Попробуйте ещё раз:"
        )


async def process_birthdate(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Обрабатывает ввод даты рождения пользователя
    
    :param update: Объект обновления от Telegram
    :param context: Контекст бота
    """
    try:
        chat_id = update.effective_chat.id
        user_input = update.message.text.strip()
        
        logger.info(f"Пользователь {chat_id} ввёл дату рождения: {user_input}")
        
        # Валидируем дату рождения
        is_valid, result = validate_birthdate(user_input)
        
        if not is_valid:
            # Дата некорректна - показываем ошибку и просим ввести заново
            error_msg = await update.message.reply_text(
                f"❌ {result}\n\n"
                "📅 Попробуйте ещё раз. Введите дату рождения в формате ДД.ММ.ГГГГ\n"
                "(например: 15.03.1990):"
            )
            add_message_to_delete(chat_id, error_msg.message_id)
            logger.info(f"Некорректная дата от пользователя {chat_id}: {result}")
            return
        
        # Дата корректна - сохраняем пользователя в базу и переходим к магическому числу
        session_data = get_user_data(chat_id)
        
        # Сохраняем пользователя в хранилище (теперь с user_id и telegram данными)
        user = update.message.from_user
        success = save_user(
            chat_id=chat_id,
            user_id=user.id, 
            name=session_data['name'], 
            birthdate=result['date'],
            telegram_username=user.username,
            telegram_first_name=user.first_name,
            telegram_last_name=user.last_name
        )
        
        if not success:
            error_msg = await update.message.reply_text(
                "❌ Ошибка сохранения данных. Попробуйте позже или обратитесь к /start"
            )
            add_message_to_delete(chat_id, error_msg.message_id)
            logger.error(f"Не удалось сохранить пользователя {chat_id}")
            return
        
        # Обновляем данные в сессии
        update_data(chat_id, 'birthdate', result['date'])
        update_data(chat_id, 'age', result['age'])
        
        # СПИСЫВАЕМ КРЕДИТ ДЛЯ НОВОГО ПОЛЬЗОВАТЕЛЯ
        tariff_key = session_data.get('tariff', 'beginner')
        if not use_credit(user.id, tariff_key):
            error_msg = await update.message.reply_text(
                "❌ Ошибка при списании кредита. Попробуйте позже.",
            )
            add_message_to_delete(chat_id, error_msg.message_id)
            logger.error(f"Не удалось списать кредит для нового пользователя {user.id}")
            return
        
        # Переходим к следующему шагу (магическое число или сразу к вопросам)
        if is_magic_numbers_enabled():
            success_message = (
                f"✅ Спасибо! Ваш возраст: {result['age']} лет.\n\n"
                "🔮 Теперь сосредоточьтесь на своём вопросе и введите магическое число от 1 до 999:"
            )
        else:
            success_message = (
                f"✅ Спасибо! Ваш возраст: {result['age']} лет.\n\n"
                "🔮 Готовимся к анализу вашего расклада..."
            )
        
        await proceed_to_questions_or_magic_number(update, context, chat_id, success_message)
        
        logger.info(f"Пользователь {chat_id} сохранён, возраст: {result['age']}")
        
    except Exception as e:
        logger.error(f"Ошибка в process_birthdate для пользователя {update.effective_chat.id}: {e}")
        await update.message.reply_text(
            "❌ Произошла ошибка при обработке даты. Попробуйте ещё раз:"
        )


async def process_magic_number(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Обрабатывает ввод магического числа пользователя
    
    :param update: Объект обновления от Telegram
    :param context: Контекст бота
    """
    try:
        chat_id = update.effective_chat.id
        user_input = update.message.text.strip()
        session_data = get_user_data(chat_id)
        tariff = session_data.get('tariff', 'beginner')  # Получаем выбранный тариф
        
        logger.info(f"Пользователь {chat_id} ввёл магическое число: {user_input}")
        
        # Валидируем магическое число
        is_valid, result = validate_magic_number(user_input)
        
        if not is_valid:
            # Число некорректно - показываем ошибку и просим ввести заново
            await update.message.reply_text(
                f"❌ {result}\n\n"
                "🔮 Попробуйте ещё раз. Введите магическое число от 1 до 999:"
            )
            logger.info(f"Некорректное число от пользователя {chat_id}: {result}")
            return
        
        # Число корректно - определяем выбранный расклад и начинаем задавать предварительные вопросы
        session_data = get_user_data(chat_id)
        spread_type = session_data.get('spread_type')
        magic_number = result
        
        # Сохраняем магическое число в данных сессии
        update_data(chat_id, 'magic_number', magic_number)
        
        # Получаем предварительные вопросы для расклада
        spread_config_type = SPREAD_MAPPING.get(spread_type, spread_type)
        questions = get_questions_for_spread(spread_config_type)
        
        if questions and len(questions.questions) > 0:
            # Есть предварительные вопросы - начинаем их задавать
            update_data(chat_id, 'questions', questions)
            update_data(chat_id, 'current_question', 0)
            update_data(chat_id, 'preliminary_answers', [])
            set_state(chat_id, UserState.WAITING_PRELIMINARY_ANSWERS)
            
            first_question = questions.questions[0]
            await update.message.reply_text(
                f"✅ Магическое число {magic_number} принято!\n\n"
                f"🎴 {questions.name}\n"
                f"Рекомендуемое время: {questions.estimated_time}\n\n"
                "Для более точной интерпретации ответьте на несколько вопросов:\n\n"
                f"**{first_question.text}**\n\n"
                f"💡 {first_question.hint}",
                parse_mode='Markdown'
            )
            
            logger.info(f"Начат процесс предварительных вопросов для пользователя {chat_id}, расклад {spread_type}")
        else:
            # Нет предварительных вопросов - сразу переходим к LLM интерпретации
            await start_llm_interpretation(update, context, chat_id, session_data, tariff)
        
    except Exception as e:
        logger.error(f"Ошибка в process_magic_number для пользователя {update.effective_chat.id}: {e}")
        await update.message.reply_text(
            "❌ Произошла ошибка при обработке числа. Попробуйте ещё раз:"
        )


async def process_preliminary_answers(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Обрабатывает ответы на предварительные вопросы
    
    :param update: Объект обновления от Telegram
    :param context: Контекст бота
    """
    try:
        chat_id = update.effective_chat.id
        user_input = update.message.text.strip()
        session_data = get_user_data(chat_id)
        
        questions = session_data.get('questions')
        current_question_index = session_data.get('current_question', 0)
        preliminary_answers = session_data.get('preliminary_answers', [])
        
        if not questions or current_question_index >= len(questions.questions):
            # Ошибка состояния - переходим к финализации
            tariff = session_data.get('tariff', 'beginner')  # Получаем выбранный тариф
            logger.error(f"Некорректное состояние вопросов для пользователя {chat_id}")
            await start_llm_interpretation(update, context, chat_id, session_data, tariff)
            return
        
        # Сохраняем текущий ответ
        current_question = questions.questions[current_question_index]
        preliminary_answers.append({
            'question_id': current_question.id,
            'question_text': current_question.text,
            'answer': user_input,
            'expected_length': current_question.expected_length
        })
        
        update_data(chat_id, 'preliminary_answers', preliminary_answers)
        
        logger.info(f"Пользователь {chat_id} ответил на вопрос {current_question_index + 1}: {user_input[:50]}...")
        
        # Переходим к следующему вопросу
        next_question_index = current_question_index + 1
        
        if next_question_index < len(questions.questions):
            # Есть еще вопросы
            update_data(chat_id, 'current_question', next_question_index)
            
            next_question = questions.questions[next_question_index]
            await update.message.reply_text(
                f"✅ Ответ сохранен!\n\n"
                f"❓ Вопрос {next_question_index + 1} из {len(questions.questions)}:\n\n"
                f"**{next_question.text}**\n\n"
                f"💡 {next_question.hint}",
                parse_mode='Markdown'
            )
        else:
            # Все вопросы завершены - переходим к генерации (без лишних сообщений)
            tariff = session_data.get('tariff', 'beginner')  # Получаем выбранный тариф
            await start_llm_interpretation(update, context, chat_id, session_data, tariff)
        
    except Exception as e:
        logger.error(f"Ошибка в process_preliminary_answers для пользователя {update.effective_chat.id}: {e}")
        await update.message.reply_text(
            "❌ Произошла ошибка при обработке ответа. Попробуйте заново:",
            reply_markup=main_menu()
        )


async def finalize_spread_generation(update: Update, context: ContextTypes.DEFAULT_TYPE, 
                                   chat_id: int, session_data: dict, 
                                   spread_type: str, magic_number: int) -> None:
    """
    Завершает процесс и генерирует расклад
    
    :param update: Объект обновления от Telegram
    :param context: Контекст бота
    :param chat_id: ID чата
    :param session_data: Данные сессии
    :param spread_type: Тип расклада
    :param magic_number: Магическое число
    """
    try:
        # Обновляем время последнего расклада
        update_last_spread(chat_id)
        
        # Очищаем состояние - возвращаемся в главное меню
        reset_to_idle(chat_id, keep_data=False)
        
        # Проверяем, реализован ли данный расклад
        if spread_type in IMPLEMENTED_SPREADS:
            # Генерируем готовый расклад
            tariff = session_data.get('tariff', 'beginner')  # Получаем выбранный тариф
            logger.info(f"Генерируем реализованный расклад {spread_type} (тариф: {tariff}) для пользователя {chat_id}")
            await perform_spread(update, context, spread_type, magic_number, tariff)
        else:
            # Для неготовых раскладов показываем заглушку
            spread_name = SPREAD_NAMES.get(spread_type, 'Неизвестный расклад')
            
            await update.message.reply_text(
                f"✨ Ваше магическое число {magic_number} принято!\n\n"
                f"🎴 Расклад: {spread_name}\n"
                f"👤 Для: {session_data.get('name', 'Неизвестно')}\n\n"
                "🔧 Этот расклад появится в следующей версии.\n\n"
                "Попробуйте один из готовых раскладов:",
                reply_markup=main_menu()
            )
            
            logger.info(f"Показана заглушка для нереализованного расклада {spread_type} пользователю {chat_id}")
            
    except Exception as e:
        logger.error(f"Ошибка в finalize_spread_generation для пользователя {chat_id}: {e}")
        await update.message.reply_text(
            "❌ Произошла ошибка при генерации расклада. Попробуйте заново:",
            reply_markup=main_menu()
        )


async def handle_feedback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обрабатывает обратную связь от пользователя"""
    try:
        query = update.callback_query
        chat_id = query.message.chat.id
        feedback_type = query.data.replace("feedback_", "")
        
        # Сохраняем обратную связь
        session_data = get_user_data(chat_id)
        interpretation_text = session_data.get('interpretation_text', '')
        
        feedback_data = {
            'chat_id': chat_id,
            'feedback': feedback_type,
            'spread_type': session_data.get('spread_type'),
            'interpretation_length': len(interpretation_text),
            'timestamp': time.time()
        }
        
        # Здесь можно сохранить в БД или файл
        logger.info(f"Получена обратная связь от пользователя {chat_id}: {feedback_type}")
        
        # Благодарим пользователя
        feedback_messages = {
            'excellent': '⭐️ Отлично! Рад, что интерпретация вам понравилась!',
            'good': '👍 Спасибо за отзыв! Буду стараться ещё лучше!', 
            'poor': '👎 Спасибо за честность. Буду работать над улучшением интерпретаций.',
            'bad': '❌ Извините, что не оправдал ожиданий. Ваш отзыв поможет мне стать лучше!'
        }
        
        message = feedback_messages.get(feedback_type, 'Спасибо за отзыв!')
        
        await query.edit_message_text(
            f"{message}\n\n✨ Возвращайтесь за новыми раскладами!",
            reply_markup=main_menu()
        )
        
        # Очищаем состояние
        reset_to_idle(chat_id, keep_data=False)
        
    except Exception as e:
        logger.error(f"Ошибка при обработке обратной связи: {e}")


async def handle_my_credits(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Показывает пользователю информацию о доступных кредитах
    """
    try:
        query = update.callback_query
        user_id = query.from_user.id
        config = load_config()
        tariff_plans = config.get('tariff_plans', {})
        
        # Получаем кредиты пользователя
        credits = get_user_credits(user_id)
        if credits is None:
            await query.edit_message_text(
                "❌ Вы не зарегистрированы. Сначала сделайте расклад.",
                reply_markup=back_button("back_to_main")
            )
            return
        
        # Формируем сообщение с описанием тарифов
        text = "💰 Ваши доступные расклады:\n\n"
        
        for tariff_key, plan_info in tariff_plans.items():
            name = plan_info.get('name', tariff_key)
            description = plan_info.get('description', '')
            icon = plan_info.get('icon', '🔮')
            available = credits.get(tariff_key, 0)
            
            text += f"{icon} **{name}**\n"
            text += f"_{description}_\n"
            text += f"📊 Доступно: **{available}** расклад(ов)\n\n"
        
        limitations = config.get('limitations', {})
        if not limitations.get('refill_available', False):
            text += f"ℹ️ {limitations.get('refill_message', 'Пополнение недоступно')}"
        
        await query.edit_message_text(
            text=text,
            reply_markup=credits_info_menu(),
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"Ошибка при показе кредитов пользователя {query.from_user.id}: {e}")
        await query.edit_message_text(
            "❌ Произошла ошибка при загрузке информации о кредитах",
            reply_markup=back_button("back_to_main")
        )


async def handle_tariff_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Обрабатывает выбор тарифа для расклада
    """
    try:
        query = update.callback_query
        user_id = query.from_user.id
        chat_id = query.message.chat.id
        callback_data = query.data
        
        # Парсим callback: tariff_{tariff_key}_{spread_type}
        parts = callback_data.split('_')
        if len(parts) < 3:
            await query.edit_message_text(
                "❌ Неверный формат команды",
                reply_markup=back_button("back_to_main")
            )
            return
        
        if parts[1] == 'empty':
            # Недоступный тариф
            config = load_config()
            limitations = config.get('limitations', {})
            message = limitations.get('refill_message', 'У вас недостаточно кредитов на этом тарифе')
            
            await query.edit_message_text(
                f"❌ {message}",
                reply_markup=back_button("spreads_list")
            )
            return
        
        tariff_key = parts[1]  # beginner или expert
        spread_type = '_'.join(parts[2:])  # spread_celtic, spread_single, etc.
        
        # Сохраняем выбранный тариф и переходим к сбору данных пользователя
        spread_name = SPREAD_NAMES.get(spread_type, "Неизвестный расклад")
        
        # Проверяем существует ли пользователь
        if user_exists(user_id=user_id):
            # Существующий пользователь - проверяем кредиты
            if not has_credits(user_id, tariff_key):
                await query.edit_message_text(
                    "❌ У вас недостаточно кредитов на выбранном тарифе",
                    reply_markup=back_button("spreads_list")
                )
                return
            
            # СПИСЫВАЕМ КРЕДИТ СРАЗУ ПОСЛЕ ВЫБОРА ТАРИФА
            if not use_credit(user_id, tariff_key):
                await query.edit_message_text(
                    "❌ Ошибка при списании кредита. Попробуйте позже.",
                    reply_markup=back_button("spreads_list")
                )
                return
            
            # Переходим к следующему шагу (магическое число или сразу к вопросам)
            user_data = get_user(user_id=user_id)
            if user_data:
                # Обновляем данные сессии
                set_state(chat_id, UserState.IDLE, {  # Временно устанавливаем IDLE
                    'spread_type': spread_type,
                    'tariff': tariff_key,
                    'name': user_data['name'],
                    'age': user_data['age']
                })
                
                config = load_config()
                tariff_name = config['tariff_plans'][tariff_key]['name']
                
                if is_magic_numbers_enabled():
                    # Стандартный поток - просим магическое число
                    set_state(chat_id, UserState.WAITING_MAGIC_NUMBER)
                    await query.edit_message_text(
                        f"🔮 Привет снова, {user_data['name']}!\n\n"
                        f"🎴 Расклад: {spread_name}\n"
                        f"✨ Таролог: {tariff_name}\n"
                        f"👤 Возраст: {user_data['age']} лет\n\n"
                        "Сосредоточьтесь на своём вопросе и введите магическое число от 1 до 999:"
                    )
                else:
                    # Пропускаем магическое число - переходим сразу к вопросам
                    random_magic = generate_random_magic_number(user_id)
                    update_data(chat_id, 'magic_number', random_magic)
                    
                    await query.edit_message_text(
                        f"🔮 Привет снова, {user_data['name']}!\n\n"
                        f"🎴 Расклад: {spread_name}\n"
                        f"✨ Таролог: {tariff_name}\n"
                        f"👤 Возраст: {user_data['age']} лет\n\n"
                        "✅ Готовимся к анализу..."
                    )
                    
                    # Создаем псевдо-update для start_preliminary_questions
                    # (функция ожидает message, но мы можем имитировать)
                    from types import SimpleNamespace
                    fake_update = SimpleNamespace()
                    fake_update.message = SimpleNamespace()
                    fake_update.message.reply_text = lambda text, **kwargs: query.message.reply_text(text, **kwargs)
                    
                    await start_preliminary_questions(fake_update, context, chat_id)
            else:
                await query.edit_message_text(
                    "❌ Ошибка загрузки данных",
                    reply_markup=back_button("back_to_main")
                )
        else:
            # Новый пользователь - начинаем регистрацию
            set_state(chat_id, UserState.WAITING_NAME, {
                'spread_type': spread_type,
                'tariff': tariff_key
            })
            
            await query.edit_message_text(
                f"🌟 Добро пожаловать!\n\n"
                f"🎴 Расклад: {spread_name}\n\n"
                "Давайте познакомимся! Как вас зовут?\n"
                "💡 Введите ваше имя (от 2 до 50 символов):"
            )
        
    except Exception as e:
        logger.error(f"Ошибка при выборе тарифа: {e}")
        await query.edit_message_text(
            "❌ Произошла ошибка при выборе тарифа",
            reply_markup=back_button("spreads_list")
        )


async def handle_refill_info(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Показывает информацию о пополнении кредитов
    """
    try:
        query = update.callback_query
        config = load_config()
        limitations = config.get('limitations', {})
        
        message = limitations.get('refill_message', 'В настоящее время возможность пополнить количество раскладов отсутствует.')
        
        await query.edit_message_text(
            f"ℹ️ **Информация о пополнении**\n\n{message}",
            reply_markup=back_button("spreads_list"),
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"Ошибка при показе информации о пополнении: {e}")


async def handle_spread_guide(update: Update, context: ContextTypes.DEFAULT_TYPE, step: int = 1) -> None:
    """
    Показывает гид по раскладам - многошаговое объяснение применения каждого расклада
    
    :param update: Объект обновления от Telegram
    :param context: Контекст бота
    :param step: Номер шага гида (1-5)
    """
    try:
        query = update.callback_query
        
        # Тексты для каждого шага гида
        guide_texts = {
            1: (
                "🤔 Какой расклад выбрать?\n\n"
                "Каждый расклад Таро предназначен для определённых ситуаций. Выбор правильного расклада поможет получить максимально точную и полезную интерпретацию.\n\n"
                "📚 Ниже представлен гид по всем доступным раскладам:"
            ),
            2: (
                "🎴 **ПРОСТЫЕ РАСКЛАДЫ**\n\n"
                "✨ **На одну карту**\n"
                "• Быстрый совет на день\n"
                "• Простой ответ на конкретный вопрос\n"
                "• Первое знакомство с Таро\n"
                "• Ежедневная духовная практика\n"
                "_Примеры: \"Стоит ли принимать это предложение?\", \"На что обратить внимание сегодня?\"_\n\n"
                "🔮 **На три карты (Прошлое-Настоящее-Будущее)**\n"
                "• Понимание развития ситуации во времени\n"
                "• Анализ причин и следствий\n"
                "• Планирование ближайших действий\n"
                "_Примеры: развитие отношений, карьерные изменения, личностный рост_"
            ),
            3: (
                "🎯 **СПЕЦИАЛИЗИРОВАННЫЕ РАСКЛАДЫ**\n\n"
                "🍀 **Подкова (7 карт)**\n"
                "• Планирование и достижение целей\n"
                "• Преодоление препятствий\n"
                "• Комплексный анализ ситуации\n"
                "_Примеры: запуск нового проекта, решение сложных проблем, поиск выхода из кризиса_\n\n"
                "💕 **Любовный треугольник (6 карт)**\n"
                "• Сложные любовные ситуации\n"
                "• Выбор между партнерами\n"
                "• Анализ чувств и эмоций\n"
                "_Примеры: любовный треугольник, неопределённость в отношениях, решение о разводе_"
            ),
            4: (
                "🔍 **ГЛУБОКИЕ РАСКЛАДЫ**\n\n"
                "✟ **Кельтский крест (10 карт)**\n"
                "• Глубокий анализ жизненной ситуации\n"
                "• Комплексные жизненные вопросы\n"
                "• Понимание скрытых мотиваций\n"
                "• Духовный поиск\n"
                "_Примеры: кардинальные изменения в жизни, поиск предназначения, судьбоносные решения_\n\n"
                "📅 **Прогноз на неделю (7 карт)**\n"
                "• Планирование предстоящей недели\n"
                "• Подготовка к важным событиям\n"
                "• Понимание энергий каждого дня\n"
                "_Примеры: важная рабочая неделя, подготовка к экзаменам, период восстановления_"
            ),
            5: (
                "🎡 **ДОЛГОСРОЧНОЕ ПЛАНИРОВАНИЕ**\n\n"
                "🎡 **Колесо года (12 карт)**\n"
                "• Планирование года\n"
                "• Понимание жизненных циклов\n"
                "• Долгосрочные цели и мечты\n"
                "• Духовное развитие на год\n"
                "• Подведение итогов прошедшего года\n\n"
                "**Идеально подходит для:**\n"
                "• Начала нового года\n"
                "• Дня рождения\n"
                "• Важных жизненных рубежей\n"
                "• Планирования карьеры\n"
                "• Семейного планирования\n\n"
                "💡 **Совет:** Выбирайте расклад исходя из глубины вашего вопроса и времени, которое готовы потратить на размышления."
            )
        }
        
        text = guide_texts.get(step, guide_texts[1])
        
        await query.edit_message_text(
            text=text,
            reply_markup=spread_guide_navigation(step),
            parse_mode='Markdown'
        )
        
        logger.info(f"Показан шаг {step} гида по раскладам для пользователя {query.from_user.id}")
        
    except Exception as e:
        logger.error(f"Ошибка при показе гида по раскладам шаг {step}: {e}")
        await query.edit_message_text(
            "❌ Произошла ошибка при загрузке гида",
            reply_markup=back_button("spreads_list")
        )


# Для совместимости с существующим кодом
handle_callback_query = handle_callback