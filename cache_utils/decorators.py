#coding: utf-8
from django.core.cache import get_cache
from django.utils.functional import wraps
from cache_utils.utils import _cache_key, _func_info, _func_type, sanitize_memcached_key

def cached(timeout, group=None, backend=None, name_callback=None):
    """ Caching decorator. Can be applied to function, method or classmethod.
    Supports bulk cache invalidation and invalidation for exact parameter
    set. Cache keys are human-readable because they are constructed from
    callable's full name and arguments and then sanitized to make
    memcached happy.

    It can be used with or without group_backend. Without group_backend
    bulk invalidation is not supported.

    Wrapped callable gets `invalidate` methods. Call `invalidate` with
    same arguments as function and the result for these arguments will be
    invalidated.
    """

    backend_kwargs = {} if not group else {'group': group}

    if backend:
        cache_backend = get_cache(backend)
    else:
        cache_backend = get_cache('default')

    def _cached(func):

        func_type = _func_type(func)

        @wraps(func)
        def wrapper(*args, **kwargs):

            # try to get the value from cache
            key = get_key(*args, **kwargs)
            value = cache_backend.get(key, **backend_kwargs)

            # in case of cache miss recalculate the value and put it to the cache
            if value is None:
                value = func(*args, **kwargs)
                cache_backend.set(key, value, timeout, **backend_kwargs)

            return value

        def invalidate(*args, **kwargs):
            ''' invalidates cache result for function called with passed arguments '''
            cache_backend.delete(get_key(*args, **kwargs), **backend_kwargs)

        def force_recalc(*args, **kwargs):
            '''
            forces a call to the function & sets the new value in the cache
            '''
            value = func(*args, **kwargs)
            cache_backend.set(get_key(*args, **kwargs), value, timeout,
                              **backend_kwargs)
            return value

        def get_key(*args, **kwargs):
            key = _cache_key(name(*args, **kwargs), func_type, args, kwargs)
            return sanitize_memcached_key(key)

        def name(*args, **kwargs):
            # full name is stored as attribute on first call
            name, _args = _func_info(func, args)
            return name if not name_callback \
                else name_callback(name, *args)

        wrapper.invalidate = invalidate
        wrapper.force_recalc = force_recalc

        return wrapper
    return _cached
