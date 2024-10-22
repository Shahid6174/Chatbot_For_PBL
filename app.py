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

# Function to load the appropriate Gemini model and get responses
def get_gemini_response(question, image=None):
    if image:
        # Use gemini-1.5-flash when an image is provided
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content([question, image] if question else image)
    else:
        # Use gemini-pro for text-only input
        model = genai.GenerativeModel('gemini-pro')
        response = model.generate_content(question)
    
    return response.text

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

        # If speech recognition is selected
        if input_method == "Voice Input":
            input_text = recognize_speech_from_mic()

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

        # If ask button is clicked
        if input_text or image:
            response = get_gemini_response(input_text, image)
    
    return render_template("index.html", response=response, image_base64=image_base64)

if __name__ == "__main__":
    app.run(debug=True)
