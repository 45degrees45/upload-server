#!/usr/bin/env python3
"""Screenshot upload server — stdlib only, port 8400."""

import json
import re
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path

UPLOAD_DIR = Path("/home/jo/claude_projects/Screenshot")
PORT = 8400

HTML = b"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Screenshot Upload</title>
<style>
  body{font-family:sans-serif;max-width:600px;margin:40px auto;padding:0 20px;background:#f5f5f5}
  h1{color:#333}
  #zone{border:3px dashed #aaa;border-radius:8px;padding:40px;text-align:center;
        cursor:pointer;background:#fff;transition:background .2s}
  #zone.hover{background:#e8f4fd;border-color:#3498db}
  button{margin-top:12px;padding:6px 16px;cursor:pointer}
  #file-input{display:none}
  #status{margin-top:14px;font-size:.9em;min-height:1.2em}
  .bar-wrap{width:100%;height:8px;background:#ddd;border-radius:4px;margin-top:8px;display:none}
  .bar{height:100%;background:#3498db;border-radius:4px;width:0%;transition:width .15s}
  #file-list{margin-top:24px}
  #file-list h2{font-size:1em;color:#555}
  ul{list-style:none;padding:0}
  li{padding:4px 0;border-bottom:1px solid #eee;font-size:.85em;color:#333}
</style>
</head>
<body>
<h1>Screenshot Upload</h1>
<div id="zone">
  Drop files here
  <div><button onclick="document.getElementById('file-input').click()">Pick files</button></div>
  <input type="file" id="file-input" multiple>
  <div class="bar-wrap" id="bw"><div class="bar" id="bar"></div></div>
</div>
<div id="status"></div>
<div id="file-list"><h2>Files in Screenshot/</h2><ul id="files"></ul></div>
<script>
const zone=document.getElementById('zone'),
      status=document.getElementById('status'),
      bw=document.getElementById('bw'),
      bar=document.getElementById('bar');

function loadFiles(){
  fetch('/files').then(r=>r.json()).then(data=>{
    const ul=document.getElementById('files');
    function esc(s){return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');}
    ul.innerHTML=data.length?data.map(f=>`<li>${esc(f)}</li>`).join(''):'<li><em>No files yet</em></li>';
  });
}

function upload(file){
  const fd=new FormData();
  fd.append('file',file);
  const xhr=new XMLHttpRequest();
  xhr.upload.onprogress=e=>{
    if(e.lengthComputable){bw.style.display='block';bar.style.width=(e.loaded/e.total*100)+'%';}
  };
  xhr.onload=()=>{
    bw.style.display='none';bar.style.width='0%';
    if(xhr.status===200){
      status.textContent='Uploaded: '+JSON.parse(xhr.responseText).filename;
      loadFiles();
    }else{status.textContent='Upload failed ('+xhr.status+')';}
  };
  xhr.onerror=()=>{status.textContent='Network error.';bw.style.display='none';};
  xhr.open('POST','/upload');
  xhr.send(fd);
}

zone.addEventListener('dragover',e=>{e.preventDefault();zone.classList.add('hover');});
zone.addEventListener('dragleave',()=>zone.classList.remove('hover'));
zone.addEventListener('drop',e=>{
  e.preventDefault();zone.classList.remove('hover');
  [...e.dataTransfer.files].forEach(upload);
});
document.getElementById('file-input').addEventListener('change',e=>[...e.target.files].forEach(upload));
loadFiles();
</script>
</body>
</html>"""


def _parse_multipart(content_type: str, body: bytes):
    """Return (filename, data) from a multipart/form-data body, or (None, None).
    Uses memoryview to avoid copying payload bytes."""
    m = re.search(r'boundary="?([^";]+)"?', content_type)
    if not m:
        return None, None
    boundary = m.group(1).strip().encode()
    mv = memoryview(body)
    sep = b"--" + boundary
    start = body.find(sep)
    while start != -1:
        part_start = start + len(sep)
        # Skip \r\n after boundary
        if body[part_start:part_start+2] == b"\r\n":
            part_start += 2
        next_sep = body.find(b"\r\n--" + boundary, part_start)
        if next_sep == -1:
            break
        part = body[part_start:next_sep]
        if b"\r\n\r\n" not in part:
            start = body.find(sep, next_sep)
            continue
        head_end = part.find(b"\r\n\r\n")
        head_str = part[:head_end].decode("utf-8", errors="replace")
        if "filename=" in head_str:
            for line in head_str.splitlines():
                if "filename=" in line:
                    raw = line.split("filename=")[1].strip().strip('"')
                    filename = Path(raw).name
                    # Use memoryview slice — no copy of payload bytes
                    payload_start = part_start + head_end + 4
                    payload_end = next_sep
                    return filename, bytes(mv[payload_start:payload_end])
        start = body.find(sep, next_sep)
    return None, None


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):  # silence per-request logs
        pass

    def do_GET(self):
        if self.path == "/":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", len(HTML))
            self.end_headers()
            self.wfile.write(HTML)
        elif self.path == "/files":
            try:
                files = sorted(f.name for f in UPLOAD_DIR.iterdir() if f.is_file())
            except FileNotFoundError:
                UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
                files = []
            body = json.dumps(files).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", len(body))
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_error(404)

    def do_POST(self):
        if self.path != "/upload":
            self.send_error(404)
            return
        ct = self.headers.get("Content-Type", "")
        if "multipart/form-data" not in ct:
            self.send_error(400, "Expected multipart/form-data")
            return
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)
        filename, data = _parse_multipart(ct, body)
        if not filename:
            self.send_error(400, "No file in upload")
            return
        (UPLOAD_DIR / filename).write_bytes(data)
        resp = json.dumps({"ok": True, "filename": filename}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", len(resp))
        self.end_headers()
        self.wfile.write(resp)


if __name__ == "__main__":
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Listening on http://0.0.0.0:{PORT}  →  {UPLOAD_DIR}")
    HTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
