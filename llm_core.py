import requests
import json

# The prompt from Step 2
SYSTEM_PROMPT = SYSTEM_PROMPT = """
You are an expert AI agent that converts user instructions into a precise, executable plan for a web browser automation tool.
Your response MUST be a valid JSON object. Do not add any text or explanation before or after the JSON.

The user will provide an instruction. You will generate a JSON array of "actions".
Each action is an object with a "command" and its necessary "parameters".

Supported commands and their parameters are:
1. "goto": Navigates to a URL.
   - "url": The full URL to visit.
2. "fill": Types text into an input field.
   - "selector": A CSS selector to find the element (e.g., 'input[name="q"]').
   - "text": The text to type.
3. "click": Clicks on an element.
   - "selector": A CSS selector for the element to click.
4. "scrape": Extracts text from the page.
   - "selector": A CSS selector for the element(s) to get text from.
   - "return_key": The key name to store the scraped data under in the final output.

Example user instruction: "Search for 'best python libraries' on Google"
Your required JSON output:
[
  {
    "command": "goto",
    "parameters": { "url": "https://www.google.com" }
  },
  {
    "command": "fill",
    "parameters": { "selector": "textarea[name='q']", "text": "best python libraries" }
  },
  {
    "command": "click",
    "parameters": { "selector": "input[type='submit']" }
  }
]

Now, generate the JSON plan for the following user instruction.
"""

def generate_plan(user_instruction):
    """
    Sends the instruction to Ollama and gets a JSON plan back.
    """
    full_prompt = f"{SYSTEM_PROMPT}\nUser instruction: \"{user_instruction}\""
    
    # Ollama's API endpoint
    url = 'http://localhost:11434/api/generate'
    
    payload = {
        "model": "llama3:latest",
        "prompt": full_prompt,
        "stream": False,  # We want the full response at once
        "format": "json"  # Crucial for getting clean JSON output
    }
    
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status() # Raise an exception for bad status codes
        
        # The actual response from the model is a JSON string inside the 'response' key
        response_json_str = response.json().get('response', '{}')
        
        # Parse the inner JSON string into a Python object
        plan = json.loads(response_json_str)
        return plan
        
    except requests.exceptions.RequestException as e:
        print(f"Error communicating with Ollama: {e}")
        return None
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON from Ollama's response: {e}")
        print(f"Raw response was: {response_json_str}")
        return None

# --- Your Test ---
if __name__ == "__main__":
    instruction = "Go to wikipedia and search for the 'Eiffel Tower'"
    plan = generate_plan(instruction)
    
    if plan:
        print("Successfully generated plan:")
        print(json.dumps(plan, indent=2))
    else:
        print("❌ Failed to generate a plan.")