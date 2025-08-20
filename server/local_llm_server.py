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
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import os
 from fastapi.staticfiles import StaticFiles

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

class GenerateResponse:
    def __init__(self, response: str, processing_time: float):
        self.response = response
        self.processing_time = processing_time

class ServerStatus:
    def __init__(self, status: str, model_loaded: bool, 
                 model_path: Optional[str] = None, context_size: Optional[int] = None,
                 memory_usage_mb: Optional[float] = None):
        self.status = status
        self.model_loaded = model_loaded
        self.model_path = model_path
        self.context_size = context_size
        self.memory_usage_mb = memory_usage_mb


# Global model instance
llm_model: Optional[Llama] = None
model_config = {}

# FastAPI app
app = FastAPI(
    title="Local GGUF LLM Server",
    description="Simple HTTP API for local GGUF model inference",
    version="1.0.0"
)

# Paths for static serving (serve UI from the same server)
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
STATIC_DIR = os.path.join(BASE_DIR, "static")
PUBLIC_DIR = os.path.join(BASE_DIR, "public")
INDEX_HTML = os.path.join(BASE_DIR, "index.html")

# Mount static directories if they exist
if os.path.isdir(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
if os.path.isdir(PUBLIC_DIR):
    app.mount("/public", StaticFiles(directory=PUBLIC_DIR), name="public")

# Serve index.html at root
@app.get("/")
async def serve_index():
    if os.path.isfile(INDEX_HTML):
        return FileResponse(INDEX_HTML)
    return {"status": "ui_not_found", "detail": INDEX_HTML}

# CORS middleware for browser access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

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

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy" if llm_model is not None else "model_not_loaded",
        "timestamp": time.time()
    }

@app.get("/status")
async def get_status():
    """Get detailed server status."""
    memory_usage = None
    try:
        import psutil
        process = psutil.Process()
        memory_usage = process.memory_info().rss / 1024 / 1024  # MB
    except ImportError:
        pass
    
    status_obj = ServerStatus(
        status="ready" if llm_model is not None else "model_not_loaded",
        model_loaded=llm_model is not None,
        model_path=model_config.get("model_path"),
        context_size=model_config.get("n_ctx"),
        memory_usage_mb=memory_usage
    )
    return {
        "status": status_obj.status,
        "model_loaded": status_obj.model_loaded,
        "model_path": status_obj.model_path,
        "context_size": status_obj.context_size,
        "memory_usage_mb": status_obj.memory_usage_mb
    }

@app.post("/generate")
async def generate_response(request_data: dict):
    """Generate a response using the local GGUF model."""
    if llm_model is None:
        raise HTTPException(status_code=503, detail="Model not loaded")
    
    # Parse request data
    try:
        message = request_data.get("message", "")
        history_data = request_data.get("history", [])
        max_tokens = request_data.get("max_tokens", 200)
        temperature = request_data.get("temperature", 0.4)
        top_p = request_data.get("top_p", 0.9)
        stop = request_data.get("stop")
        
        # Convert history data to ChatMessage objects
        history = []
        for msg_data in history_data:
            if isinstance(msg_data, dict):
                history.append(ChatMessage(msg_data.get("role", ""), msg_data.get("content", "")))
            elif hasattr(msg_data, "role") and hasattr(msg_data, "content"):
                history.append(msg_data)
        
        request = GenerateRequest(message, history, max_tokens, temperature, top_p, stop)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid request data: {str(e)}")
    
    start_time = time.time()
    
    try:
        # Create prompt
        prompt = create_prompt(request.message, request.history)
        logger.info(f"Generating response for: {request.message[:100]}...")
        
        # Generate response with simple stop sequences
        response = llm_model(
            prompt,
            max_tokens=request.max_tokens,
            temperature=request.temperature,
            top_p=request.top_p,
            stop=request.stop or ["User:", "\nUser:", "Human:", "\n\n"],
            echo=False
        )
        
        # Extract response text
        response_text = response['choices'][0]['text'].strip()
        
        # Clean up common artifacts
        if response_text.startswith("Assistant:"):
            response_text = response_text[10:].strip()
        
        processing_time = time.time() - start_time
        logger.info(f"Response generated in {processing_time:.2f}s: {response_text[:100]}...")
        
        return {
            "response": response_text,
            "processing_time": processing_time
        }
        
    except Exception as e:
        logger.error(f"Error generating response: {e}")
        raise HTTPException(status_code=500, detail=f"Generation failed: {str(e)}")

def load_model(model_path: str, capacity_bytes: int = None, **kwargs) -> Llama:
    """Load the GGUF model."""
    if not os.path.exists(model_path):
        raise FileNotFoundError(f"Model file not found: {model_path}")
    
    logger.info(f"Loading model from: {model_path}")
    
    # Default parameters optimized for mobile/local inference
    default_params = {
        "n_ctx": 8192,                # context window
        "n_batch": 1024,              # prompt eval batch size
        "type_k": llama_cpp.GGML_TYPE_Q4_0,  # Commented out - undefined
        "type_v": llama_cpp.GGML_TYPE_Q4_0,  # Commented out - undefined
    }
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

        model.set_cache(LlamaRAMCache(capacity_bytes=capacity_bytes))  # Commented out - undefined  

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
    # parser.add_argument(
    #     "--n-ctx", 
    #     type=int, 
    #     default=2048,
    #     help="Context window size (default: 2048)"
    # )
    # parser.add_argument(
    #     "--n-threads", 
    #     type=int, 
    #     default=None,
    #     help="Number of threads (default: auto-detect)"
    # )
    # parser.add_argument(
    #     "--n-gpu-layers", 
    #     type=int, 
    #     default=0,
    #     help="Number of GPU layers (default: 0 for CPU-only)"
    # )
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
    
    # Run server
    logger.info(f"Starting server on {args.host}:{args.port}")
    uvicorn.run(
        app, 
        host=args.host, 
        port=args.port,
        log_level="info" if not args.verbose else "debug"
    )



if __name__ == "__main__":
    main()
