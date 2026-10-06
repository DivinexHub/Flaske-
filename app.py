import os, shutil, tempfile
from flask import Flask, request, jsonify, send_file, render_template_string, after_this_request
import yt_dlp

app = Flask(__name__)

HTML = """<!doctype html>
<html lang="th"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Video Downloader</title>
<style>
body{font-family:system-ui,sans-serif;max-width:640px;margin:40px auto;padding:0 16px;background:#0f172a;color:#e2e8f0}
h1{font-size:1.5rem}
input{width:100%;padding:12px;border-radius:8px;border:1px solid #334155;background:#1e293b;color:#fff;box-sizing:border-box}
button,a.btn{display:inline-block;margin-top:10px;margin-right:8px;padding:10px 16px;border:0;border-radius:8px;background:#3b82f6;color:#fff;text-decoration:none;cursor:pointer;font-size:1rem}
#info{margin-top:20px}img{max-width:100%;border-radius:8px}
.err{color:#f87171}.note{font-size:.8rem;color:#94a3b8;margin-top:24px}
</style></head><body>
<h1>⬇️ ดึงวิดีโอจากเว็บ</h1>
<input id="url" placeholder="วางลิงก์วิดีโอที่นี่ เช่น https://...">
<button onclick="getInfo()">ตรวจสอบวิดีโอ</button>
<div id="info"></div>
<p class="note">ดาวน์โหลดเฉพาะวิดีโอที่คุณเป็นเจ้าของ หรือได้รับอนุญาต และปฏิบัติตามข้อกำหนดของเว็บต้นทาง</p>
<script>
async function getInfo(){
  const url=document.getElementById('url').value.trim(), box=document.getElementById('info');
  box.innerHTML='กำลังตรวจสอบ...';
  try{
    const r=await fetch('/api/info',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({url})});
    const d=await r.json(); if(!r.ok) throw new Error(d.error);
    const q=encodeURIComponent(url);
    box.innerHTML=(d.thumbnail?'<img src="'+d.thumbnail+'">':'')+'<h3></h3>'
      +'<a class="btn" href="/api/download?mode=video&url='+q+'">ดาวน์โหลดวิดีโอ (MP4)</a>'
      +'<a class="btn" href="/api/download?mode=audio&url='+q+'">เฉพาะเสียง</a>';
    box.querySelector('h3').textContent=d.title;
  }catch(e){box.innerHTML='<p class="err"></p>';box.querySelector('p').textContent=e.message;}
}
</script></body></html>"""


def valid(url):
    return isinstance(url, str) and url.startswith(("http://", "https://"))


@app.get("/")
def index():
    return render_template_string(HTML)


@app.post("/api/info")
def info():
    url = (request.get_json(silent=True) or {}).get("url", "")
    if not valid(url):
        return jsonify(error="ลิงก์ไม่ถูกต้อง"), 400
    try:
        with yt_dlp.YoutubeDL({"quiet": True, "noplaylist": True}) as y:
            d = y.extract_info(url, download=False)
        return jsonify(title=d.get("title"), thumbnail=d.get("thumbnail"))
    except Exception as e:
        return jsonify(error="ดึงข้อมูลไม่ได้: " + str(e)[:200]), 400


@app.get("/api/download")
def download():
    url, mode = request.args.get("url", ""), request.args.get("mode", "video")
    if not valid(url):
        return "invalid url", 400
    tmp = tempfile.mkdtemp()
    fmt = "bestaudio[ext=m4a]/bestaudio" if mode == "audio" else "best[ext=mp4]/best"
    opts = {"quiet": True, "noplaylist": True, "format": fmt,
            "outtmpl": os.path.join(tmp, "%(title).80s.%(ext)s")}
    try:
        with yt_dlp.YoutubeDL(opts) as y:
            y.extract_info(url, download=True)
        path = os.path.join(tmp, os.listdir(tmp)[0])
    except Exception as e:
        shutil.rmtree(tmp, ignore_errors=True)
        return "ดาวน์โหลดไม่สำเร็จ: " + str(e)[:200], 400

    @after_this_request
    def cleanup(resp):
        shutil.rmtree(tmp, ignore_errors=True)
        return resp

    return send_file(path, as_attachment=True)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
