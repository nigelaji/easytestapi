import inspect

__all__ = ['test_funcs']

try:
    test_funcs_module = __import__('test_funcs')
except ModuleNotFoundError:
    test_funcs_module = None


test_funcs = {}

if test_funcs_module is not None:
    func_list = inspect.getmembers(test_funcs_module, predicate=inspect.isfunction)
    test_funcs.update(dict(func_list))

