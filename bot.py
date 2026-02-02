"""
Telegram-бот с расписанием занятий.
Выбор недели (I/II), расписание привязано к текущему дню недели.
"""

import os
from datetime import datetime

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

from schedule_data import get_schedule, DAY_NAMES, DAY_NAMES_SHORT


BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")

# По умолчанию какая неделя выбрана (1 или 2)
DEFAULT_WEEK = 1


def get_user_week(context: ContextTypes.DEFAULT_TYPE) -> int:
    """Номер выбранной пользователем недели (1 или 2)."""
    return context.user_data.get("week", DEFAULT_WEEK)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Команда /start."""
    user = update.effective_user
    week = get_user_week(context)
    await update.message.reply_text(
        f"Привет, {user.first_name}!\n\n"
        f"Я бот с расписанием. Сейчас выбрана **{week} неделя**.\n\n"
        "Команды:\n"
        "/rasp — расписание на сегодня\n"
        "/rasp пн, /rasp вт, … — расписание на выбранный день\n"
        "/week — выбрать неделю (I или II)",
        parse_mode="Markdown",
    )


async def week_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Команда /week — выбор недели."""
    keyboard = [
        [
            InlineKeyboardButton("I неделя", callback_data="week_1"),
            InlineKeyboardButton("II неделя", callback_data="week_2"),
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    current = get_user_week(context)
    await update.message.reply_text(
        f"Сейчас выбрана: **{current} неделя**.\nВыбери неделю:",
        reply_markup=reply_markup,
        parse_mode="Markdown",
    )


async def week_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка нажатия кнопки выбора недели."""
    query = update.callback_query
    await query.answer()
    if query.data == "week_1":
        context.user_data["week"] = 1
        text = "Выбрана **I неделя**."
    else:
        context.user_data["week"] = 2
        text = "Выбрана **II неделя**."
    await query.edit_message_text(text=text, parse_mode="Markdown")


def format_day_schedule(week_num: int, day: int) -> str:
    """Форматирует расписание на один день."""
    lessons = get_schedule(week_num, day)
    day_name = DAY_NAMES[day]
    week_label = "I" if week_num == 1 else "II"
    header = f"📅 {day_name} ({DAY_NAMES_SHORT[day]}), {week_label} неделя\n\n"
    if not lessons:
        return header + "Занятий нет."
    lines = [f"🕐 {time}\n   {subject}" for time, subject in lessons]
    return header + "\n\n".join(lines)


def parse_day_arg(arg: str) -> int | None:
    """Парсит день из аргумента: пн, вт, ср, чт, пт, сб, вс. Возвращает 0–6 или None."""
    short = ("пн", "вт", "ср", "чт", "пт", "сб", "вс")
    arg = (arg or "").strip().lower()
    for i, name in enumerate(short):
        if name == arg:
            return i
    return None


async def rasp_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Команда /rasp — расписание на сегодня или на указанный день.
    /rasp — на сегодня (по реальному времени)
    /rasp пн, /rasp вт, ... — на выбранный день
    """
    week = get_user_week(context)
    # Есть аргумент — день недели
    if context.args:
        day = parse_day_arg(context.args[0])
        if day is None:
            await update.message.reply_text(
                "Неизвестный день. Напиши: /rasp пн, /rasp вт, /rasp ср, /rasp чт, /rasp пт, /rasp сб, /rasp вс"
            )
            return
    else:
        # Нет аргумента — сегодня (понедельник=0, воскресенье=6)
        day = datetime.now().weekday()
    text = format_day_schedule(week, day)
    await update.message.reply_text(text)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Команда /help."""
    await update.message.reply_text(
        "/start — приветствие\n"
        "/rasp — расписание на **сегодня** (день по реальному времени)\n"
        "/rasp пн, /rasp вт, … — расписание на выбранный день\n"
        "/week — выбрать неделю (I или II)\n"
        "/help — эта справка",
        parse_mode="Markdown",
    )


def main() -> None:
    if not BOT_TOKEN:
        print("Ошибка: нужен токен бота.")
        print("Создай бота у @BotFather в Telegram и задай TELEGRAM_BOT_TOKEN в .env")
        return

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("week", week_command))
    app.add_handler(CommandHandler("rasp", rasp_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CallbackQueryHandler(week_callback, pattern="^week_"))

    print("Бот запущен. Остановка: Ctrl+C")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
