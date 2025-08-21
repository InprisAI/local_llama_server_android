# CUPRA Local Assistant - Termux Installation Guide

Complete guide to install and run the CUPRA Local Assistant on Android using Termux.

## 📋 Prerequisites

- **Android Device**: ARM64 (recommended) or ARM32
- **RAM**: 6-8GB (4GB minimum but may be slow)
- **Storage**: 5-8GB free space
- **Android Version**: 7.0+ (API level 24+)
- **Browser**: Chrome or Edge (for Web Speech API support)

## 🚀 Step 1: Install Termux

### Method 1: F-Droid (Recommended)

1. **Install F-Droid**:
   - Download from: https://f-droid.org/
   - Install the F-Droid.apk file
   - Open F-Droid app

2. **Install Termux**:
   - Search for "Termux" in F-Droid
   - Install the official Termux app
   - **DO NOT** use the Google Play Store version (it's outdated)

### Method 2: Direct APK Download

1. Go to: https://github.com/termux/termux-app/releases
2. Download the latest APK for your architecture:
   - `termux-app_vX.X.X+apt-android-7-github-debug_arm64-v8a.apk` (ARM64)
   - `termux-app_vX.X.X+apt-android-7-github-debug_armeabi-v7a.apk` (ARM32)
3. Install the APK file

## 🔧 Step 2: Set Up Termux Environment

### 2.1 Initial Setup

Open Termux and run these commands:

```bash
# Update package repositories
pkg update && pkg upgrade

# Install essential packages
pkg install python git wget nano

# Install compilation tools (needed for some Python packages)
pkg install build-essential cmake

# Verify Python installation
python --version
```

### 2.2 Configure Storage Access (Optional but Recommended)

```bash
# Allow Termux to access device storage
termux-setup-storage
```

This creates a `storage` directory in your Termux home with access to your device's files.

### 2.3 Install Python Dependencies

```bash
# Upgrade pip to latest version
pip install --upgrade pip

# Install required Python packages
pip install Flask>=2.0.0
pip install Flask-Cors>=4.0.0
pip install psutil>=5.9.0

# Install llama-cpp-python (this may take 10-15 minutes)
pip install llama-cpp-python>=0.2.20
```

**Note**: Installing `llama-cpp-python` will compile from source, which takes time. Be patient!

## 📥 Step 3: Download the Project

### 3.1 Clone or Download Project

```bash
# Option 1: If you have the project in a git repository
git clone <your-repo-url> cupra_local
cd cupra_local

# Option 2: If you have project files elsewhere, copy them
# Use termux-setup-storage first, then copy from your device storage
cp -r /storage/emulated/0/Download/local_llama_server_android cupra_local
cd cupra_local
```

### 3.2 Verify Project Structure

```bash
ls -la
```

You should see:
- `index.html`
- `config.json`
- `server/` directory with `local_llm_server.py` and `requirements.txt`
- `static/` directory with avatar assets

## 🤖 Step 4: Download a GGUF Model

Choose one of these optimized models for mobile devices. The CUPRA assistant is trained for ambience themes and conversational responses:

### Option 1: CUPRA-4B Model (Recommended)

```bash
# If you have the CUPRA-specific model
# Place your model file in the project directory
cp /storage/emulated/0/Download/humains-cupra-4b.gguf ./
```

### Option 2: Phi-3 Mini 3.8B (General Purpose)

```bash
# Create models directory
mkdir -p models
cd models

# Download Phi-3 Mini (good general performance)
wget https://huggingface.co/microsoft/Phi-3-mini-4k-instruct-gguf/resolve/main/Phi-3-mini-4k-instruct-q4_k_m.gguf

cd ..
```

### Option 3: Qwen2.5-3B (Alternative)

```bash
mkdir -p models
cd models

# Download Qwen2.5-3B
wget https://huggingface.co/Qwen/Qwen2.5-3B-Instruct-GGUF/resolve/main/qwen2.5-3b-instruct-q4_k_m.gguf

cd ..
```

### Option 4: Gemma 2 2B (For devices with 4GB RAM)

```bash
mkdir -p models
cd models

# Download smaller model for lower RAM devices
wget https://huggingface.co/bartowski/gemma-2-2b-it-GGUF/resolve/main/gemma-2-2b-it-Q4_K_M.gguf

cd ..
```

## 🚀 Step 5: Run the CUPRA Assistant

The project includes a built-in Flask server that serves both the API and static files, so no additional setup scripts are needed.

### 5.1 Start the Server

```bash
# Start with your CUPRA model
cd server
python local_llm_server.py -m "../humains-cupra-4b.gguf" --port 8080 --host 0.0.0.0

# Or with a downloaded model
python local_llm_server.py -m "../models/Phi-3-mini-4k-instruct-q4_k_m.gguf" --port 8080 --host 0.0.0.0
```

## 🎯 Step 6: Access the Interface

### 6.1 Open in Browser

1. **Wait for server startup** (you'll see "Server ready to handle requests")
2. **Open your browser** (Chrome or Edge recommended)
3. **Navigate to**: `http://localhost:8080`
4. **Allow microphone permissions** when prompted

### 6.2 Using the Assistant

1. **Tap the screen** to activate the assistant
2. **Speak clearly** when you see "Listening..."
3. **Watch the avatar animations** change states:
   - **Idle**: Default state, tap to start
   - **Listening**: Recording your voice
   - **Thinking**: Processing your request
   - **Speaking**: Responding with streamed audio
4. **Tap again** to exit conversation mode

### 6.3 Features

- **Real-time streaming**: Responses start playing as soon as sentences are complete
- **Theme generation**: Ask for ambience themes with colors and backgrounds
- **Voice recognition**: Web Speech API for natural conversation
- **Avatar animations**: Visual feedback during different states
- **Local processing**: Everything runs on your device

## 📱 Step 7: Android-Specific Optimizations

### 7.1 Keep Termux Running

```bash
# Acquire wake lock to prevent Android from killing Termux
termux-wake-lock
```

### 7.2 Battery Optimization

1. Go to **Android Settings** > **Apps** > **Termux**
2. Select **Battery**
3. Choose **Don't optimize** or **Unrestricted**

### 7.3 Performance Tuning

Edit the server startup command for better performance:

```bash
# For devices with 6GB+ RAM (recommended)
python local_llm_server.py \
  -m "../humains-cupra-4b.gguf" \
  --port 8080 \
  --host 0.0.0.0 \
  --n-ctx 2048 \
  --n-threads 4 \
  --verbose

# For devices with 4GB RAM (basic)
python local_llm_server.py \
  -m "../humains-cupra-4b.gguf" \
  --port 8080 \
  --host 0.0.0.0 \
  --n-ctx 1024 \
  --n-threads 2
```

## 🔧 Troubleshooting

### Common Issues

#### "llama-cpp-python installation failed"
```bash
# Install additional dependencies
pkg install rust cmake ninja

# Try installing again
pip install llama-cpp-python
```

#### "Permission denied" errors
```bash
# Fix permissions
chmod -R 755 .
```

#### "Model loading failed"
```bash
# Check model file
ls -lh models/
file models/*.gguf

# Verify sufficient RAM
free -h
```

#### Browser can't connect
```bash
# Check if server is running
ps aux | grep python

# Check port
netstat -ln | grep :8080

# Check server logs for errors
# Look for "Server ready to handle requests"
```

#### Voice recognition not working
- Use **Chrome** or **Edge** browser (Safari/Firefox may not work)
- Ensure **microphone permissions** are granted
- Ensure you're accessing via `localhost:8080` (not IP address)
- Check browser console for errors (F12 → Console)

#### No audio playback
- Check browser console for `[TTS]` messages
- Ensure device volume is up
- Try refreshing the page
- Check that Web Speech API is supported

#### Streaming not working
- Check browser console for `[Stream]` messages
- Verify `/generate_stream` endpoint is working
- Check server logs for `[SSE]` messages
- Ensure CORS headers are properly set

### Performance Issues

#### Slow responses
- Use a **smaller model** (Gemma 2 2B)
- Reduce **context size**: `--n-ctx 1024`
- Reduce **threads**: `--n-threads 2`

#### High battery usage
- Enable **battery optimization exemption** for Termux
- Use **termux-wake-lock** only when needed
- Consider using smaller models

#### Out of memory
- **Close other apps** before starting
- Use **Q4_K_S** quantization instead of Q4_K_M
- Reduce context size to 512 or 1024

## 📊 Model Comparison

| Model | Size | RAM Usage | Speed | Quality | Best For |
|-------|------|-----------|-------|---------|----------|
| Phi-3 Mini 3.8B Q4_K_M | 2.4GB | ~4GB | Fast | High | Balanced performance |
| Qwen2.5-3B Q4_K_M | 2.1GB | ~3.5GB | Fast | High | Multilingual support |
| Gemma 2 2B Q4_K_M | 1.4GB | ~3GB | Very Fast | Good | Low-end devices |
| Llama 3.2 3B Q4_K_S | 1.8GB | ~3.2GB | Fast | Good | Memory constrained |

## 🎉 Success!

Once everything is running:

1. **Tap the screen** in the browser to activate
2. **Speak to the assistant** or type messages
3. **Watch the avatar animations** respond to different states
4. **Enjoy your local, private AI assistant!**

## 💡 Tips for Best Experience

- **Use headphones** to prevent audio feedback
- **Speak clearly** and wait for the "Listening..." indicator
- **Keep Termux in foreground** when possible
- **Monitor battery usage** and temperature
- **Check browser console** for debugging streaming issues
- **Use Chrome or Edge** for best Web Speech API support
- **Restart server** if streaming becomes unresponsive
- **Test with simple phrases** first (e.g., "Hello" or "Make it blue")

## 🛠️ Advanced Configuration

### Debugging Streaming

To debug streaming issues, check these browser console messages:

- `[Stream] onData: token` - Tokens arriving from server
- `[Stream] No JSON, adding token to speech buffer` - Normal conversation mode
- `[flushSentences] Will speak` - Sentences ready for TTS
- `[TTS] Speaking` - Audio playback starting
- `[SSE]` messages in server logs - Server-side streaming

### Performance Optimization

```bash
# Enable verbose logging for debugging
python local_llm_server.py -m "../humains-cupra-4b.gguf" --verbose

# Adjust context window for memory usage
python local_llm_server.py -m "../humains-cupra-4b.gguf" --n-ctx 1024

# Adjust thread count for CPU usage  
python local_llm_server.py -m "../humains-cupra-4b.gguf" --n-threads 2
```

### Custom System Prompt

The CUPRA assistant system prompt is built into the server. To modify it, edit the `create_prompt()` function in `server/local_llm_server.py`.

---

**🚗 Enjoy your local CUPRA Assistant!** This setup gives you a fully functional AI assistant running entirely on your Android device with complete privacy and no internet dependency for inference.
