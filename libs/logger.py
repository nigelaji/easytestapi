import logging
import logging.handlers
import os
import sys
from bin import config
from colorama import init

init(autoreset=True)  # cmd中也可以展示出颜色
"""
filename：   用指定的文件名创建FiledHandler（后边会具体讲解handler的概念），这样日志会被存储在指定的文件中。
filemode：   文件打开方式，在指定了filename时使用这个参数，默认值为“a”还可指定为“w”。
format：      指定handler使用的日志显示格式。
datefmt：    指定日期时间格式。
level：        设置rootlogger（后边会讲解具体概念）的日志级别
stream：     用指定的stream创建StreamHandler。可以指定输出到sys.stderr,sys.stdout或者文件，默认为sys.stderr。
                  若同时列出了filename和stream两个参数，则stream参数会被忽略。
https://docs.python.org/zh-cn/3/library/logging.html#logrecord-attributes
"""


class NewLineFormatter(logging.Formatter):

    def __init__(self, fmt, date_fmt=None):
        """
        Init given the log line format and date format
        """
        logging.Formatter.__init__(self, fmt, date_fmt)

    def format(self, record):
        """
        Override format function
        """
        msg = logging.Formatter.format(self, record)

        if record.message != "":
            parts = msg.split(record.message.rstrip('\n'))
            msg = msg.replace('\n', '\n' + parts[0])
        return msg


log_colors = {
    logging.DEBUG: "\033[1;34m",  # blue
    logging.INFO: "\033[1;32m",  # green
    logging.WARNING: "\033[1;35m",  # magenta
    logging.ERROR: "\033[1;31m",  # red
    logging.CRITICAL: "\033[1;41m",  # red reverted
}


if not getattr(config, 'LOG_PATH', None):
    if not os.path.exists('../log'):
        os.mkdir('../log')
    LOG_PATH = os.path.join(os.path.join(os.path.dirname(__file__), '../log'), 'eta.log')
else:
    LOG_PATH = config.LOG_PATH


def file_handler(level=logging.WARNING):

    handler = logging.handlers.RotatingFileHandler(
        filename=LOG_PATH,
        mode='a+',
        maxBytes=1024 * 1024 * 10,
        backupCount=3,
        encoding='utf-8',
    )
    my_fmt = logging.Formatter(
        fmt='%(asctime)s %(pathname)s[line:%(lineno)d] %(name)s %(levelname)-8s %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    handler.setLevel(level)
    handler.setFormatter(my_fmt)
    return handler


def basic_logger(level=logging.DEBUG, offset=True):
    log_fmt = '%(asctime)s %(filename)s [line:%(lineno)d] %(levelname_c)-8s %(message)s'
    # LOG_FORMAT = '%(asctime)s %(pathname)s[line:%(lineno)d] %(name)s %(levelname_c)-8s %(message)s'
    date_fmt = '%Y-%m-%d %H:%M:%S'
    logging.basicConfig(
        level=level,
        stream=sys.stdout,
    )

    formatter = NewLineFormatter(log_fmt, date_fmt=date_fmt)

    orig_record_factory = logging.getLogRecordFactory()

    def record_factory(*args, **kwargs):
        record = orig_record_factory(*args, **kwargs)
        record.levelname_c = "{}{}{}".format(log_colors[record.levelno], record.levelname, "\033[0m")  # 定制LogRecord属性
        # record.message_shorten = "{}".format(textwrap.shorten(record.msg, width=180, placeholder='...'))
        # record.message_colored = ""
        # record.name_shorten = "{}".format(textwrap.shorten(record.name, width=4, placeholder='...'))
        # record.filename
        record.msg.rstrip('\n')
        return record

    logging.setLogRecordFactory(record_factory)
    lgr = logging.getLogger()
    lgr.handlers[0].setFormatter(formatter)
    return lgr


def assert_log(flag, title, content):
    """定制断言日志"""
    print(flag, title, content)
    if flag:
        color = log_colors[logging.INFO]
    else:
        color = log_colors[logging.ERROR]
    msg = f"{color}{title}\033[0m {content}"
    logging.info(msg)


logger = basic_logger(logging.DEBUG)
# logger = basic_logger(logging.INFO)

logger.assert_log = assert_log

logger.addHandler(file_handler(logging.DEBUG))


if __name__ == '__main__':
    logger.assert_log(False, "yyyyy", "zzzz")