import streamlit as st
import uuid
import streamlit as st
import streamlit.components.v1 as components
import time 

cache = {}

def set_cookie(name: str, value: str, ttl_days: int):
    components.html(
        """
        <script>
        function setCookie(name,value,days) {
            var expires = "";
            if (days) {
                var date = new Date();
                date.setTime(date.getTime() + (days*24*60*60*1000));
                expires = "; expires=" + date.toUTCString();
            }
            document.cookie = name + "=" + (value || "")  + expires + "; path=/";
        }
        """ + f"setCookie(\"{name}\", \"{value}\", {ttl_days});\n</script>", 0, 0
    )

def get_user_cache() -> dict:
    USER_ID_COOKIE_KEY = "streamlit_app_user_id"

    try:
        user_id = st.session_state['domotic_user_id'] if 'domotic_user_id' in st.session_state else st.context.cookies[USER_ID_COOKIE_KEY]
        if user_id is None:
            raise ValueError
        user_cache = cache[user_id]
    except:
        new_id = str(uuid.uuid4())
        print(f'new user: {new_id}')
        st.session_state['domotic_user_id'] = new_id
        set_cookie(USER_ID_COOKIE_KEY, new_id, 10800)

        cache[new_id] = {}
        user_cache = cache[new_id]
    return user_cache