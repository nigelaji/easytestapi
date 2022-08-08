# coding:utf-8
import os
import sys

sys.path.append(os.path.dirname(sys.path[0]))

from libs.parse import ApiParser
import argparse

pwd = os.getcwd()

parser = argparse.ArgumentParser(description=''' easy test api. ''')

parser.add_argument('-r', '--run', type=str,
                    help='直接通过接口定义json文档运行用例')

parser.add_argument('-d', '--dump',
                    help='生成用例')

args = parser.parse_args()


def run_testcase():
    api = ApiParser(args.run)
    api.run_cases()


def dump_testcase():
    api = ApiParser(args.dump)
    api.dump_cases()


if args.run:
    run_testcase()
elif args.dump:
    dump_testcase()
else:
    parser.format_help()
