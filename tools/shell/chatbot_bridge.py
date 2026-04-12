import time
import json
import urllib.request
import urllib.parse
import subprocess
import argparse

def send_message(token, chat_id, text):
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    data = {"chat_id": chat_id, "text": text}
    req = urllib.request.Request(url, json.dumps(data).encode('utf-8'), {'Content-Type': 'application/json'})
    try:
        urllib.request.urlopen(req)
    except Exception as e:
        print(f"Failed to send message: {e}")

def get_updates(token, offset=None):
    url = f"https://api.telegram.org/bot{token}/getUpdates"
    if offset:
        url += f"?offset={offset}&timeout=10"
    else:
        url += "?timeout=10"
        
    try:
        response = urllib.request.urlopen(url, timeout=15)
        return json.loads(response.read().decode('utf-8'))
    except Exception as e:
        print(f"Failed to get updates: {e}")
        return None

def execute_intent(text):
    text = text.lower()
    if 'mute' in text:
        subprocess.run(['amixer', 'set', 'Master', 'toggle'], capture_output=True)
        return "Toggled hardware mute."
    elif 'ip' in text or 'network' in text:
        res = subprocess.run(['ip', 'a'], capture_output=True, text=True)
        return res.stdout[:500] + "..." if len(res.stdout) > 500 else res.stdout
    elif 'lock' in text:
        subprocess.run(['xdg-screensaver', 'lock'], capture_output=True)
        return "Screen locked."
    elif 'status' in text:
        res = subprocess.run(['uptime'], capture_output=True, text=True)
        return f"System Status:\n{res.stdout.strip()}"
    else:
        # Fallback to pure shell execution for power user remote access
        try:
            res = subprocess.run(text, shell=True, capture_output=True, text=True, timeout=10)
            if res.returncode == 0:
                out = res.stdout.strip()
                return out[:1000] if out else "Done."
            else:
                err = res.stderr.strip()
                return f"Error ({res.returncode}):\n{err[:1000]}"
        except Exception as e:
            return f"Failed: {str(e)}"

def main():
    parser = argparse.ArgumentParser(description="MnemonicOS Mobile Bridge")
    parser.add_argument('--token', required=True, help="Telegram Bot Token")
    args = parser.parse_args()
    
    token = args.token
    print(f"Starting Chatbot Bridge with token {token[:5]}...{token[-5:]}")
    
    offset = None
    
    # Simple loop to poll for messages
    while True:
        try:
            updates = get_updates(token, offset)
            if updates and updates.get('ok'):
                for msg in updates['result']:
                    offset = msg['update_id'] + 1
                    
                    if 'message' in msg and 'text' in msg['message']:
                        chat_id = msg['message']['chat']['id']
                        text = msg['message']['text']
                        print(f"Received from {chat_id}: {text}")
                        
                        # Process intent
                        response_text = execute_intent(text)
                        
                        # Send back
                        send_message(token, chat_id, response_text)
            
            time.sleep(1)
        except KeyboardInterrupt:
            print("Shutting down bridge...")
            break
        except Exception as e:
            print(f"Loop error: {e}")
            time.sleep(5)

if __name__ == '__main__':
    main()
