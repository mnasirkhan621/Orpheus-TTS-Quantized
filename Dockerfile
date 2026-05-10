FROM python:3.10-slim

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    ffmpeg \
    git \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .

# Temporarily set to 0 to allow downloading models and dependencies
ENV HF_HUB_OFFLINE=0

RUN pip install --no-cache-dir -r requirements.txt

# Download the required models directly into the image during the build process
RUN huggingface-cli download heydryft/Orpheus-3b-FT-AWQ
RUN huggingface-cli download hubertsiuzdak/snac_24khz

# Enforce offline mode at runtime
ENV HF_HUB_OFFLINE=1

COPY server.py .

EXPOSE 8000

CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]
