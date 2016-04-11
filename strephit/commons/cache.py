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
    """ Decorator to cache function results based on its arguments """
    def wrapper(*args, **kwargs):
        key = str([function.__module__]) + function.__name__ + str(args) + str(kwargs)
        res = get(key)
        if res is None:
            res = function(*args, **kwargs)
            if res is not None:
                set(key, res)
        return res
    return wrapper
