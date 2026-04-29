# Upload Server

A minimal, dependency-free Python file upload server for local network use. Run it on any machine and browse to port 8400 from any device on the same network to drag-and-drop or pick files — they land in the `Screenshot/` directory on the host.

See [docs/architecture.md](docs/architecture.md) for an architecture diagram.

## Usage

```bash
python3 server.py
# Listening on http://0.0.0.0:8400  →  /home/jo/claude_projects/Screenshot
```

Open `http://<host-ip>:8400` in any browser.
