""" Very simple cache for utf8 textual content """
import tempfile
import os
import hashlib


BASE_DIR = tempfile.gettempdir()


def hash_for(key):
    return hashlib.sha1(key).hexdigest()


def path_for(hashed_key):
    return os.path.join(BASE_DIR, hashed_key[:3], hashed_key)


def get(key, default=None):
    loc = path_for(hash_for(key))
    if os.path.exists(loc):
        with open(loc) as f:
            return f.read().decode('utf8')
    else:
        return default


def set(key, value, overwrite=True):
    loc = path_for(hash_for(key))
    if overwrite or not os.path.exists(loc):
        with open(loc, 'w') as f:
            f.write(value.encode('utf8'))
