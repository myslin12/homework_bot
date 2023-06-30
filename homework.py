import logging
import os
import time
import telegram
import requests
import sys

from dotenv import load_dotenv
from http import HTTPStatus

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


logging.basicConfig(
    level=logging.DEBUG,
    filename='program.log',
    format='%(asctime)s, %(levelname)s, %(message)s'
)

logging.debug('debug message')
logging.info('info')
logging.warning('warning')
logging.error('error')
logging.critical('critical')


def check_tokens():
    """Проверка доступности переменных окружения."""
    available_tokens = [
        PRACTICUM_TOKEN,
        TELEGRAM_TOKEN,
        TELEGRAM_CHAT_ID
    ]
    for tokens in available_tokens:
        if tokens is None:
            logging.critical(
                f'Отсуствует обязательная переменная окружения {tokens}'
            )
            raise ValueError(
                f'Переменная {tokens} не обнаружена'
            )
    return True


def send_message(bot, message):
    """Отправка сообщения."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logging.debug('Сообщение успешно отправлено')
    except KeyError:
        logging.error('Ошибка отправки сообщения')


def get_api_answer(timestamp):
    """Запрос к единственному эндпоинту API-сервиса."""
    params = {'from_date': timestamp}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)
    except requests.RequestException as e:
        logging.error(f'Ошибка при обращении к API: {e}')
        return None

    if response.status_code != HTTPStatus.OK:
        logging.error(f'HTTP ошибка при обращении к API:'
                      f'{response.status_code}')
        raise requests.exceptions.HTTPError('HTTP статус не равен 200.')

    try:
        return response.json()
    except ValueError as e:
        logging.error(f'Ошибка при преобразовании ответа в JSON: {e}')
        return None


def check_response(response):
    """Проверка ответа API на соответствие документации."""
    if not response:
        message = 'Словарь пустой'
        logging.error(message)
        raise KeyError(message)

    elif not isinstance(response, dict):
        message = 'Имеет некорректный тип'
        logging.error(message)
        raise TypeError(message)

    elif 'homeworks' not in response:
        message = 'Нет ожидаемых ключей в ответе'
        logging.error(message)
        raise KeyError(message)

    elif not isinstance(response.get('homeworks'), list):
        message = 'Иной формат ответа'
        logging.error(message)
        raise TypeError(message)

    return response['homeworks']


def parse_status(homework):
    """Извлекает из информации о домашней работе статус этой работы."""
    try:
        status = homework.get('status')
    except ValueError:
        return 'Статус домашней работы отсутсвует'
    if status not in HOMEWORK_VERDICTS:
        raise ValueError
    else:
        verdict = HOMEWORK_VERDICTS.get(status)
    if 'homework_name' not in homework:
        raise KeyError
    else:
        homework_name = homework.get('homework_name')
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        logging.critical(
            'Отсутствует обязательная переменная окружения.'
            'Программа принудительно остановлена.'
        )
        sys.exit()

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())

    while True:
        try:
            response = get_api_answer(timestamp - RETRY_PERIOD)
            if check_response(response):
                for homework in response.get('homeworks'):
                    message = parse_status(homework)
                    send_message(bot, message)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logging.error(message)
        time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
