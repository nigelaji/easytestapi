import base64
import datetime
import os
import random
import re
import string
import time
from libs import restr

__all__ = [
    'u_random',
    'Str', '_str',
    'Int', '_int',
    'Float', '_float',
    'Bool', '_bool',
    'List', '_list',
    'Date', '_date', '_datetime',
    'TimeStamp', 'timestamp',
    'Enum', 'enum',
    'File', 'file'
]


class BaseDType:

    def random(self, **kwargs):
        """必须实现随机出一个符合字段条件的值
        :return:
        """
        raise NotImplemented()


class Str(BaseDType):

    def __init__(self):
        self.charsets = string.ascii_letters

    def random(self, length=0, mark="", pattern=None, charsets: list = None, **kwargs):
        length = length or 10
        if length - len(mark) <= 0:
            raise ValueError(' length-len(mark) must be greater than 0 ')
        if mark:
            length -= len(mark)
        if pattern is not None:
            return mark + restr.xeger(pattern, length)
        if charsets is None:
            return mark + restr.rstr(self.charsets, length)
        return mark + restr.rstr(charsets, length)


_str = Str()


class Int(BaseDType):

    def random(self, limits=None, length=None, signed=False, **kwargs):
        """
        :param limits: 限制范围。不定长时，填写参数或者使用默认
        :param length: 数字长度。比如4，那么随机范围为1000~9999
        :param signed: 确定正负数。默认为False代表正数，True代表负数
        :return:
        """
        limits = limits or [0, 2147483647]
        if length:
            limits = [pow(10, (length - 1)), pow(10, length) - 1]  # 求固定长度的取值范围
        v = random.randint(*limits)
        return -v if signed else v


_int = Int()


class Float(BaseDType):
    """先随便写了"""

    def random(self, point=2, limits=None, length=None, signed=False, **kwargs):
        """
        :param point: 2代表小数点后两位
        :param limits:
        :param length:
        :param signed:
        :param kwargs:
        :return:
        """
        limits = limits or [0, 100]
        if length:
            limits = [pow(10, (length - 1)), pow(10, length) - 1]  # 求固定长度的取值范围
        fv = round(random.uniform(*limits), point)
        if len(str(fv).split('.')[1]) <= 1:
            fv += round(0.111111111111, point)
        return -fv if signed else fv


_float = Float()


class Bool(BaseDType):

    def random(self, **kwargs):
        return random.choice([True, False])


_bool = Bool()


class List(BaseDType):

    def random(self, length=10, seeds=string.ascii_letters, **kwargs):
        r_list = []
        for i in range(length):
            r_list.append(random.choice(seeds))
        return r_list


_list = List()


class Date(BaseDType):

    def __init__(self, format_str="%Y-%m-%d"):
        self.format_str = format_str
        self.current = datetime.datetime.now()

    def random(self, offset: int = 0, **kwargs):
        """随机一个范围内的日期
        :param offset: 指定偏移量，单位天，可正负或浮点数。
            默认0，返回当前时间。
            -1 ，返回昨天此刻至今日此刻范围内的时间
        :return:
        """

        if offset < 0:
            left, right = [offset, 0]
        elif offset == 0:
            return self.current.strftime(self.format_str)
        else:
            left, right = [0, offset]
        r_float = random.uniform(int(left), int(right))
        return (self.current + datetime.timedelta(days=r_float)).strftime(self.format_str)


_date = Date()
_datetime = Date("%Y-%m-%d %H:%M:%S")


class TimeStamp(BaseDType):

    def random(self, offset=0, unit=1, **kwargs):
        """
        :param offset: 偏移量，单位天，可正负或浮点数。
            默认0，返回当前时间戳。
            -1 ，返回昨天此刻至今日此刻范围内的时间戳
        :param unit 单位，1代表s，2代表ms
        :return:
        """
        current_t = int(time.time() * 1000000)
        offset_t = int(3600 * 24 * offset * 1000000)
        if unit == 1:
            denominator = 1000000
        else:
            denominator = 1000
        if offset < 0:
            left, right = [int(current_t - offset_t), current_t]
        elif offset == 0:
            return current_t // denominator
        else:
            left, right = [current_t, int(current_t + offset_t)]
        return random.randint(left // denominator, right // denominator)


timestamp = TimeStamp()


class Enum(BaseDType):

    def random(self, enums=None, **kwargs):
        """随机枚举值
        :param enums: 枚举值集合
            enums = [1,2,3]
        :return: 随机其中一个
        """
        if isinstance(enums, list):
            return random.choice(enums)
        else:
            raise Exception('enums write like this ["A","B","C"]')


enum = Enum()


class File(BaseDType):
    def __init__(self, test_dir='./', shape='content'):
        self.test_dir = test_dir
        self.shape = shape

    @staticmethod
    def to_b64str(filepath):
        return base64.b64encode(
            File.to_content(filepath)
        ).decode()

    @staticmethod
    def to_content(filepath):
        with open(filepath, mode='rb') as f:
            return f.read()

    def read_block(self, filename, size=1024 * 1024):
        filepath = os.path.join(self.test_dir, filename)
        file_handler = open(filepath, mode='rb')
        file_size = os.path.getsize(filepath)
        start_size = 0
        content_length = size
        while True:
            chunk = file_handler.read(size)
            end_size = start_size + size
            if end_size > file_size:
                end_size = file_size
                content_length = end_size - start_size
            content_range = f'bytes {start_size}-{end_size}/{file_size}'
            start_size += size + 1
            if not chunk:
                file_handler.close()
                break
            yield chunk, content_length, content_range

    def random(self, basedir=None, pattern=None, **kwargs):
        """
        默认会过滤掉文件夹，
        :param basedir: 在哪个文件夹中取文件
        :param pattern: 过滤掉匹配的文件
        :return: 返回一个文件的绝对路径
        """
        root_dir = basedir or self.test_dir
        filenames = os.listdir(root_dir)
        if pattern:
            # 过滤匹配名称的文件和过滤掉文件夹
            filter_files = filter(
                lambda name: re.match(pattern, name) and os.path.isfile(os.path.join(root_dir, name)),
                filenames
            )
        else:
            # 过滤掉文件夹
            filter_files = filter(lambda name: os.path.isfile(os.path.join(root_dir, name)), filenames)

        filename = random.choice(list(filter_files))
        filepath = os.path.join(root_dir, filename)
        if self.shape == 'content':
            return File.to_content(filepath)
        elif self.shape == 'base64':
            return File.to_b64str(filepath)
        else:
            return 'not yet supported, contact the developer'


file = File()
_base_64 = File(shape='base64')

type_map = {
    "str": _str,
    "string": _str,
    "char": _str,
    "varchar": _str,
    "text": _str,
    "int": _int,
    "integer": _int,
    "float": _float,
    "bool": _bool,
    "list": _list,
    "date": _date,
    "datetime": _datetime,
    "timestamp": timestamp,
    "enum": enum,
    "file": file,
    "base64": _base_64,
}


def u_random(_type, **kwargs):
    return type_map[_type].random(**kwargs)


if __name__ == '__main__':
    # print("str ==>\t\t\t", u_random("str"))
    # print("int ==>\t\t\t", u_random("int"))
    # print("float ==>\t\t", u_random("float"))
    # print("bool ==>\t\t", u_random("bool"))
    # print("list ==>\t\t", u_random("list"))
    # print("date ==>\t\t", u_random("date"))
    # print("datetime ==>\t", u_random("datetime"))
    # print("timestamp ==>\t", u_random("timestamp"))
    # print("enum ==>\t\t", u_random("enum"))
    # print("file ==>\t\t", u_random("file"))
    # 如果类型为dict、json类型，则会先生成fieldmaps转化成一个个的dtype类型进行随机值

    print("email ==>\t", u_random("str", length=30, pattern="^\\w+@qq\\.com$"))
