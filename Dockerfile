FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y gcc curl && rm -rf /var/lib/apt/lists/*

COPY requirements-docker.txt .
RUN pip install --no-cache-dir -r requirements-docker.txt

COPY web_api_docker.py ./web_api.py
COPY panel_docker.html ./templates/panel.html
COPY login.html ./templates/login.html
COPY central_client.py .
COPY config.json .
COPY bg-login.jpg .
COPY logo.png .
COPY icon.ico .
COPY builder2.py .
COPY Program.py .
COPY compile_rat.py .
COPY requirements.txt .

RUN mkdir -p ./dist ./logs ./data ./screenshots ./templates

EXPOSE 5000

ENV FLASK_ENV=production

CMD ["python", "-u", "web_api.py"]
