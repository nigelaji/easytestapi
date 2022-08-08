import decimal
import json
from .models import Case, Api

__all__ = [
    'ApiParser', 'CaseParser'
]


class ApiParser:

    def __new__(cls, path=None, api_json=None):
        if path:
            with open(path, 'r', encoding='utf-8') as fs:
                api_json = json.loads(fs.read(), parse_float=decimal.Decimal)
        else:
            if not api_json:
                raise 'api parser error'
        return Api(**api_json)


class CaseParser:

    def __new__(cls, path=None, case_json=None, api_path=None, api_json=None):
        api = ApiParser(api_path, api_json)
        if path:
            with open(path, 'r', encoding='utf-8') as fs:
                case_json = json.loads(fs.read(), parse_float=decimal.Decimal)
        else:
            if not case_json:
                raise 'case parser error'
        return Case(api=api, **case_json)





