"""
Интеграция LLM алгоритма в handlers
"""

import asyncio
import logging
from typing import List, Optional, Dict, Any
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from src.llm_session import LLMSession, InterpretationStage
from src.prompt_manager import PromptManager
from src.simple_state import UserState, set_state, get_user_data, update_data, reset_to_idle, get_messages_to_delete, clear_messages_to_delete
from src.card_manager import TarotDeck, select_cards
from src.image_generator import ImageGenerator
from src.spread_configs import get_spread_config
from src.user_manager import update_last_spread
from src.config import load_config
from src.progress_bar import create_progress_bar, InterpretationProgress
from src.spread_logger import get_spread_logger
from src.feedback_system import get_feedback_system

logger = logging.getLogger(__name__)

# Инициализируем глобальные объекты
_prompt_manager = None
_image_generator = None
_tarot_deck = None

def get_prompt_manager():
    """Получает глобальный экземпляр PromptManager"""
    global _prompt_manager
    if _prompt_manager is None:
        _prompt_manager = PromptManager(
            prompts_dir="prompts",
            tarot_cards_file="assets/tarot-cards-images-info-ru.json"
        )
    return _prompt_manager

def get_image_generator():
    """Получает глобальный экземпляр ImageGenerator"""
    global _image_generator
    if _image_generator is None:
        _image_generator = ImageGenerator()
    return _image_generator

def get_tarot_deck():
    """Получает глобальный экземпляр TarotDeck"""
    global _tarot_deck
    if _tarot_deck is None:
        _tarot_deck = TarotDeck()
    return _tarot_deck


async def start_llm_interpretation(update: Update, context: ContextTypes.DEFAULT_TYPE,
                                 chat_id: int, session_data: dict, tariff: str = "beginner") -> None:
    """
    Запускает процесс LLM интерпретации после получения всех предварительных данных
    
    :param update: Telegram Update объект
    :param context: Telegram Context объект
    :param chat_id: ID чата пользователя
    :param session_data: Данные сессии пользователя
    :param tariff: Выбранный тариф ("beginner" или "expert")
    """
    try:
        spread_type = session_data.get('spread_type')
        magic_number = session_data.get('magic_number')
        preliminary_answers = session_data.get('preliminary_answers', [])
        
        logger.info(f"Начинаем LLM интерпретацию для пользователя {chat_id}, расклад {spread_type}")
        
        # Создаем прогресс-бар СРАЗУ после ответов на предварительные вопросы
        progress_bar = await create_progress_bar(update, context)
        progress_manager = InterpretationProgress(progress_bar)
        progress_manager.set_update_context(update, context)  # Сохраняем контекст для пересоздания
        await progress_manager.start_preparation()  # 0% - Подготавливаю расклад...
        
        # Подготавливаем данные для LLM
        user_data = {
            'name': session_data.get('name'),
            'age': session_data.get('age')
        }
        
        # ОТКЛАДЫВАЕМ генерацию изображения до финальной стадии - только подготавливаем данные
        
        # Маппинг callback названий в конфигурационные названия
        SPREAD_MAPPING = {
            'spread_single': 'single_card',
            'spread_three': 'three_cards', 
            'spread_horseshoe': 'horseshoe',
            'spread_love': 'love_triangle',
            'spread_celtic': 'celtic_cross',
            'spread_week': 'week_forecast',
            'spread_year': 'year_wheel'
        }
        
        # Подготавливаем данные для генерации карт (но не генерируем изображение)
        mapped_spread_type = SPREAD_MAPPING.get(spread_type, spread_type)
        
        # Выбираем карты без создания изображения
        from src.spread_configs import get_spread_config
        spread_config = get_spread_config(mapped_spread_type)
        if not spread_config:
            await progress_bar.cancel()
            await update.message.reply_text("❌ Ошибка конфигурации расклада. Попробуйте позже.")
            return
            
        tarot_deck = get_tarot_deck()
        selected_cards = select_cards(tarot_deck, spread_config['card_count'], magic_number, chat_id)
        
        # Сохраняем данные расклада (изображение создадим в финале)
        update_data(chat_id, 'selected_cards', selected_cards)
        update_data(chat_id, 'positions', spread_config['positions']) 
        update_data(chat_id, 'spread_config', spread_config)  # Сохраняем конфигурацию для генерации позже
        
        # Создаем лог расклада
        spread_logger = get_spread_logger()
        from src.keyboards import SPREAD_NAMES
        spread_name = SPREAD_NAMES.get(spread_type, "Неизвестный расклад")
        
        log_filepath = spread_logger.create_spread_log(
            chat_id=chat_id,
            user_data=user_data,
            spread_type=spread_type,
            spread_name=spread_name,
            magic_number=session_data.get('magic_number'),
            selected_cards=selected_cards,
            positions=spread_config['positions'],
            telegram_username=session_data.get('telegram_username'),
            telegram_first_name=session_data.get('telegram_first_name'),
            telegram_last_name=session_data.get('telegram_last_name'),
            user_id=session_data.get('user_id')
        )
        
        # Сохраняем путь к логу для дальнейшего использования
        update_data(chat_id, 'log_filepath', log_filepath)
        
        # Логируем предварительные вопросы и ответы
        if session_data.get('questions') and session_data.get('preliminary_answers'):
            preliminary_questions = [q.text for q in session_data.get('questions', {}).questions]
            preliminary_answers = session_data.get('preliminary_answers', [])
            spread_logger.update_preliminary_questions(log_filepath, preliminary_questions, preliminary_answers)
        
        # Подготавливаем данные расклада для LLM
        spread_data = {
            'spread_type': mapped_spread_type,
            'cards': selected_cards,
            'positions': spread_config['positions'],
            'questions': [q.text for q in session_data.get('questions', {}).questions] if session_data.get('questions') else []
        }
        
        # Получаем модель для выбранного тарифа
        config = load_config()
        tariff_plans = config.get('tariff_plans', {})
        tariff_info = tariff_plans.get(tariff, tariff_plans.get('beginner', {}))
        model_name = tariff_info.get('model_name', 'deepseek/deepseek-chat-v3-0324:free')
        
        # Создаем LLM сессию с выбранной моделью
        llm_session = LLMSession(get_prompt_manager(), model_name=model_name)
        update_data(chat_id, 'llm_session', llm_session)
        
        # Запускаем первую часть интерпретации
        try:
            questions, _ = await llm_session.run_full_interpretation(
                user_data=user_data,
                spread_data=spread_data,
                preliminary_answers=preliminary_answers
            )
        except Exception as llm_error:
            # Обработка ошибок OpenRouter API
            await handle_llm_error(update, context, chat_id, llm_error)
            return
        
        if questions:
            # LLM сгенерировал уточняющие вопросы
            update_data(chat_id, 'llm_questions', questions)
            update_data(chat_id, 'current_llm_question', 0)
            update_data(chat_id, 'llm_answers', [])
            update_data(chat_id, 'progress_manager', progress_manager)  # Сохраняем для продолжения
            
            # Обновляем прогресс до 25% после генерации вопросов
            await progress_manager.complete_llm_questions_generation()  # 25%
            
            set_state(chat_id, UserState.WAITING_LLM_QUESTIONS)
            
            await update.message.reply_text(
                f"❓ У меня есть несколько уточняющих вопросов для более точной интерпретации:\n\n"
                f"**Вопрос 1 из {len(questions)}:**\n"
                f"{questions[0]}",
                parse_mode='Markdown'
            )
            
            logger.info(f"LLM сгенерировал {len(questions)} уточняющих вопросов для пользователя {chat_id}")
        else:
            # Нет дополнительных вопросов - продолжаем с тем же прогресс-баром
            update_data(chat_id, 'progress_manager', progress_manager)
            await progress_manager.complete_llm_questions_generation()  # 25%
            
            # Получаем обновленные данные сессии с LLM объектом
            updated_session_data = get_user_data(chat_id)
            await continue_final_interpretation(update, context, chat_id, updated_session_data)
            
    except Exception as e:
        logger.error(f"Ошибка при запуске LLM интерпретации для пользователя {chat_id}: {e}")
        await update.message.reply_text(
            "❌ Произошла ошибка при анализе вашего расклада. Попробуйте позже."
        )


async def process_llm_questions(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обрабатывает ответы на уточняющие вопросы от LLM"""
    try:
        chat_id = update.effective_chat.id
        user_input = update.message.text.strip()
        session_data = get_user_data(chat_id)
        
        llm_questions = session_data.get('llm_questions', [])
        current_question = session_data.get('current_llm_question', 0)
        llm_answers = session_data.get('llm_answers', [])
        
        # Сохраняем ответ
        llm_answers.append(user_input)
        update_data(chat_id, 'llm_answers', llm_answers)
        
        # Проверяем, есть ли еще вопросы
        if current_question + 1 < len(llm_questions):
            # Переходим к следующему вопросу
            next_question = current_question + 1
            update_data(chat_id, 'current_llm_question', next_question)
            
            await update.message.reply_text(
                f"✅ Спасибо за ответ!\n\n"
                f"**Вопрос {next_question + 1} из {len(llm_questions)}:**\n"
                f"{llm_questions[next_question]}",
                parse_mode='Markdown'
            )
        else:
            # Все вопросы отвечены - переходим к финальной интерпретации
            await continue_final_interpretation(update, context, chat_id, session_data)
            
    except Exception as e:
        logger.error(f"Ошибка при обработке LLM вопросов для пользователя {chat_id}: {e}")
        await update.message.reply_text("❌ Ошибка при обработке ответа. Попробуйте еще раз:")


async def continue_final_interpretation(update: Update, context: ContextTypes.DEFAULT_TYPE,
                                       chat_id: int, session_data: dict) -> None:
    """Продолжает финальную генерацию интерпретации с существующим прогресс-баром"""
    try:
        set_state(chat_id, UserState.PROCESSING_INTERPRETATION)
        
        llm_session = session_data.get('llm_session')
        llm_answers = session_data.get('llm_answers', [])
        log_filepath = session_data.get('log_filepath')
        progress_manager = session_data.get('progress_manager')
        
        if not llm_session:
            raise ValueError("LLM сессия не найдена")
        
        if not progress_manager:
            # Создаем новый прогресс-бар если его нет
            progress_bar = await create_progress_bar(update, context)
            progress_manager = InterpretationProgress(progress_bar)
            await progress_manager.complete_llm_questions_generation()  # 25%
        
        # Запускаем генерацию с прогресс-баром
        try:
            interpretation = await generate_interpretation_with_visual_progress(
                llm_session, llm_answers, progress_manager, log_filepath
            )
            
            # Завершаем прогресс-бар
            await progress_manager.finish()
            
        except Exception as llm_error:
            # Логируем ошибку
            if log_filepath:
                spread_logger = get_spread_logger()
                spread_logger.log_llm_error(log_filepath, str(llm_error), "final_interpretation")
            
            # Отменяем прогресс-бар при ошибке
            await progress_manager.cancel()
            await handle_llm_error(update, context, chat_id, llm_error)
            return
        
        if interpretation:
            # Отправляем финальную интерпретацию С ИЗОБРАЖЕНИЕМ
            await send_final_interpretation_with_image(update, context, chat_id, interpretation, session_data)
        else:
            await update.message.reply_text(
                "❌ Не удалось сгенерировать интерпретацию. Попробуйте позже."
            )
            
    except Exception as e:
        logger.error(f"Ошибка при генерации финальной интерпретации для пользователя {chat_id}: {e}")
        await update.message.reply_text("❌ Ошибка при генерации интерпретации.")


async def generate_interpretation_with_visual_progress(llm_session: LLMSession, 
                                                    llm_answers: List[str],
                                                    progress_manager: InterpretationProgress,
                                                    log_filepath: str = None) -> Optional[str]:
    """Генерирует финальную интерпретацию с визуальным прогресс-баром"""
    try:
        # Логируем начало LLM обработки
        if log_filepath:
            spread_logger = get_spread_logger()
            spread_logger.start_llm_processing(log_filepath, llm_session.agent.model_name)
        
        # Пересоздаем прогресс-бар после завершения всех вопросов для лучшей видимости
        recreated = await progress_manager.recreate_progress_bar(25)
        if not recreated:
            await progress_manager.progress_bar.update_progress(25)
        
        # Этап 1: 25-50% - Анализ контекста (промпт 04)
        await progress_manager.start_context_analysis()
        
        await llm_session.add_question_answers(llm_answers)
        success = await llm_session.generate_context_analysis()
        if not success:
            return None
            
        await progress_manager.complete_context_analysis()
        
        # Этап 2: 50-75% - Синтез (промпт 05)
        await progress_manager.start_synthesis()
        
        success = await llm_session.generate_synthesis()
        if not success:
            return None
            
        await progress_manager.complete_synthesis()
        
        # Этап 3: 75-100% - Финальная интерпретация (промпт 06)
        await progress_manager.start_final_interpretation()
        
        interpretation = await llm_session.generate_final_interpretation()
        
        await progress_manager.complete_final_interpretation()
        
        return interpretation
        
    except Exception as e:
        logger.error(f"Ошибка при генерации интерпретации с визуальным прогрессом: {e}")
        return None


async def cleanup_chat_messages(update: Update, context: ContextTypes.DEFAULT_TYPE, chat_id: int) -> None:
    """Удаляет все промежуточные сообщения из чата"""
    try:
        messages_to_delete = get_messages_to_delete(chat_id)
        if messages_to_delete:
            logger.info(f"Удаляем {len(messages_to_delete)} промежуточных сообщений для чата {chat_id}")
            
            for message_id in messages_to_delete:
                try:
                    await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
                    await asyncio.sleep(0.1)  # Небольшая задержка между удалениями
                except Exception as e:
                    # Сообщение уже могло быть удалено или недоступно
                    logger.warning(f"Не удалось удалить сообщение {message_id}: {e}")
            
            # Очищаем список после удаления
            clear_messages_to_delete(chat_id)
            logger.info(f"Очистка чата завершена для {chat_id}")
    except Exception as e:
        logger.error(f"Ошибка при очистке чата: {e}")


async def send_final_interpretation_with_image(update: Update, context: ContextTypes.DEFAULT_TYPE,
                                              chat_id: int, interpretation: str, session_data: dict) -> None:
    """Отправляет финальное сообщение с изображением и интерпретацией"""
    try:
        # СНАЧАЛА ОЧИЩАЕМ ЧАТ ОТ ПРОМЕЖУТОЧНЫХ СООБЩЕНИЙ
        await cleanup_chat_messages(update, context, chat_id)
        # ГЕНЕРИРУЕМ ИЗОБРАЖЕНИЕ ТОЛЬКО СЕЙЧАС!
        spread_config = session_data.get('spread_config')
        selected_cards = session_data.get('selected_cards', [])
        
        if spread_config and selected_cards:
            # Генерируем изображение в финале
            image_generator = get_image_generator()
            image_bytes = image_generator.generate_spread_image(
                background_id=spread_config['background_id'],
                cards=selected_cards,
                positions=spread_config['positions'], 
                scale=spread_config['scale']
            )
        else:
            image_bytes = None
        
        # Создаём описание карт
        cards_description = "🎴 Выпавшие карты:\n"
        for i, card in enumerate(selected_cards, 1):
            cards_description += f"{i}. {card['name']}\n"
            
        # Обрезаем длинную интерпретацию для caption
        config = load_config()
        max_caption_length = 1024  # Telegram limit for captions
        
        # Формат финального сообщения (убираем лишнюю строку "Интерпретация:")
        full_message = f"🎴 {cards_description}\n{interpretation}"
        
        # Отправляем сообщения с увеличенным таймаутом и повторными попытками
        from telegram.constants import ParseMode
        from telegram.error import TimedOut, NetworkError
        
        MAX_RETRIES = 3
        TIMEOUT = 60  # 60 секунд вместо стандартных 20
        
        for attempt in range(MAX_RETRIES):
            try:
                if image_bytes:
                    if len(full_message) <= max_caption_length:
                        # Отправляем всё одним сообщением
                        await asyncio.wait_for(
                            update.message.reply_photo(
                                photo=image_bytes,
                                caption=full_message,
                                read_timeout=TIMEOUT,
                                write_timeout=TIMEOUT,
                                connect_timeout=TIMEOUT,
                                pool_timeout=TIMEOUT
                            ),
                            timeout=TIMEOUT
                        )
                    else:
                        # Отправляем изображение с кратким caption
                        await asyncio.wait_for(
                            update.message.reply_photo(
                                photo=image_bytes,
                                caption=cards_description,
                                read_timeout=TIMEOUT,
                                write_timeout=TIMEOUT,
                                connect_timeout=TIMEOUT,
                                pool_timeout=TIMEOUT
                            ),
                            timeout=TIMEOUT
                        )
                        await asyncio.sleep(0.3)
                        
                        # Отправляем интерпретацию отдельным сообщением
                        max_text_length = config.get("max_message_length", 4096)
                        interpretation_text = interpretation
                        
                        if len(interpretation_text) <= max_text_length:
                            await asyncio.wait_for(
                                update.message.reply_text(
                                    interpretation_text,
                                    read_timeout=TIMEOUT,
                                    write_timeout=TIMEOUT,
                                    connect_timeout=TIMEOUT,
                                    pool_timeout=TIMEOUT
                                ),
                                timeout=TIMEOUT
                            )
                        else:
                            # Разбиваем на части
                            parts = split_long_message(interpretation_text, max_text_length)
                            for i, part in enumerate(parts):
                                await asyncio.wait_for(
                                    update.message.reply_text(
                                        part,
                                        read_timeout=TIMEOUT,
                                        write_timeout=TIMEOUT,
                                        connect_timeout=TIMEOUT,
                                        pool_timeout=TIMEOUT
                                    ),
                                    timeout=TIMEOUT
                                )
                                if i < len(parts) - 1:
                                    await asyncio.sleep(0.5)
                else:
                    # Нет изображения - отправляем только текст
                    await asyncio.wait_for(
                        update.message.reply_text(
                            full_message,
                            read_timeout=TIMEOUT,
                            write_timeout=TIMEOUT,
                            connect_timeout=TIMEOUT,
                            pool_timeout=TIMEOUT
                        ),
                        timeout=TIMEOUT
                    )
                
                # Если дошли сюда - отправка успешна
                break
                
            except (TimedOut, NetworkError, asyncio.TimeoutError) as e:
                if attempt < MAX_RETRIES - 1:
                    logger.warning(f"Попытка {attempt + 1} отправить сообщение пользователю {chat_id} не удалась: {e}. Повторяем...")
                    await asyncio.sleep(2 ** attempt)  # Экспоненциальная задержка
                    continue
                else:
                    logger.error(f"Все попытки отправить сообщение пользователю {chat_id} исчерпаны: {e}")
                    # Отправляем упрощенное уведомление
                    try:
                        await update.message.reply_text(
                            "⚠️ Интерпретация готова, но произошла ошибка при отправке изображения. "
                            "Попробуйте создать новый расклад.",
                            read_timeout=30,
                            write_timeout=30
                        )
                    except:
                        pass
                    return
            
        # Логируем завершение интерпретации
        log_filepath = session_data.get('log_filepath')
        if log_filepath:
            spread_logger = get_spread_logger()
            spread_logger.complete_interpretation(log_filepath, interpretation)
            
            # Логируем LLM вопросы и ответы если есть
            llm_questions = session_data.get('llm_questions', [])
            llm_answers = session_data.get('llm_answers', [])
            if llm_questions:
                spread_logger.update_llm_questions(log_filepath, llm_questions, llm_answers)
        
        # Запрашиваем обратную связь через систему обратной связи
        feedback_system = get_feedback_system()
        await feedback_system.request_feedback(update, context, chat_id)
        
        # Обновляем время последнего расклада
        update_last_spread(chat_id)
        
        logger.info(f"Интерпретация с изображением отправлена пользователю {chat_id}")
        
    except Exception as e:
        logger.error(f"Ошибка при отправке финального сообщения пользователю {chat_id}: {e}")
        # Уведомляем пользователя об ошибке
        try:
            await update.message.reply_text(
                "❌ Произошла ошибка при отправке интерпретации. Попробуйте создать новый расклад.",
                read_timeout=30,
                write_timeout=30
            )
        except:
            pass


async def send_final_interpretation(update: Update, context: ContextTypes.DEFAULT_TYPE,
                                  chat_id: int, interpretation: str) -> None:
    """Отправляет финальную интерпретацию и запрашивает обратную связь"""
    try:
        # Разбиваем длинное сообщение если нужно
        config = load_config()
        max_length = config.get("max_message_length", 4096)
        
        if len(interpretation) > max_length:
            # Разбиваем на части
            parts = split_long_message(interpretation, max_length)
            for i, part in enumerate(parts):
                if i == 0:
                    await update.message.reply_text(f"🔮 **ВАША ИНТЕРПРЕТАЦИЯ:**\n\n{part}", parse_mode='Markdown')
                else:
                    await update.message.reply_text(part, parse_mode='Markdown')
                await asyncio.sleep(0.5)  # Небольшая пауза между сообщениями
        else:
            await update.message.reply_text(f"🔮 **ВАША ИНТЕРПРЕТАЦИЯ:**\n\n{interpretation}", parse_mode='Markdown')
        
        # Логируем завершение интерпретации
        session_data = get_user_data(chat_id)
        log_filepath = session_data.get('log_filepath')
        
        if log_filepath:
            spread_logger = get_spread_logger()
            spread_logger.complete_interpretation(log_filepath, interpretation)
            
            # Логируем LLM вопросы и ответы если есть
            llm_questions = session_data.get('llm_questions', [])
            llm_answers = session_data.get('llm_answers', [])
            if llm_questions:
                spread_logger.update_llm_questions(log_filepath, llm_questions, llm_answers)
        
        # Запрашиваем обратную связь через систему обратной связи
        feedback_system = get_feedback_system()
        await feedback_system.request_feedback(update, context, chat_id)
        
        # Обновляем время последнего расклада
        update_last_spread(chat_id)
        
        logger.info(f"Интерпретация отправлена пользователю {chat_id}")
        
    except Exception as e:
        logger.error(f"Ошибка при отправке интерпретации пользователю {chat_id}: {e}")


async def generate_spread_image(spread_type: str, magic_number: int, chat_id: int) -> Optional[tuple]:
    """Генерирует изображение расклада"""
    try:
        # Маппинг от callback_data к конфигурациям
        SPREAD_MAPPING = {
            'spread_single': 'single_card',
            'spread_three': 'three_cards', 
            'spread_horseshoe': 'horseshoe',
            'spread_love': 'love_triangle',
            'spread_celtic': 'celtic_cross',
            'spread_week': 'week_forecast',
            'spread_year': 'year_wheel'
        }
        
        # Конвертируем ключ расклада
        config_key = SPREAD_MAPPING.get(spread_type, spread_type)
        
        # Получаем конфигурацию расклада
        spread_config = get_spread_config(config_key)
        if not spread_config:
            logger.error(f"Конфигурация расклада {config_key} (callback: {spread_type}) не найдена")
            return None
            
        # Выбираем карты
        tarot_deck = get_tarot_deck()
        selected_cards = select_cards(tarot_deck, spread_config['card_count'], magic_number, chat_id)
        
        # Генерируем изображение
        image_generator = get_image_generator()
        
        image_bytes = image_generator.generate_spread_image(
            background_id=spread_config['background_id'],
            cards=selected_cards,
            positions=spread_config['positions'], 
            scale=spread_config['scale']
        )
        
        return image_bytes, selected_cards, spread_config['positions']
        
    except Exception as e:
        logger.error(f"Ошибка при генерации изображения расклада: {e}")
        return None


# Оставляем эту функцию для совместимости, но она больше не используется
async def send_spread_image(update: Update, context: ContextTypes.DEFAULT_TYPE,
                          image_bytes, selected_cards: List[Dict], spread_type: str) -> None:
    """Отправляет изображение расклада пользователю (устаревшая)"""
    try:
        # Создаем описание карт
        cards_description = "🎴 **Выпавшие карты:**\n"
        for i, card in enumerate(selected_cards, 1):
            cards_description += f"{i}. {card['name']}\n"
            
        await update.message.reply_photo(
            photo=image_bytes,
            caption=f"🔮 **Ваш расклад готов!**\n\n{cards_description}",
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"Ошибка при отправке изображения расклада: {e}")


# Новая функция для обратной совместимости
async def start_final_interpretation(update: Update, context: ContextTypes.DEFAULT_TYPE,
                                   chat_id: int, session_data: dict) -> None:
    """Обратная совместимость - перенаправляет к continue_final_interpretation"""
    await continue_final_interpretation(update, context, chat_id, session_data)


def split_long_message(text: str, max_length: int) -> List[str]:
    """Разбивает длинное сообщение на части"""
    if len(text) <= max_length:
        return [text]
    
    parts = []
    current_part = ""
    
    # Разбиваем по параграфам
    paragraphs = text.split('\n\n')
    
    for paragraph in paragraphs:
        if len(current_part) + len(paragraph) + 2 <= max_length:
            if current_part:
                current_part += '\n\n' + paragraph
            else:
                current_part = paragraph
        else:
            if current_part:
                parts.append(current_part)
                current_part = paragraph
            else:
                # Параграф слишком длинный - разбиваем по предложениям
                sentences = paragraph.split('. ')
                for sentence in sentences:
                    if len(current_part) + len(sentence) + 2 <= max_length:
                        if current_part:
                            current_part += '. ' + sentence
                        else:
                            current_part = sentence
                    else:
                        if current_part:
                            parts.append(current_part)
                        current_part = sentence
    
    if current_part:
        parts.append(current_part)
    
    return parts


async def handle_llm_error(update: Update, context: ContextTypes.DEFAULT_TYPE, 
                          chat_id: int, error: Exception, progress_message=None) -> None:
    """Обрабатывает ошибки OpenRouter API и уведомляет пользователя"""
    from src.openrouter_client import OpenRouterError
    from src.keyboards import main_menu
    
    error_str = str(error).lower()
    
    # Определяем тип ошибки
    if isinstance(error, OpenRouterError):
        if 'rate limit' in error_str or 'too many requests' in error_str:
            error_message = (
                "⏸️ **Сервер временно перегружен**\n\n"
                "Слишком много запросов к нейросети. Пожалуйста, попробуйте через несколько минут.\n\n"
                "🔄 Ваш расклад сохранен, можете вернуться к нему позже."
            )
        elif 'insufficient credits' in error_str or 'balance' in error_str:
            error_message = (
                "💳 **Временные технические проблемы**\n\n"
                "К сожалению, сейчас не могу сгенерировать интерпретацию. Попробуйте позже.\n\n"
                "🎴 Ваш расклад готов, интерпретация появится при следующем обращении."
            )
        elif 'timeout' in error_str or 'connection' in error_str:
            error_message = (
                "⏱️ **Превышено время ожидания**\n\n"
                "Нейросеть слишком долго генерирует ответ. Попробуйте еще раз.\n\n"
                "🔄 Обычно это занимает меньше времени."
            )
        else:
            error_message = (
                "🤖 **Технические неполадки**\n\n"
                "Произошла ошибка при обращении к нейросети. Попробуйте позже.\n\n"
                "⚙️ Мы работаем над устранением проблемы."
            )
    else:
        error_message = (
            "❌ **Не удалось создать интерпретацию**\n\n"
            "Произошла неожиданная ошибка. Попробуйте создать расклад заново.\n\n"
            "🔧 Если проблема повторяется, обратитесь к разработчику."
        )
    
    logger.error(f"LLM ошибка для пользователя {chat_id}: {error}")
    
    # Удаляем прогресс-бар если есть
    if progress_message:
        try:
            await progress_message.delete()
        except:
            pass
    
    # Отправляем сообщение об ошибке
    await update.message.reply_text(
        error_message,
        reply_markup=main_menu(),
        parse_mode='Markdown'
    )
    
    # Очищаем состояние пользователя
    from src.simple_state import reset_to_idle
    reset_to_idle(chat_id, keep_data=False)