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

# Optional prompt cache classes (available in newer llama-cpp-python versions)
try:
    from llama_cpp import LlamaRAMCache, LlamaDiskCache  # type: ignore
except Exception:
    LlamaRAMCache = None  # type: ignore
    LlamaDiskCache = None  # type: ignore

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

# Track last prompt tokens to estimate cache prefix reuse across requests
last_prompt_tokens: List[int] = []
last_cached_prefix_len: int = 0

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

Core task: Create an in-car ambience theme with exactly one Background and two Colors

Conversation flow (strict):
1) Greeting: If no prior conversation, greet and briefly explain you create ambience themes (lighting + display background + vibe). If there is prior context, acknowledge and continue.
2) Preference gathering (no JSON yet): Ask one short question at a time to identify mood, color preference (warm/cool or specific), and any imagery. If unclear, ask for clarification; e.g., if the user says "like harry poter", ask which house (Gryffindor, Slytherin, Ravenclaw, Hufflepuff) and what atmosphere they want.
3) Theme generation (only after preferences are clear):
   - Output a single JSON object on the first line exactly as:
     {"background":"<Background>","color1":"<Color>","color2":"<Color>"}
   - Then add one short friendly sentence describing the vibe. Avoid technical file names.
   - Use names only from the lists below, exactly as written.
4) Presentation & confirmation: After JSON + sentence, ask for confirmation. Do not output another JSON unless the user requests changes or declines. If uncertain, ask one clarifying question.
5) Off‑topic: Reply briefly and steer back to ambience creation.


Background and hints (Only use the capitalized words in the json):
- Clouds=airy
- Crystal=bright
- Daisy=floral
- Electrified=electric
- Core=bold
- Liquid=fluid
- Glitter=sparkling
- Hearty=warm
- Magnetic=metallic
- Me=neutral
- Nebulosa=cosmic
- Off=dim
- Performance=sporty
- Pool=refreshing
- Rainforest=lush
- Fpa=abstract

Colors (pick two that match the mood): Blue, Light Blue, Cyan, Teal, Green, Lime, Yellow, Orange, Red, Pink, Purple, White, Warm White, Copper, Gray, Black

Constraints:
- Do not output JSON until preferences are clear.
- The JSON must be the very first line and use keys background, color1, color2.
- Keep messages concise and friendly; focus on recent turns.

Example:
User: Hi

Assistant: Hi! I help you create a custom ambience with a display background and lighting colors. What mood would you like—relaxing, energetic, focused, night drive, or nature?

User: Energetic in red

Assistant: {"background":"Performance","color1":"Red","color2":"Black"} Energetic sports mood with bold contrast.
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

        # Limit history to keep TTFT low while still hitting the prompt cache.
        # Keep only the last N turns (configurable via CLI).
        max_history_turns = int(model_config.get("max_history_turns", 2))
        if max_history_turns > 0 and len(history) > max_history_turns:
            history = history[-max_history_turns:]
        
    except Exception as e:
        return jsonify({"detail": f"Invalid request data: {str(e)}"}), 400
    
    start_time = time.time()
    
    try:
        # Create prompt
        prompt = create_prompt(message, history)

        # Log prompt token count to correlate with TTFT and estimate cache reuse
        try:
            prompt_tokens = llm_model.tokenize(prompt.encode("utf-8"))
            # Estimate shared prefix with previous prompt to infer cache hit extent
            global last_prompt_tokens
            global last_cached_prefix_len
            shared = 0
            max_shared = min(len(last_prompt_tokens), len(prompt_tokens))
            while shared < max_shared and last_prompt_tokens[shared] == prompt_tokens[shared]:
                shared += 1
            new_tokens = len(prompt_tokens) - shared
            logger.info(f"Prompt tokens: {len(prompt_tokens)} (cached prefix ~{shared}, new {new_tokens})")
            # Warn if cached prefix shrinks notably; may indicate cache capacity too small
            if model_config.get("enable_cache", False) and shared + 16 < last_cached_prefix_len:
                logger.warning(
                    "Cached prefix decreased from %d to %d tokens; consider increasing cache capacity (-cb)",
                    last_cached_prefix_len,
                    shared,
                )
            last_cached_prefix_len = shared
            last_prompt_tokens = prompt_tokens
        except Exception:
            pass
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

def load_model(model_path: str, capacity_bytes: int = None, enable_cache: bool = True, cache_type: str = "ram", warm_cache: bool = True, **kwargs) -> Llama:
    """Load the GGUF model."""
    if not os.path.exists(model_path):
        raise FileNotFoundError(f"Model file not found: {model_path}")
    
    logger.info(f"Loading model from: {model_path}")
    
    # Default parameters optimized for aggressive on-device performance
    default_params = {
        "n_ctx": 1024,                # context window
        "n_batch": 1024,              # larger prompt eval batch for faster prefix eval
        "n_gpu_layers": 0,
        "use_mmap": True,
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
        "enable_cache": enable_cache,
        "cache_type": cache_type,
        "capacity_bytes": capacity_bytes,
        **params
    })
    
    logger.info(f"Model parameters: {params}")
    if params.get("n_threads"):
        logger.info(f"Using {params['n_threads']} CPU threads")
    if params.get("n_batch"):
        logger.info(f"Using n_batch={params['n_batch']} for prompt eval")
    
    try:
        start_time = time.time()
        model = Llama(model_path=model_path, **params)
        load_time = time.time() - start_time
        logger.info(f"Model loaded successfully in {load_time:.2f}s")

        # Enable prompt caching if requested
        if enable_cache:
            try:
                if capacity_bytes is None:
                    # Default to 2 GiB; adjust with -cb if needed
                    capacity_bytes = 2 * 1024 * 1024**2  # 2 GiB

                if cache_type == "disk":
                    if 'LlamaDiskCache' in globals() and LlamaDiskCache is not None:  # type: ignore
                        model.set_cache(LlamaDiskCache(capacity_bytes=capacity_bytes))  # type: ignore
                        logger.info(f"Enabled DISK prompt cache (capacity {capacity_bytes} bytes)")
                    else:
                        logger.warning("LlamaDiskCache not available; falling back to RAM cache")
                        if 'LlamaRAMCache' in globals() and LlamaRAMCache is not None:  # type: ignore
                            model.set_cache(LlamaRAMCache(capacity_bytes=capacity_bytes))  # type: ignore
                            logger.info(f"Enabled RAM prompt cache (capacity {capacity_bytes} bytes)")
                        else:
                            logger.warning("LlamaRAMCache not available; prompt caching disabled")
                else:
                    if 'LlamaRAMCache' in globals() and LlamaRAMCache is not None:  # type: ignore
                        model.set_cache(LlamaRAMCache(capacity_bytes=capacity_bytes))  # type: ignore
                        logger.info(f"Enabled RAM prompt cache (capacity {capacity_bytes} bytes)")
                    else:
                        logger.warning("LlamaRAMCache not available; prompt caching disabled")
            except Exception as cache_err:
                logger.warning(f"Failed to enable prompt cache: {cache_err}")

            # Optional: warm the cache with the system prompt so first request is faster
            if warm_cache:
                try:
                    warm_text = create_prompt("", [])
                    tokens = model.tokenize(warm_text.encode("utf-8"))
                    model.eval(tokens)
                    logger.info("Prompt cache warmed with system prompt")
                except Exception as warm_err:
                    logger.warning(f"Failed to warm prompt cache: {warm_err}")

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
    parser.add_argument(
        "--disable-cache",
        action="store_true",
        help="Disable prompt cache (enabled by default)"
    )
    parser.add_argument(
        "--cache-type",
        type=str,
        default="ram",
        choices=["ram", "disk"],
        help="Prompt cache type: 'ram' or 'disk' (default: ram)"
    )
    parser.add_argument(
        "--no-warm-cache",
        action="store_true",
        help="Disable warming the cache at startup (enabled by default)"
    )
    parser.add_argument(
        "--n-threads",
        type=int,
        default=0,
        help="Number of CPU threads to use (0 = auto/all cores)"
    )
    parser.add_argument(
        "--n-batch",
        type=int,
        default=0,
        help="Prompt eval batch size (0 = use default aggressive setting)"
    )
    parser.add_argument(
        "--max-history-turns",
        type=int,
        default=0,
        help="Limit the number of prior messages kept in the prompt (0 = keep all; default: 0)"
    )
    
    args = parser.parse_args()
    
    # Set up logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Load model
    global llm_model
    try:
        # Compute dynamic parameters
        import multiprocessing
        auto_threads = multiprocessing.cpu_count()
        chosen_threads = (auto_threads if args.n_threads == 0 else args.n_threads)
        chosen_batch = (args.n_batch if args.n_batch and args.n_batch > 0 else None)

        # Build kwargs without overriding defaults with None
        model_kwargs = {
            "verbose": args.verbose,
            "n_threads": chosen_threads,
        }
        if chosen_batch is not None:
            model_kwargs["n_batch"] = chosen_batch

        llm_model = load_model(
            model_path=args.model_path,
            capacity_bytes=args.capacity_bytes,
            enable_cache=not args.disable_cache,
            cache_type=args.cache_type,
            warm_cache=not args.no_warm_cache,
            **model_kwargs
        )
        logger.info("Server ready to handle requests")
        
    except Exception as e:
        logger.error(f"Failed to initialize model: {e}")
        exit(1)
    
    # Reduce werkzeug request logging unless verbose
    if not args.verbose:
        logging.getLogger('werkzeug').setLevel(logging.ERROR)

    # Store runtime config for request handlers
    model_config["max_history_turns"] = args.max_history_turns

    # Run server
    logger.info(f"Starting server on {args.host}:{args.port}")
    app.run(
        host=args.host, 
        port=args.port,
        debug=args.verbose
    )

if __name__ == "__main__":
    main()
