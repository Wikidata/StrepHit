import tempfile
import os
import hashlib
import json


BASE_DIR = os.path.join(tempfile.gettempdir(), 'strephit-cache')
ENABLED = True


def _hash_for(key):
    return hashlib.sha1(key.encode('utf8')).hexdigest()


def _path_for(hashed_key):
    """ Computes the path in which the given key should be stored.

        :return: tuple (full path, base path, file name)
    """
    loc = os.path.join(BASE_DIR, hashed_key[:3])
    return os.path.join(loc, hashed_key), loc, hashed_key


def get(key, default=None):
    """ Retrieves an item from the cache
        :param key: Key of the item
        :param default: Default value to return if the
         key is not in the cache
        :return: The item associated with the given key or
         the default value

        Sample usage:

        >>> from strephit.commons import cache
        >>> cache.get('kk', 13)
        13
        >>> cache.get('kk', 0)
        0
        >>> cache.set('kk', 15)
        >>> cache.get('kk', 0)
        15
    """
    if not ENABLED:
        return default

    hashed = _hash_for(key)
    loc, _, _ = _path_for(hashed)
    if os.path.exists(loc):
        with open(loc) as f:
            stored_key = f.readline().decode('utf8')[:-1]
            if stored_key == key:
                return json.loads(f.read().decode('utf8'))
            else:
                return get(key + hashed, default)
    else:
        return default


def set(key, value, overwrite=True):
    """ Stores an item in the cache under the given key
        :param key: Unique key used to identify the idem.
        :param value: Value to store in the cache. Must be
         JSON-dumpable
        :param overwrite: Whether to overwrite the previous
         value associated with the key (if any)
        :return: Nothing

        Sample usage:

        >>> from strephit.commons import cache
        >>> cache.get('kk', 13)
        13
        >>> cache.get('kk', 0)
        0
        >>> cache.set('kk', 15)
        >>> cache.get('kk', 0)
        15
    """
    if not ENABLED:
        return

    hashed = _hash_for(key)
    loc, path, fname = _path_for(hashed)
    if not os.path.exists(loc):
        if not os.path.exists(path):
            os.makedirs(path)

        with open(loc, 'w') as f:
            f.write(key.encode('utf8') + '\n')
            f.write(json.dumps(value).encode('utf8'))
    else:
        with open(loc, 'r+') as f:
            stored_key = f.readline().decode('utf8')[:-1]
            if stored_key == key:
                if overwrite:
                    f.write(json.dumps(value).encode('utf8'))
                    f.truncate()
                return
        set(key + hashed, value, overwrite)


def cached(function):
    """ Decorator to cache function results based on its arguments

    Sample usage:

    >>> from strephit.commons import cache
    >>> @cache.cached
    ... def f(x):
    ...     print 'inside f'
    ...     return 2 * x
    ...
    >>> f(10)
    inside f
    20
    >>> f(10)
    20

    """
    def wrapper(*args, **kwargs):
        key = str([function.__module__]) + function.__name__ + str(args) + str(kwargs)
        res = get(key)
        if res is None:
            res = function(*args, **kwargs)
            if res is not None:
                set(key, res)
        return res
    return wrapper
