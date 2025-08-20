#!/usr/bin/env python3
"""
Local GGUF LLM Server for CUPRA Assistant

This server provides a simple HTTP API for interacting with a local GGUF model.
It's designed to work with llama.cpp or similar GGUF inference engines.

Usage:
    python local_llm_server.py --model-path /path/to/model.gguf --port 8080

Requirements:
    - llama-cpp-python (pip install llama-cpp-python)
    - fastapi (pip install fastapi uvicorn)
"""

import argparse
import logging
import time
from typing import List, Optional
import os
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

# Try to import llama-cpp-python
try:
    from llama_cpp import Llama
except ImportError:
    print("ERROR: llama-cpp-python is required. Install with:")
    print("pip install llama-cpp-python")
    exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Request/Response models using standard Python classes
class ChatMessage:
    def __init__(self, role: str, content: str):
        self.role = role  # 'user' or 'assistant'
        self.content = content

class GenerateRequest:
    def __init__(self, message: str, history: List[ChatMessage] = None, 
                 max_tokens: int = 200, temperature: float = 0.4, 
                 top_p: float = 0.9, stop: Optional[List[str]] = None):
        self.message = message
        self.history = history or []
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.top_p = top_p
        self.stop = stop

# Global model instance
llm_model: Optional[Llama] = None
model_config = {}

# Paths for static serving (serve UI from the same server)
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
STATIC_DIR = os.path.join(BASE_DIR, "static")
INDEX_HTML = os.path.join(BASE_DIR, "index.html")

# Flask app
app = Flask(__name__, static_folder=STATIC_DIR, static_url_path="/static")

# Serve index.html at root
@app.route("/")
def serve_index():
    if os.path.isfile(INDEX_HTML):
        return send_from_directory(BASE_DIR, "index.html")
    return jsonify({"status": "ui_not_found", "detail": INDEX_HTML}), 404

# Optional: serve favicon to avoid 404 noise
@app.route('/favicon.ico')
def favicon():
    candidate = os.path.join(STATIC_DIR, 'favicon.ico')
    if os.path.isfile(candidate):
        return send_from_directory(STATIC_DIR, 'favicon.ico')
    return ('', 204)

# CORS middleware for browser access
CORS(app)

def format_chat_history(history: List[ChatMessage]) -> str:
    """Format chat history into a prompt string."""
    if not history:
        return ""
    
    formatted = []
    for msg in history:
        role_prefix = "User: " if msg.role == "user" else "CUPRA_AI: "
        formatted.append(f"{role_prefix}{msg.content}")
    
    return "\n".join(formatted) + "\n"

def create_prompt(message: str, history: List[ChatMessage]) -> str:
    """Create a complete prompt for the model."""
    system_prompt = """You are the CUPRA Local Ambience Assistant.

Core Task:
- Help the user personalize their in-car ambience by creating a theme.
- A theme consists of ONE background and TWO colors.

Conversation Flow (strict):
1) Greeting
   - If there is no prior conversation, greet the user.
   - Briefly explain you create ambience themes (lighting + display background + sound vibe) and guide the user through a quick setup.
   - If there IS prior conversation indicating a theme was discussed, acknowledge and offer to continue or adjust.

2) Preference Gathering (do not output JSON yet)
   - Ask 1 short question at a time to identify:
     • Desired mood (e.g., relaxing, energetic, focused, night drive, nature, techy)
     • Preferred colors (warm vs cool, or specific names)
     • Any imagery they associate with the mood (e.g., ocean, sunset, forest, stars/space)
   - If the user is unsure, interview them helpfully with 1–2 concise questions (e.g., warm/cool, calm/energetic, day/night, bold/subtle).

3) Theme Generation (only AFTER preferences are clear)
   - Output a SINGLE JSON object on the first line with EXACTLY these keys:
     {"background":"<Background>","color1":"<Color>","color2":"<Color>"}
   - Then add ONE short sentence describing the vibe in friendly language. Avoid technical file names.
   - Use the lists below; use names exactly as written.

Backgrounds (choose exactly one):
  Clouds, Crystal, Daisy, Electrified, Core, Liquid, Glitter, Hearty, Magnetic, Me, Nebulosa, Off, Performance, Pool, Rainforest, Fpa

Background semantics (guidance; not user-visible):
  - Clouds: soft cloud-like, airy, flowing
  - Crystal: crisp geometric facets, bright
  - Daisy: floral petal feel, cheerful
  - Electrified: electric arcs/energy lines, high-tech, energetic
  - Core: centered bold core motif, minimal and strong
  - Liquid: fluid waves/water-like motion
  - Glitter: sparkling particles, festive
  - Hearty: heart motifs, warm and friendly
  - Magnetic: metallic lines/field patterns, technical
  - Me: neutral minimal default style
  - Nebulosa: space nebula and stars, cosmic
  - Off: subdued neutral/dim baseline
  - Performance: sporty angular streaks, dynamic
  - Pool: water ripple patterns, refreshing
  - Rainforest: leafy/forest textures, nature
  - Fpa: abstract performance-art motif

Simple Colors (choose exactly two):
  Blue, Light Blue, Cyan, Teal, Green, Lime, Yellow, Orange, Red, Pink, Purple, White, Warm White, Copper, Gray, Black

4) Theme Presentation & Confirmation
   - After generating the theme (JSON + one sentence), ask for confirmation (e.g., “Would you like to use this?”).
   - Do NOT generate another JSON unless the user asks for changes or declines. If uncertain, ask one clarifying question.

5) Chit‑chat / Off‑topic
   - Respond politely and briefly, then steer back to ambience creation.
   - Example: “Hello! I’m here to help you create a personalized ambience for your CUPRA. Shall we start with your preferred mood?”

Constraints:
- DO NOT output any JSON until the user’s preference is clear.
- When outputting JSON, it MUST be the very first line, no markdown/code fences.
- JSON keys must be exactly: background, color1, color2.
- Keep explanations concise and friendly.
- For long chats, rely on the most recent turns and keep questions short.

Examples:
User: Hi
Assistant: Hi! I help you create a custom ambience with a display background and lighting colors. What mood would you like—relaxing, energetic, focused, night drive, or nature?

User: Energetic in red
Assistant:
{"background":"Performance","color1":"Red","color2":"Black"} Energetic sports mood with bold contrast.
"""
    
    # Build conversation history
    chat_context = format_chat_history(history)
    
    # Create final prompt - CUPRA format
    if chat_context:
        prompt = f"{system_prompt}{chat_context}User: {message}\nCUPRA_AI:"
    else:
        prompt = f"{system_prompt}User: {message}\nCUPRA_AI:"
    
    return prompt

@app.route("/health")
def health_check():
    """Health check endpoint."""
    return jsonify({
        "status": "healthy" if llm_model is not None else "model_not_loaded",
        "timestamp": time.time()
    })

@app.route("/status")
def get_status():
    """Get detailed server status."""
    memory_usage = None
    try:
        import psutil
        process = psutil.Process()
        memory_usage = process.memory_info().rss / 1024 / 1024  # MB
    except ImportError:
        pass
    
    status_obj = {
        "status": "ready" if llm_model is not None else "model_not_loaded",
        "model_loaded": llm_model is not None,
        "model_path": model_config.get("model_path"),
        "context_size": model_config.get("n_ctx"),
        "memory_usage_mb": memory_usage
    }
    return jsonify(status_obj)

@app.route("/generate", methods=["POST"])
def generate_response():
    """Generate a response using the local GGUF model."""
    if llm_model is None:
        return jsonify({"detail": "Model not loaded"}), 503
    
    # Parse request data from JSON body
    try:
        request_data = request.get_json()
        if not request_data:
            return jsonify({"detail": "Invalid JSON"}), 400
            
        message = request_data.get("message", "")
        history_data = request_data.get("history", [])
        max_tokens = request_data.get("max_tokens", 200)
        temperature = request_data.get("temperature", 0.4)
        top_p = request_data.get("top_p", 0.9)
        stop = request_data.get("stop")
        
        # Convert history data to ChatMessage objects
        history = [ChatMessage(msg.get("role", ""), msg.get("content", "")) for msg in history_data]
        
    except Exception as e:
        return jsonify({"detail": f"Invalid request data: {str(e)}"}), 400
    
    start_time = time.time()
    
    try:
        # Create prompt
        prompt = create_prompt(message, history)
        logger.info(f"Generating response for: {message[:100]}...")
        
        # Generate response with streaming to capture timing metrics
        stream = llm_model(
            prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            top_p=top_p,
            stop=stop or ["User:", "\nUser:", "Human:", "\n\n"],
            echo=False,
            stream=True
        )
        
        response_text = ""
        first_token_time = None
        token_count = 0
        
        for chunk in stream:
            if first_token_time is None:
                first_token_time = time.time()
                ttft = first_token_time - start_time
                logger.info(f"Time to first token: {ttft:.2f}s")
            token = chunk['choices'][0]['text']
            response_text += token
            token_count += 1
        
        total_time = time.time() - start_time
        if token_count > 0 and total_time > 0:
            tps = token_count / total_time
            logger.info(f"Completed: {token_count} tokens in {total_time:.2f}s ({tps:.2f} tok/s)")
        
        return jsonify({
            "response": response_text.strip(),
            "processing_time": total_time
        })
        
    except Exception as e:
        logger.error(f"Error generating response: {e}")
        return jsonify({"detail": f"Generation failed: {str(e)}"}), 500

def load_model(model_path: str, capacity_bytes: int = None, **kwargs) -> Llama:
    """Load the GGUF model."""
    if not os.path.exists(model_path):
        raise FileNotFoundError(f"Model file not found: {model_path}")
    
    logger.info(f"Loading model from: {model_path}")
    
    # Default parameters optimized for mobile/local inference
    default_params = {
        "n_ctx": 8192,                # context window
        "n_batch": 128,              # prompt eval batch size
        "n_gpu_layers": 0,
    }
    # "type_k": llama_cpp.GGML_TYPE_Q4_0,  
    # "type_v": llama_cpp.GGML_TYPE_Q4_0,  
    # default_params = {
    #     "n_ctx": 4096,  # Increased context window for CUPRA system prompt
    #     "n_batch": 128,  # Batch size
    #     "n_threads": None,  # Auto-detect
    #     "verbose": False,
    #     "use_mmap": True,
    #     "use_mlock": False,
    #     "n_gpu_layers": 0  # CPU-only by default for compatibility
    # }
    
    # Override with user-provided parameters
    params = {**default_params, **kwargs}
    
    # Store config for status endpoint
    model_config.update({
        "model_path": model_path,
        **params
    })
    
    logger.info(f"Model parameters: {params}")
    
    try:
        start_time = time.time()
        model = Llama(model_path=model_path, **params)
        load_time = time.time() - start_time
        logger.info(f"Model loaded successfully in {load_time:.2f}s")

        # add prompt caching
        if not capacity_bytes:
            capacity_bytes = 4 * 1024**3  # ~4 GiB

        # model.set_cache(LlamaRAMCache(capacity_bytes=capacity_bytes))  # Commented out - undefined  

        # …or on-disk cache (persists across runs; slower than RAM but big)
        # model.set_cache(LlamaDiskCache(capacity_bytes=20 * 1024**3))  # ~20 GiB
        # (capacity_bytes is the knob you tune)

        return model
        
    except Exception as e:
        logger.error(f"Failed to load model: {e}")
        raise

def main():
    parser = argparse.ArgumentParser(description="Local GGUF LLM Server")
    parser.add_argument(
        "-m", "--model-path", 
        type=str, 
        required=True,
        help="Path to the GGUF model file"
    )
    parser.add_argument(
        "-cb", "--capacity-bytes",
        type=int,
        help="Capacity of the cache in bytes (default: None)"
    )
    parser.add_argument(
        "--port", 
        type=int, 
        default=8080,
        help="Port to run the server on (default: 8080)"
    )
    parser.add_argument(
        "--host", 
        type=str, 
        default="0.0.0.0",
        help="Host to bind to (default: 0.0.0.0)"
    )
    parser.add_argument(
        "--verbose", 
        action="store_true",
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    # Set up logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Load model
    global llm_model
    try:
        llm_model = load_model(
            model_path=args.model_path,
            capacity_bytes=args.capacity_bytes,
            verbose=args.verbose
        )
        logger.info("Server ready to handle requests")
        
    except Exception as e:
        logger.error(f"Failed to initialize model: {e}")
        exit(1)
    
    # Reduce werkzeug request logging unless verbose
    if not args.verbose:
        logging.getLogger('werkzeug').setLevel(logging.ERROR)

    # Run server
    logger.info(f"Starting server on {args.host}:{args.port}")
    app.run(
        host=args.host, 
        port=args.port,
        debug=args.verbose
    )

if __name__ == "__main__":
    main()
