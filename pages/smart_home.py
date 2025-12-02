import streamlit as st
import pandas as pd
import json
import datetime
import numpy as np
from utils import stream_generator, Cache

cache = Cache()

cache['homepage_visited'] = True

def get_placeholder_json():
    """
    Generates a JSON representing hourly energy consumption for 4 devices over the past 24 hours.
    """
    data = {
        "report_date": str(datetime.date.today()),
        "devices": [
            {
                "name": "Living Room AC",
                "type": "hvac",
                # AC running harder in the afternoon
                "hourly_consumption_kwh": [round(np.random.uniform(0.5, 1.2), 2) if 12 <= i <= 20 else 0.1 for i in range(24)]
            },
            {
                "name": "Kitchen Refrigerator",
                "type": "appliance",
                # Cycling compressor usage
                "hourly_consumption_kwh": [round(np.random.uniform(0.1, 0.3), 2) for _ in range(24)]
            },
            {
                "name": "Living Room Lamp",
                "type": "lighting",
                # 0 consumption during day, ~60W (0.06kWh) from 18:00 to 23:00
                "hourly_consumption_kwh": [0.06 if 18 <= i <= 23 else 0.0 for i in range(24)]
            },
            {
                "name": "Bedroom Air Purifier",
                "type": "appliance",
                # Constant low usage, slightly higher at night
                "hourly_consumption_kwh": [0.05 if i > 20 or i < 8 else 0.02 for i in range(24)]
            }
        ]
    }
    return json.dumps(data, indent=2)

if 'energy_data' not in cache:
    cache['energy_data'] = None
    cache['placeholder_data'] = get_placeholder_json()

with st.container(border=True):
    st.markdown("""
**Welcome to your energy command center.** Here, you can receive an immediate, granular overview of your home's power usage. 
Analyze your consumption patterns and then **chat directly with Domitico**, your AI energy assistant, 
to find smart ways to save money and optimize efficiency.  
                
Here's how you can use this page:
""")

with st.container(border=True):
    tab1, tab2, tab3 = st.tabs(["🔌 Domotic Hub", "🛠️ Do It Yourself", "🧪 Test the System"])

    with tab1:
        col1, col2 = st.columns([1, 1], gap="large", vertical_alignment="top")
        
        with col1:
            st.subheader("The Domotic Hub")
            st.markdown("""
            **:green[The premium, hassle-free solution.]**
            
            Our proprietary hub acts as the central brain of your smart home. 
            It can replace your current bridge or attach seamlessly to your existing setup.
            
            * **One-time hardware purchase.**
            * **Plug & Play:** :green[No coding] required.
            * **Secure:** Local processing with cloud sync.
            
            Once logged in, your real-time data appears :green[directly on this dashboard].
            """)
            
        with col2:
            try:
                # Removed caption, changed width to use_container_width (modern syntax)
                st.image("assets/images/HUB.png", use_container_width=True)
            except:
                st.warning("Image not found: assets/images/HUB.png")
                
            # Added button to product page (placeholder URL)
            st.button("📦 Buy Domotic Hub", use_container_width=True, type="primary")


    with tab2:
        col1, col2 = st.columns([1, 1], gap="large", vertical_alignment="top")
        
        with col1:
            st.subheader("The DIY Edition")
            st.markdown("""
            **:green[For the makers and hackers.]**
            
            Already have a smart home server? You can run Domitico's engine completely :green[for free].
            
            * **Install:** on anything that can run Docker.
            * **Connect:** via MQTT or REST API.
            * **Pay:** :green[nothing]. You just bring your own hardware.
            
            Follow our documentation to spin up the container and start piping data immediately.
            """)
            
        with col2:
            try:
                st.image("assets/images/DIY.png", use_container_width=True)
            except:
                st.warning("Image not found: assets/images/DIY.png")

            st.button("📚 Read Setup Tutorial", use_container_width=True, type="primary")


    with tab3:
        col1, col2 = st.columns([1, 1], gap="large", vertical_alignment="top")
        
        with col1:
            st.subheader("Simulate Your Data")
            st.markdown("""
            **:green[Don't have the hardware yet?]**
            
            You can :green[test the dashboard] visualization capabilities right now. 
            Simply press :green[**Edit**] and mjodify or paste a JSON energy report in the text area. 
            
            We have pre-filled it with sample data for you to try immediately. 
            Just click :green[**Analyze**] to see our report below.
            """)
            
        with col2:
            with st.container(height=300, border=False):
                st.json(cache['placeholder_data'], expanded=3)

            btn_col1, btn_col2 = st.columns([1, 1], gap="small")
            
            with btn_col1:
                with st.popover("📝 Edit", use_container_width=True):
                    def update_data():
                        cache['placeholder_data'] = st.session_state['placeholder_data_textarea']
                    st.text_area(
                        "json smart home data",
                        value=cache['placeholder_data'],
                        key='placeholder_data_textarea',
                        height=250,
                        label_visibility="collapsed",
                        on_change=update_data
                    )
            
            with btn_col2:
                if st.button("📊 Analyze", type="primary", use_container_width=True):
                    try:
                        parsed_data = json.loads(cache['placeholder_data'])
                        cache['energy_data'] = parsed_data
                        cache['energy_comment'] = None
                        st.rerun()
                    except json.JSONDecodeError:
                        st.error("Invalid JSON format.")

if cache['energy_data']:
    st.divider()
    
    data = cache['energy_data']
    devices = data.get("devices", [])
    
    total_consumption = 0
    graph_data = []
    
    for device in devices:
        name = device['name']
        consumptions = device['hourly_consumption_kwh']
        device_total = sum(consumptions)
        total_consumption += device_total
        
        for hour_idx, kwh in enumerate(consumptions):
            graph_data.append({
                "Device": name,
                "Hour": f"{hour_idx:02d}:00",
                "Consumption (kWh)": kwh
            })

    df = pd.DataFrame(graph_data)

    with st.container(border=True):
        col_sum1, col_sum2 = st.columns([3, 1], vertical_alignment="center")
        with col_sum1:
            st.subheader("📝 Energy Report Summary")
        with col_sum2:
            st.metric(label="Total 24h Load", value=f"{total_consumption:.2f} kWh")
        energy_comment = st.empty()


    with st.container(border=True):
        st.subheader("Hourly Consumption per Device")
        st.bar_chart(
            data=df,
            x="Hour",
            y="Consumption (kWh)",
            color="Device",
            stack=True,
            height=400
        )

    with energy_comment:
        if 'energy_comment' not in cache or cache['energy_comment'] == None:
            try:
                stream = st.session_state.client.chat.send(
                    model=cache['selected_model']['id'],
                    messages=[
                        {
                            "role": "system",
                            "content": json.dumps(cache['energy_data'])
                        },
                        {
                            "role": "user",
                            "content": "Very briefly comment on the energy consumption of my smart home devices based on the json data you have."
                        }
                    ],
                    stream=True,
                )
                cache['energy_comment'] = st.write_stream(stream_generator(stream))
            except Exception as e:
                st.error(e)
        else:
            st.write(cache['energy_comment'])

st.markdown("""
<style>
div[data-testid="stImage"] img {
    height: 300px !important;
    object-fit: cover !important;
    border-radius: 8px;
}
</style>
""", unsafe_allow_html=True)