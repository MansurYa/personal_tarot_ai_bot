"""
Простой тест для проверки bot.py
"""
import os
import sys

def test_bot_file():
    """
    Простая проверка bot.py на наличие основных элементов
    """
    print("🧪 Простой тест bot.py")
    
    bot_file = os.path.join(os.path.dirname(__file__), '..', 'src', 'bot.py')
    
    try:
        with open(bot_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Проверяем наличие основных элементов
        checks = [
            ('import logging', 'импорт логирования'),
            ('from telegram import Update', 'импорт telegram'),
            ('async def start_command', 'функция start_command'),
            ('async def help_command', 'функция help_command'),
            ('async def handle_message', 'функция handle_message'),
            ('def run_bot', 'функция run_bot'),
            ('🔮 Добро пожаловать в мир Таро!', 'приветственное сообщение'),
            ('📖 Доступные команды:', 'сообщение помощи'),
            ('✨ Функция в разработке', 'сообщение о разработке'),
            ('application.run_polling', 'запуск polling'),
        ]
        
        all_passed = True
        
        for check, description in checks:
            if check in content:
                print(f"✅ {description}")
            else:
                print(f"❌ Отсутствует: {description}")
                all_passed = False
        
        # Проверяем синтаксис
        try:
            compile(content, bot_file, 'exec')
            print("✅ Синтаксис корректен")
        except SyntaxError as e:
            print(f"❌ Синтаксическая ошибка: {e}")
            all_passed = False
        
        return all_passed
        
    except Exception as e:
        print(f"❌ Ошибка при чтении файла: {e}")
        return False


if __name__ == "__main__":
    print("🚀 Простой тест bot.py\n")
    
    if test_bot_file():
        print("\n🎉 Все проверки прошли успешно!")
        print("✅ Бот готов к запуску с реальным токеном")
    else:
        print("\n❌ Некоторые проверки провалились")
        sys.exit(1)