import os
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

# Initialize the OpenAI client
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

def test_openai_connection():
    try:
        # Make a simple API call
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": "Hello, are you working?"}],
            max_tokens=10
        )
        print("✓ API connection successful!")
        print(f"Response: {response.choices[0].message.content}")
        
    except Exception as e:
        print("✗ Error connecting to OpenAI:")
        print(e)

if __name__ == "__main__":
    test_openai_connection()