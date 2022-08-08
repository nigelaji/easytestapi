"""
用作命令行提示模板
"""
case_tmpl = """{
    "value": required,
    "flag": default true,
    "expect_result": not required if flag else required,
    "desc": required
}
"""
cases_tmpl = """{
    "values": [required1, ...],
    "flag": default true,
    "expect_result": not required if flag else required,
    "desc": required
}"""