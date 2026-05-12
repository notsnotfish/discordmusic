FROM python:3.11-alpine

WORKDIR /app

COPY requirements.txt requirements.txt

RUN apk add --no-cache alpine-sdk ffmpeg libffi-dev \
    && pip3 install -r requirements.txt \
    && apk del alpine-sdk

COPY . .

# Set stop signal to SIGTERM to ensure clean shutdown
STOPSIGNAL SIGTERM

CMD ["python3", "/app/discodrome.py"]