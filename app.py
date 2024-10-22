import os
from flask import Flask, render_template, request
import google.generativeai as genai
import speech_recognition as sr
from dotenv import load_dotenv
from PIL import Image
from io import BytesIO
import base64

# Load environment variables from .env
load_dotenv()

# Configure the Google AI
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

app = Flask(__name__)

# Function to format the response into HTML
def format_response(response_text):
    # Check if response_text is a string and wrap it in HTML
    if isinstance(response_text, str):
        return f"<div><p>{response_text.replace('*', '<strong>').replace('\\n', '</p><p>')}</p></div>"

    formatted_response = "<div>"

    for key, value in response_text.items():
        formatted_response += f"<h3>{key}</h3>"

        if isinstance(value, str):
            formatted_response += f"<p>{value}</p>"
        elif isinstance(value, list):
            formatted_response += "<ul>"
            for item in value:
                if isinstance(item, dict):
                    title = item.get("title", "")
                    description = item.get("description", "")
                    formatted_response += f"<li><strong>{title}:</strong> {description}</li>"
                else:
                    formatted_response += f"<li>{item}</li>"
            formatted_response += "</ul>"
        elif isinstance(value, dict):
            formatted_response += format_response(value)  # Recursive formatting for nested dicts

    formatted_response += "</div>"
    return formatted_response

# Function to load the appropriate Gemini model and get responses
def get_gemini_response(question, image=None):
    try:
        if image:
            model = genai.GenerativeModel('gemini-1.5-flash')
            response = model.generate_content([question, image] if question else image)
        else:
            model = genai.GenerativeModel('gemini-pro')
            response = model.generate_content(question)

        # Check for safety ratings in the response
        safety_ratings = response.safety_ratings if hasattr(response, 'safety_ratings') else []
        error_messages = []

        for rating in safety_ratings:
            if rating.category in ['HARM_CATEGORY_SEXUALLY_EXPLICIT', 'HARM_CATEGORY_HATE_SPEECH', 'HARM_CATEGORY_HARASSMENT']:
                error_messages.append(f"Inappropriate content detected: {rating.category}")

        # Raise error if inappropriate content is detected
        if error_messages:
            return "Your query could not be processed due to inappropriate content."

        # Format the response as HTML
        formatted_response = format_response(response.text)
        return formatted_response

    except Exception as e:
        return f"An error occurred: {str(e)}"

# Speech recognition function
def recognize_speech_from_mic():
    r = sr.Recognizer()
    with sr.Microphone() as source:
        print("Listening...")
        audio = r.listen(source)

    try:
        print("Recognizing...")
        text = r.recognize_google(audio)
        print(f"Recognized Text: {text}")
        return text
    except sr.UnknownValueError:
        print("Sorry, I could not understand the audio.")
        return None
    except sr.RequestError as e:
        print(f"Could not request results from Google Speech Recognition service; {e}")
        return None

# Home route to render the input form
@app.route("/", methods=["GET", "POST"])
def home():
    response = None
    image_base64 = None
    if request.method == "POST":
        input_method = request.form.get("input_method")
        input_text = request.form.get("input_text")

        # If speech recognition is selected and processed
        if input_text:
            response = get_gemini_response(input_text)

        # Handle image upload
        uploaded_file = request.files.get("image")
        image = None
        if uploaded_file and uploaded_file.filename != "":
            image = Image.open(uploaded_file)
            # Convert image to RGB if it is in RGBA mode
            if image.mode == "RGBA":
                image = image.convert("RGB")
            # Convert image to base64 for displaying in HTML
            buffered = BytesIO()
            image.save(buffered, format="JPEG")
            image_base64 = base64.b64encode(buffered.getvalue()).decode()

        # If ask button is clicked or voice input is processed
        if input_text or image:
            response = get_gemini_response(input_text, image)
    
    return render_template("index.html", response=response, image_base64=image_base64)

if __name__ == "__main__":
    app.run(debug=True)