from google import genai
import os

def main():
    client = genai.Client(api_key=os.environ.get('GEMINI_API_KEY'))
    models = client.list_models()
    print(models)

if __name__ == '__main__':
    main()