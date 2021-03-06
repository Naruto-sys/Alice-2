import os
from flask import Flask, request
import logging
import json
import random

from geo import get_country

app = Flask(__name__)

logging.basicConfig(level=logging.INFO)

cities = {
    'москва': ['965417/45b8a793543af50238d1', '965417/f21c5033cadb2be62819'],
    'нью-йорк': ['1030494/2d12dfb5aa3b9b00a0ee', '965417/56263cbe79c1d19bf49e'],
    'париж': ["997614/e2191d156e0d7f0b39f4", '997614/6707536797b2f0440cc1']
}

sessionStorage = {}


@app.route('/post', methods=['POST'])
def main():
    logging.info('Request: %r', request.json)
    response = {
        'session': request.json['session'],
        'version': request.json['version'],
        'response': {
            'end_session': False
        }
    }
    handle_dialog(response, request.json)
    logging.info('Response: %r', response)
    return json.dumps(response)


def handle_dialog(res, req):
    user_id = req['session']['user_id']
    if req['session']['new']:
        res['response']['text'] = 'Привет! Назови своё имя!'
        res['response']['buttons'] = [
            {
                'title': "Помощь",
                'hide': False
            }
        ]
        sessionStorage[user_id] = {
            'first_name': None,
            'game_started': False,
            'city_answered': False
        }
        return

    if 'Помощь' in req['request']['command']:
        res['response']['text'] = 'Я буду присылать Вам фото городов, а Вы' \
                                  ' должны будете угадывать, какой именно город' \
                                  ' я прислала! Если не справитесь - я помогу!'
        return

    if sessionStorage[user_id]['first_name'] is None:
        first_name = get_first_name(req)
        if first_name is None:
            res['response']['text'] = 'Не расслышала имя. Повтори, пожалуйста!'
        else:
            sessionStorage[user_id]['first_name'] = first_name
            sessionStorage[user_id]['guessed_cities'] = []
            res['response']['text'] = f'Приятно познакомиться, {first_name.title()}. Я Алиса. Отгадаешь город по фото?'
            res['response']['buttons'] = [
                {
                    'title': 'Да',
                    'hide': True
                },
                {
                    'title': 'Нет',
                    'hide': True
                }
            ]
    else:
        if not sessionStorage[user_id]['game_started']:
            if 'да' in req['request']['nlu']['tokens']:
                if len(sessionStorage[user_id]['guessed_cities']) == 3:
                    res['response']['text'] = 'Ты отгадал все города!'
                    res['end_session'] = True
                else:
                    sessionStorage[user_id]['game_started'] = True
                    sessionStorage[user_id]['city_answered'] = False
                    sessionStorage[user_id]['attempt'] = 1
                    play_game(res, req)
            elif 'нет' in req['request']['nlu']['tokens']:
                res['response']['text'] = 'Ну и ладно!'
                res['end_session'] = True
            else:
                res['response']['text'] = 'Не поняла ответа! Так да или нет?'
                res['response']['buttons'] = [
                    {
                        'title': 'Да',
                        'hide': True
                    },
                    {
                        'title': 'Нет',
                        'hide': True
                    }
                ]
        else:
            play_game(res, req)


def play_game(res, req):
    user_id = req['session']['user_id']
    attempt = sessionStorage[user_id]['attempt']
    if attempt == 1:
        city = random.choice(list(cities))
        while city in sessionStorage[user_id]['guessed_cities']:
            city = random.choice(list(cities))
        sessionStorage[user_id]['city'] = city
        res['response']['card'] = {}
        res['response']['card']['type'] = 'BigImage'
        res['response']['card']['title'] = 'Что это за город?'
        res['response']['card']['image_id'] = cities[city][attempt - 1]
        res['response']['text'] = 'Тогда сыграем!'
    elif not sessionStorage[user_id]['city_answered']:
        city = sessionStorage[user_id]['city']
        if get_city(req) == city:
            res['response']['text'] = 'Правильно! А в какой стране этот город?'
            sessionStorage[user_id]['attempt'] = 2
            sessionStorage[user_id]['guessed_cities'].append(city)
            sessionStorage[user_id]['city_answered'] = True
            return
        else:
            if attempt == 3:
                res['response']['text'] = f'Вы пытались. Это {city.title()}. Сыграем ещё?'
                sessionStorage[user_id]['game_started'] = False
                sessionStorage[user_id]['attempt'] = 1
                sessionStorage[user_id]['guessed_cities'].append(city)
                return
            else:
                res['response']['card'] = {}
                res['response']['card']['type'] = 'BigImage'
                res['response']['card']['title'] = 'Неправильно. Вот тебе дополнительное фото'
                res['response']['card']['image_id'] = cities[city][attempt - 1]
                res['response']['text'] = 'А вот и не угадал!'
    else:
        if get_country(sessionStorage[user_id]['guessed_cities'][-1]) in req['request']['command']:
            res['response']['text'] = 'Правильно! Сыграем ещё?'
            sessionStorage[user_id]['game_started'] = False
            res['response']['buttons'] = [
                {
                    'title': 'Да',
                    'hide': True
                },
                {
                    'title': 'Нет',
                    'hide': True
                },
                {
                    'title': 'Покажи город на карте',
                    'url': f"https://yandex.ru/maps/?mode=search&text={sessionStorage[user_id]['guessed_cities'][-1]}",
                    'hide': True
                }
            ]
            return
        else:
            if attempt == 3:
                sessionStorage[user_id]['attempt'] = 1
                sessionStorage[user_id]['game_started'] = False
                res['response']['text'] = 'Вы пытались. Это ' \
                                          f"{get_country(sessionStorage[user_id]['guessed_cities'][-1])}. Сыграем ещё?"
                return
            else:
                res['response']['text'] = 'Попробуйте ещё!'
    sessionStorage[user_id]['attempt'] += 1


def get_city(req):
    for entity in req['request']['nlu']['entities']:
        if entity['type'] == 'YANDEX.GEO':
            return entity['value'].get('city', None)


def get_first_name(req):
    for entity in req['request']['nlu']['entities']:
        if entity['type'] == 'YANDEX.FIO':
            return entity['value'].get('first_name', None)


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
