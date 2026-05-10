import asyncio
import websockets
import json
import numpy as np
import soundfile as sf
import sys

async def test_tts(text, voice_id="tara", output_file="output.wav"):
    uri = "ws://localhost:8000/stream_audio"
    
    print(f"Connecting to {uri}...")
    try:
        async with websockets.connect(uri) as websocket:
            print(f"Connected! Requesting TTS for voice '{voice_id}'...")
            
            payload = {
                "text": text,
                "voice_id": voice_id
            }
            await websocket.send(json.dumps(payload))
            
            audio_chunks = []
            
            print("Receiving audio stream...")
            try:
                while True:
                    chunk = await websocket.recv()
                    # Convert raw bytes back to numpy array (Int16)
                    pcm_data = np.frombuffer(chunk, dtype=np.int16)
                    audio_chunks.append(pcm_data)
                    sys.stdout.write(".")
                    sys.stdout.flush()
            except websockets.exceptions.ConnectionClosed:
                print("\nStream complete.")
                
            if audio_chunks:
                full_audio = np.concatenate(audio_chunks)
                # Convert Int16 back to Float32 for soundfile saving
                full_audio_float = full_audio.astype(np.float32) / 32767.0
                sf.write(output_file, full_audio_float, 24000)
                print(f"Saved generated audio to '{output_file}'!")
            else:
                print("No audio received.")
                
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    text_to_speak = "Hello there! This is a real-time streaming test of the Orpheus TTS server."
    asyncio.run(test_tts(text_to_speak, "tara", "test_stream.wav"))
