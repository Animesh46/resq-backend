from google import genai
import os

api_key = os.environ.get('GEMINI_API_KEY')
if not api_key:
    raise RuntimeError('GEMINI_API_KEY not set')

from google.genai import types

# force the stable v1 API so newer "pro" models are available
client = genai.Client(
    api_key=api_key,
    http_options=types.HttpOptions(api_version='v1'),
)

for model in ['gemini-2.0-pro', 'gemini-2.0-flash', 'gemini-2.1', 'text-bison-001']:
    try:
        print('Testing', model)
        resp = client.models.generate_content(model=model, contents='Hello')
        print('Success', resp.text)
    except Exception as e:
        print('Failed', model, '->', e)

print('\nNow trying GEMINI_MODEL env handling...')
for m in ['gemini-2.0-flash', 'invalid-model']:
    os.environ['GEMINI_MODEL'] = m
    print('Setting GEMINI_MODEL', m)
    try:
        text = gemini._call_model('Ping')
        print('call returned', text)
    except Exception as e:
        print('call_model raised', e)
