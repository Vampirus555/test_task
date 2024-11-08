Задание:
Для решения описанной проблемы необходимо написать программу на языкеPython, которая будет осуществлять проверку сайта и в случае его отказа информировать об этом пользователя.
Помимо этого, программа должна иметь возможность формирования отчёта за выбранный период мониторинга (1 день, с 00:00:00 до 23:59:59), который содержит в себе uptime сайта и время его простоя за выбранный период.
Для выполнения тестового задания самостоятельно сформируйте перечень, состоящий из 5 организаций, занимающихся банковской или страховой деятельностью, сервисы которых будут проверяться в программе.
При сборе информации необходимо предусмотреть проверку её достоверности.

Описание решения:
*предполагается, что программа стартует в 00:00:00 и работает пока не остановят*
1) Хранение логов реализовано при помощи SQLite (локальная бд на время работы приложения)в одной таблице: status_logs (id, log_date, organization, log_type, time_down, name_code_down, time_up)

2) Первая функция - monitoring_websites. В начале периода (00:00:00) создается первый лог состояния работы сайта для каждой организации. Далее каждые 10 секунд снова отправляем запрос на доступность сайта. Если состояние сайта отлично от предыдущего запроса, это означает, что сайт либо возобновил работу (если ранее был остановлен), либо остановил работу (если ранее работал). В БД создаем запись: дата лога-организация-тип лога-время остановки(если тип лога соответствующий, иначе ничего)-название ошибки (если тип лога соответствующий, иначе ничего)-время восстановления(если тип лога соответствующий, иначе ничего).

3) Вторая функция - monitoring_report. Для каждой организации надо посчитать uptime (в процентах время работы за день) и сумму неработы сайта. Если сайт в течении дня не менял состояния, то по первому логу определяем значения в зависимости от типа лога.
Если несколько записей, значит сайт менял свою работоспособность. Рассчитывать будет через время неработы (т.к. время работы = сутки - время неработы). Ищем лог с типом "down" и если это не последняя запись, то следующий будет "up" и накапливаем сумму разницы возобновления сайта и остановки. Если последняя запись, то смотрим на тип лога. Если "down" то это означает, что до конца дня сайт не работает и считаем, сколько осталось до конца дня. Если же последний лог - "up", то уже накопили сумму неработы сайта. Полученные результаты сохраняем в массив, по которому отрисовываем отчетную таблицу.

4) Принцип работы. После запуска программы открывается второй поток, в котором отрабатывает первая функция (мониторинг сайтов). Это позволяет пользователю, оставаясь в основном потоке при необходимости в любой момент времени может сформировать отчет в виде таблицы по конкретному дню (нужно указывать полную дату).
