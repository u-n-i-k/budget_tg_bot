from telegram import Update, ParseMode
from telegram.ext import (
    Updater,
    CommandHandler,
    MessageHandler,
    Filters,
    ConversationHandler,
    CallbackContext,
)
import traceback
import html
import json
import cv2
import numpy as np
import datetime
import io
import re

import budget
from constants import *


def error_handler(update: object, context: CallbackContext):
    tb_list = traceback.format_exception(None, context.error, context.error.__traceback__)
    tb_string = ''.join(tb_list)

    update_str = update.to_dict() if isinstance(update, Update) else str(update)
    message = (
        f'Got an exception\n'
        f'<pre>update = {html.escape(json.dumps(update_str, indent=2, ensure_ascii=False))}'
        '</pre>\n\n'
        f'<pre>context.chat_data = {html.escape(str(context.chat_data))}</pre>\n\n\n'
        f'<pre>context.user_data = {html.escape(str(context.user_data))}</pre>\n\n\n'
        f'<pre>{html.escape(tb_string)}</pre>'
    )

    context.bot.send_message(chat_id=LOGGER_CHAT_ID, text=message, parse_mode=ParseMode.HTML)


def check_access(update: Update, context: CallbackContext):
    if update.message.from_user.id not in ALLOWED_IDS:
        update.message.reply_text(
            "Вам не разрешено пользоваться этим ботом\n"
            f'По вопросам использования обращайтесь к <a href="tg://user?id={ADMIN_ID}">u-n-i-k</a>',
            parse_mode=ParseMode.HTML
        )
        raise Exception("Unauhorized Access Attempt")
    


def msg_handler(update: Update, context: CallbackContext):
    check_access(update, context)
    user = update.message.from_user
    msg = update.message.text.strip()
    params = None

    if not re.fullmatch(r't=\d+T\d+&s=\d+\.?\d*&fn=\d+&i=\d+&fp=\d+&n=\d+', msg):
        update.message.reply_text("Это не похоже на строку с информацией о чеке")
        return
    j = budget.get_json(msg)
    update.message.reply_text(f"Получил строку с информацией о чеке <pre>{msg}</pre>, обрабатываю", parse_mode=ParseMode.HTML)
    msg = budget.process_json(j)
    update.message.reply_text(msg, parse_mode=ParseMode.HTML)


def photo_handler(update: Update, context: CallbackContext):
    check_access(update, context)

    update.message.reply_text('Получил фото, обрабатываю\n')

    user = update.message.from_user
    photo_file = update.message.photo[-1].get_file()
    msg = update.message.text

    photo_bytes = photo_file.download(out=io.BytesIO())
    nparr = np.frombuffer(photo_bytes.getvalue(), np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_UNCHANGED)
    data, _, _ = cv2.QRCodeDetector().detectAndDecode(img)
        
    if data != '':
        update.message.reply_text(f"Распознан QR код: <pre>{data}</pre>", parse_mode=ParseMode.HTML)
    else:
        update.message.reply_text("Не удалось распознать QR код")
        raise Exception("Error parsing QR code from image")
    
    j = budget.get_json(data)
    msg = budget.process_json(j)
    update.message.reply_text(msg, parse_mode=ParseMode.HTML)
    
    
    



def json_handler(update: Update, context: CallbackContext):
    check_access(update, context)
    update.message.reply_text('Получил json, обрабатываю')
    json_file = update.message.document.get_file()
    json_bytes = json_file.download(out=io.BytesIO())
    j = json.loads(json_bytes.getvalue().decode("utf-8"))
    msg = budget.process_json(j)
    update.message.reply_text(msg, parse_mode=ParseMode.HTML)


def cmd_handler(update: Update, context: CallbackContext):
    check_access(update, context)
    msg = update.message.text
    if msg == "/ping":
        update.message.reply_text('pong')
        return
    if msg == "/cancel":
        update.message.reply_text('Пока. Был рад помочь :)')
        return ConversationHandler.END
    
    update.message.reply_text(
        'Привет! Я - Бот Счетовод\n'
        'Пока я могу только сохранять информацию о ваших тратах\n'
        'Чтобы добавить новый чек пришлите мне одно из:\n'
        '- фото QR-кода с чека\n'
        '- результат сканирования QR-кода с чека\n'
        '- json файл чека из приложения "Проверка чека"\n'
        '"/help" - вывести эту подсказку\n'
        '"/cancel" - для завершения диалога\n'
        f'А вот <a href="{GDRIVE_FOLDER_LINK}">тут</a> хранятся таблички с данными',
        parse_mode=ParseMode.HTML
    )


def retry_failed_imports(context: CallbackContext):
    new_import_status = budget.retry_failed_imports()

    if new_import_status != '':
        context.bot.send_message(chat_id=ADMIN_ID, text=new_import_status, parse_mode=ParseMode.HTML)
        context.bot.send_message(chat_id=FAMILY_BUDGET_CHAT_ID, text=new_import_status)


def main() -> None:
    updater = Updater(TG_TOKEN)

    # Add sheduler for retrying failed imports at 04:00
    updater.job_queue.run_daily(callback=retry_failed_imports, time=datetime.time(hour=4))

    # Add conversation handler
    updater.dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, msg_handler)),
    updater.dispatcher.add_handler(MessageHandler(Filters.photo | Filters.document.category("image"), photo_handler)),
    updater.dispatcher.add_handler(MessageHandler(Filters.document.file_extension("json"), json_handler)),
    updater.dispatcher.add_handler(CommandHandler('ping', cmd_handler)),
    updater.dispatcher.add_handler(CommandHandler('help', cmd_handler)),
    updater.dispatcher.add_handler(CommandHandler('start', cmd_handler)),
    updater.dispatcher.add_handler(CommandHandler('cancel', cmd_handler)),
    updater.dispatcher.add_error_handler(error_handler)

    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
