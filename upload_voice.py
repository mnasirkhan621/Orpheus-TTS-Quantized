import requests
import sys

def upload_voice(wav_file_path, custom_voice_id):
    url = "http://localhost:8000/add_voice"
    
    print(f"Uploading {wav_file_path} to create voice '{custom_voice_id}'...")
    
    try:
        with open(wav_file_path, 'rb') as f:
            files = {'file': (wav_file_path, f, 'audio/wav')}
            data = {'custom_voice_id': custom_voice_id}
            
            response = requests.post(url, files=files, data=data)
            
        if response.status_code == 200:
            print("Success!")
            print(response.json())
        else:
            print(f"Failed. Status code: {response.status_code}")
            print(response.text)
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python upload_voice.py <path_to_wav> <custom_voice_id>")
        sys.exit(1)
        
    upload_voice(sys.argv[1], sys.argv[2])
