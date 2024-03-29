import re
import string
from itertools import chain
import sys

if sys.version_info[0] >= 3:
    unichr = chr
    xrange = range

# The * and + characters in a regular expression
# match up to any number of repeats in theory,
# (and actually 65535 repeats in python) but you
# probably don't want that many repeats in your
# generated strings. This sets an upper-bound on
# repeats generated from + and * characters.
STAR_PLUS_LIMIT = 100


def equal_counts(x):
    """
    计算每组的元素个数是否一致
    [(1, 2), (3, 4), (5, 6), (5, 6)]    True
    [(1, 2), (3, 4), (5, 6, 7)]    False
    """
    l = len(x)
    return len(x[l - 1]) == len(x[l - 2])


class Xeger(object):
    """Inspired by the Java library Xeger: http://code.google.com/p/xeger/
    This class adds functionality to Rstr allowing users to generate a
    semi-random string from a regular expression."""

    def __init__(self):
        super(Xeger, self).__init__()
        self._cache = dict()
        self._categories = {
            'category_digit': lambda: self._alphabets['digits'],
            'category_not_digit': lambda: self._alphabets['nondigits'],
            'category_space': lambda: self._alphabets['whitespace'],
            'category_not_space': lambda: self._alphabets['nonwhitespace'],
            'category_word': lambda: self._alphabets['word'],
            'category_not_word': lambda: self._alphabets['nonword'],
        }

        self._cases = {'literal': lambda x: unichr(x),
                       'not_literal': lambda x: self._random.choice(
                           string.printable.replace(unichr(x), '')),
                       'at': lambda x: '',
                       'in': lambda x: self._handle_in(x),
                       'any': lambda x: self.printable(1, exclude='\n'),
                       'range': lambda x: [unichr(i) for i in range(x[0], x[1] + 1)],
                       'category': lambda x: self._categories[x](),
                       'branch': lambda x: self.branch(x),
                       'subpattern': lambda x: self._handle_group(x),
                       'assert': lambda x: ''.join(self._handle_state(i) for i in x[1]),
                       'assert_not': lambda x: '',
                       'groupref': lambda x: self._cache[x],
                       'min_repeat': lambda x: self._handle_repeat(*x),
                       'max_repeat': lambda x: self._handle_repeat(*x),
                       'negate': lambda x: [False],
                       }

    def branch(self, x):
        # if equal_counts(x[1]):
        #     return ''.join(self._handle_state(i) for i in self._random.choice(x[1]))
        # else:
        #     raise ValueError('因为边界问题，分支中的元素个数需要一致')
        return ''.join(self._handle_state(i) for i in self._random.choice(x[1]))
    # def fixed_repeat(self):
    #     return self._handle_repeat(*x)

    def xeger(self, string_or_regex, *sizes):
        """
        sizes: 每个branch的限制长度
        例如('\\w+66\\w+', 1,2) 就代表 \\w{1}66\\w{2}
        例如('\\w+66\\w+', 1) 就代表 \\w{1}66\\w{1}
        """
        try:
            pattern = string_or_regex.pattern
        except AttributeError:
            pattern = string_or_regex

        # self.__dict__['size'] = int(size)
        self.__dict__['size'] = (size for size in sizes)
        self.__dict__['end_size'] = sizes[-1]

        parsed = re.sre_parse.parse(pattern)
        result = self._build_string(parsed)
        self._cache.clear()
        return result

    def _build_string(self, parsed):
        newstr = []
        for state in parsed:
            newstr.append(self._handle_state(state))
        return ''.join(newstr)

    def _handle_state(self, state):
        opcode, value = state
        opcode, value = _2and3(opcode, value)
        return self._cases[opcode](value)

    def _handle_group(self, value):
        result = ''.join(self._handle_state(i) for i in value[-1])
        if value[0]:
            self._cache[value[0]] = result
        return result

    def _handle_in(self, value):
        candidates = list(chain(*(self._handle_state(i) for
                                  i in value)))
        if candidates[0] is False:
            candidates = set(string.printable).difference(candidates[1:])
            return self._random.choice(list(candidates))
        else:
            return self._random.choice(candidates)

    def _handle_repeat(self, start_range, end_range, value):
        result = []
        try:
            size = next(self.size)
        except StopIteration:
            size = self.end_size
        end_range = min((end_range, size))
        times = end_range  # 选用最大值，所以尽量用{m}表达式来匹配
        # times = self._random.randint(start_range, end_range)
        for i in xrange(times):
            result.append(''.join(self._handle_state(i) for i in value))
        return ''.join(result)


def _2and3(opcode, value):
    opcode = str(opcode).lower()
    if sys.version_info >= (3, 5) and opcode == 'category':
        value = value.name.lower()
    return opcode, value
