import streamlit as st
from utils import model_name_format, stream_generator, Cache
import uuid

cache = Cache()

cache['homepage_visited'] = True

avatar = {
    'user': '👤',
    'assistant': '🧙‍♂️'
}

def chat_message(name):
    return st.container(key=f"{name}-{uuid.uuid4()}").chat_message(name=name, avatar=avatar[name])

st.markdown("""
<style>
.stBottom {
    margin-top: 5em;
    bottom: 5em;
}

@media (prefers-color-scheme: dark) {         
    [class*="st-key-user"] {
        border-radius: 1em;
        background-color: #145A32;
    }
    [class*="st-key-assistant"] {
        border-radius: 1em;
        background-color: #1F2E2E;
    }
}

@media (prefers-color-scheme: light) {
    [class*="st-key-user"] {
        border-radius: 1em;
        background-color: #C1E6DF;
    }
    [class*="st-key-assistant"] {
        border-radius: 1em;
        background-color: #A2D9CE;
    }
}
</style>
""", unsafe_allow_html=True)

if 'messages' not in cache:
    cache['messages'] = [
        {
            'role': 'assistant',
            'content': 'Ciao! Il mio nome è Domitico e sono qui per aiutarti. Sentiti libero di chiedermi qualsiasi cosa riguardo alla tua bolletta elettrica :smile:'
        }
    ]

for message in cache['messages']:
    with chat_message(message["role"]):
        st.markdown(message["content"])

latest_message_user = st.empty()
latest_message_assistant = st.empty()

if prompt := st.chat_input('Fai le tue domande qui:'):

    cache['messages'].append({"role": "user", "content": prompt})
    with latest_message_user:
        with chat_message("user"):
            st.markdown(prompt)


    messages = [{
                "role": m["role"], 
                "content": m["content"]
            } for m in cache['messages']]
    
    if cache['csv_content'] is not None:
        csv_messages = [
            {
                'role': 'system',
                'content': 'Utilizza i dati CSV sulle offerte disponibili dal seguente file CSV per supportare le tue risposte.'
            },
            {
                'role': 'system',
                'content': cache['csv_content']
            }
        ]
        messages = csv_messages + messages

    if cache['pdf_content'] is not None:
        pdf_messages = [
            {
                'role': 'system',
                'content': 'Utilizza i dati JSON relativi alla bolletta elettrica dell\'utente dal seguente file JSON per fornire suggerimenti ad hoc. Questi dati sono stati precedentemente analizzati da te, direttamente dal file PDF caricato dall\'utente.'
            },
            {
                'role': 'user',
                'content': cache['pdf_content']
            }
        ]
        messages = pdf_messages + messages

    messages = [
        {
            "role": "system",
            "content": "Sei un assistente utile. Sei esperto in bollette elettriche, consumo energetico, ecc. L'utente potrebbe farti domande relative a quest'area."
        },
        {
            "role": "system",
            "content": "Devi respingere le domande non correlate a bollette elettriche, piani tariffari, elettrodomestici e consumo generale di elettricità domestica."
        },
        {
            "role": "system",
            "content": "Per quanto riguarda il sito, gli utenti possono caricare, ottenere un sommario e parlare con te di: la loro bolletta, che puo` essere caricata da loro in PDF, le offerte disponibili, che sono caricate nel sistema e i dati di consumo raccolti in tempo reale nella loro smart home, grazie al nostro Domotic hub, che puo` anche essere testato gratuitamente. L'utilizzo del sito e` sempre gratuito, grazie alle partnership con i fornitori, e i dati sono trattati con massima privacy e nel rispetto del GDPR. Inoltre tutte le funzioni del sito sono accessibili dalla sidebar a sinistra, che se l'utente non vede puo` essere aperta con il pulsante in alto a sinistra."
        },
        {
            "role": "system",
            "content": "Rispondi pure in formato markdown, e se vuoi enfatizzare una determinata parola o frase mettila all'interno delle parentesi quadre con la keyword :green davanti, in questo modo: :green[la_tua_parola_o_frase_da_enfatizzare]"
        },
        *messages
    ]

    try:
        stream = st.session_state.client.chat.send(
            model=cache['selected_model']['id'],
            messages=messages,
            stream=True,
        )
        with latest_message_assistant:
            with chat_message("assistant"):
                response = st.write_stream(stream_generator(stream))
    except Exception as e:
        with latest_message_assistant:
            with chat_message("assistant"):
                response = "Mi dispiace ma non ho saputo rispondere al tuo messaggio."
                error = f'''  
:gray[*messaggio di errore: {e} ({type(e).__name__})*]'''
                st.write(response + error)
    finally:
        model_signature = f'''  
:gray[*risposta di {model_name_format(cache["selected_model"]).split(", from")[0]}*]'''
        cache['messages'].append({"role": "assistant", "content": response + model_signature})