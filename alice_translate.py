import os
import requests
from flask import Flask, request
import logging
import json

app = Flask(__name__)

logging.basicConfig(level=logging.INFO, filename='app.log', format='%(asctime)s %(levelname)s %(name)s %(message)s')


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

    logging.info('Request: %r', response)

    return json.dumps(response)


def handle_dialog(res, req):
    if req['session']['new']:
        res['response']['text'] = 'Скажите "Переведи слово", а затем само слово,' \
                                  ' и я переведу Вам это слово на английский язык!'
        return

    res['response']['text'] = translate(req) + "\nПопробуете ещё?"


def translate(req):
    text = ""
    try:
        for word in req['request']['nlu']['tokens'][2:]:
            text += word
        params = {
            "key": "trnsl.1.1.20200428T170441Z.aa3e646d79eb90ac.cd983e95119d3f95037f94ddba30a85e9684604a",
            "text": text,
            "lang": "ru-en"
        }
        response = requests.get("https://translate.yandex.net/api/v1.5/tr.json/translate", params=params)
        return response.json()['text'][0].title()
    except Exception:
        return "Что-то не так! Повторите, пожалуйста, запрос!"


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
