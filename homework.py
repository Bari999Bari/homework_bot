import json
import logging
import os
import time
from http import HTTPStatus

import requests
import telegram
from dotenv import load_dotenv
from telegram import TelegramError

load_dotenv()

PRACTICUM_TOKEN = os.getenv(
    'PRACTICUM_TOKEN',
    default='AQAAAAA8HY7DAqwertVXY0SlJcccl0FGNmamhC0')
TELEGRAM_TOKEN = os.getenv(
    'TELEGRAM_TOKEN',
    default='5315268360:AAEfgvertY-JdffR2aiK6m920KSd9fZddw')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID', default=999999)  # imes`a

RETRY_TIME = int(os.getenv('RETRY_TIME', default=888))
ENDPOINT = os.getenv(
    'ENDPOINT',
    default='https://practicum.yandex.ru/api/user_api/homework_statuses/')
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
    except TelegramError:
        logging.error('Сбой при отправке сообщения')


def get_api_answer(current_timestamp):
    """Делает запрос к серверу."""
    params = {'from_date': current_timestamp}
    try:
        response = requests.get(url=ENDPOINT, headers=HEADERS, params=params)
        if response.status_code != HTTPStatus.OK:
            raise Exception('Ответ API не получен')
        return response.json()
    except requests.RequestException:
        raise Exception('Сервер не отвечает')
        # logging.error('Сервер не отвечает')
    except json.decoder.JSONDecodeError:
        raise Exception('Ошибка преобразования в JSON')


def check_response(response):
    """Проверяет ответ API на корректность."""
    if not isinstance(response, dict):
        raise TypeError('Формат ответа API отличается от ожидаемого')
    homeworks = response.get('homeworks')
    if homeworks is None:
        raise KeyError('Ответ API не содержит ключ \'homeworks\'')
    if not isinstance(homeworks, list):
        raise TypeError('Тип значения домашних работ отличается от ожидаемого')
    return homeworks


def parse_status(homework):
    """Извлекает информацию о конкретной работе."""
    if not isinstance(homework, dict):
        raise TypeError(
            f'Тип значения домашки {type(homework)},'
            f'ожидаемый тип dict')
    else:
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
        if globals().get(x) is None:
            logging.critical(f'Отсутствует обязательная'
                             f' переменная окружения: {x}')
            condition = False
    return condition


def main():
    """Основная логика работы бота."""
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    if not check_tokens():
        logging.critical('Oтсутствие обязательных переменных'
                         ' окружения во время запуска бота')
    else:
        error_text = ''
        current_timestamp = int(time.time()) - 86400 * 30
        while True:
            try:
                response = get_api_answer(current_timestamp)
                homeworks = check_response(response)
                for homework in homeworks:
                    send_message(bot, parse_status(homework))
                    logging.info('Сообщение отправлено')
                current_timestamp = response.get('current_date', int(time.time()))

            except Exception as error:
                logging.error(f'Недоступность эндпоинта: {error}')
                if error != error_text:
                    message = f'Сбой в работе программы: {error}'
                    send_message(bot, message)
                    error_text = error
            finally:
                time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
