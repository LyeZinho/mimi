# Fish Shell Setup Guide

If you're using Fish shell, follow this guide to properly activate the Python venv.

## Quick Start

```fish
# Activate venv using Fish-specific script
source .venv/bin/activate.fish

# Then run the agent
python agent/main.py
```

## Full Setup (3 Terminals)

**Terminal 1 - WebSocket Server (Bash/Zsh or Fish):**
```fish
cd web_avatar && node server.js
```

**Terminal 2 - Python Agent (Fish):**
```fish
# Navigate to project root
cd /home/pedro/repo/mimi

# Activate venv for Fish
source .venv/bin/activate.fish

# Run agent
python agent/main.py
```

**Terminal 3 - React Frontend (Bash/Zsh or Fish):**
```fish
cd web_avatar && npm run dev
```

Then open: **http://localhost:5173**

## Why the difference?

- **Bash/Zsh** use: `source .venv/bin/activate`
- **Fish** uses: `source .venv/bin/activate.fish`

The `.venv/bin/activate.fish` script is created automatically by Python's venv module and is Fish-compatible.

## Troubleshooting

### "case builtin not inside of switch block"

This error means you tried to use the Bash activate script in Fish. Use the Fish version instead:

```fish
# ❌ Wrong (Bash script in Fish)
source .venv/bin/activate

# ✅ Correct (Fish script in Fish)
source .venv/bin/activate.fish
```

### Venv not activating?

Check if the Fish script exists:
```fish
ls -la .venv/bin/activate.fish
```

If missing, recreate venv:
```fish
rm -rf .venv
python3 -m venv .venv
source .venv/bin/activate.fish
```

### Module import errors after activation?

Verify venv is active:
```fish
echo $VIRTUAL_ENV
# Should output: /home/pedro/repo/mimi/.venv
```

If empty, venv didn't activate. Try again:
```fish
source .venv/bin/activate.fish
```

## Creating an Alias (Optional)

Add to your `~/.config/fish/config.fish`:

```fish
alias activate="source .venv/bin/activate.fish"
```

Then just run:
```fish
cd ~/repo/mimi
activate
python agent/main.py
```
