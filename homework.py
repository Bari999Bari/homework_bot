import logging
import os
import time
from http import HTTPStatus

import requests
import telegram
from dotenv import load_dotenv

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')  # imes`a

retry_time = int(os.getenv('RETRY_TIME'))
endpoint = os.getenv('ENDPOINT')
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

logging.basicConfig(
    level=logging.DEBUG,
    filename='program.log',
    format='%(asctime)s, %(levelname)s, %(message)s, %(name)s'
)


def send_message(bot, message):
    """Отправляет сообщение в чат."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
    except Exception:
        logging.error('Сбой при отправке сообщения')


def get_api_answer(current_timestamp):
    """Делает запрос к серверу."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    try:
        response = requests.get(url=endpoint, headers=HEADERS, params=params)
        if response.status_code != HTTPStatus.OK:
            raise Exception('Ответ API не получен')
        return response.json()
    except requests.RequestException as e:
        print(e)


def check_response(response):
    """Проверяет ответ API на корректность."""
    if not isinstance(response, dict):
        raise TypeError('Формат ответа API отличается от ожидаемого')
    homeworks = response.get('homeworks')
    if homeworks is None:
        raise KeyError('Ответ API не содержит ключ \'homeworks\'')
    if not isinstance(homeworks, list):
        raise TypeError('Тип значения домашки отличается от ожидаемого')
    return homeworks


def parse_status(homework):
    """Извлекает информацию о конкретной работе."""
    homework_name = homework.get('homework_name')
    if homework_name is None:
        raise KeyError('Нет домашней работы с таким именем')
    homework_status = homework.get('status')
    if homework_status is None:
        raise KeyError('Нет статуса домашней работы')
    verdict = HOMEWORK_STATUSES.get(homework_status)
    if verdict is None:
        raise KeyError('Неизвестный статутс домашней работы')
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверяет доступность переменных окружения."""
    token_keys = ['PRACTICUM_TOKEN', 'TELEGRAM_TOKEN', 'TELEGRAM_CHAT_ID']
    condition = True
    for x in token_keys:
        if globals()[x] is None:
            logging.critical(f'Отсутствует обязательная'
                             f' переменная окружения: {x}')
            condition = False
    return condition


def main():
    """Основная логика работы бота."""
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    if not check_tokens():
        logging.critical('Oтсутствие обязательных переменных'
                         ' окружения во время запуска бота')
    else:
        while True:
            try:
                response = get_api_answer(current_timestamp)
                homeworks = check_response(response)
                send_message(bot, parse_status(homeworks[0]))
                logging.info('Сообщение отправлено')
                time.sleep(retry_time)

            except Exception as error:
                logging.error('Недоступность эндпоинта')
                message = f'Сбой в работе программы: {error}'
                send_message(bot, message)
                time.sleep(retry_time)
            else:
                ...


if __name__ == '__main__':
    main()
