import streamlit as st
import uuid
from streamlit_cookies_controller import CookieController
from collections.abc import MutableMapping

cookies = CookieController()

class Cache(MutableMapping):
    def __init__(self):
        self._internal_cache = {}

    def __getitem__(self, key):
        return self._internal_cache[key]

    def __setitem__(self, key, value):
        self._internal_cache[key] = value

    def __delitem__(self, key):
        del self._internal_cache[key]

    def __iter__(self):
        return iter(self._internal_cache)

    def __len__(self):
        return len(self._internal_cache)

    def __repr__(self):
        return f"Cache({self._internal_cache})"

    def clear(self, key=None):
        if key is None:
            self._internal_cache.clear()
        else:
            if key in self._internal_cache:
                del self._internal_cache[key]
            else:
                raise KeyError(f"Key not found: {key}")

global_cache = {}

def get_user_cache() -> Cache:
    USER_ID_COOKIE_KEY = "streamlit_app_user_id"
    
    try:
        user_id = cookies.get(USER_ID_COOKIE_KEY)
    except:
        user_id = None

    if user_id is None or len(user_id) == 0:
        new_id = str(uuid.uuid4())
        print(f'new user: {new_id}')
        cookies.set(USER_ID_COOKIE_KEY, new_id, max_age=10800) 
        user_id = new_id
        global_cache[user_id] = Cache()

    return global_cache[user_id]    