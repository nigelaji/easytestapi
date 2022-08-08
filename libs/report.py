report = {
    "summary": {
        "api_num": "100",
        "case_num": "1000",
        "pass_num": "900",
        "fail_num": "100"
    },
    "apis": [
        {
            "name": "接口名称1111111111111111111",
            "cases": [
                {
                    "name": "测试用例名称11111111111111111",
                    "flag": True,
                    "steps": [
                        {"info": "asdasdasdasdasd"},
                        {"info": "asdasdasdasdasd"},
                        {"info": "asdasdasdasdasd"},
                        {"info": "asdasdasdasdasd"},
                        {"info": "asdasdasdasdasd"},
                    ]
                },
                {
                    "name": "测试用例名称11111111111111111",
                    "flag": True,
                    "steps": [
                        {"info": "asdasdasdasdasd"},
                        {"info": "asdasdasdasdasd"},
                        {"info": "asdasdasdasdasd"},
                        {"info": "asdasdasdasdasd"},
                        {"info": "asdasdasdasdasd"},
                    ]
                }
            ]
        },
        {
            "name": "接口名称1111111111111111111",
            "cases": [
                {
                    "name": "测试用例名称11111111111111111",
                    "flag": True,
                    "steps": [
                        {"info": "asdasdasdasdasd"},
                        {"info": "asdasdasdasdasd"},
                        {"info": "asdasdasdasdasd"},
                        {"info": "asdasdasdasdasd"},
                        {"info": "asdasdasdasdasd"},
                    ]
                },
                {
                    "name": "测试用例名称11111111111111111",
                    "flag": True,
                    "steps": [
                        {"info": "asdasdasdasdasd"},
                        {"info": "asdasdasdasdasd"},
                        {"info": "asdasdasdasdasd"},
                        {"info": "asdasdasdasdasd"},
                        {"info": "asdasdasdasdasd"},
                    ]
                }
            ]
        }
    ]
}

import jinja2
import time

# report = {
#     "summary": {
#         "api_num": "0",
#         "case_num": "0",
#         "pass_num": "0",
#         "fail_num": "0"
#     },
#     "apis": []
# }

#
# def report_write_summary(which):
#     report["summary"][which] += 1
#
#
# def report_write_step(step):
#     _steps = []
#     _steps.append(step)
#     _cases = {
#         "name": case.name,
#         "flag": case.run_res,
#         "steps": []
#     }
#     _api = {
#         "name": api.name,
#         "cases": []
#     }
#     return report


timestamp = int(time.time())

with open('../templates/report_template.html', 'r', encoding='utf-8') as f:
    template = f.read()

t = jinja2.Template(template)
html = t.render(summary=report["summary"], apis=report["apis"])

with open(f'report{timestamp}.html', 'w', encoding='utf-8') as f:
    f.write(html)
