import os
import io
import asyncio
import uuid
import re
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse
import torch
import numpy as np
import soundfile as sf
import librosa
from snac import SNAC
from vllm import AsyncLLMEngine, AsyncEngineArgs, SamplingParams
from transformers import AutoTokenizer

# Config
MODEL_ID = "heydryft/Orpheus-3b-FT-AWQ"
SNAC_MODEL_ID = "hubertsiuzdak/snac_24khz"
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
POS_OFFSETS = [0, 4096, 8192, 12288, 16384, 20480, 24576]

# Global variables
engine = None
tokenizer = None
snac_model = None

voice_cache = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    global engine, tokenizer, snac_model
    print("Loading vLLM engine...")
    engine_args = AsyncEngineArgs(
        model=MODEL_ID,
        quantization="awq",
        tensor_parallel_size=1,
        trust_remote_code=True,
        max_model_len=4096,
        enforce_eager=False,
    )
    engine = AsyncLLMEngine.from_engine_args(engine_args)
    tokenizer = AutoTokenizer.from_pretrained(MODEL_ID, trust_remote_code=True)
    
    print("Loading SNAC model...")
    snac_model = SNAC.from_pretrained(SNAC_MODEL_ID).eval().to(DEVICE)
    print("Models loaded successfully.")
    yield

app = FastAPI(lifespan=lifespan)

def get_custom_token_ids(raw_codes):
    tokens = [f"<custom_token_{c}>" for c in raw_codes]
    ids = tokenizer.convert_tokens_to_ids(tokens)
    for i, t_id in enumerate(ids):
        if t_id is None:
            ids[i] = tokenizer.encode(tokens[i], add_special_tokens=False)[0]
    return ids

@app.post("/add_voice")
async def add_voice(file: UploadFile = File(...), custom_voice_id: str = Form(...)):
    try:
        audio_bytes = await file.read()
        audio, sr = librosa.load(io.BytesIO(audio_bytes), sr=24000)
        
        audio_tensor = torch.tensor(audio).unsqueeze(0).unsqueeze(0).to(DEVICE)
        with torch.inference_mode():
            codes = snac_model.encode(audio_tensor)
        
        c0 = codes[0].squeeze(0).cpu().numpy()
        c1 = codes[1].squeeze(0).cpu().numpy()
        c2 = codes[2].squeeze(0).cpu().numpy()
        
        N = len(c0)
        raw_codes = []
        for i in range(N):
            frame_snac_codes = [
                c0[i],
                c1[2*i],
                c2[4*i],
                c2[4*i+1],
                c1[2*i+1],
                c2[4*i+2],
                c2[4*i+3]
            ]
            for pos, sc in enumerate(frame_snac_codes):
                raw_code = sc + POS_OFFSETS[pos] + 10
                raw_codes.append(int(raw_code))
                
        token_ids = get_custom_token_ids(raw_codes)
        voice_cache[custom_voice_id] = token_ids
        
        return JSONResponse({"status": "success", "voice_id": custom_voice_id})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def decode_frames(frames):
    if not frames:
        return None
    c0 = torch.tensor([f[0] for f in frames], dtype=torch.long).unsqueeze(0)
    c1 = torch.tensor([v for f in frames for v in [f[1], f[4]]], dtype=torch.long).unsqueeze(0)
    c2 = torch.tensor([v for f in frames for v in [f[2], f[3], f[5], f[6]]], dtype=torch.long).unsqueeze(0)
    
    with torch.inference_mode():
        audio = snac_model.decode([c0.to(DEVICE), c1.to(DEVICE), c2.to(DEVICE)])
    return audio.squeeze().cpu().numpy()

@app.websocket("/stream_audio")
async def stream_audio(websocket: WebSocket):
    await websocket.accept()
    try:
        data = await websocket.receive_json()
        text = data.get("text", "")
        voice_id = data.get("voice_id", "tara")
        
        prompt_ids = [128000, 128259] # BOS, start_tts
        
        if voice_id in voice_cache:
            prompt_ids.extend(voice_cache[voice_id])
            
        text_tokens = tokenizer.encode(f"{voice_id}: {text}", add_special_tokens=False)
        prompt_ids.extend(text_tokens)
        prompt_ids.append(128260) # audio_trigger
        
        stop_id = tokenizer.convert_tokens_to_ids("<custom_token_2>")
        if stop_id is None:
            stop_id = tokenizer.encode("<custom_token_2>", add_special_tokens=False)[0]
             
        sampling_params = SamplingParams(
            temperature=0.6,
            top_p=0.9,
            repetition_penalty=1.3,
            presence_penalty=0.5,
            max_tokens=2000,
            stop_token_ids=[stop_id]
        )
        
        request_id = str(uuid.uuid4())
        results_generator = engine.generate(
            prompt={"prompt_token_ids": prompt_ids},
            sampling_params=sampling_params,
            request_id=request_id
        )
        
        pointer = 0
        recent_frames = [] 
        
        async for request_output in results_generator:
            new_text = request_output.outputs[0].text
            name_nums = [int(m) for m in re.findall(r"<custom_token_(\d+)>", new_text)]
            audio_nums = [n for n in name_nums if n >= 10]
            
            n_full = (len(audio_nums) // 7) * 7
            
            loop_detected = False
            
            if n_full > pointer:
                new_frames = []
                for i in range(pointer, n_full, 7):
                    frame = []
                    valid = True
                    for pos in range(7):
                        raw_code = audio_nums[i + pos] - 10
                        snac_code = raw_code - POS_OFFSETS[pos]
                        if not (0 <= snac_code < 4096):
                            valid = False
                            break
                        frame.append(snac_code)
                    
                    if valid:
                        new_frames.append(frame)
                        recent_frames.append(frame)
                        if len(recent_frames) > 20:
                            recent_frames.pop(0)
                        
                        # Loop detection: check if last 4 frames match previous 4 frames
                        if len(recent_frames) >= 8:
                            if recent_frames[-4:] == recent_frames[-8:-4]:
                                await engine.abort(request_id)
                                loop_detected = True
                                break
                                
                pointer = n_full
                
                if new_frames:
                    wav_chunk = decode_frames(new_frames)
                    if wav_chunk is not None:
                        pcm_chunk = (wav_chunk * 32767.0).astype(np.int16)
                        await websocket.send_bytes(pcm_chunk.tobytes())
                        
            if loop_detected:
                break
                
    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"WebSocket error: {e}")
        try:
            await websocket.close()
        except:
            pass
