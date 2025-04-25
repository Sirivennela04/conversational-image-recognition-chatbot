# Image Recognition Chatbot

This application allows users to upload images and interact with them through a chatbot interface.

## Setting Up Image Recognition APIs

The application is set up to work with various image recognition APIs. By default, it will use mock data, but you can configure it to use one of the following services:

### General Setup

1. Open `app.py` and locate the `API_CONFIG` section
2. Uncomment the section for the API you want to use
3. Add your API keys and other required configuration
4. Set `"service"` to the appropriate value (e.g., `"google"`, `"azure"`, etc.)
5. Set `"enable_mock"` to `False` to use the actual API

### Google Cloud Vision API

To use Google Cloud Vision API:

1. Create a Google Cloud account and project
2. Enable the Vision API for your project
3. Create API credentials (Service Account Key)
4. Install the required package:
   ```
   pip install google-cloud-vision
   ```
5. Set up authentication by setting the environment variable:
   ```
   export GOOGLE_APPLICATION_CREDENTIALS="/path/to/your-project-credentials.json"
   ```
6. Configure the `API_CONFIG` in `app.py`:
   ```python
   API_CONFIG = {
       "service": "google",
       "api_key": "YOUR_GOOGLE_API_KEY",
       "project_id": "your-project-id",
       "enable_mock": False
   }
   ```

## Setting Up Conversational AI (LLM)

While the image recognition APIs can detect objects in images, they don't provide conversational capabilities. To enable the chatbot to have more natural conversations about images, the application integrates with Large Language Models (LLMs).

### LLM Setup

1. Open `app.py` and locate the `LLM_CONFIG` section
2. Set `"enabled"` to `True` to activate LLM integration
3. Choose your preferred LLM service and configure it

### Google AI Studio (Gemini) Integration

To use Google's Gemini models:

1. Create a Google AI Studio account at https://ai.google.dev/
2. Create an API key in the Google AI Studio console
3. Install the required package:
   ```
   pip install google-generativeai
   ```
4. Configure the `LLM_CONFIG` in `app.py`:
   ```python
   LLM_CONFIG = {
       "enabled": True,
       "service": "gemini",
       "api_key": "YOUR_GOOGLE_AI_API_KEY",
       "model": "gemini-pro",  # Text-only model
   }
   ```


## Requirements

All requirements should be installed in your virtual environment:

```
pip install -r requirements.txt
```

The requirements.txt file should include any packages needed for your chosen API:

```
flask==2.0.1
flask-cors==3.0.10
flask-pymongo==2.3.0
pymongo==3.12.0
requests==2.26.0
python-dotenv==0.19.0

# Uncomment based on your chosen image recognition API:
# google-cloud-vision==2.6.1
# azure-cognitiveservices-vision-computervision==0.9.0
# boto3==1.18.63
# clarifai-grpc==8.0.0

# Uncomment based on your chosen LLM API:
# openai==0.28.0  # For OpenAI GPT integration
# google-generativeai==0.3.1  # For Google AI Studio / Gemini integration
```

## Security Notes

- Never commit API keys or credentials to your repository
- Use environment variables or a .env file for sensitive information
- Consider using a key management service in production 