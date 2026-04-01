FROM python:3.10-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    nodejs npm \
    libportaudio2 \
    portaudio19-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt pyproject.toml ./
COPY agent/ ./agent/
COPY web_avatar/ ./web_avatar/

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --upgrade pip && pip install -r requirements.txt && \
    pip install --force-reinstall --no-cache-dir sounddevice

RUN npm install && cd web_avatar && npm install && cd ..

EXPOSE 8765 5173

CMD ["sh", "-c", "node web_avatar/server.js & python agent/main.py & cd web_avatar && npm run dev"]
