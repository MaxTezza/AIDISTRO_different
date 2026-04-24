#!/usr/bin/env python3
import sys
import os
from PIL import Image
import moondream as md

# To minimize memory between calls in this demo, we'll initialize per call
# In production, this would be a long-running service.

def main():
    if len(sys.argv) < 2:
        print("I need an image to look at.")
        return

    image_path = sys.argv[1]
    prompt = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else "What do you see?"

    if not os.path.exists(image_path):
        print(f"Error: Image not found at {image_path}")
        return

    try:
        # Load image
        image = Image.open(image_path)
        
        # Initialize moondream (downloads model automatically on first run)
        model = md.vl(model='moondream-latest.bit6.4.whl') # Or specify local path
        
        # Encode image
        encoded_image = model.encode_image(image)
        
        # Answer the question
        answer = model.answer_question(encoded_image, prompt)
        
        print(answer)
        
    except Exception as e:
        # Fallback to OCR if VLM fails (e.g. memory issues)
        try:
            import pytesseract
            text = pytesseract.image_to_string(Image.open(image_path))
            if text.strip():
                print(f"I see some text on your screen: '{text.strip()[:100]}...'")
            else:
                print("I see your screen, but I'm having trouble describing it right now.")
        except Exception:
            print(f"Vision error: {e}")

if __name__ == "__main__":
    main()
