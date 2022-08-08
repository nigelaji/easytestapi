import time
import jinja2
from libs.parse import ApiParser


api_name = "./tests/apis/test_create_tester_api.json"

api = ApiParser(api_name)


with open('../templates/api_doc_template.html', 'r', encoding='utf-8') as f:
    template = f.read()


t = jinja2.Template(template)
# print(api.api_fmt.doc_serialize())
html = t.render(api=api.api_fmt.doc_serialize())
timestamp = int(time.time())

with open(f'{api_name}_{timestamp}.html', 'w', encoding='utf-8') as f:
    f.write(html)
