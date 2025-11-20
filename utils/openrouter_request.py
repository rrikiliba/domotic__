from streamlit import secrets
import requests
import base64
import json

def pdf_request(model, data, **kwargs) -> dict:
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
                            "text": "Create a summary of the most important information about this electricity bill, in syntactically correct json format."
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
    # print(json.dumps(response, indent=4))
    return response['choices'][0]['message']['content']