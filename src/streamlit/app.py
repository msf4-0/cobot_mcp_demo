import streamlit as st
from streamlit_webrtc import WebRtcMode, webrtc_streamer
from streamlit.runtime.scriptrunner import add_script_run_ctx, get_script_run_ctx
import requests
import uuid
from pathlib import Path
import speech_recognition as sr
import cv2
import av
import threading
import numpy as np
import pyttsx3
from typing import List, NamedTuple
import pymongo
from ultralytics import YOLO
import torch

# Page configuration
st.set_page_config(layout="wide")

torch.classes.__path__ = [] # add this line to manually set it to empty.

# N8N webhook configuration
WEBHOOK_URL = "http://localhost:5678/webhook/llm_agent"  # Replace with your actual webhook URL
API_TOKEN = "n8n_llm_auth"  # Replace with your actual token

HERE = Path(__file__).parent
ROOT = HERE.parent
MODEL_LOCAL_PATH = ROOT / "./models/shapes_detection/first_50_epoch/weights/best.pt"
MONGO_URL = "mongodb://localhost:27017/"
MM_PER_PIXEL_X = 0.4 # Based on original_position = (245.7, 27.5, 313)
MM_PER_PIXEL_Y = 0.4 # Based on original_position = (245.7, 27.5, 313)

class Detection(NamedTuple):
    class_id: int
    label: str
    score: float
    box: np.ndarray

# Initialize session state variables
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

if "messages" not in st.session_state:
    st.session_state.messages = []

if "rtsp_url" not in st.session_state:
    st.session_state.rtsp_url = ""

# if "frame_counter" not in st.session_state:
#     st.session_state.frame_counter = 0

def tts_run(text): 
    # engine = st.session_state.tts_engine
    engine = pyttsx3.init()
    engine.setProperty('rate', 200)
    engine.setProperty('volume',1.0)
    engine.setProperty('voice', 0)
    if not st.session_state.loop_running:
        # engine.startLoop(False)
        st.session_state.loop_running = True
    engine.say(text)
    engine.runAndWait()
    engine.stop()
    if engine._inLoop:
        engine.endLoop()
    engine = None
    st.session_state.loop_running = False

st.session_state.loop_running = False

# @st.cache_resource  # type: ignore
# def generate_label_colors():
#     return np.random.uniform(0, 255, size=(len(CLASSES), 3))
# COLORS = generate_label_colors()

@st.cache_resource
def load_mongodb():
    return pymongo.MongoClient(MONGO_URL)
mongo_client = load_mongodb()


# Session-specific caching
cache_key = "object_detection_yolo"
if cache_key in st.session_state:
    yolo = st.session_state[cache_key]
else:
    yolo = YOLO(str(MODEL_LOCAL_PATH))
    st.session_state[cache_key] = yolo

score_threshold = 0.5
frame_counter = 0

def pixel_to_mm_offset(x_pixel, y_pixel):
    offset_x_mm = -x_pixel * MM_PER_PIXEL_X  # right positive
    offset_y_mm = -y_pixel * MM_PER_PIXEL_Y  # top positive
    return offset_x_mm, offset_y_mm

def getColours(cls_num):
    base_colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255)]
    color_index = cls_num % len(base_colors)
    increments = [(1, -2, 1), (-2, 1, -1), (1, -1, 2)]
    return tuple((base_colors[color_index][i] + increments[color_index][i] *
                  (cls_num // len(base_colors))) % 256 for i in range(3))

def video_frame_callback(frame: av.VideoFrame) -> av.VideoFrame:
    global frame_counter
    cleared_db = 0 # Flag to indicate whether database has been cleared for this round
    frame = frame.to_ndarray(format="bgr24")
    
    # Get database client
    objs_db = mongo_client["objs_db"]
    latest_obj = objs_db["latest_detected_obj"] # To store the current obj detection results
    
    # Clear database if no objects detected in last 5 frames
    frame_counter += 1
    if frame_counter == 5:
        latest_obj.delete_many({})
        
    frame_height, frame_width = frame.shape[:2]
    image_center_x = frame_width // 2
    image_center_y = frame_height // 2

    results = yolo.predict(frame, save=False, verbose=False)
    for result in results:
        for box in result.boxes:
            if box.conf[0] > score_threshold:
                # There's a detection, so clear database if not already cleared
                if cleared_db == 0:
                    frame_counter = 0
                    latest_obj.delete_many({})
                    cleared_db = 1
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                x_center = int((x1 + x2) / 2)
                y_center = int((y1 + y2) / 2)
                cls = int(box.cls[0])
                class_name = result.names[cls]
                colour = getColours(cls)

                cv2.rectangle(frame, (x1, y1), (x2, y2), colour, 2)
                cv2.circle(frame, (x_center, y_center), 5, colour, -1)

                offset_x_pixel = (x_center - image_center_x)  # right positive
                offset_y_pixel = (y_center - image_center_y)  # down positive
                offset_x_mm, offset_y_mm = pixel_to_mm_offset(offset_x_pixel, offset_y_pixel)

                label = f'{class_name} {box.conf[0]:.2f}|X:{offset_x_mm:.1f}mm Y:{offset_y_mm:.1f}mm'
                cv2.putText(frame, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, colour, 2)
                # cv2.line(frame, (image_center_x, image_center_y), (x_center, y_center), (255, 255, 0), 2)
                
                # Update database 
                latest_obj.insert_one({"label": str(class_name), "offset_x_mm": offset_x_mm, "offset_y_mm": offset_y_mm})
    
    return av.VideoFrame.from_ndarray(frame, format="bgr24")

# Create two columns for layout
col1, col2 = st.columns(2)

# Video stream in the left column
with col1:
    st.header("Video Stream")
    
    webrtc_ctx = webrtc_streamer(
                key="object-detection",
                mode=WebRtcMode.SENDRECV,
                video_frame_callback=video_frame_callback,
                media_stream_constraints={"video": True, "audio": False},
                async_processing=True,
            )

    score_threshold = st.slider("Score threshold", 0.0, 1.0, 0.5, 0.05)

# LLM Chat in the right column
with col2:
    # App title
    st.title("LLM Chat Interface")
    
    # Function to send message to webhook and get response
    def process_message(prompt):
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        # Send message to n8n webhook
        headers = {
            "Authorization": f"{API_TOKEN}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "sessionId": st.session_state.session_id,
            "chatInput": prompt
        }
        
        # Display a spinner while waiting for the response
        with st.spinner("Getting response..."):
            try:
                response = requests.post(WEBHOOK_URL, headers=headers, json=payload)
                response.raise_for_status()  # Raise an exception for HTTP errors
                
                # Parse the response
                result = response.json()
                llm_response = result.get("output", "Sorry, I couldn't process your request.")
                
            except requests.exceptions.RequestException as e:
                llm_response = f"Error: Unable to connect to the LLM service. {str(e)}"
        
        # Add assistant response to chat history
        st.session_state.messages.append({"role": "assistant", "content": llm_response})
        
        # Say response using TTS
        thread = threading.Thread(target=tts_run, args=(llm_response,))
        thread.daemon = True
        add_script_run_ctx(thread, get_script_run_ctx())
        thread.start()

        # Rerun to update the chat display
        st.rerun()

    # Function to transcribe audio from microphone
    def transcribe_audio():
        recognizer = sr.Recognizer()
        microphone = sr.Microphone()
        
        with st.spinner("Listening..."):
            try:
                with microphone as source:
                    recognizer.adjust_for_ambient_noise(source)
                    st.info("Listening... Speak now.")
                    audio = recognizer.listen(source, timeout=5)
                    st.success("Audio captured! Processing...")
                
                text = recognizer.recognize_google(audio)
                # text = recognizer.recognize_whisper(audio)
                return text
            except sr.WaitTimeoutError:
                st.error("No speech detected. Please try again.")
            except sr.RequestError:
                st.error("Could not request results from speech recognition service.")
            except sr.UnknownValueError:
                st.error("Could not understand audio.")
            except Exception as e:
                st.error(f"Error: {str(e)}")
        
        return None

    # Create a container with fixed height for the chat messages
    chat_placeholder = st.empty()
    with chat_placeholder.container():
        # Apply CSS to create scrollable container
        st.markdown("""
        <style>
        .stChatMessages {
            height: 500px;
            overflow-y: auto;
        }
        .streamlit-container {
            max-width: 100%;
        }
        </style>
        """, unsafe_allow_html=True)
        
        # Display all messages in the scrollable container
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
    
    # Audio input button
    col_type, col_send = st.columns([3, 1])
    with col_type:
        # Text input for typing messages
        prompt = st.chat_input("What would you like to discuss?")
        
    with col_send:
        # Audio input button
        if st.button("🎤 Speak"):
            transcribed_text = transcribe_audio()
            if transcribed_text:
                # Process the transcribed text
                process_message(transcribed_text)
    
    # Process text input if provided
    if prompt:
        process_message(prompt)

# Add a sidebar with session information
with st.sidebar:
    st.header("Session Information")
    st.write(f"Session ID: {st.session_state.session_id}")
    
    # Add a button to start a new session
    if st.button("Start New Session"):
        # Reset chat session
        st.session_state.session_id = str(uuid.uuid4())
        st.session_state.messages = []
        st.rerun()

# Clean up resources on script termination
def cleanup():
    st.session_state.tts_engine.stop()

# Register cleanup handler
import atexit
atexit.register(cleanup)