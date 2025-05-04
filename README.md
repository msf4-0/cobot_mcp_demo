
# Cobot MCP Demo

This project uses N8N AI Agent Tool and MCP Server to allow an LLM to control a cobot arm.




## Installation and Setup

### Build servers using Docker Compose
The following will build the image for N8N, MCP server, and MongoDB server.
Make sure Docker Desktop is installed and running.
```bash
  docker-compose build
```

### Setup Streamlit Virtual Environment
Install uv (https://docs.astral.sh/uv/getting-started/installation/). Then, in a PowerShell with admin priviledges:
```bash
uv venv streamlit --python 3.10
# Enable uv venv activation:
Set-ExecutionPolicy RemoteSigned
# Activate venv:
.\streamlit\Scripts\activate
uv pip install streamlit, SpeechRecognition, PyAudio, streamlit_webrtc, opencv-python, pyttsx3, pymongo
```
## Running UI
Make sure cobot is turned on and connected to system.

First, start the servers:
```
docker-compose up
```

Next, setup N8N
- Open http://localhost:5678. 
- Create an N8N account and login. 
- Start a new template and import the file n8n/N8N_MCP_OPENAI.json.

Then, in a PowerShell with admin priviledges:
```bash
# Activate streamlit venv and run streamlit UI:
streamlit run src/streamlit/app.py
```
