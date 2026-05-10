# Orpheus TTS Server

A production-ready, real-time streaming Text-to-Speech server using the Orpheus-3B model and vLLM. Designed to be deployed on RunPod Serverless or Dedicated GPU instances.

## Features
- **vLLM Integration:** Utilizes continuous batching and PagedAttention for maximum throughput and minimal latency.
- **Real-Time Streaming:** Streams 24kHz PCM audio over WebSockets as soon as chunks are available (~100-200ms Time-To-First-Audio).
- **Voice Caching & Cloning:** Instantly switch between default voices or upload a 3-5s `.wav` to create custom clones on the fly.
- **Robustness:** Includes strict sliding-window loop detectors to prevent model repetition and filters for garbled audio tokens.
- **Fully Offline:** Models are baked into the Docker image, enabling fast cold-starts without hitting the Hugging Face hub.

## RunPod Deployment Instructions

### 1. Build the Docker Image
You can build and push the image to Docker Hub (or any container registry) locally:

```bash
# Build the image (this will download the ~6GB models into the container)
docker build -t yourusername/orpheus-tts:latest .

# Push to your registry
docker push yourusername/orpheus-tts:latest
```

### 2. Deploy on RunPod
1. Go to your RunPod dashboard and click **Deploy**.
2. Select a GPU template (e.g., RTX 4090 or RTX A4000).
3. In the **Container Image** field, enter your image name: `yourusername/orpheus-tts:latest`
4. In the **Expose HTTP Ports** field, ensure `8000` is exposed.
5. Launch the pod. The server will start automatically with offline model loading.

## API Usage

### WebSocket Endpoint: `/stream_audio`
Connect via WebSocket to stream audio in real time.

**Request payload:**
```json
{
    "text": "Hello, this is a test of the real-time TTS system.",
    "voice_id": "tara"
}
```
**Response:**
Raw binary chunks of 24kHz Int16 PCM audio.

### REST Endpoint: `/add_voice`
Create a custom voice clone from a short audio sample.

**POST /add_voice**
- **file**: (form-data) The `.wav` audio file (3-5 seconds recommended).
- **custom_voice_id**: (form-data) The unique name for this voice.

Example using `curl`:
```bash
curl -X POST http://<runpod-url>:8000/add_voice \
  -F "file=@my_voice.wav" \
  -F "custom_voice_id=my_custom_clone"
```
After a successful response, you can use `"voice_id": "my_custom_clone"` in your WebSocket requests.
