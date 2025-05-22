Software Design Specification (Updated for Cerebras SDK and Systray)
1. Introduction:
This document outlines the detailed design specifications for the Hotkey-Activated Text Augmentation Utility (HAT-AU). It builds upon the Software Design Brief, providing technical details for implementation, with a specific focus on integrating with the Cerebras Cloud SDK for text generation and a Windows System Tray interface for configuration.
2. System Architecture:
The system will be a single Python script designed to run in the background. It will leverage several external libraries:
keyboard: For global hotkey detection and suppression.
pyperclip: For cross-platform clipboard access.
pyautogui: For simulating keyboard inputs.
time: For introducing necessary small delays.
json: For parsing and pretty-printing JSON (if applicable to other potential API interactions, less so for direct Cerebras stream).
os: For accessing environment variables (e.g., API keys).
asyncio: (Standard library) For managing asynchronous operations required by the Cerebras SDK.
cerebras-cloud-sdk: The official SDK for interacting with Cerebras cloud services.
pystray: For creating and managing the Windows System Tray icon and context menu.
3. Functional Requirements:
FR1: Global Hotkey Activation
FR1.1: The utility must listen for a specific global hotkey combination.
FR1.2: The hotkey combination shall be configurable (e.g., via a constant in the script). Default suggestion: Win+Y.
FR1.3: The hotkey listener must be active system-wide.
FR1.4: The non-modifier key part of the hotkey must be suppressed (suppress=True).
FR2: Selected Text Detection and Copying
FR2.1: Upon hotkey activation, copy currently selected text from the active application.
FR2.2: Achieved by simulating a "Copy" command.
FR2.3: If no text is selected/copy fails, handle gracefully.
FR3: API Interaction (Cerebras Cloud SDK)
FR3.1: The utility must interact with the Cerebras Cloud API using the cerebras-cloud-sdk.
FR3.2: API Key Management: The utility will expect the Cerebras API key to be available as an environment variable (CEREBRAS_API_KEY), as per SDK best practices.
FR3.3: Asynchronous Operation: The Cerebras SDK interaction is asynchronous. The hotkey callback (synchronous) will initiate and await the completion of the asynchronous API call. This will likely involve using asyncio.run() within the callback for simplicity in the prototype.
FR3.4: Input Construction: The selected text (from FR2) will be used as the primary content for the messages payload sent to the Cerebras chat.completions.create endpoint.
Example payload structure:
messages=[
    {
        "role": "user",
        "content": "<selected_text_content>" # Dynamically inserted
    }
]



FR3.5: Model Selection: The model (e.g., "llama3.1-8b") shall be dynamically selected via the Windows Systray menu (see FR6) and used for API calls.
FR3.6: Streaming Response Handling: The API response will be streamed. The utility must asynchronously iterate through the stream chunks and concatenate the delta.content to form the complete response text.
FR3.7: The utility must handle API responses, including successful data retrieval and potential errors from the SDK or API.
FR4: Response Handling and Insertion
FR4.1: Upon receiving and concatenating the complete API response from Cerebras, prepare to insert it.
FR4.2: Simulate key presses: Right Arrow, then Enter.
FR4.3: Copy the complete API response text to the clipboard.
FR4.4: Simulate a "Paste" command.
FR4.5: (Less relevant for direct text stream) If the API response were structured (e.g., JSON from a different API), it should be formatted appropriately. For Cerebras text stream, it will be pasted as plain text.
FR5: Configuration & Feedback
FR5.1: Key parameters (hotkey) will be configurable via constants. API key via environment variable. Cerebras model selection will be managed via the Systray menu.
FR5.2: Console logging for actions and errors.
FR6: Windows Systray Integration
FR6.1: The utility must display an icon in the Windows System Tray upon startup.
FR6.2: Right-clicking the Systray icon must open a context menu.
FR6.3: The context menu must contain options to select the active AI model from a list.
FR6.4: Model Retrieval and Caching: The list of available AI models will be retrieved from the Cerebras API (e.g., client.models.list()) once at application startup. This list will be cached and used to populate the Systray menu. If the API call fails, a default set of common models will be used.
FR6.5: Selecting a model from the menu will update the internal variable used for model in FR3.5.
FR6.6: The menu should visually indicate the currently selected model (e.g., with a checkmark).
FR6.7: The context menu must include an "Exit" option to gracefully terminate the application.
4. Non-Functional Requirements:
NFR1: Performance: Response time will be dependent on the Cerebras API latency. The utility itself should add minimal overhead.
NFR2: Reliability: Robust error handling for SDK and API issues.
NFR3: Usability: Easy to start/stop via the Systray menu; clear indication of running status.
NFR4: Resource Consumption: Minimal when idle.
NFR5: Platform Compatibility: Initial target: Windows.
5. Technical Stack (Updated):
Programming Language: Python (version 3.7+ recommended for asyncio features)
Libraries:
keyboard
pyperclip
pyautogui
cerebras-cloud-sdk (and its dependencies like httpx)
asyncio (standard library)
os (standard library)
time (standard library)
pystray
6. API Interaction Details (Elaboration - Cerebras SDK):
Initialization:
import os
from cerebras.cloud.sdk import AsyncCerebras

# client = AsyncCerebras(api_key=os.environ.get("CEREBRAS_API_KEY"))
# Note: If using asyncio.run() for each call, the client might need to be initialized within the async function
# or passed, or a synchronous client might be simpler if available and fits the use case.
# For the provided example, AsyncCerebras is used.



API Call Structure (within an async function):
# async def get_cerebras_completion(selected_text: str, model_name: str) -> str:
#    client = AsyncCerebras(api_key=os.environ.get("CEREBRAS_API_KEY")) # Initialize client here or globally
#    full_response_content = ""
#    stream = await client.chat.completions.create(
#        messages=[{"role": "user", "content": selected_text}],
#        model=model_name, # e.g., "llama3.1-8b" - now dynamic from Systray
#        stream=True,
#    )
#    async for chunk in stream:
#        full_response_content += (chunk.choices[0].delta.content or "")
#    await client.close() # Important to close the client session
#    return full_response_content



Model Listing (within an async function, typically at startup):
# async def get_available_models() -> list[str]:
#    client = AsyncCerebras(api_key=os.environ.get("CEREBRAS_API_KEY"))
#    try:
#        models_response = await client.models.list()
#        model_names = [model.id for model in models_response.data] # Assuming 'id' is the model name
#        return model_names
#    except Exception as e:
#        print(f"Error fetching models: {e}")
#        return ["llama3.1-8b", "llama3.1-70b"] # Default fallback models
#    finally:
#        await client.close()



Invoking from Synchronous Hotkey Callback:
# def perform_action():
#    selected_text = get_selected_text()
#    if selected_text:
#        # current_model_name is now a global variable updated by the Systray menu
#        api_response = asyncio.run(get_cerebras_completion(selected_text, current_model_name))
#        if api_response:
#            type_response(api_response)



API Key: Must be set in the CEREBRAS_API_KEY environment variable. The script should check for its presence or inform the user.
7. Error Handling & Logging (Updated):
No text selected: Log message, abort.
CEREBRAS_API_KEY not set: Log error, inform user, abort.
Cerebras SDK/API Errors (authentication, model not found, rate limits, network issues): Catch specific SDK exceptions if possible, or general exceptions. Log error. Optionally paste a generic error message.
Empty or unexpected stream response: Log, potentially paste nothing or an error.
Failures in simulating key presses or clipboard: Log error.
Console logging for all significant actions.
Error fetching models from Cerebras API: Log error, use default models.
8. Future Considerations / Potential Enhancements:
Support for more Cerebras API parameters (temperature, max tokens etc.).
Option to show a "processing..." indicator due to potential API latency.
Asynchronous task management if hotkeys can be triggered rapidly (moving beyond simple asyncio.run() in callback).
Packaging as a standalone executable.
More sophisticated handling of pystray and keyboard event loops, potentially using threading or advanced asyncio integration for robustness.
This revised specification directly addresses the use of the Cerebras SDK and the addition of a Windows Systray icon for model selection. The main challenge and change is the introduction of asyncio into the workflow and the integration of pystray for the GUI element. The provided solution using asyncio.run() within the synchronous hotkey callback is a pragmatic approach for a prototype. For a production-grade tool with frequent use, a more sophisticated threading model for the asyncio event loop might be considered.
