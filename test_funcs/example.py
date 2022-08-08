import json
import random
import requests
from requests import JSONDecodeError
from libs.dtype import _str
from libs.logger import logger


def random_int(a=1, b=10):
    return random.randint(a, b)


def random_str(length):
    return _str.random(length)


def get_account():
    return {
        "account": "admin",
        "password": "123456"
    }


def request_api(method, url, headers=None, params=None, data_raw=None, timeout=30, **kwargs) -> dict:
    try:
        response = requests.request(method, url, headers=headers, params=params, data=data_raw, timeout=timeout, **kwargs)
        try:
            resp = {'resp': response.json()}
        except JSONDecodeError:
            resp = {'resp': response.text}
        logger.info(f"[response]: {json.dumps(resp, ensure_ascii=False)}")
    except Exception as e:
        logger.info(f"[request-error]: {e}")
        resp = {'no-resp': f'{e}'}
    return resp


def tp_login_api(account="admin", password="123456"):
    body = {
        "account": account,
        "password": password
    }
    return request_api(
        "POST",
        "http://localhost:5000/user/login",
        json=body,
        data=json.dumps(body),
        headers={"Content-Type": "application/json"}
    )


def tp_post_user_api(token, username, user_code, email, phone=None, remark=None):
    return request_api(
        "POST",
        "http://localhost:5000/tp/users",
        json={
            "username": username,
            "user_code": user_code,
            "email": email,
            "phone": phone,
            "remark": remark,
        },
        headers={
            "Content-Type": "application/json",
            "token": token
        }
    )


def tp_del_user_api(token, id):
    return request_api(
        "DELETE",
        "http://localhost:5000/tp/users/{id}".format(id=id),
        headers={
            "Content-Type": "application/json",
            "token": token
        }
    )


def abstract(**kwargs):

    return request_api(
        method="",
        url="",
        headers="",

    )


if __name__ == '__main__':
    token = tp_login_api("admin", "123456")["resp"]["data"]["token"]

    id = tp_post_user_api(token, "eeeee", "eeee", "eeeee@qq.com")["resp"]["data"]["id"]

    tp_del_user_api(token, id)

    print(1&2)
