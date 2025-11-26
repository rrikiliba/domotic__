import streamlit as st
from collections.abc import MutableMapping

@st.cache_resource(ttl=None)
def _get_cached_cache_object() -> object:
    class CacheContainer:
        def __init__(self):
            self.instance = None
    return CacheContainer()

class Cache(MutableMapping):
    _internal_cache = {}
    _container = _get_cached_cache_object()

    def __new__(cls, *args, **kwargs):
        if cls._container.instance is None:
            instance = object.__new__(cls)
            cls._container.instance = instance
            instance._internal_cache = {}
        return cls._container.instance

    def __init__(self):
        pass

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

# Streamlit Example Usage
def example():
    cache_obj = Cache()

    st.title("Streamlit Singleton Cache with Conditional Clear 🧠")
    st.code(f"cache_obj is Cache(): {cache_obj is Cache()}")

    if 'key1' not in cache_obj:
        cache_obj['key1'] = 'Initial Value'
        cache_obj['key_to_delete'] = 'Will be deleted'
        st.info("Cache initialized with 'key1' and 'key_to_delete'.")
    else:
        st.success(f"Cache retrieved! 'key1' is: **{cache_obj.get('key1', 'N/A')}**")

    st.divider()

    new_value = st.text_input("Enter a new value for 'new_key':", value="Hello Streamlit")
    if st.button("Add to Cache"):
        cache_obj['new_key'] = new_value
        st.success(f"Added 'new_key': {new_value}")
        st.rerun()

    st.subheader("Current Cache Contents")
    st.code(str(cache_obj))

    st.subheader("Clear Operations")
    col1, col2 = st.columns(2)

    with col1:
        if st.button("Clear 'key_to_delete'"):
            try:
                cache_obj.clear('key_to_delete')
                st.warning("Deleted 'key_to_delete'.")
                st.rerun()
            except KeyError as e:
                st.error(str(e))

    with col2:
        if st.button("Clear ALL Cache Contents"):
            cache_obj.clear()
            st.error("Internal cache cleared completely.")
            st.rerun()
