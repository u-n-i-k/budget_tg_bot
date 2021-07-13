import os
import json
import requests


class TicketsAPI:
    _HOST = 'irkkt-mobile.nalog.ru:8888'

    @property
    def _headers(self):
        headers = {
            'Host': self._HOST,
            'Accept': '*/*',
            'Device-OS': 'iOS',
            'Device-Id': 'my-device-id',
            'clientVersion': '2.9.0',
            'Accept-Language': 'ru-RU;q=1, en-US;q=0.9',
            'User-Agent': 'billchecker/2.9.0 (iPhone; iOS 13.6; Scale/2.00)',
        }
        if self._session_id:
            headers['sessionId'] = self._session_id
        return headers

    def __init__(self, client_secret, inn, password):
        self._client_secret = client_secret
        self._inn = inn
        self._password = password
        
        self._session_id = None
        self.get_session_id()

    def get_session_id(self) -> None:
        url = f'https://{self._HOST}/v2/mobile/users/lkfl/auth'
        payload = {
            'inn': self._inn,
            'password': self._password,
            'client_secret': self._client_secret
        }

        res = requests.post(url, json=payload, headers=self._headers)

        self._session_id = res.json()['sessionId']

    def _get_ticket_id(self, qr):
        url = f'https://{self._HOST}/v2/ticket'
        payload = {'qr': qr}

        res = requests.post(url, json=payload, headers=self._headers)

        return res.json()["id"]

    def get_ticket(self, qr):
        ticket_id = self._get_ticket_id(qr)
        url = f'https://{self._HOST}/v2/tickets/{ticket_id}'

        res = requests.get(url, headers=self._headers)

        return res.json()
