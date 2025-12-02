import streamlit as st
from utils import analysis_offerte as ao
from utils import model_name_format, pdf_request, Cache 
import json

cache = Cache()

def upload_bill():
    cache['bill_info_confirmed'] = False
    if 'pdf_file' in st.session_state and st.session_state['pdf_file'] is not None:
        cache['pdf_model'] = cache['selected_model']
        try:
            with st.spinner(text="Analyzing your bill. Please wait.", show_time=True):
                res = pdf_request(cache['pdf_model'], st.session_state['pdf_file'].getvalue())
                cache['pdf_content'] = res
        except KeyError:
            st.error('Our chatbot couldn\'t analyze your pdf.')
        except Exception as e:
            st.error(e)
        with open("./parsed_bill.json", "w+") as f:
            f.write(json.dumps(cache['pdf_content'], indent=4))

def show_info_about_bill():
    cache['pdf_content']['estimated_annual_cost'] = cache['pdf_content']['total_price']*12
    cache['pdf_content']['price_no_tv'] = float(cache['pdf_content']["total_price"])-float(cache['pdf_content']["tv_price"])
    cache['pdf_content']['fixed_cost'] = cache['pdf_content']['price_no_tv']-cache['pdf_content']["taxes"]-cache['pdf_content']['variable_cost']
    

    with st.container(border=True):
        # Header
        col_h1, col_h2, col_h3 = st.columns([2, 1,1])
        
        with col_h1:
            st.markdown("Ecco i tuoi dati")
            st.markdown(f"Codice offerta: :gray[*{cache['pdf_content']['offer_code']}*]")


        with col_h2:
            st.metric(
                "Costo mensile (no TV)",
                f"€{cache['pdf_content']['price_no_tv']:.2f}",
                help  = f"Prezzo variabile(€{cache['pdf_content']['variable_cost']:.2f}) + quota fissa (€{cache['pdf_content']['fixed_cost']:.2f})"
            )

            
        with col_h3:
            st.metric(
                "Costo annuo (stima)",
                "€{:.2f}".format(cache['pdf_content']["estimated_annual_cost"])
            )

def show_offers(best_offers: list):
    st.markdown("### 📋 Dettaglio offerte")
    
    for i, offer in enumerate(best_offers[:10]):
        is_best = offer['consigliata']
        
        with st.container(border=True):
            # Header
            col_h1, col_h2, col_h3 = st.columns([2, 1, 1])
            
            with col_h1:
                if is_best and i < 3:
                    st.markdown("⭐ **CONSIGLIATA**")
                st.markdown(f"### #{i+1} | {offer['fornitore']}")
                st.caption(offer['offerta'])
                
                # Badge tipo prezzo
                tipo_color = "🟢" if offer['tipo_prezzo'] == 'Fisso' else "🟡"
                st.caption(f"{tipo_color} {offer['tipo_prezzo']}")
            
            with col_h2:
                delta_value = f"-€{offer['risparmio_euro']:.2f}" if offer['risparmio_euro'] > 0 else f"+€{abs(offer['risparmio_euro']):.2f}"
                st.metric(
                    "Costo Annuo",
                    f"€{offer['costo_totale_anno']:.2f}",
                    delta=delta_value,
                    delta_color="normal" if offer['risparmio_euro'] > 0 else "inverse"
                )
            
            with col_h3:
                st.metric("Score", f"{offer['score']:.0f}/100")
            
            # Dettagli espandibili
            with st.expander("📊 Dettagli completi offerta"):
                detail_col1, detail_col2 = st.columns(2)
                
                with detail_col1:
                    st.markdown("**Componenti Costo**")
                    st.text(f"Prezzo energia: €{offer['prezzo_kwh']:.4f}/kWh")
                    st.text(f"Quota fissa: €{offer['costo_fisso_anno']:.2f}/anno")
                    st.text(f"Costo energia: €{offer['costo_energia_anno']:.2f}/anno")
                
                with detail_col2:
                    st.markdown("**Risparmio**")
                    st.text(f"Risparmio totale: €{offer['risparmio_euro']:.2f}/anno")
                    st.text(f"Percentuale: {offer['risparmio_pct']:.1f}%")
                    mensile = offer['risparmio_euro'] / 12
                    st.text(f"Mensile: €{mensile:.2f}")
                
                # Link offerta se disponibile
                if offer.get('url_offerta') and offer['url_offerta'] != 'nan':
                    st.markdown(f"🔗 [Vai all'offerta sul Portale ARERA]({offer['url_offerta']})")



def show_compared_to_other_bills() -> list:
    df_offerte, error = ao.load_arera_offers()
    best_offers = ao.find_best_offers(df_offerte, cache['pdf_content'], top_n=-1)
    if len(best_offers) == 0:
        st.warning("Nessuna offerta migliore trovata nel database")
    else:
        # Statistiche rapide
        col_s1, col_s2, col_s3, col_s4 = st.columns(4)
        
        with col_s1:
            max_saving = max([o['risparmio_euro'] for o in best_offers])
            st.metric(
                "Risparmio Max",
                f"€{max_saving:.2f}/anno",
                delta=f"{max_saving/cache['pdf_content']['estimated_annual_cost']*100:.0f}%" if cache['pdf_content']['estimated_annual_cost'] > 0 else None
            )
        
        with col_s2:
            avg_saving = sum([o['risparmio_euro'] for o in best_offers]) / len(best_offers)
            st.metric("Risparmio Medio", f"€{avg_saving:.2f}/anno")
        
        with col_s3:
            recommended = sum([1 for o in best_offers if o['consigliata']])
            st.metric("Consigliate", recommended)
        
        with col_s4:
            n_fisso = sum([1 for o in best_offers if o['tipo_prezzo'] == 'Fisso'])
            st.metric("Prezzo Fisso", f"{n_fisso}/{len(best_offers)}")
    return best_offers

def change_value(key):
    cache['pdf_content'][key] = st.session_state[key]

def change_client_type(options:list):
    type = options.index(st.session_state["customer_type_box"])
    if type == 0:
        cache['pdf_content']['client_type'] = "domestico"
        cache['pdf_content']['resident']  = True
    elif type == 1:
        cache['pdf_content']['client_type'] = "domestico"
        cache['pdf_content']['resident']  = False
    else:
        cache['pdf_content']['client_type'] = "business"
        cache['pdf_content']['resident']  = False

def show_editable_info(): 
    col1, col2 = st.columns([1, 2])

    cache['pdf_content']['fixed_cost']=cache['pdf_content']['total_price']-cache['pdf_content']["taxes"]-cache['pdf_content']['variable_cost']
    options=['Domestico residente', 'Domestico non residente', 'Business']

    try:
        index = options.index(cache['pdf_content']['client_type']) 
    except:
        index = 0 
    col1.selectbox("Tipo di customer",options, index, key="customer_type_box",args=(options,),on_change=change_client_type)
    col1.text_input("Città", cache['pdf_content']['city'].capitalize(), max_chars=15, key='city', args=('city',), on_change=change_value)

    with col2:
        c1, c2, c3 = st.columns(3, vertical_alignment="bottom")
        c1.number_input(
            "Costo Bolletta (€)", 
            value=float(cache['pdf_content']['total_price']), 
            step=1.0,
            format="%.2f",
            key="total_price",
            args=("total_price",),
            on_change=change_value
        )
        c2.number_input(
            "Consumo annuo (kWh)", 
            value=float(cache['pdf_content']['annual_consume']), 
            step=10.0,
            format="%.2f",
            key="annual_consume",
            args=("annual_consume",),
            on_change=change_value
        )
        c3.number_input(
            "Potenza Impegnata (kW)", 
            value=float(cache['pdf_content']['potenza_impegnata']), 
            step=0.5,
            format="%.2f",
            key="potenza_impegnata",
            args=("potenza_impegnata",),
            on_change=change_value
        )

        c4, c5,c6 = st.columns(3, vertical_alignment="bottom")
        c4.number_input(
            "Costo variabile (€)", 
            value=float(cache['pdf_content']['variable_cost']), 
            step=0.1,
            format="%.2f",
            key="variable_cost",
            args=("variable_cost",),
            on_change=change_value
        )
        c5.number_input(
            "Costo IVA + Accise (€)", 
            value=float(cache['pdf_content']['taxes']), 
            step=0.1, 
            format="%.2f",
            key="taxes",
            args=("taxes",),
            on_change=change_value
        )
        
        c7, c8, c9 = st.columns(3, vertical_alignment="bottom")
        
        c7.number_input(
            "Consumi Fascia F1 (€)", 
            value=float(cache['pdf_content']['f1_consume']), 
            step=1.0, 
            format="%.2f",
            key="f1_consume",
            args=("f1_consume",),
            on_change=change_value
        )
        c8.number_input(
            "Consumi Fascia F2 (€)", 
            value=float(cache['pdf_content']['f2_consume']), 
            step=1.0, 
            format="%.2f",
            key="f2_consume",
            args=("f2_consume",),
            on_change=change_value
        )
        c9.number_input(
            "Consumi Fascia F3 (€)", 
            value=float(cache['pdf_content']['f3_consume']), 
            step=1.0, 
            format="%.2f",
            key="f3_consume",
            args=("f3_consume",),
            on_change=change_value
        )
            
    st.space("small")
    st.button(label="Confirm", on_click=confirm, type='primary', width="stretch")


def confirm():
    cache['bill_info_confirmed'] = True 

with st.container(border=True):
    st.file_uploader('Carica la tua bolletta elettrica per un confronto dell\'offerta', accept_multiple_files=False, key='pdf_file', on_change=upload_bill, type='pdf')
    model_signature = st.empty()


if 'pdf_model' in cache and cache['pdf_model'] is not None and 'pdf_file' in st.session_state and st.session_state['pdf_file'] is not None:
    model_signature.write(f':gray[*file analizzato da {model_name_format(cache["selected_model"]).split(", from")[0]}*]')
    with st.container(border=True):
        if 'bill_info_confirmed' in cache and cache['bill_info_confirmed'] == True:
            show_info_about_bill()
            best_offers = show_compared_to_other_bills()
            st.markdown("---")
            show_offers(best_offers)
        else:
            show_editable_info()
                
