# Quick Start Commands - CUPRA Local Assistant

## 🚀 One-Time Setup

```bash
# 1. Install Termux from F-Droid (not Google Play)
# 2. In Termux, run:
pkg update && pkg upgrade
pkg install python git wget build-essential cmake
pip install --upgrade pip
pip install Flask Flask-Cors psutil llama-cpp-python

# 3. Get the project (adjust path as needed)
git clone <your-repo> cupra_local
# OR: cp -r /storage/emulated/0/Download/local_llama_server_android cupra_local

cd cupra_local

# 4. Download a model (choose one)
mkdir models
wget -P models https://huggingface.co/microsoft/Phi-3-mini-4k-instruct-gguf/resolve/main/Phi-3-mini-4k-instruct-q4_k_m.gguf
```

## 🏃 Every Time You Want to Use It

```bash
# Navigate to project
cd cupra_local

# Keep Termux awake
termux-wake-lock

# Start the assistant (adjust model name as needed)
python start_cupra.py --model-path models/Phi-3-mini-4k-instruct-q4_k_m.gguf

# Open browser: http://localhost:3000
# Tap screen to start, speak to the assistant!
```

## 🛑 To Stop

```bash
# Press Ctrl+C in Termux to stop servers
# Or just close Termux app
```

## 🔧 Manual Start (if script doesn't work)

```bash
# Terminal 1: Start LLM server
python server/local_llm_server.py --model-path models/Phi-3-mini-4k-instruct-q4_k_m.gguf --port 8080

# Terminal 2: Start web server (new session)
python serve_static.py --port 3000

# Browser: http://localhost:3000
```

## 📱 Essential Android Settings

1. **Termux Battery**: Settings > Apps > Termux > Battery > Don't optimize
2. **Browser**: Use Chrome or Edge for best voice support
3. **Microphone**: Allow microphone access when prompted

## 🚨 Quick Troubleshooting

- **"Can't connect"**: Check both servers are running with `ps aux | grep python`
- **"Slow responses"**: Add `--n-threads 2 --n-ctx 1024` to server command
- **"Out of memory"**: Close other apps, use smaller model (Gemma 2B)
- **"Voice not working"**: Use Chrome, check microphone permissions

## 📊 Recommended Models by Device

- **8GB+ RAM**: Phi-3 Mini 3.8B Q4_K_M (2.4GB)
- **6GB RAM**: Qwen2.5-3B Q4_K_M (2.1GB) 
- **4GB RAM**: Gemma 2 2B Q4_K_M (1.4GB)

That's it! Your local AI assistant is ready to go! 🚗✨
