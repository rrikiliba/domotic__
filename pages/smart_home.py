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
    st.subheader('🔌 Centro di comando energetico.', anchor=False)
    st.markdown("Qui puoi ricevere una panoramica immediata e granulare dell':green[utilizzo di energia della tua casa]. Analizza i tuoi :green[schemi di consumo] e poi chatta direttamente con :blue[Domitico] 🧙‍♂️, il tuo assistente AI, per trovare :green[modi intelligenti per risparmiare] denaro :green[e ottimizzare] l'efficienza.")

with st.container(border=True):
    tab1, tab2, tab3 = st.tabs(["🔌 Domotic Hub", "🛠️ Edizione DIY", "🧪 Prova il sistema"])

    with tab1:
        col1, col2 = st.columns([1, 1], gap="large", vertical_alignment="top")
        
        with col1:
            st.subheader("Il Domotic Hub")
            st.markdown(""":green[La soluzione premium e senza problemi.]  
  
Il nostro hub proprietario funge da cervello centrale della tua casa intelligente.  
Può sostituire il tuo bridge attuale o collegarsi perfettamente alla tua configurazione esistente.  

* :green[Acquisto hardware una tantum.]
* **Plug & Play:** :green[Niente programmazione] richiesta.
* **Sicuro:** Elaborazione locale con sincronizzazione cloud.

Una volta effettuato l'accesso, i tuoi dati in tempo reale appaiono :green[direttamente su questa dashboard].
            """)
            
        with col2:
            try:
                st.image("assets/images/HUB.png", width="stretch")
            except:
                st.warning("Image not found: assets/images/HUB.png")
                
            st.button("📦 Acquista Domotic Hub", width="stretch", type="primary")


    with tab2:
        col1, col2 = st.columns([1, 1], gap="large", vertical_alignment="top")
        
        with col1:
            st.subheader("L'edizione DIY")
            st.markdown("""
:green[Per i creatori e gli smanettoni.]

Hai già un server a casa? Puoi eseguire l'engine di Domotic completamente :green[gratuitamente].

* **Installa:** su qualsiasi cosa possa girare Docker.
* **Connettiti:** tramite MQTT o API REST.
* **Paga:** :green[nulla]. Devi solo portare il tuo hardware.

Segui la nostra documentazione per avviare il container e iniziare subito a trasmettere i dati.
""")
            
        with col2:
            try:
                st.image("assets/images/DIY.png", width="stretch")
            except:
                st.warning("Image not found: assets/images/DIY.png")

            st.button("📚 Leggi la documentazione", width="stretch", type="primary")


    with tab3:
        col1, col2 = st.columns([1, 1], gap="large", vertical_alignment="top")
        
        with col1:
            st.subheader("Simula i dati")
            st.markdown(""":green[Non hai ancora l'hardware?]

Puoi :green[testare subito le funzionalità] di visualizzazione della dashboard.
Ti basta premere :green[**Modifica**] e modificare o incollare un report energetico in formato JSON nell'area di testo.

Lo abbiamo pre-compilato con dati di esempio che puoi provare immediatamente.
Basta cliccare :green[**Analizza**] per vedere il nostro report qui sotto.
""")
            
        with col2:
            with st.container(height=300, border=False):
                st.json(cache['placeholder_data'], expanded=3)

            btn_col1, btn_col2 = st.columns([1, 1], gap="small")
            
            with btn_col1:
                with st.popover("📝 Edit", width="stretch"):
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
                if st.button("📊 Analyze", type="primary", width="stretch"):
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