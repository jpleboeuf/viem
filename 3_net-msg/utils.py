"""utils"""

from functools import wraps

def count_calls(f):
    @wraps(f)
    def _(*args, **kwds):
        try:
            return f(*args, **kwds)
        finally:
            _.__calls__ += 1
    _.__calls__ = 0
    return _
