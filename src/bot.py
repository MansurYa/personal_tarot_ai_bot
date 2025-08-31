"""
Основная логика телеграм-бота "Личный Таролог ✨🔮✨"
"""
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from src.config import load_config
from src.keyboards import main_menu
from src.handlers import handle_callback, handle_text_message
from src.user_manager import init_storage


# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Обработчик команды /start
    Отправляет приветственное сообщение с главным меню
    """
    try:
        welcome_message = (
            "🔮 Добро пожаловать в мир Таро!\n\n"
            "Я ваш личный таролог, готовый приоткрыть завесу будущего.\n\n"
            "✨ Выберите действие:"
        )
        await update.message.reply_text(
            text=welcome_message,
            reply_markup=main_menu()
        )
        logger.info(f"Пользователь {update.effective_user.id} использовал команду /start")
    except Exception as e:
        logger.error(f"Ошибка в start_command: {e}")
        await update.message.reply_text("Произошла ошибка. Попробуйте позже.")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Обработчик команды /help
    Отправляет справку о доступных командах с главным меню
    """
    try:
        help_message = (
            "📖 **Как пользоваться ботом:**\n\n"
            "🔮 Выберите один из 7 типов раскладов таро\n"
            "✨ Ответьте на вопросы для персонализации\n"
            "🎯 Введите магическое число (любое от 1 до 999)\n"
            "🎴 Получите красивый расклад с интерпретацией\n\n"
            "💡 **Доступные команды:**\n"
            "/start - Главное меню\n"
            "/help - Эта справка\n\n"
            "✨ Выберите действие:"
        )
        await update.message.reply_text(
            text=help_message,
            reply_markup=main_menu(),
            parse_mode='Markdown'
        )
        logger.info(f"Пользователь {update.effective_user.id} использовал команду /help")
    except Exception as e:
        logger.error(f"Ошибка в help_command: {e}")
        await update.message.reply_text("Произошла ошибка. Попробуйте позже.")


# Удаляем старый handle_message - заменяем на handle_text_message из handlers.py


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Обработчик ошибок
    Логирует все ошибки, которые происходят в боте
    """
    error_str = str(context.error)
    
    # Проверяем, не является ли это конфликтом polling
    if "Conflict: terminated by other getUpdates request" in error_str:
        logger.warning("Обнаружен конфликт getUpdates - другий экземпляр бота может быть запущен")
        return
    
    # Сетевые ошибки - логируем как warning, не как error
    if any(network_error in error_str.lower() for network_error in [
        "nodename nor servname provided", "server disconnected", 
        "connection", "timeout", "network", "connect"
    ]):
        logger.warning(f"Сетевая ошибка (автоматическое восстановление): {context.error}")
        return
    
    # Ошибки Telegram API - логируем как info  
    if any(tg_error in error_str.lower() for tg_error in [
        "message to delete not found", "message is not modified", 
        "bad request", "forbidden"
    ]):
        logger.info(f"Telegram API уведомление: {context.error}")
        return
    
    # Остальные ошибки логируем как error
    logger.error(f"Исключение при обработке обновления {update}:", exc_info=context.error)


def run_bot(config=None):
    """
    Главная функция запуска телеграм-бота
    
    :param config: Словарь с конфигурацией. Если None, будет загружен из файла
    
    Выполняет:
    - Загрузку конфигурации (если не передана)
    - Инициализацию Application (python-telegram-bot)
    - Регистрацию обработчиков команд и сообщений
    - Запуск polling
    """
    try:
        # Загружаем конфигурацию если не передана
        if config is None:
            print("🔧 Загружаем конфигурацию...")
            config = load_config()
        else:
            print("🔧 Используем переданную конфигурацию...")
        
        # Инициализируем хранилище пользователей
        print("💾 Инициализируем хранилище пользователей...")
        storage_success = init_storage()
        if not storage_success:
            print("❌ Не удалось инициализировать хранилище пользователей")
            print("💡 Проверьте права доступа к папке проекта")
            return
        else:
            print("✅ Хранилище пользователей готово")
        
        # Инициализируем приложение с дополнительными параметрами для устранения конфликтов
        print("🤖 Инициализируем бота...")
        application = (Application.builder()
            .token(config['telegram_bot_token'])
            .read_timeout(30)
            .write_timeout(30)
            .connect_timeout(30)
            .pool_timeout(30)
            .get_updates_read_timeout(30)
            .get_updates_write_timeout(30)
            .get_updates_connect_timeout(30)
            .get_updates_pool_timeout(30)
            .build())
        
        # Регистрируем обработчики команд
        print("📝 Регистрируем обработчики...")
        
        # Команда /start
        application.add_handler(CommandHandler("start", start_command))
        
        # Команда /help
        application.add_handler(CommandHandler("help", help_command))
        
        # Обработчик callback-запросов от inline-кнопок
        application.add_handler(CallbackQueryHandler(handle_callback))
        
        # Обработчик всех текстовых сообщений (кроме команд) - поддерживает пошаговый сбор данных
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))
        
        # Обработчик ошибок
        application.add_error_handler(error_handler)
        
        # Выводим информацию о боте
        bot_username = config.get('bot_username', 'Unknown')
        print(f"🚀 Запускаем бота {bot_username}...")
        print("📱 Доступные команды:")
        print("   /start - Главное меню с inline-кнопками")
        print("   /help - Справка и главное меню")
        print("🎯 Доступные функции:")
        print("   • Меню выбора из 7 раскладов таро")
        print("   • Пошаговый сбор данных пользователя (имя, дата рождения)")
        print("   • Валидация всех видов пользовательского ввода")
        print("   • Автоматическое сохранение и загрузка пользователей")
        print("   • Inline-навигация с кнопками")
        print("   • Подробная справка по каждому раскладу")
        print("💾 Данные пользователей сохраняются в data/users.json")
        print("⚡ Бот готов к работе! Нажмите Ctrl+C для остановки.")
        
        # Запускаем polling с дополнительными параметрами для устранения конфликтов
        print("🔄 Ожидание разрешения возможных конфликтов...")
        application.run_polling(
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True,  # Очищаем pending обновления
            poll_interval=2.0,          # Увеличен интервал polling для стабильности
            timeout=20,                 # Увеличен timeout для getUpdates  
            bootstrap_retries=5         # Количество попыток переподключения
        )
        
    except KeyboardInterrupt:
        print("\n🛑 Получен сигнал остановки...")
        print("👋 Бот остановлен")
    except Exception as e:
        logger.error(f"Критическая ошибка при запуске бота: {e}")
        print(f"❌ Ошибка запуска бота: {e}")
        raise