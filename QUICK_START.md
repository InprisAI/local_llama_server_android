# Quick Start Commands - CUPRA Local Assistant

## 🚀 One-Time Setup

```bash
# 1. Install dependencies
pip install -r server/requirements.txt

# 2. Get the project (if not already cloned)
git clone <your-repo> cupra_local
cd cupra_local

# 3. Download LLM model (choose one)
mkdir models
# Example: wget -P models https://huggingface.co/microsoft/Phi-3-mini-4k-instruct-gguf/resolve/main/Phi-3-mini-4k-instruct-q4_k_m.gguf

# 4. Download Vosk STT model for offline speech recognition
cd models
wget https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip
unzip vosk-model-small-en-us-0.15.zip
cd ..
```

## 🏃 Every Time You Want to Use It

```bash
# Navigate to project/server directory
cd cupra_local/server

# Start the assistant with offline STT (adjust model path as needed)
python local_llm_server.py -m "path/to/your/model.gguf" --stt-model-dir "../models/vosk-model-small-en-us-0.15"

# Open browser: http://localhost:8080
# Tap screen to start, speak to the assistant!
```

## 🛑 To Stop

```bash
# Press Ctrl+C in Termux to stop servers
# Or just close Termux app
```

## 🔧 Alternative Commands

```bash
# Without offline STT (online-only speech recognition)
python local_llm_server.py -m "path/to/your/model.gguf" --port 8080

# With custom port
python local_llm_server.py -m "path/to/your/model.gguf" --stt-model-dir "../models/vosk-model-small-en-us-0.15" --port 8080

# Verbose output for debugging
python local_llm_server.py -m "path/to/your/model.gguf" --stt-model-dir "../models/vosk-model-small-en-us-0.15" --verbose
```

## 📱 Essential Android Settings

1. **Termux Battery**: Settings > Apps > Termux > Battery > Don't optimize
2. **Browser**: Use Chrome or Edge for best voice support
3. **Microphone**: Allow microphone access when prompted

## 🚨 Quick Troubleshooting

- **"Can't connect"**: Check server is running with `ps aux | grep python`
- **"Slow responses"**: Add `--n-threads 2 --n-ctx 1024` to server command
- **"Out of memory"**: Close other apps, use smaller model (Gemma 2B)
- **"Voice not working"**: Use Chrome, check microphone permissions
- **"STT 503 errors"**: Vosk model not loaded, check `--stt-model-dir` path
- **"No offline STT"**: Download Vosk model with setup commands above

## 🎤 Vosk Speech-to-Text Setup (Detailed)

### Windows:
```powershell
# Create models directory
mkdir models
cd models

# Download Vosk model
Invoke-WebRequest -Uri "https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip" -OutFile "vosk-model-small-en-us-0.15.zip"

# Extract
Expand-Archive -Path "vosk-model-small-en-us-0.15.zip" -DestinationPath "."

# Go back to project root
cd ..
```

### Linux/Android (Termux):
```bash
cd models
wget https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip
unzip vosk-model-small-en-us-0.15.zip
cd ..
```

### Available Vosk Models:
- **Small (40MB)**: `vosk-model-small-en-us-0.15` - Fast, good accuracy
- **Large (1.8GB)**: `vosk-model-en-us-0.22` - Better accuracy, slower
- **Other languages**: Check https://alphacephei.com/vosk/models

## 📊 Recommended Models by Device

- **8GB+ RAM**: Phi-3 Mini 3.8B Q4_K_M (2.4GB)
- **6GB RAM**: Qwen2.5-3B Q4_K_M (2.1GB) 
- **4GB RAM**: Gemma 2 2B Q4_K_M (1.4GB)

## ✅ Verification

After setup, check `http://localhost:8080/status` should show:
```json
{
  "status": "ready",
  "model_loaded": true,
  "stt_offline": true
}
```

That's it! Your local AI assistant with offline speech recognition is ready! 🚗✨
