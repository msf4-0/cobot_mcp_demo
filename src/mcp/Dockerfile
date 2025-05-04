FROM python:3.10-slim

WORKDIR /app

COPY src/mcp/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/mcp .

CMD ["python", "cobot_mcp_server.py"]
