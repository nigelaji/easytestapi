import requests
from logger import logger
import json
from json import JSONDecodeError
from requests.structures import CaseInsensitiveDict


def raw(headers: dict, data):
    headers = CaseInsensitiveDict(headers)
    if 'application/json' in headers['Content-Type']:
        return json.dumps(data)
    elif 'application/x-www-form-urlencoded' in headers['Content-Type']:
        parts = []
        for k, v in data.items():
            part = k + "=" + str(v)
            parts.append(part)
        return "&".join(parts)
    elif 'multipart/form-data' in headers['Content-Type']:
        return data
    else:
        return str(data)


def show_debug_log(**kwargs):
    for k, v in kwargs.items():
        if v:
            logger.debug(f'[{k}]: {v}')


def request_api(method, url, headers=None, params=None, data=None, files=None, timeout=30, **kwargs) -> dict:
    """
    :param method:
    :param url:
    :param headers:
    :param params:
    :param data: 这个data就直接从把body_params放进来就行了
    :param files:
    :param timeout:
    :param kwargs:
    :return:
    """
    payload = raw(headers, data)
    try:
        response = requests.request(method, url, headers=headers, params=params, data=payload, files=files,
                                    timeout=timeout, **kwargs)
        show_debug_log(headers=headers, params=params, data=payload, files=files)
        try:
            resp = {'resp': response.json()}
        except JSONDecodeError:
            resp = {'resp': response.text}
        logger.info(f"[response]: {json.dumps(resp, ensure_ascii=False)}")
    except Exception as e:
        logger.info(f"[request-error]: {e}")
        resp = {'error-resp': f'{e}'}
    return resp
