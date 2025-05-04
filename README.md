
# Cobot MCP Demo

This project uses N8N AI Agent Tool and MCP Server to allow an LLM to control a cobot arm.




## Installation and Setup

### Build servers using Docker Compose
The following will build the image for the MCP server.
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
Make sure cobot is turned on and connected to system. **Important: Change the cobot IP address in docker-compose.yaml.**

First, start the servers:
```
docker-compose up
```

Next, setup N8N
- Open http://localhost:5678. 
- Create an N8N account and login. 
- Start a new template and import the file n8n/N8N_MCP_OPENAI.json. You should see the following:
![n8n_dashboard](https://github.com/ReubenLimMonash/cobot_mcp_demo/tree/main/assets/images/n8n_dashboard.png)
- Edit the Webhook component to create a new credential for _Credential for Header Auth_. Set "Name" to **Authorization** and "Value" to **n8n_llm_auth** (must follow API_KEY in src/streamlit/app.py.
![n8n_dashboard](https://github.com/ReubenLimMonash/cobot_mcp_demo/tree/main/assets/images/header_auth_credentials.png)
- Enter OpenAI API key in _OpenAI Chat Model_ component. 
![n8n_dashboard](https://github.com/ReubenLimMonash/cobot_mcp_demo/tree/main/assets/images/openai_credentials.png)

Then, in a PowerShell with admin priviledges:
```bash
# Activate streamlit venv and run streamlit UI:
streamlit run src/streamlit/app.py
```
