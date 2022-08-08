"""
Relying on json-schema for verification

document: https://horejsek.github.io/python-fastjsonschema/
"""
import json
import fastjsonschema


__all__ = [
    'api_validator', 'fields_validator', 'case_validator', 'cases_validator'
]

schemas = {
    "api": "./schemas/api.schema",
    "fields": "./schemas/fields.schema",
    "case": "./schemas/case.schema",
    "cases": "./schemas/cases.schema",
}


def _validator(which):
    with open(schemas[which], encoding='utf-8') as sf:
        text_json = sf.read()
    validate = fastjsonschema.compile(json.loads(text_json))
    return validate


def api_validator():
    return _validator('api')


def fields_validator():
    return _validator('fields')


def case_validator():
    return _validator('case')


def cases_validator():
    return _validator('cases')




