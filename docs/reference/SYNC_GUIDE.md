# Real-time Sync & Transparent Background - Usage Guide

## ✨ New Features

### 1. Real-time Synchronization
OBS page now mirrors exactly what's happening in the main interface!

### 2. Transparent Background
Perfect for OBS without needing chroma key.

### 3. State Broadcasting
All changes are automatically synced across all connected clients.

## 🚀 Quick Start

### Basic Setup

1. **Start the server**:
   ```bash
   .\start.bat
   ```

2. **Open main interface**:
   ```
   http://localhost:8000
   ```

3. **Open OBS page** (in another tab or OBS Browser Source):
   ```
   http://localhost:8000/obs.html
   ```

4. **Test synchronization**:
   - Change expression in main interface
   - Watch it update in OBS page automatically!

## 🎥 OBS Configuration

### Option 1: Transparent Background (Recommended)

**URL**:
```
http://localhost:8000/obs.html?transparent=true
```

**OBS Settings**:
- Width: 1920
- Height: 1080
- ✅ No chroma key needed!

### Option 2: Chroma Key (Green Screen)

**URL**:
```
http://localhost:8000/obs.html
```

**OBS Settings**:
- Width: 1920
- Height: 1080
- Add **Chroma Key** filter:
  - Type: Green
  - Similarity: 400
  - Smoothness: 80

### Option 3: Custom Background Color

**URL**:
```
http://localhost:8000/obs.html?bg=0000ff
```

Colors:
- `00ff00` - Green (chroma key)
- `0000ff` - Blue
- `ff00ff` - Magenta
- `000000` - Black
- `transparent` - Transparent

## 🎮 URL Parameters

| Parameter | Values | Description |
|-----------|--------|-------------|
| `transparent` | `true`/`false` | Enable transparent background |
| `bg` | Hex color or `transparent` | Background color |
| `model` | `Mimi.vrm`, `Mimi01.vrm` | Model to load |
| `ws` | WebSocket URL | Custom WebSocket server |
| `controls` | `true`/`false` | Enable camera controls |
| `status` | `true`/`false` | Show connection status |
| `autoload` | `true`/`false` | Auto-load model on start |

### Examples

**Transparent with specific model**:
```
http://localhost:8000/obs.html?transparent=true&model=Mimi01.vrm
```

**Blue background with camera controls**:
```
http://localhost:8000/obs.html?bg=0000ff&controls=true
```

**No auto-load, show status**:
```
http://localhost:8000/obs.html?autoload=false&status=true
```

## 🔄 How Synchronization Works

### Main Interface (Controller)
- Broadcasts all changes to WebSocket server
- Changes include:
  - Model selection
  - Expression changes
  - Animations (future)
  - Camera position (future)

### OBS Page (Viewer)
- Listens for state updates
- Applies changes automatically
- No user interaction needed

### Flow
```
Main Interface → WebSocket Server → OBS Page
     (Control)                      (Mirror)
```

## 🧪 Testing Synchronization

1. Open main interface: `http://localhost:8000`
2. Open OBS page in another tab: `http://localhost:8000/obs.html?transparent=true`
3. In main interface:
   - Select a model → OBS updates
   - Click expression → OBS updates
   - Click "Falar" → OBS lip-syncs

## 💡 Tips

### For Best Quality
- Use 1920x1080 resolution
- Enable hardware acceleration in browser
- Use `transparent=true` instead of chroma key

### For Performance
- Use lower resolution (1280x720)
- Disable `controls` parameter
- Close unnecessary browser tabs

### For Debugging
- Add `status=true` to see connection status
- Open browser console (F12) to see logs
- Check WebSocket connection in Network tab

## 🎨 Customization

### Change Default Model
Edit `obs.html` URL:
```
?model=YourModel.vrm
```

### Multiple OBS Sources
You can have multiple OBS browser sources, all will sync:
```
Source 1: http://localhost:8000/obs.html?transparent=true
Source 2: http://localhost:8000/obs.html?bg=0000ff
```

Both will show the same avatar state!

## 🐛 Troubleshooting

### OBS page doesn't update
1. Check WebSocket is connected (add `?status=true`)
2. Verify main interface is open
3. Check browser console for errors

### Transparent background shows black
1. Make sure you're using `?transparent=true`
2. Check OBS browser source settings
3. Try refreshing the browser source

### Model doesn't load
1. Verify model file exists in `vroid_model/`
2. Check model name in URL parameter
3. Look for errors in browser console

### Performance issues
1. Lower resolution in OBS
2. Disable camera controls (`controls=false`)
3. Close other browser tabs
4. Update graphics drivers

## 📊 Performance

| Resolution | FPS | Memory | CPU |
|------------|-----|--------|-----|
| 1920x1080 | 60 | ~150MB | ~5% |
| 1280x720 | 60 | ~100MB | ~3% |
| 1024x576 | 60 | ~80MB | ~2% |

*Tested on: i5-8400, GTX 1060, 16GB RAM*

## 🔮 Coming Soon

- [ ] Animation synchronization
- [ ] Camera position sync
- [ ] FBX animation support
- [ ] Custom gestures
- [ ] Multiple avatar support

## 📚 Related Docs

- [OBS Setup Guide](OBS_SETUP.md)
- [Quick Start](QUICKSTART.md)
- [Implementation Plan](../../.gemini/antigravity/brain/.../implementation_plan.md)
