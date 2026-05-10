import requests
import sys

RUNPOD_API_KEY = "rpa_BDCKASCJXC72J2XGKHYHB8U1ME8SIGNPGG23LVTG1wohf9"
BASE_URL = "https://k37q06aycrlyut.api.runpod.ai"


def generate_tts(text, voice_id="tara", output_file="output.wav"):
    url = f"{BASE_URL}/tts"
    headers = {"Authorization": f"Bearer {RUNPOD_API_KEY}"}
    payload = {"text": text, "voice_id": voice_id}

    print(f"Sending TTS request for voice '{voice_id}'...")
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=120)
        response.raise_for_status()

        with open(output_file, "wb") as f:
            f.write(response.content)

        print(f"Saved {len(response.content):,} bytes to '{output_file}'")
    except requests.exceptions.HTTPError as e:
        print(f"HTTP error {response.status_code}: {response.text}")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    text_to_speak = "Hello there! This is a test of the Orpheus TTS server."
    generate_tts(text_to_speak, "tara", "test_output.wav")
