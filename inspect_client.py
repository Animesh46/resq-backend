from google import genai
import os

client = genai.Client(api_key=os.environ.get('GEMINI_API_KEY'))
print('client attributes:')
for attr in dir(client):
    if 'model' in attr.lower() or 'list' in attr.lower():
        print(' ', attr)

print('\nclient.models attributes:')
for attr in dir(client.models):
    if 'model' in attr.lower() or 'list' in attr.lower():
        print(' ', attr)
