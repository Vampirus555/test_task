import requests
import threading
from urllib.error import HTTPError
import sqlite3
from datetime import datetime
import time
from tabulate import tabulate
import pandas as pd

# функция создания локальной БД в памяти
def create_db():
    # Создаем БД в памяти
    db_name = "Monitoring"
    db = sqlite3.connect(db_name)
    cur = db.cursor()

    # Создаем в БД таблицу organizations
    cur.execute("""CREATE TABLE IF NOT EXISTS organizations (
                        id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    				    name TEXT,
    				    domain TEXT
                )""")
    db.commit()

    # Создаем в БД таблицу status_logs
    cur.execute("""CREATE TABLE IF NOT EXISTS status_logs (
    				    id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    				    log_date TEXT,
    				    organization TEXT,
				        log_type TEXT,
				        time_down TEXT,
				        name_code_down TEXT,
				        time_up TEXT
				)""")
    db.commit()

    # Перечень организаций
    organizations_data = [
        ("absolutbank", "https://absolutbank.ru/"),
        ("akcept", "https://www.akcept.ru/"),
        ("blanc", "https://blanc.ru/"),
        ("absolutins", "https://www.absolutins.ru/"),
        ("ingos", "https://www.ingos.ru/")
    ]

    # Добавляем в таблицу БД записи об организациях
    cur.executemany("INSERT INTO organizations (name, domain) VALUES (?, ?)", organizations_data)
    db.commit()


# функция мониторинга сайтов организаций
def monitor_websites():
    # подключаемся к БД
    db = sqlite3.connect("Monitoring")
    cur = db.cursor()

    # получаем организации, которые будем мониторить
    cur.execute("SELECT name, domain FROM organizations")
    organizations_data = cur.fetchall()

    send_requests_time = 10
    last_status = []
    current_status = None
    log_type = [('up'), ('down')]
    while True:
        # получаем текущую дату и время
        current_date = datetime.today().strftime("%Y-%m-%d")
        current_time = datetime.now().strftime("%H:%M:%S")
        for i in range(len(organizations_data)):
            response = requests.get(organizations_data[i][1])

            # ветка условия, если сайт не работает
            if response.status_code != 200:
                # если начало периода (дня)
                if current_time == "00:00:00":
                    last_status[i] = 'down'
                    cur.execute("""INSERT INTO status_logs (
                                        log_date, organization, log_type, time_down, name_code_down, time_up
                                    ) VALUES (
                                        ?, ?, ?, ?, ?, ?
                                    )
                                """, (current_date, organizations_data[i][0], log_type[1], current_time, response.reason, None))
                    db.commit()
                # если внутри периода 
                else:
                    current_status = 'down'
                    #если текущий статус неравен предыдущему, значит произошла смена статуса и записываем лог
                    if current_status!=last_status[i]:  
                        cur.execute("""INSERT INTO status_logs (
                                            log_date, organization, log_type, time_down, name_code_down, time_up
                                        ) VALUES (
                                            ?, ?, ?, ?, ?, ?
                                        )
                                    """, (current_date, organizations_data[i][0], log_type[1], current_time, response.reason, None))
                        db.commit()

            # ветка условия, если сайт работает
            else:
                # если начало периода (дня)
                if current_time == "00:00:00":
                    last_status[i] = 'up'
                    cur.execute("""INSERT INTO status_logs (
                                        log_date, organization, log_type, time_down, name_code_down, time_up
                                    ) VALUES (
                                        ?, ?, ?, ?, ?, ?
                                    )
                                """, (current_date, i[0], log_type[0], None, None, current_time))
                    db.commit()
                # если внутри периода 
                else:
                    current_status = 'up'
                    #если текущий статус неравен предыдущему, значит произошла смена статуса и записываем лог
                    if current_status!=last_status[i]:
                        cur.execute("""INSERT INTO status_logs (
                                            log_date, organization, log_type, time_down, name_code_down, time_up
                                        ) VALUES (
                                            ?, ?, ?, ?, ?, ?
                                        )
                                    """, (current_date, i[0], log_type[0], None, None, current_time))
                        db.commit()

                
            current_status = None
        time.sleep(send_requests_time)


def monitoring_report(date):
    # подключаемся к БД
    db = sqlite3.connect("Monitoring")
    cur = db.cursor()

    # получение организаций
    cur.execute("SELECT name FROM organizations")
    organizations_data = cur.fetchall()

    results = []

    # получение записей за указанную дату для каждой организации
    for organization in organizations_data:
        cur.execute("SELECT organization, log_type, time_down, time_up FROM status_logs WHERE log_date = ? AND organization = ?",(date, organization))
        # ..[0] - organization, ..[1] - log_type, ..[2] - time_down, ..[3] - time_up,
        log_data = cur.fetchall()
        len_rows = len(log_data)
        
        sum_down = 0
        uptime = 0

        for i in range(len_rows):
            # если для организации за отчетный период только стартовый лог
            if len_rows == 1:
                # если лог up, то сайт работает весь день
                if log_data[i][1] == 'up': 
                    uptime = 100,00
                    results.append((organization, uptime, sum_down))
                # если лог down, то сайт не работает весь день
                else:
                    sum_down = 86400
                    # сохраняем рассчитанные данные для рассматриевамой организации
                    results.append((organization, uptime, sum_down))
            # если для организации за отчетный период несколько логов
            else:
                # если запись не последняя
                if i != (len_rows-1):
                    # если лог down, то следующий будет up и накапливаем сумму неработы (time_up - time_down)
                    if log_data[i][1] == 'down':
                        start_down =  datetime.strptime(log_data[i][2], "%H:%M:%S")
                        end_down = datetime.strptime(log_data[i+1][3], "%H:%M:%S")
                        diff_time = 0

                        diff_time = end_down - start_down
                        sum_down += diff_time.total_seconds()
                # если запись последняя
                elif i == (len_rows-1):
                    # если лог down, то дорассчитываем время неработы как разницу конца периода и time_down
                    if log_data[i][1] == 'down':
                        start_down =  datetime.strptime(log_data[i][2], "%H:%M:%S")
                        end_down = datetime.strptime("23:59:59", "%H:%M:%S")
                        diff_time = 0

                        diff_time = end_down - start_down
                        sum_down += diff_time.total_seconds()
                        # uptime = непрерывная работа (время периода - время неработы)/время периода * 100%
                        uptime = (86400 - sum_down)/86400*100
                        # сохраняем рассчитанные данные для рассматриевамой организации
                        results.append((organization, round(uptime,2), sum_down))
                    # если лог up, то уже нашли накопленное время неработы за период
                    else:
                        # uptime = непрерывная работа (время периода - время неработы)/время периода * 100%
                        uptime = (86400 - sum_down)/86400*100
                        # сохраняем рассчитанные данные для рассматриевамой организации
                        results.append((organization, round(uptime,2), sum_down))

    
    # формирование отчетной таблицы
    headers = ["organization", "uptime, %", "sum_down, sec"]
    table = tabulate(results, headers=headers, tablefmt="grid")
    print(table)




def main():
    create_db()


    # создаем поток, в котором будет выполнятсья мониторинг сайтов организаций
    monitor_thread = threading.Thread(target=monitor_websites)
    monitor_thread.start()

    while True:
        # вывод меню
        print("""
Меню:
    1. Создать отчет
    2. Завершить программу
    """)
        # выбор пункта меню
        num_menu = int(input("Введите дату в числовом формате год-месяц-день: "))
        # если выбрали создание отчета, то указываем нужную дату и получаем таблицу
        if num_menu == 1:
            date = input("Введите дату в числовом формате год-месяц-день: ")
            monitoring_report(datetime.strptime(date, "%Y-%m-%d"))
        # если выбрали завершение программы, то останавливаем поток с мониторингом и после этого завершаем полностью программу
        elif num_menu == 2:
            monitor_thread.join()
            break


if __name__ == "__main__":
    main()