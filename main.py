"""
Точка входа для телеграм-бота "Личный Таролог ✨🔮✨"
"""
import sys
from src.config import load_config
from src.bot import run_bot


def main():
    """
    Главная функция для запуска бота
    
    Выполняет:
    - Загрузку конфигурации
    - Проверку наличия токена
    - Запуск бота
    - Обработку graceful shutdown
    """
    try:
        print("🌟 Запуск Личного Таролога...")
        print("=" * 50)
        
        # Загружаем конфигурацию
        print("🔧 Загружаем конфигурацию...")
        config = load_config()
        
        # Проверяем наличие токена
        token = config.get('telegram_bot_token', '').strip()
        if not token:
            print("❌ Ошибка: Токен бота не найден в config.json")
            print("💡 Добавьте действительный токен от @BotFather в поле 'telegram_bot_token'")
            sys.exit(1)
        
        # Выводим информацию о боте
        bot_username = config.get('bot_username', 'Не указан')
        model_name = config.get('model_name', 'Не указан')
        
        print(f"🤖 Bot: {bot_username}")
        print(f"🧠 Model: {model_name}")
        print("=" * 50)
        print("🚀 Бот запущен. Нажмите Ctrl+C для остановки.")
        print("=" * 50)
        
        # Запускаем бота
        run_bot(config)
        
    except KeyboardInterrupt:
        print("\n" + "=" * 50)
        print("🛑 Получен сигнал остановки (Ctrl+C)...")
        print("👋 Бот остановлен")
        print("=" * 50)
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Критическая ошибка при запуске: {e}")
        print("💡 Проверьте конфигурацию и попробуйте снова")
        sys.exit(1)


if __name__ == "__main__":
    main()