""" Very simple cache for utf8 textual content """
import tempfile
import os
import hashlib


BASE_DIR = os.path.join(tempfile.gettempdir(), 'strephit-cache')


def hash_for(key):
    return hashlib.sha1(key.encode('utf8')).hexdigest()


def path_for(hashed_key):
    """ Computes the path in which the given key should be stored.
        :return: tuple (full path, base path, file name)
    """
    loc = os.path.join(BASE_DIR, hashed_key[:3])
    return os.path.join(loc, hashed_key), loc, hashed_key


def get(key, default=None):
    loc, _, _ = path_for(hash_for(key))
    if os.path.exists(loc):
        with open(loc) as f:
            return f.read().decode('utf8')
    else:
        return default


def set(key, value, overwrite=True):
    loc, path, fname = path_for(hash_for(key))
    if overwrite or not os.path.exists(loc):
        if not os.path.exists(path):
            os.makedirs(path)
        with open(loc, 'w') as f:
            f.write(value.encode('utf8'))


def cached(function):
    """ Decorator to cache function results based on its arguments """
    def wrapper(*args, **kwargs):
        key = str(args) + str(kwargs)
        res = get(key)
        if res is None:
            res = function(*args, **kwargs)
            if res is not None:
                set(key, res)
        return res
    return wrapper
