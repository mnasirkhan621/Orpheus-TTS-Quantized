import requests
import sys

def test_tts_http():
    # Replace with your actual endpoint URL
    url = "https://k37q06aycrlyut.api.runpod.ai/tts"
    
    # Replace the placeholder below with your actual RunPod API Key
    RUNPOD_API_KEY = "rpa_BDCKASCJXC72J2XGKHYHB8U1ME8SIGNPGG23LVTG1wohf9"
    headers = {"Authorization": f"Bearer {RUNPOD_API_KEY}"}
    
    payload = {
        "text": "This is a standard HTTP request test! I am waiting for the entire audio to finish generating.",
        "voice_id": "tara"
    }
    
    print(f"Sending POST request to {url}...")
    try:
        response = requests.post(url, json=payload, headers=headers)
        
        if response.status_code == 200:
            output_file = "output_http.wav"
            with open(output_file, 'wb') as f:
                f.write(response.content)
            print(f"Success! Saved generated audio to '{output_file}'!")
        else:
            print(f"Failed. Status code: {response.status_code}")
            print(response.text)
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_tts_http()
