# CUPRA Local Assistant

A simplified, local version of the CUPRA voice assistant that runs entirely on your device using a local GGUF model. This version maintains the same UI/UX as the original while removing complex cloud dependencies.

## Features

- 🎭 **Same Avatar Animation System** - Full CUPRA avatar with states and transitions
- 🧠 **Local GGUF Model** - Runs 3.9B parameter models locally (no internet required for inference)
- 🎤 **Voice Interaction** - Speech recognition and text-to-speech using browser APIs
- 💬 **Session Chat History** - Maintains conversation context during session
- 📱 **Mobile Optimized** - Designed for Android devices
- 🔒 **Privacy First** - All processing happens locally

## Quick Start

### 1. Download a GGUF Model

Download a 3.9B parameter GGUF model. Recommended options:

```bash
# Phi-3 Mini 3.8B (recommended for mobile)
wget https://huggingface.co/microsoft/Phi-3-mini-4k-instruct-gguf/resolve/main/Phi-3-mini-4k-instruct-q4_k_m.gguf

# Or Qwen2.5-3B
wget https://huggingface.co/Qwen/Qwen2.5-3B-Instruct-GGUF/resolve/main/qwen2.5-3b-instruct-q4_k_m.gguf
```

### 2. Install Python Dependencies

```bash
cd cupra_local/server
pip install -r requirements.txt
```

### 3. Start the Local LLM Server

```bash
python local_llm_server.py --model-path /path/to/your/model.gguf --port 8080
```

### 4. Start the Web Server

```bash
# In a new terminal
cd cupra_local
python serve_static.py --port 3000
```

### 5. Open in Browser

Navigate to `http://localhost:3000` and tap the screen to start conversation!

## Detailed Setup

### System Requirements

- **RAM**: 6-8GB (4GB for model + 2-4GB for system)
- **Storage**: 3-5GB for model files
- **CPU**: Modern ARM64 or x86_64 processor
- **OS**: Windows, macOS, Linux, or Android (with Termux)

### Android Setup (Termux)

1. Install Termux from F-Droid
2. Update packages:
   ```bash
   pkg update && pkg upgrade
   pkg install python git wget
   ```
3. Install dependencies:
   ```bash
   pip install -r server/requirements.txt
   ```
4. Follow the quick start steps above

### Model Recommendations

For 3.9B models optimized for mobile:

| Model | Size | Quality | Speed | Use Case |
|-------|------|---------|-------|----------|
| Phi-3 Mini 3.8B Q4_K_M | ~2.4GB | High | Fast | General conversation |
| Qwen2.5-3B Q4_K_M | ~2.1GB | High | Fast | Multilingual support |
| Llama-3.2-3B Q4_K_M | ~2.0GB | Good | Very Fast | Basic chat |

### Configuration Options

#### LLM Server Options

```bash
python local_llm_server.py \
  --model-path model.gguf \
  --port 8080 \
  --n-ctx 2048 \           # Context window size
  --n-threads 4 \          # CPU threads (auto-detect if not specified)
  --n-gpu-layers 0 \       # GPU layers (0 for CPU-only)
  --verbose                # Enable debug logging
```

#### Performance Tuning

- **For faster responses**: Use Q4_K_M quantization
- **For lower memory usage**: Use Q4_K_S quantization  
- **For better quality**: Use Q5_K_M quantization
- **CPU threads**: Set to number of CPU cores for best performance
- **Context window**: Reduce to 1024 if memory constrained

## Architecture Overview

### Components

1. **Frontend (index.html)**
   - Avatar animation system
   - Voice recognition (Web Speech API)
   - Text-to-speech (Web Speech API)
   - Local server communication

2. **LLM Server (local_llm_server.py)**
   - GGUF model loading and inference
   - HTTP API for chat completion
   - Session management

3. **Static Server (serve_static.py)**
   - Serves HTML interface and assets
   - CORS support for local development

### Key Differences from Original

| Original | Local Version |
|----------|---------------|
| LiveKit WebRTC | Web Speech API |
| HumainsLLM API | Local GGUF server |
| Complex agent worker | Simple HTTP client |
| Persistent chat history | Session-only history |
| Real-time streaming | Batch processing |
| External TTS/STT | Browser APIs |

### API Endpoints

#### LLM Server (port 8080)

- `GET /health` - Health check
- `GET /status` - Detailed server status
- `POST /generate` - Generate chat response

#### Static Server (port 3000)

- `GET /` - Main interface
- `GET /static/*` - Avatar assets and images

## Troubleshooting

### Common Issues

#### "Model not loaded" error
- Check that the model file path is correct
- Verify model file is not corrupted
- Ensure sufficient RAM (6GB+ recommended)

#### "Local server offline" in UI
- Verify LLM server is running on port 8080
- Check firewall settings
- Ensure CORS is enabled (should be by default)

#### Slow responses
- Try a smaller model (Q4_K_S quantization)
- Reduce context window (`--n-ctx 1024`)
- Increase CPU threads (`--n-threads`)

#### Voice recognition not working
- Use Chrome/Edge browser (best Web Speech API support)
- Check microphone permissions
- Ensure secure context (HTTPS or localhost)

### Performance Optimization

1. **Model Selection**: Use Q4_K_M quantization for best speed/quality balance
2. **Memory Management**: Close other applications to free RAM
3. **CPU Usage**: Set n_threads to match your CPU cores
4. **Context Management**: The system automatically manages conversation history

### Debug Mode

Enable verbose logging:

```bash
python local_llm_server.py --model-path model.gguf --verbose
```

## Development

### Project Structure

```
cupra_local/
├── index.html              # Main interface (same UI/UX as original)
├── serve_static.py          # Static file server
├── server/
│   ├── local_llm_server.py  # Local GGUF LLM server
│   └── requirements.txt     # Python dependencies
├── static/
│   └── media_cupra/         # Avatar assets (copied from original)
└── README.md
```

### Customization

- **Avatar Assets**: Modify files in `static/media_cupra/`
- **System Prompt**: Edit the system prompt in `local_llm_server.py`
- **UI Colors**: Modify CSS variables in `index.html`
- **Voice Settings**: Adjust TTS parameters in the SimpleTTS class

### Adding New Features

The codebase is designed to be easily extensible:

- **New TTS Engines**: Replace SimpleTTS class
- **Different Models**: Add support in local_llm_server.py
- **UI Enhancements**: Modify index.html
- **Additional Endpoints**: Add routes to local_llm_server.py

## Contributing

This is a simplified demonstration version. Improvements welcome:

1. Better error handling
2. Model hot-swapping
3. Settings UI
4. Multi-language support
5. Progressive web app features

## License

Based on the original CUPRA assistant codebase. This simplified version removes proprietary dependencies while maintaining the core functionality and user experience.

## Credits

- Original CUPRA assistant UI/UX design
- llama.cpp for GGUF model support
- FastAPI for the local server
- Web Speech API for browser-based voice features
