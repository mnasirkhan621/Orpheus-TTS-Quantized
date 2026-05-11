FROM vllm/vllm-openai:v0.5.4

USER root
ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    ffmpeg \
    git \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Temporarily set to 0 to allow downloading models and dependencies
ENV HF_HUB_OFFLINE=0

RUN pip install --no-cache-dir fastapi uvicorn websockets snac torchaudio librosa soundfile huggingface_hub numpy python-multipart
RUN pip install --no-cache-dir --upgrade tokenizers transformers
RUN pip install --no-cache-dir autoawq

# Download the required models directly into the image during the build process
RUN python3 -c "from huggingface_hub import snapshot_download; snapshot_download('heydryft/Orpheus-3b-FT-AWQ')"
RUN python3 -c "from huggingface_hub import snapshot_download; snapshot_download('hubertsiuzdak/snac_24khz')"

# Enforce offline mode at runtime
ENV HF_HUB_OFFLINE=1
ENV VLLM_USE_V1=0
ENV VLLM_WORKER_MULTIPROC_METHOD=spawn

COPY server.py .

EXPOSE 8000

# Override the default vllm entrypoint
ENTRYPOINT []
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]
