"""
models of api, fields, values, etc.
"""
import json
import os
import re
import uuid
import warnings
from json import JSONDecodeError
from collections import OrderedDict
import numpy as np
import requests
from jsonpath import jsonpath

from bin import config
from .loader_funcs import test_funcs
from .logger import logger
from libs.dtype import u_random

HOST = getattr(config, 'HOST')
if not HOST:
    HOST = "localhost:5000"

__all__ = [
    'ValueCoat',
    'Field',
    'Fields',
    'Case',
    'Api'
]


def safe_eval(string, context: dict):
    """ 用于解析执行字符串
    :param string: 执行的字符串
    :param context: 上下文环境
    :return:
    """
    if not isinstance(string, str):
        return string
    sub_string = string.split(":")
    if sub_string[0] != "eval":
        return string
    else:
        try:
            logger.debug(f"[exec]: {sub_string[1]}")
            ret = eval(sub_string[1], {"__builtins__": None}, context)
        except Exception as e:
            logger.error(f"[exec]: {sub_string[1]} exec error. {e}")
            ret = None
        return ret


class ValueCoat:
    """
    用例某个字段的值的封装
    """
    __slots__ = ('field', 'value', 'flag', 'expect_result', 'desc')

    def __init__(self, field, value: object, flag: bool = True, expect_result: dict = None, desc: str = None):
        """
        :param field:   Field实例
        :param value:   字段真正的值
        :param flag:    字段值是正向还是反向，最后用于判断用例为正向还是反向的字段
        :param expect_result:    值的预期，用于断言。如果值为正向，默认走正向预期
        :param desc:    值的描述，后面可来组合用例名称
        """
        if field is None:
            raise 'missing field instance'
        self.field = field
        self.value = value
        self.flag = flag
        self.expect_result = expect_result
        self.desc = desc

    def __bool__(self):
        return self.flag

    def __repr__(self):
        if self.flag:
            return f"vTrue<{self.field, self.value, self.desc}>"
        else:
            return f"vFalse<{self.field, self.value, self.desc}>"


class Field:
    """字段对象"""

    def __init__(self, props: dict):
        """
        : name:         字段名         √
        : data_type:    类型          默认string
        : location:     位置          默认 1
        : length:       长度
        : required:     是否必填        默认不必填
        : nullable:     是否可为空       默认可为空
        : unique:       是否唯一        默认不唯一
        : regular:      格式要求
        : prefetch:     是否要预获取
        : mark:         标记
        : desc:         字段描述        √
        : data_line     数据线，这个字段之后请求的数据来源，里面可以填写方法来获取数据
        """
        self.props = props
        self.std_props = self.standardized()
        for k, v in self.std_props.items():
            setattr(self, k, v)

        self.tested_values = []

    def standardized(self):
        """
        将属性标准化，便于之后统一处理
        """
        default_props = {
            'data_type': 'str',
            'length': 10,
            'location': 1,
            'required': False,
            'nullable': True,
            'unique': False
        }
        default_props.update(self.props)
        std_props = {}
        for k, v in default_props.items():
            if k not in ['name', 'location', 'desc', 'mark']:
                if not isinstance(v, dict):
                    std_props[k] = {'base': v}
                else:
                    std_props[k] = v
            else:
                std_props[k] = v
        return std_props

    def _append_value(self, value: object, flag: bool = True, expect_result: dict = None, desc: str = None):
        self.tested_values.append(
            ValueCoat(field=self, value=value, flag=flag, expect_result=expect_result, desc=desc)
        )
        logger.debug(f'append case: field={self.name}, value={value}, desc={desc}')

    def _load_value(self, case):
        if isinstance(case, dict) and case:
            self._append_value(**case)
            values = case.get("values")
            if isinstance(values, list) and values:
                flag = case.get('flag')
                expect_result = case.get('expect_result')
                if not flag:
                    expect_result = case["expect_result"]
                desc = case["desc"]
                for v in values:
                    self._append_value(v, flag, expect_result, desc)

    def _load_values(self, values_attr):
        """
        :param values_attr:
        case
            1.{
                "value": required,
                "flag": default true,
                "expect_result": not required if flag else required,
                "desc": required
            }
            2.{
                "values": [required1, ...],
                "flag": default true,
                "expect_result": not required if flag else required,
                "desc": required
            }
        cases
            [ case1, case2, ...]
        :return:
        """
        case = values_attr.get('case')
        cases = values_attr.get('cases')
        self._load_value(case)
        if isinstance(cases, list):
            for case in cases:
                self._load_value(case)

    def load_values(self):
        for attr in self.std_props.values():
            if isinstance(attr, dict):
                enable = attr.get("enable")
                if enable is None or enable:
                    self._load_values(attr)

    def get_tested_items(self):
        self.load_values()
        return self.tested_values

    @staticmethod
    def check(grammar: str):
        if grammar.strip().startswith('eval'):
            return
        else:
            warnings.warn('you should use eval grammar')

    def generate_true_value(self, **kwargs):
        """
        根据规则生成一个正向的值
        获取字段随机值的先后顺序：
        ----> data_line --false--> [pre_get] --false--> [regular] --false--> [data_type]
                  |                     |                |                      |
        return<-true--------------------|                |                    true
                                                         |                      |
        return<-true-------------------------------------|                      |
                                                                                |
        return<-false------------[unique] <---------------true<----------- [length]
                                     |
        return<------ <判断> <--true--|
        """
        if self.data_line is not None:
            Field.check(self.data_line)
            return self.data_line

        if self.prefetch:
            pre_base_inst = self.std_props["prefetch"]["base"]
            desc = self.std_props["prefetch"].get('desc') or '预获取值'
            return ValueCoat(self, value=pre_base_inst, desc=desc)

        length = self.std_props["length"]["base"]
        if self.regular:
            pattern = self.std_props["regular"]["base"]
            desc = self.std_props["regular"].get('desc') or '正则随机值'
            value = u_random('str', length=length, pattern=pattern)
            return ValueCoat(self, value=value, desc=desc)

        if self.enums:
            enums = self.std_props["enums"]["base"]
            desc = self.std_props["enums"].get('desc') or '随机枚举值'
            enum = u_random('enum', enums=enums)
            return ValueCoat(self, value=enum, desc=desc)

        _type = self.std_props["data_type"]["base"]
        value = u_random(_type.lower(), length=length, **kwargs)

        return ValueCoat(self, value=value, desc="随机值")

    def __getattr__(self, item):
        return None

    def __repr__(self):
        return f"<Field:{self.name}>"


class Fields:
    def __init__(self, fields: list = None):
        """
        :param fields: [{..},{..}, .. ]
        """
        self.fields = [Field(field) for field in fields]

    def __len__(self):
        return len(self.fields)

    def __iter__(self):
        return iter(self.fields)

    def append(self, field):
        self.fields.append(Field(field))

    def t_case_values(self):
        """生成一组正向数据组"""
        case_values = []
        for field in self.fields:
            true_value = field.generate_true_value()
            case_values.append(true_value)
        return case_values

    def matrix_values(self):
        """获取参数值实例集合的参数化矩阵"""

        for i, field in enumerate(self.fields):
            matrix = []
            p = field.get_tested_items()  # 获取这个字段的所有要测试的
            p_length = len(p)
            matrix.append(p)

            fields_shadow = self.fields.copy()
            fields_shadow.pop(i)
            for f_shadow in fields_shadow:
                temp = []
                for _ in range(p_length):
                    temp.append(f_shadow.generate_true_value())
                matrix.append(temp)
            cases_values = np.array(matrix, dtype=object).transpose()
            yield cases_values

    def extract(self):
        """抽取case需要的变量
        flag: 标记这个用例预期是真是假
        desc: 值的验证性描述
        route_params: 路径参数
        params: 查询参数
        body: 请求体参数
        rsp: 响应预期
        """
        for cases_values in self.matrix_values():
            for case_values in cases_values:
                # case_values的第一个字段是要测试的那个字段
                props = {
                    "flag": case_values[0].flag,
                    "desc": f"{case_values[0].field.name}_{case_values[0].desc}",
                    "route_params": {},
                    "params": {},
                    "body": {},
                    "rsp": case_values[0].expect_result
                }
                for vc in case_values:
                    if 'notfill' in str(vc.value).lower():
                        continue
                    if vc.field.location == 1:
                        props["body"].update({
                            vc.field.name: vc.value,
                        })
                    elif vc.field.location == 2:
                        props["params"].update({
                            vc.field.name: vc.value,
                        })
                    else:
                        props["route_params"].update({
                            vc.field.name: vc.value,
                        })
                yield props

    def __repr__(self):
        return f"<Fields:{self.fields}>"


def assert_resp(expected: dict, actual: dict):
    """ 断言响应
    :param expected: 响应预期
    :param actual: 真实响应结果
    :return:
    """
    asserts = []
    is_ok = True
    for j_path, expected_pattern in expected.items():
        actual_value = jsonpath(actual, j_path)
        # target_value = json.loads(json.dumps(actual_value))
        result = re.match(str(expected_pattern), str(actual_value[0]))
        if result:
            logger.assert_log(True, "[assert][I]", f"断言成功:{j_path} 实际结果:{actual_value[0]} 预期结果:{expected_pattern}")
            asserts.append((True, actual_value[0], expected_pattern))
        else:
            logger.assert_log(False, "[assert][E]", f"断言失败:{j_path} 实际结果:{actual_value[0]} 预期结果:{expected_pattern}")
            asserts.append((False, actual_value[0], expected_pattern))
            is_ok = False
    return is_ok, asserts


def interpreter(obj, context):
    """解释器
    :param obj: 解释的对象
    :param context: 解释时的上下文环境
    :return:
    """
    if isinstance(obj, str):
        # 解释纯字符串时
        return safe_eval(obj, context)
    elif isinstance(obj, dict):
        # 解释请求体这种字典格式的时候，因为请求体的构造需要所有的参数准备好同时出参
        for k, v in obj.items():
            if v:
                obj.update({k: safe_eval(v, context)})
        return obj
    else:
        return obj


def merge(a, b, path=None):
    """merges b into a"""
    if path is None:
        path = []
    for key in b:
        if key in a:
            if isinstance(a[key], dict) and isinstance(b[key], dict):
                merge(a[key], b[key], path + [str(key)])
            elif a[key] == b[key]:
                pass  # same leaf value
            else:
                raise Exception('Conflict at %s' % '.'.join(path + [str(key)]))
        else:
            a[key] = b[key]
    return a


def convert_dotted_dict(dotted_dict: dict):
    """把带"."的键，解构成嵌套的字典的键
    :param dotted_dict:  example {"a.b.c": 1, "a.b.d": 2, "a.e": 3, "f": 4}
    :return: dict
    """
    root = {}

    for key in dotted_dict:
        split_key = key.split(".")
        split_key.reverse()
        value = dotted_dict[key]
        curr = {split_key[0]: value}
        for ind in range(1, len(split_key)):
            curr = {split_key[ind]: curr}
        root = merge(root, curr)
    return root


def render(obj, context):
    """渲染需要解析的对象
    :param obj:
    :param context: 上下文环境
    :return:
    """
    if isinstance(obj, str):
        return safe_eval(obj, context)
    elif isinstance(obj, dict):
        for k, v in obj.items():
            if v:
                obj.update({k: safe_eval(v, context)})
        return obj
    # elif isinstance(obj, list):
    #     mixes = []
    #     for v in obj:
    #         mixes.append(safe_eval(v, context))
    #     return mixes
    else:
        return obj


class Case:
    case_id = uuid.uuid4()

    def __init__(self, api, flag, name, versions, route, route_params, params, method,
                 setup=None, headers=None, body=None, teardown=None, response_assert=None):
        """
        :param api:  <apifmt> 对象
        :param flag: 用例真假
        :param name: 用例名称
        :param versions: 隶属版本
        :param route:   路径
        :param route_params:    路径参数
        :param params:  查询参数
        :param method: 请求方法
        :param setup: 前置步骤
        :param headers: 请求头
        :param body:  请求体参数
        :param teardown: 后置步骤
        :param response_assert: jsonpath响应断言
        """
        self.api = api
        self.flag = flag
        self.name = name
        self.versions = versions
        self.route = route
        self.url = f"{HOST}{self.route}"
        self.route_params = route_params
        self.params = params
        self.method = method
        self.setup = setup or []
        self.headers = headers or {}
        self.body = body or {}
        self.teardown = teardown or []
        self.response_assert = response_assert or {}

        self.step_idx = 1
        self.context_funcs = test_funcs
        self.steps = OrderedDict()
        self.result = True

        self.actual_response = None

    def serialize(self):
        return {
            "flag": self.flag,
            "name": self.name,
            "versions": self.versions,
            "route": self.route,
            "route_params": self.route_params,
            "params": self.params,
            "method": self.method,
            "setup": self.setup,
            "headers": self.headers,
            "body": self.body,
            "teardown": self.teardown,
            "response_assert": self.response_assert
        }

    def _load_steps(self):
        return

    @staticmethod
    def _render(obj, context):
        if isinstance(obj, str):
            return safe_eval(obj, context)
        elif isinstance(obj, dict):
            for k, v in obj.items():
                if v:
                    obj.update({k: safe_eval(v, context)})
            return obj
        else:
            return obj

    def run_setup(self):
        self._load_steps()
        for step in self.setup:
            logger.info(f"[step-{self.step_idx}][setup]: {step}")
            step_info = {f"s{self.step_idx}": render(step, self.context_funcs)}
            self.save_step(self.step_idx, 'setup', step_info)
            self.steps.update(step_info)
            self.step_idx += 1
            self.context_funcs.update(self.steps)

    def render_url(self):
        self.url = render(self.url.format(**self.route_params), self.context_funcs)

    def render_params(self):
        self.params = render(self.params, self.context_funcs)

    def render_headers(self):
        self.headers = render(self.headers, self.context_funcs)

    def render_body(self):
        trans_body = render(self.body, self.context_funcs)
        self.body = convert_dotted_dict(trans_body)

    def run_teardown(self):
        for step in self.teardown:
            try:
                step_info = {f"s{self.step_idx}": render(step, self.context_funcs)}
                logger.info(f"[step-{self.step_idx}][teardown]: {step}")
            except Exception as e:
                step_info = {f"s{self.step_idx}": e.args}
                logger.error(f"[step-{self.step_idx}][teardown]: {step}")
            self.steps.update(step_info)
            self.save_step(self.step_idx, 'teardown', step_info)
            self.step_idx += 1
            self.context_funcs.update(self.steps)

    def start_request(self):
        logger.info(f"[step-{self.step_idx}][test]: start test {self.name}")
        raw = json.dumps(self.body)
        response = requests.request(
            method=self.method, url=self.url,
            params=self.params, data=raw,
            headers=self.headers
        )
        logger.debug(f"[headers]: {self.headers}")
        logger.debug(f"[req-entries]: {self.route_params} {self.params} {raw}")

        try:
            resp = {"resp": response.json()}
        except JSONDecodeError:
            resp = {"resp": response.text}

        self.actual_response = resp
        logger.info(f"[receive-response]: {resp}")
        step_info = {f"s{self.step_idx}": resp}
        self.steps.update(step_info)
        self.save_step(self.step_idx, 'test', step_info)
        self.step_idx += 1
        self.context_funcs.update(self.steps)

    def start_assert(self):
        if self.flag:
            self.response_assert = self.api.response_assert
        is_ok, asserts = assert_resp(self.actual_response["resp"], self.response_assert)
        self.result = is_ok
        self.steps.update({
            "asserts": asserts
        })

    def save_step(self, step_index: int, step_type: str, step_info: dict):
        from storage import get_session, easytest_step_log
        sess = get_session()
        esl = easytest_step_log(self.case_id, step_index, step_type, step_info)
        sess.add(esl)
        sess.commit()
        logger.info(f"保存用例步骤")

    def run(self):
        logger.info(f"[start-case]: 《{self.name}》")
        try:
            self.run_setup()
            self.render_url()
            self.render_params()
            self.render_body()
            self.render_headers()
            self.start_request()
            self.run_teardown()
            self.start_assert()
            logger.info(f"[finish-case]: * * case run success * *\n")
        except Exception as e:
            logger.info(f"[error]: * * case run error * *")
            logger.info(f"[error]: {e}\n")

    def get_report(self):
        return {
            "name": self.name,
            "result": self.result,
            "steps": self.steps
        }

    def dump(self, to_db=False):
        """持久化用例，默认到本地"""
        if to_db:
            self.dump_to_db()
            logger.info(f"用例《{self.name}》已导入数据库 ")
        else:
            case_filename = f"{self.name}.json"
            case_dir = f"{self.api.name}"
            if not os.path.exists(case_dir):
                os.mkdir(case_dir)
            case_filepath = os.path.join(case_dir, case_filename)
            with open(case_filepath, 'w', encoding="utf-8") as f:
                f.write(json.dumps(self.serialize(), indent=4, ensure_ascii=False))
            logger.info(f"用例《{case_filename}》已生成至本地路径: {case_filepath}")

    def dump_to_db(self):
        from storage import get_session, easytest_case_meta
        sess = get_session()
        eacm = easytest_case_meta(case_id=self.case_id, api_id=self.api.id, case_info=self.serialize())
        sess.add(eacm)
        sess.commit()

    def __repr__(self):
        return f'<Case:{self.name}>'


class Api:
    def __init__(self, name, code, versions, route, method,
                 setup=None, headers=None, fields=None, files=None, additional=None,
                 teardown=None, response=None, response_assert=None):
        self.name = name
        self.code = code
        self.versions = versions
        self.route = route
        self.method = method
        self.setup = setup or []
        self.headers = headers or dict()
        self.fields = Fields(fields)
        self.files = files
        self.additional = additional or []
        self.teardown = teardown or []
        self.response = response or dict()
        self.response_assert = response_assert or dict()

        self.report = {
            "name": self.name,
            "cases": []
        }

    def serialize(self):
        return {
            "name": self.name,
            "code": self.code,
            "versions": self.versions,
            "route": self.route,
            "method": self.method,
            "setup": self.setup,
            "headers": self.headers,
            "fields": self.fields,
            "teardown": self.teardown,
            "response": self.response,
            "response_assert": self.response_assert
        }

    def html_serialize(self):
        """供HTML模板渲染使用的"""
        return {
            "code": self.code,
            "versions": self.versions,
            "name": self.name,
            "route": self.route,
            "method": self.method,
            "headers": json.dumps(self.headers, ensure_ascii=False, indent=4),
            "fields": [field.standardized() for field in self.get_fields()],
            "response": json.dumps(self.response, ensure_ascii=False, indent=4),
            "response_assert": self.response_assert
        }

    @property
    def url(self):
        return f"{HOST}{self.route}"

    def dump(self, to_db=False):
        """持久化"""
        if to_db:
            self.dump_to_db()
            logger.info(f"接口《{self.name}》已导入数据库")
        else:
            api_filename = f"{self.name}.json"
            with open(api_filename, 'w', encoding="utf-8") as f:
                f.write(json.dumps(self.serialize(), indent=4, ensure_ascii=False))
            logger.info(f"接口《{api_filename}》已导出至本地")

    def dump_to_db(self):
        from storage import get_session, easytest_api_meta
        sess = get_session()
        eam = easytest_api_meta(self.serialize())
        sess.add(eam)
        sess.commit()
        logger.info(f"接口《{self.name}》已导入数据库")

    def get_cases_from_additional(self):
        cases = []
        for case_info in self.additional:
            desc = case_info["desc"]
            flag = case_info.get("flag") or True
            expect_result = case_info["expect_result"] or self.response_assert
            route_params = case_info.get("route_params") or {}
            params = case_info.get("params") or {}
            body = case_info.get("body") or {}
            teardown = self.teardown if flag else []
            case = Case(api=self, flag=flag, name=f"{self.name}{'_' + desc if desc else ''}",
                        versions=self.versions, route=self.route,
                        route_params=route_params, params=params,
                        method=self.method, setup=self.setup,
                        headers=self.headers, body=body,
                        teardown=teardown, response_assert=expect_result)
            cases.append(case)
        return cases

    def get_cases_from_fields(self):
        cases = []
        for props in self.fields.extract():
            desc = props["desc"]
            flag = props["flag"]
            expect_result = props["rsp"] or self.response_assert
            route_params = props["route_params"]
            params = props["params"]
            body = props["body"]
            teardown = self.teardown if flag else []
            # print(self.name, desc)
            case = Case(api=self, flag=flag, name=f"{self.name}{'_' + desc if desc else ''}",
                        versions=self.versions, route=self.route,
                        route_params=route_params, params=params,
                        method=self.method, setup=self.setup,
                        headers=self.headers, body=body,
                        teardown=teardown, response_assert=expect_result)
            cases.append(case)
        return cases

    def yield_fields_cases(self):
        """生成用例，通过Fields实例的extract方法获取一条条用例所需数据
        还通过additional属性获取额外添加的用例"""
        for case in self.get_cases_from_fields():
            yield case
        for case in self.get_cases_from_additional():
            yield case

    def yield_all_cases(self):
        positive_case = self.get_case()
        yield positive_case
        for case in self.yield_fields_cases():
            yield case

    def get_case(self):
        """获取一个正向用例"""
        props = {
            "route_params": {},
            "params": {},
            "body": {},
        }
        for value_c in self.fields.t_case_values():
            if value_c.field.location == 1:
                props['body'].update({
                    value_c.field.name: value_c.value
                })
            elif value_c.field.location == 2:
                props['params'].update({
                    value_c.field.name: value_c.value
                })
            else:
                props['route_params'].update({
                    value_c.field.name: value_c.value
                })
        return Case(api=self, flag=True, name=f"{self.name}_随机正向值测试用例",
                    versions=self.versions, route=self.route,
                    route_params=props["route_params"], params=props["params"],
                    method=self.method, setup=self.setup,
                    headers=self.headers, body=props["body"],
                    teardown=self.teardown, response_assert=self.response_assert)

    def dump_cases(self, to_db=False):
        for case in self.yield_all_cases():
            case.dump(to_db)

    def run_cases(self):
        for case in self.yield_all_cases():
            case.run()
            self.report["cases"].append(
                case.get_report()
            )

    def get_fields(self, names: list = None):
        if names is None:
            return self.fields
        fields = []
        for field in self.fields:
            if field.name in names:
                fields.append(field)
        return fields

    def get_field(self, name):
        for field in self.fields:
            if field.name == name:
                return field

    def get_data_set(self):
        route_params = {}
        query_params = {}
        body_params = {}
        for field in self.get_fields():
            if field.location == 1:
                body_params.update({
                    field.name: field.generate_true_value().value
                })
            elif field.location == 2:
                query_params.update({
                    field.name: field.generate_true_value().value
                })
            else:
                route_params.update({
                    field.name: field.generate_true_value().value
                })
        return route_params, query_params, convert_dotted_dict(body_params)

    def debugging(self):
        data_set = self.get_data_set()
        rsp = request_api(self.method, self.url.format(data_set[0]), headers=self.headers, params=data_set[1], data=data_set[2], files=self.files, timeout=30)
        return rsp

    def __repr__(self):
        return f'<Api:{self.name}>'

    def load_define_func(self):
        from types import FunctionType
        foo_code = f"""
def {self.code}(url, method, headers, route_params, query_params, body_params, files, **kwargs):\n\
    

"""
        foo = compile(foo_code, '<dynamic>', 'exec')
        func = FunctionType(foo.co_consts[0], globals(), "foo", argdefs=(None, None, None, None, None, None, None))
        test_funcs.update({
            self.code: func
        })

    def auto_create_func(self):
        from types import FunctionType
        data_set = self.get_data_set()

        foo_code = f'''\
def {self.code}(\n\
        url, \n\
        method, \n\
        headers, \n\
        route_params, \n\
        query_params, \n\
        body_params, \n\
        files, \n\
    ):\n\
    """\n\
    this is dynamic generated method, the method name from api\'s code, \n\
    parameters from api\'s body, so cute \n\
    """\n\
    url = url or "{self.url}"\n\
    method = method or "{self.method}"\n\
    headers = headers or {self.headers}\n\
    route_params = route_params or {data_set[0]}\n\
    query_params = query_params or {data_set[1]}\n\
    body_params = body_params or {data_set[2]}\n\
    method = "{self.method}"\n\
    url = "{self.url}".format(**route_params)\n\
    logger.debug("[Headers ]: %s"%headers)\n\
    logger.debug("[Body    ]: %s"%body_params)\n\
    response = requests.request(\n\
        method, url, \n\
        headers=headers, \n\
        data=json.dumps(body_params), params=query_params, \n\
        files=files, timeout=30\n\
    )\n\
    try:\n\
        res = {{"resp": response.json()}}\n\
    except JSONDecodeError:\n\
        res = {{"resp": response.text }}\n\
    return res'''
        foo = compile(foo_code, '<dynamic>', 'exec')
        func = FunctionType(foo.co_consts[0], globals(), "foo", argdefs=(None, None, None, None, None, None, None))
        test_funcs.update({
            self.code: func
        })
        return func


def request_api(method, url, headers=None, params=None, data=None, files=None, timeout=30, **kwargs) -> dict:
    """
    :param method:
    :param url:
    :param headers:
    :param params:
    :param data:
    :param files:
    :param timeout:
    :param kwargs:
    :return:
    """
    try:
        response = requests.request(method, url, headers=headers, params=params, data=data, files=files,
                                    timeout=timeout, **kwargs)
        logger.debug(f"[header]: %s" % headers)
        logger.debug(f"[variables]: {params}, {data}, {files}")
        try:
            resp = {'resp': response.json()}
        except JSONDecodeError:
            resp = {'resp': response.text}
        logger.info(f"[response]: {json.dumps(resp, ensure_ascii=False)}")
    except Exception as e:
        logger.info(f"[request-error]: {e}")
        resp = {'error-resp': f'{e}'}
    return resp


def auto_request_api(method, url, headers: dict, route_params: dict, query_params: dict, body_params: dict,
                     files: tuple, **kwargs):
    headers = render(headers, context=test_funcs)
    route_params = render(route_params, context=test_funcs)
    query_params = render(query_params, context=test_funcs)
    body_params = render(body_params, context=test_funcs)
    url = url.format(**route_params)
    return request_api(
        method, url, headers=headers, params=query_params, data=json.dumps(body_params), files=files, **kwargs
    )
