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
import os 

# Page configuration
st.set_page_config(layout="wide")

# N8N webhook configuration
WEBHOOK_URL = "http://localhost:5678/webhook/llm_agent"  # Replace with your actual webhook URL
API_TOKEN = "n8n_llm_auth"  # Replace with your actual token

'''For Object Detection'''
HERE = Path(__file__).parent
ROOT = HERE.parent
MODEL_LOCAL_PATH = ROOT / "./models/MobileNetSSD_deploy.caffemodel"
PROTOTXT_LOCAL_PATH = ROOT / "./models/MobileNetSSD_deploy.prototxt.txt"
MONGO_URI = os.getenv('MONGO_URI', 'mongodb://localhost:27017/objs_db')

CLASSES = [
    "background",
    "aeroplane",
    "bicycle",
    "bird",
    "boat",
    "bottle",
    "bus",
    "car",
    "cat",
    "chair",
    "cow",
    "diningtable",
    "dog",
    "horse",
    "motorbike",
    "person",
    "pottedplant",
    "sheep",
    "sofa",
    "train",
    "tvmonitor",
]

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

if "video_running" not in st.session_state:
    st.session_state.video_running = False

if "rtsp_url" not in st.session_state:
    st.session_state.rtsp_url = ""

if "frame" not in st.session_state:
    st.session_state.frame = None

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

@st.cache_resource  # type: ignore
def generate_label_colors():
    return np.random.uniform(0, 255, size=(len(CLASSES), 3))
COLORS = generate_label_colors()

@st.cache_resource
def load_mongodb():
    return pymongo.MongoClient(MONGO_URL)
mongo_client = load_mongodb()


# Session-specific caching
cache_key = "object_detection_dnn"
if cache_key in st.session_state:
    net = st.session_state[cache_key]
else:
    net = cv2.dnn.readNetFromCaffe(str(PROTOTXT_LOCAL_PATH), str(MODEL_LOCAL_PATH))
    st.session_state[cache_key] = net

score_threshold = 0.5

# NOTE: The callback will be called in another thread,
#       so use a queue here for thread-safety to pass the data
#       from inside to outside the callback.
# TODO: A general-purpose shared state object may be more useful.
# result_queue: "queue.Queue[List[Detection]]" = queue.Queue()

def video_frame_callback(frame: av.VideoFrame) -> av.VideoFrame:
    image = frame.to_ndarray(format="bgr24")

    # Run inference
    blob = cv2.dnn.blobFromImage(
        image=cv2.resize(image, (300, 300)),
        scalefactor=0.007843,
        size=(300, 300),
        mean=(127.5, 127.5, 127.5),
    )
    net.setInput(blob)
    output = net.forward()

    h, w = image.shape[:2]

    # Convert the output array into a structured form.
    output = output.squeeze()  # (1, 1, N, 7) -> (N, 7)
    output = output[output[:, 2] >= score_threshold]
    detections = [
        Detection(
            class_id=int(detection[1]),
            label=CLASSES[int(detection[1])],
            score=float(detection[2]),
            box=(detection[3:7] * np.array([w, h, w, h])),
        )
        for detection in output
    ]

    # Clear database so that new latest results can be added
    objs_db = mongo_client["object_detection"]
    latest_obj = objs_db["latest_detected_obj"] # To store the current obj detection results
    

    # Render bounding boxes and captions
    if len(detections)>0:
        latest_obj.delete_many({})
        for detection in detections:
            caption = f"{detection.label}: {round(detection.score * 100, 2)}%"
            color = COLORS[detection.class_id]
            xmin, ymin, xmax, ymax = detection.box.astype("int")
            cv2.rectangle(image, (xmin, ymin), (xmax, ymax), color, 2)
            cv2.putText(
                image,
                caption,
                (xmin, ymin - 15 if ymin - 15 > 15 else ymin + 15),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                color,
                2,
            )
            latest_obj.insert_one({"label": str(detection.label), "x": (xmin+xmax)/2, "y_min": (ymin+ymax)/2})

    return av.VideoFrame.from_ndarray(image, format="bgr24")

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
    
    # if st.checkbox("Show the detected labels", value=True):
    #     if webrtc_ctx.state.playing:
    #         labels_placeholder = st.empty()
    #         # NOTE: The video transformation with object detection and
    #         # this loop displaying the result labels are running
    #         # in different threads asynchronously.
    #         # Then the rendered video frames and the labels displayed here
    #         # are not strictly synchronized.
    #         while True:
    #             result = result_queue.get()
    #             labels_placeholder.table(result)


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
            "Authorization": f"Bearer {API_TOKEN}",
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
        # Make sure to stop video if running
        st.session_state.video_running = False
        # Reset chat session
        st.session_state.session_id = str(uuid.uuid4())
        st.session_state.messages = []
        st.rerun()
    
    # Add technical info
    st.header("Technical Info")
    if st.session_state.video_running:
        st.success("Stream Status: Running")
    else:
        st.error("Stream Status: Stopped")
    
    if st.session_state.frame is not None:
        st.write(f"Frame Size: {st.session_state.frame.shape[1]}x{st.session_state.frame.shape[0]}")

# Clean up resources on script termination
def cleanup():
    if st.session_state.video_running:
        st.session_state.video_running = False
    st.session_state.tts_engine.stop()

# Register cleanup handler
import atexit
atexit.register(cleanup)