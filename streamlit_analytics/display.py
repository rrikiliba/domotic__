import altair as alt
import pandas as pd
import streamlit as st
import json
from utils import Cache
from . import utils

cache = Cache()

def show_results(counts, reset_callback, unsafe_password=None):
    """Show analytics results in streamlit, asking for password if given."""

    with st.container(border=True):
        # Show header.
        cols = st.columns([0.75, 0.25], vertical_alignment="bottom")
        with cols[0]:
            st.subheader("Analytics Dashboard", anchor=False)
        with cols[1]:
            st.download_button("💾 Download", data=json.dumps(counts, indent=4), on_click='ignore', width="stretch", type="primary", file_name="analytics.json")
        st.markdown( """ Questa sezione mostra una serie di analytics sull'utilizzo del sito da parte degli utenti.  
        :red[È pensata per noi sviluppatori], quindi puoi tornare alle altre pagine. """ )

    if 'password' not in cache:
        cache['password'] = False

    if unsafe_password is not None and not cache['password']:
        with st.container(border=True):
            password_input = st.text_input(
                "Inserisci la password per mostrare i risultati", type="password"
            )
            if password_input != unsafe_password:
                if len(password_input) > 0:
                    st.write("Nope, non è corretta ☝️")
            else:
                cache['password'] = True
                st.rerun()
    else:
        with st.container(border=True):
            # Show traffic.
            st.header("Traffic")
            st.write(f"since {counts['start_time']}")
            col1, col2, col3 = st.columns(3)
            col1.metric(
                "Pageviews",
                counts["total_pageviews"],
                help="Every time a user (re-)loads the site.",
            )
            col2.metric(
                "Script runs",
                counts["total_script_runs"],
                help="Every time Streamlit reruns upon changes or interactions.",
            )
            col3.metric(
                "Time spent",
                utils.format_seconds(counts["total_time_seconds"]),
                help="Time from initial page load to last widget interaction, summed over all users.",
            )
            st.write("")

            # Plot altair chart with pageviews and script runs.
            try:
                alt.themes.enable("streamlit")
            except:
                pass  # probably old Streamlit version
            df = pd.DataFrame(counts["per_day"])
            base = alt.Chart(df).encode(
                x=alt.X("monthdate(days):O", axis=alt.Axis(title="", grid=True))
            )
            line1 = base.mark_line(point=True, stroke="#5276A7").encode(
                alt.Y(
                    "pageviews:Q",
                    axis=alt.Axis(
                        titleColor="#5276A7",
                        tickColor="#5276A7",
                        labelColor="#5276A7",
                        format=".0f",
                        tickMinStep=1,
                    ),
                    scale=alt.Scale(domain=(0, df["pageviews"].max() + 1)),
                )
            )
            line2 = base.mark_line(point=True, stroke="#57A44C").encode(
                alt.Y(
                    "script_runs:Q",
                    axis=alt.Axis(
                        title="script runs",
                        titleColor="#57A44C",
                        tickColor="#57A44C",
                        labelColor="#57A44C",
                        format=".0f",
                        tickMinStep=1,
                    ),
                )
            )
            layer = (
                alt.layer(line1, line2)
                .resolve_scale(y="independent")
                .configure_axis(titleFontSize=15, labelFontSize=12, titlePadding=10)
            )
            st.altair_chart(layer, use_container_width=True)

        with st.container(border=True):
            # Show widget interactions.
            st.header("Widget interactions")
            st.markdown(
                """
                Find out how users interacted with your app!
                <br>
                Numbers indicate how often a button was clicked, how often a specific text 
                input was given, ...
                <br>
                """,
                unsafe_allow_html=True,
            )
            # Note: Numbers only increase if the state of the widget
            # changes, not every time streamlit runs the script.
            st.write(counts["widgets"])

        # Show button to reset analytics.
        with st.expander("Danger zone 🔥"):
            st.write(
                """
                Here you can reset all analytics results.
                
                **This will erase everything tracked so far. You will not be able to 
                retrieve it. This will also overwrite any results synced to Firestore.**
                """
            )
            reset_prompt = st.selectbox(
                "Continue?",
                [
                    "No idea what I'm doing here",
                    "I'm absolutely sure that I want to reset the results",
                ],
            )
            if reset_prompt == "I'm absolutely sure that I want to reset the results":
                reset_clicked = st.button("Click here to reset")
                if reset_clicked:
                    reset_callback()
                    st.write("Done! Please refresh the page.")
