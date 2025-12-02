from streamlit import secrets
import requests
import base64
import json


def pdf_request(model, data, fields_to_extract:list[str], labels_to_save:list[str], **kwargs) -> dict:
    ''' Placeholder until the Python OpenRouter SDK implements the pdf reading functionality natively.'''

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
                            "The kind of client MUST be either 'Private' or 'Business'"+
                            "Save the fields with these labels: "+ ", ".join(labels_to_save)
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
                'type': 'json_object'
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
    with open("./tmp.json", mode="a") as f:
        f.write(json.dumps(response, indent=4))
    return json.loads(response['choices'][0]['message']['content'])