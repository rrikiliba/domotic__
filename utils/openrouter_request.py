from streamlit import secrets
import requests
import base64
import json


def pdf_request(model, data, **kwargs) -> dict:
    ''' Placeholder until the Python OpenRouter SDK implements the pdf reading functionality natively.'''

    fields_to_extract = [
        "Tipologia di cliente",
        "Consumo annuo",
        "Comune di fornitura",
        "Prezzo bolletta totale",
        "Importo canone televisione per uso privato",
        "Potenza impegnata",
        "Accise e IVA",
        "Quota per consumi",
        "Codice offerta",
    ] #also change json_schema in reqeust
    
    response = requests.post(
        url='https://openrouter.ai/api/v1/chat/completions', 
        headers={
            "Authorization": f"Bearer {secrets['OPENROUTER_API_KEY']}",
            "Content-Type": "application/json"
        }, 
        json={
            'model': model['id'],
            'messages': [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "Create a summary of the information about this electricity bill, in syntactically correct json format."+
                            "You must include ONLY these fields: "+ ", ".join(fields_to_extract)+
                            "Do NOT include units. Name the fields EXACTLY as the request."+
                            "Numbers must be treated as number. If there is a decimal number, separate with a dot"+
                            "The kind of client MUST be either 'Private' or 'Business'"
                        },
                        {
                            "type": "file",
                            "file": {
                                "filename": "document.pdf",
                                "file_data": f"data:application/pdf;base64,{base64.b64encode(data).decode('utf-8')}"
                            }
                        },
                    ]
                }
            ],
            'stream': False,
            'response_format': {
                'type': 'json_schema',
                "json_schema": {
                    "name": "Bill analysis",
                    "strict": True,
                    "schema": {
                        "type": "object",
                        "properties": {
                            "client_type": {
                                "type": "string",
                                "description": "Either 'Private' or 'Business'"
                            },
                            "annual_consume": {
                                "type": "number",
                                "description": "Consumo annuo"
                            },
                            "city": {
                                "type": "string",
                                "description": "città di fornitura"
                            },
                            "total_price": {
                                "type": "number",
                                "description": "Raw price of the bill"
                            },
                            "tv_price": {
                                "type": "number",
                                "description": "Price of canone tv"
                            },
                            "potenza_impegnata": {
                                "type": "number",
                                "description": "Potenza impeganta"
                            },
                            "taxes": {
                                "type": "number",
                                "description": "Accise & IVA"
                            },
                            "variable_cost": {
                                "type": "number",
                                "description": "Quota per consumi della bolletta"
                            },
                            "offer_code": {
                                "type": "string",
                                "description": "Codice offerta"
                            }
                        },
                        "required": ["client_type", "annual_consume", "city",
                                    "total_price","tv_price", "potenza_impegnata",
                                    "taxes","variable_cost","offer_code"],
                        "additionalProperties": False
                    }
                }
            },
            'plugins': [
                {
                    "id": "file-parser",
                    "pdf": {
                        "engine": "pdf-text",
                    },
                },
            ],
            **kwargs
        }
    ).json()
    # with open("./tmp.json", mode="a") as f:
        # f.write(json.dumps(response, indent=4))
    return json.loads(response['choices'][0]['message']['content'])