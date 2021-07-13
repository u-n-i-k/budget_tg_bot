from os import stat
import pygsheets
import pandas as pd
import sqlite3
import traceback
from datetime import datetime

from nalog_ru_api import TicketsAPI
from constants import *


def _create_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute(
        """
        CREATE TABLE statuses (
            qr text PRIMARY KEY,
            import_start_date DATETIME,
            status TEXT,
            import_finish_date DATETIME
        )
        """
    )
    conn.commit()
    c.close()
    conn.close()


def process_json(info):
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    qr = info['qr']
    qr_exists = c.execute("SELECT * FROM statuses WHERE qr = ? AND status = ?", [qr, IMPORT_SUCCEEDED]).fetchall()

    if len(qr_exists) > 0:
        qr_exists = qr_exists[0]
        return f"Данный чек ({qr_exists[0]}) уже был успешно загружен {qr_exists[3]}"
    
    c.execute("UPDATE statuses SET status = ? WHERE qr = ?", ['in progress', qr])
    c.execute("INSERT OR IGNORE INTO statuses(qr, import_start_date, status) VALUES (?, ?, ?)", [qr, datetime.now(), 'in progress'])
    conn.commit()

    items_info = []
    product_keys = ['name', 'price', 'quantity', 'sum']
    columns = ['date', 'seller', 'category'] + product_keys

    try:
        for elem in info if isinstance(info, list) else [info]:
            date = elem['query']['date']
            seller = f"{elem['organization']['name']} (inn: {elem['organization']['inn']})"
            items = elem['ticket']['document']['receipt']['items']

            for item in items:
                item_info = [date, seller, '']
                item_info += [item[key] / 100 if key in ['price', 'sum'] else item[key] for key in product_keys]
                items_info.append(item_info)
        
        msg = []

        filename = elem['query']['date'][:-9]

        for item in items_info:
            msg.append(f"{item[3]}\n x{item[-2]} = {item[-1]}")

        url = save_result_to_gsheet(columns, items_info, filename)
    except Exception as err:
        c.execute("UPDATE statuses SET status = ?, import_finish_date = ? WHERE qr = ?", [traceback.format_exc(), datetime.now(), qr])
        conn.commit()
        raise err
        

    c.execute("UPDATE statuses SET status = ?, import_finish_date = ? WHERE qr = ?", [IMPORT_SUCCEEDED, datetime.now(), qr])
    conn.commit()
    return "Добавлены записи о покупках:\n\n" + "\n\n".join(msg) + f'\n\n Их можно посмотреть <a href="{url}">здесь</a>'


def get_json(qr):
    client = TicketsAPI(
        NALOG_RU_CLIENT_SECRET,
        INN,
        NALOG_RU_PASSWORD
    )
    j = client.get_ticket(qr)
    return j


def retry_failed_imports():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    qrs = c.execute("SELECT qr FROM statuses WHERE status != ?", [IMPORT_SUCCEEDED]).fetchall()
    result = {}
    for qr in qrs:
        qr = qr[0]
        j = get_json(qr)
        status = IMPORT_SUCCEEDED
        finish_date = None
        try:
            result[qr] = process_json(j)
            finish_date = datetime.now()
        except Exception as err:
            result[qr] = status = traceback.format_exc()
        c.execute("UPDATE statuses SET status = ?, import_finish_date = ? WHERE qr = ?", [status, finish_date, qr])
        conn.commit()

    res_msg = []
    for qr in result:
        res_msg.append(
            'Обработано:\n\n' +
            f'<pre>{qr}</pre>\n\n' +
            'Новый статус:\n\n' +
            f'{result[qr]}'
        )
    return ('\n\n' + '#' * 10 + '\n\n').join(res_msg)


def save_result_to_gsheet(columns, items, filename):
    gc = pygsheets.authorize(client_secret=GOOGLE_KEY_FILE)

    is_new = False
    try:
        sh = gc.open(filename)
        try:
            sh.worksheet_by_title('data')
        except:
            sh.delete()
    except:
        is_new = True
        sh = gc.create(filename, folder_name='budget')
        tmpl = gc.open_by_key(TEMPLATE_TABLE_KEY)  # template table
        titles = []
        for ws in tmpl.worksheets():
            titles.append(ws.title)
            sh.add_worksheet(title=ws.title, src_worksheet=ws)
        for ws in sh.worksheets():
            if ws.title not in titles:
                sh.del_worksheet(ws)
    ws = sh.worksheet_by_title('data')
    df = pd.DataFrame(columns=columns) if is_new else ws.get_as_df(has_header=True, index_column=None)

    list_of_series = [pd.Series(row, index=columns) for row in items]
    ws.set_dataframe(df=df.append(list_of_series, ignore_index=True), start='A1')

    return sh.url


if __name__ == '__main__':
    _create_db()