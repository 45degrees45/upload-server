# Architecture

A minimal stdlib-only Python HTTP server (port 8400) that lets any device on the local network drag-and-drop or pick files through a browser UI, saving them to `/home/jo/claude_projects/Screenshot/` on the host machine.

```mermaid
flowchart TD
    Browser["Browser\n(any device on LAN)"]

    subgraph Server["server.py — HTTPServer :8400"]
        GET_ROOT["GET /\nServe inline HTML+JS"]
        GET_FILES["GET /files\nList Screenshot/ directory"]
        POST_UPLOAD["POST /upload\nParse multipart/form-data\n_parse_multipart()"]
    end

    UPLOAD_DIR["/home/jo/claude_projects/Screenshot/\n(file store)"]

    Browser -- "GET /" --> GET_ROOT
    GET_ROOT -- "200 HTML page" --> Browser
    Browser -- "GET /files" --> GET_FILES
    GET_FILES -- "JSON list of filenames" --> Browser
    Browser -- "POST /upload\n(multipart file)" --> POST_UPLOAD
    POST_UPLOAD -- "write_bytes()" --> UPLOAD_DIR
    POST_UPLOAD -- "JSON {ok, filename}" --> Browser
    GET_FILES -- "iterdir()" --> UPLOAD_DIR
```
