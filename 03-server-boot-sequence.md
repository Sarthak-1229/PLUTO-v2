# Jarvislabs Zero-Waste Boot Sequence

**CRITICAL:** At ₹85/hour, time is money. This exact sequence must be followed to prevent billing leaks and ensure immediate productivity.

## 1. Start Sequence (Beginning of Session)
1. **Unpause Instance:** Go to the Jarvislabs UI and resume the paused 48GB GPU instance. Wait ~60 seconds for the IP to become active.
2. **Update Client:** If the public IP changed upon unpausing, immediately update `CLOUD_WS_URL` in the local laptop's `client.py` file.
3. **Connect via SSH:** 
   `ssh root@<JARVISLABS_IP> -p <PORT>`
4. **Initialize tmux:** Run `tmux` in the terminal to prevent the server from crashing if the SSH connection drops.
5. **Verify AI Engine:** Ensure Ollama is running in the background. If using a custom script, run:
   `python3 server.py`
6. **Start Local Client:** On the local Windows laptop, run:
   `python client.py`

## 2. The Dev Loop
*   Once connected, all interactions happen via the local terminal or a local UI window.
*   Any code changes to the AI logic must be pushed/synced to the cloud server and `server.py` restarted.

## 3. Stop Sequence (End of Session) - DO NOT SKIP
1. **Kill Server:** Press `Ctrl+C` on the local laptop client.
2. **Kill Cloud:** In the SSH terminal, press `Ctrl+C` to stop `server.py`. 
3. **Detach tmux:** Press `Ctrl+b`, then `d`.
4. **PAUSE INSTANCE:** Go directly to the Jarvislabs dashboard and click **Pause** (or run `jl pause` if the CLI is configured). 
5. **Verify:** Confirm the billing meter has switched from compute pricing to storage pricing only.