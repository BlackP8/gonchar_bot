import logging
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    ConversationHandler,
    ContextTypes
)
from datetime import datetime
import sqlite3
import asyncio
import platform

from calendar_service import CalendarService

# Настройки
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

DB_NAME = 'studio_bot.db'
SERVICE, DATE, TIME, NAME, PHONE = range(5)

# Настройки базы данных
DB_NAME = 'studio_bot.db'

# Настройки Google Calendar
SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']
SERVICE_ACCOUNT_FILE = 'service-account.json'
CALENDAR_ID = 'e399d5723974c68bc61d920cbf33537561feaaa765a2ce64f02182b9d0207431@group.calendar.google.com'

# Инициализация сервиса календаря
calendar_service = CalendarService(
    service_account_file=SERVICE_ACCOUNT_FILE,
    calendar_id=CALENDAR_ID,
    scopes=SCOPES
)

# Инициализация базы данных
def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            service_type TEXT,
            date TEXT,
            time TEXT,
            name TEXT,
            phone TEXT,
            is_paid BOOLEAN DEFAULT 0
        )
    ''')
    conn.commit()
    conn.close()

# Показ меню
async def show_main_menu(update: Update):
    keyboard = [
        ['🗓 Расписание', '💰 Прайс-лист'],
        ['📝 Записаться', '💳 Оплата'],
        ['📞 Контакты']
    ]
    await update.message.reply_text(
        'Выберите действие:',
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )

# Команда /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await show_main_menu(update)

# Показ расписания
async def show_schedule(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    events = await calendar_service.get_events()
    if not events:
        await update.message.reply_text("📅 Расписание пока не доступно")
        await show_main_menu(update)
        return

    response = "🕒 *Расписание мастер-классов:*\n\n"
    for event in events:
        start = event['start'].get('dateTime', event['start'].get('date'))
        end = event['end'].get('dateTime', event['end'].get('date'))
        response += (
            f"📅 *{event['summary']}*\n"
            f"🕑 {start} - {end}\n"
            f"{event.get('description', '')}\n\n"
        )

    await update.message.reply_text(response, parse_mode='Markdown')
    await show_main_menu(update)

# Показ прайс-листа
async def show_prices(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    prices = """
💰 *Прайс-лист:*

- Мастер-класс (1 час): 1500 руб.
- Коворкинг (1 час): 800 руб.
- Гончарный курс (5 занятий): 6000 руб.
    """
    await update.message.reply_text(prices, parse_mode='Markdown')
    await show_main_menu(update)

# Начало записи
async def start_booking(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    keyboard = [['Мастер-класс', 'Коворкинг']]
    await update.message.reply_text(
        'Выберите тип услуги:',
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )
    return SERVICE


# Обработка выбора услуги
async def choose_service(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    service = update.message.text
    context.user_data['service'] = service

    # Пример доступных дат (можно заменить на запрос к БД)
    dates = ["2023-12-01", "2023-12-02", "2023-12-03"]
    keyboard = [[date] for date in dates]

    await update.message.reply_text(
        'Выберите дату:',
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )
    return DATE


# Обработка выбора даты
async def choose_date(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    date = update.message.text
    context.user_data['date'] = date

    # Пример доступного времени (можно заменить на запрос к БД)
    times = ["10:00", "14:00", "18:00"]
    keyboard = [[time] for time in times]

    await update.message.reply_text(
        'Выберите время:',
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )
    return TIME


# Обработка выбора времени
async def choose_time(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    time = update.message.text
    context.user_data['time'] = time
    await update.message.reply_text(
        'Введите ваше имя:',
        reply_markup=ReplyKeyboardRemove()
    )
    return NAME


# Обработка имени
async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    name = update.message.text
    context.user_data['name'] = name
    await update.message.reply_text('Введите ваш телефон:')
    return PHONE


# Обработка телефона и сохранение в БД
async def get_phone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    phone = update.message.text
    user_data = context.user_data

    # Сохраняем запись в БД
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO bookings 
        (user_id, service_type, date, time, name, phone)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (
        update.message.from_user.id,
        user_data['service'],
        user_data['date'],
        user_data['time'],
        user_data['name'],
        phone
    ))
    conn.commit()
    conn.close()

    # Отправляем реквизиты
    payment_info = """
💳 *Реквизиты для оплаты:*
СБП: +7 999 123-45-67
Банк: Тинькофф
Получатель: ИП Иванов А.А.

После оплаты отправьте скриншот чека в этот чат.
    """
    await update.message.reply_text(payment_info, parse_mode='Markdown')
    await show_main_menu(update)

    # Уведомление админу
    admin_message = (
        "📌 Новая запись!\n"
        f"Услуга: {user_data['service']}\n"
        f"Дата: {user_data['date']} {user_data['time']}\n"
        f"Имя: {user_data['name']}\n"
        f"Телефон: {phone}"
    )
    context.bot.send_message(chat_id='pashtetics', text=admin_message)
    context.user_data.clear()

    return ConversationHandler.END


# Отмена записи
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text('Запись отменена.', reply_markup=ReplyKeyboardRemove())
    context.user_data.clear()
    await show_main_menu(update)
    return ConversationHandler.END


# Показ реквизитов оплаты
async def show_payment(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    payment_info = """
💳 *Реквизиты для оплаты:*
СБП: +7 999 123-45-67
Банк: Тинькофф
Получатель: ИП Иванов А.А.
    """
    await update.message.reply_text(payment_info, parse_mode='Markdown')
    await show_main_menu(update)


# Контакты
async def show_contacts(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    contacts = """
📞 *Контакты:*
Адрес: ул. Гончарная, 15
Телефон: +7 495 123-45-67
Сайт: artclay.ru
    """
    await update.message.reply_text(contacts, parse_mode='Markdown')
    await show_main_menu(update)

# Обновленный обработчик главного меню
async def handle_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == '🗓 Расписание':
        await show_schedule(update, context)
    elif text == '💰 Прайс-лист':
        await show_prices(update, context)
    elif text == '💳 Оплата':
        await show_payment(update, context)
    elif text == '📞 Контакты':
        await show_contacts(update, context)

async def main() -> None:
    init_db()

    # Создаем Application
    application = ApplicationBuilder().token("8148657023:AAEIWjCxDqVgkqhDKjwRG4-cIJCylc--rV4").build()

    # Регистрируем обработчики
    # Добавляем общий обработчик для главного меню
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(
        filters.Regex('^(🗓 Расписание|💰 Прайс-лист|💳 Оплата|📞 Контакты)$'),
        handle_main_menu
    ))

    # Conversation Handler
    conv_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex('^📝 Записаться$'), start_booking)],
        states={
            SERVICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, choose_service)],
            DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, choose_date)],
            TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, choose_time)],
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_phone)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )
    application.add_handler(conv_handler)

    # Запуск бота
    await application.initialize()
    await application.start()
    await application.updater.start_polling()

    # Бесконечный цикл с обработкой прерывания
    while True:
        await asyncio.sleep(3600)


if __name__ == "__main__":
    if platform.system() == 'Windows':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        print("Бот остановлен")
    finally:
        loop.close()