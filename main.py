import os
import time
import asyncio
import logging
import threading
import pyperclip
import pyautogui
import keyboard
from cerebras.cloud.sdk import AsyncCerebras
import pystray
from pystray import MenuItem as item
from PIL import Image, ImageDraw

# --- Configuration ---
HOTKEY = 'windows+y'  # Configurable hotkey
DEFAULT_MODELS = ["llama3.1-8b", "llama3.1-70b"]
API_KEY_ENV = "CEREBRAS_API_KEY"

# --- Logging ---
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(message)s')

# --- Globals ---
current_model = DEFAULT_MODELS[0]
available_models = DEFAULT_MODELS.copy()
tray_icon = None

# --- Systray Icon ---
def create_image():
    # Simple black/white icon
    img = Image.new('RGB', (64, 64), color='white')
    d = ImageDraw.Draw(img)
    d.rectangle([16, 16, 48, 48], fill='black')
    return img

def update_tray_menu():
    global tray_icon
    tray_icon.menu = pystray.Menu(
        *(item(
            model,
            lambda _, m=model: set_model(m),
            checked=lambda i, m=model: m == current_model
        ) for model in available_models),
        item('Exit', on_exit)
    )

def set_model(model_name):
    global current_model
    current_model = model_name
    logging.info(f"Model set to: {model_name}")
    update_tray_menu()

def on_exit(icon, item=None):
    logging.info("Exiting application.")
    icon.stop()
    os._exit(0)

def tray_thread():
    global tray_icon
    tray_icon = pystray.Icon("GPT-AHK2", create_image(), "GPT-AHK2", pystray.Menu(item('Exit', on_exit)))
    update_tray_menu()
    tray_icon.run()

# --- Cerebras API ---
async def get_available_models():
    api_key = os.environ.get(API_KEY_ENV)
    if not api_key:
        logging.error(f"{API_KEY_ENV} not set.")
        return DEFAULT_MODELS
    client = AsyncCerebras(api_key=api_key)
    try:
        models_response = await client.models.list()
        model_names = [model.id for model in models_response.data]
        return model_names
    except Exception as e:
        logging.error(f"Error fetching models: {e}")
        return DEFAULT_MODELS
    finally:
        await client.close()

async def get_cerebras_completion(selected_text, model_name):
    api_key = os.environ.get(API_KEY_ENV)
    if not api_key:
        logging.error(f"{API_KEY_ENV} not set.")
        return None
    client = AsyncCerebras(api_key=api_key)
    full_response_content = ""
    try:
        stream = await client.chat.completions.create(
            messages=[{"role": "user", "content": selected_text}],
            model=model_name,
            stream=True,
        )
        async for chunk in stream:
            full_response_content += (chunk.choices[0].delta.content or "")
    except Exception as e:
        logging.error(f"Cerebras API error: {e}")
        return None
    finally:
        await client.close()
    return full_response_content

# --- Text Selection and Insertion ---
def get_selected_text():
    # Simulate Ctrl+C to copy selected text
    pyautogui.hotkey('ctrl', 'c')
    time.sleep(0.1)
    text = pyperclip.paste()
    if not text.strip():
        logging.info("No text selected or copy failed.")
        return None
    return text

def type_response(response):
    # Move cursor right, then Enter, then paste
    pyautogui.press('right')
    pyautogui.press('enter')
    pyperclip.copy(response)
    time.sleep(0.05)
    pyautogui.hotkey('ctrl', 'v')

# --- Hotkey Handler ---
def on_hotkey():
    selected_text = get_selected_text()
    if not selected_text:
        return
    logging.info(f"Selected text: {selected_text[:40]}...")
    response = asyncio.run(get_cerebras_completion(selected_text, current_model))
    if response:
        logging.info(f"Received response ({len(response)} chars)")
        type_response(response)
    else:
        logging.error("No response from Cerebras API.")

def main():
    global available_models
    # Fetch models at startup
    try:
        available_models = asyncio.run(get_available_models())
    except Exception as e:
        logging.error(f"Model fetch failed: {e}")
        available_models = DEFAULT_MODELS
    # Start systray in a thread
    t = threading.Thread(target=tray_thread, daemon=True)
    t.start()
    # Register hotkey
    keyboard.add_hotkey(HOTKEY, on_hotkey, suppress=True)
    logging.info(f"GPT-AHK2 running. Hotkey: {HOTKEY}. Systray active.")
    keyboard.wait()  # Block forever

if __name__ == "__main__":
    main()
