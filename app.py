import os, re
from flask import Flask, request, jsonify, render_template_string
import yt_dlp

app = Flask(__name__)

HTML = """<!doctype html>
<html lang="th">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Media Downloader Pro</title>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #0f172a; color: #f8fafc; min-height: 100vh; padding: 20px 16px; display: flex; justify-content: center; }
    .container { width: 100%; max-width: 600px; margin-top: 20px; }
    h1 { font-size: 1.5rem; text-align: center; margin-bottom: 20px; color: #38bdf8; }
    .input-group { display: flex; flex-direction: column; gap: 10px; margin-bottom: 20px; }
    input { width: 100%; padding: 14px; border-radius: 10px; border: 1px solid #334155; background: #1e293b; color: #fff; font-size: 1rem; outline: none; }
    input:focus { border-color: #38bdf8; }
    button { padding: 14px; border: 0; border-radius: 10px; background: #0284c7; color: #fff; font-weight: 600; font-size: 1rem; cursor: pointer; transition: 0.2s; }
    button:hover { background: #0369a1; }
    #loader { display: none; text-align: center; margin: 20px 0; color: #94a3b8; }
    .video-card { background: #1e293b; border-radius: 12px; padding: 16px; margin-bottom: 16px; border: 1px solid #334155; }
    .video-card img { width: 100%; height: auto; border-radius: 8px; margin-bottom: 12px; object-fit: cover; max-height: 250px; }
    .video-title { font-size: 1rem; font-weight: 600; margin-bottom: 12px; line-height: 1.4; word-break: break-word; color: #e2e8f0; }
    .btn-group { display: flex; gap: 10px; flex-wrap: wrap; }
    a.btn { flex: 1; min-width: 120px; text-align: center; padding: 10px 14px; border-radius: 8px; text-decoration: none; font-weight: 600; font-size: 0.9rem; transition: 0.2s; }
    .btn-video { background: #22c55e; color: #fff; }
    .btn-video:hover { background: #16a34a; }
    .btn-audio { background: #a855f7; color: #fff; }
    .btn-audio:hover { background: #9333ea; }
    .err { color: #f87171; background: #451a1a; padding: 12px; border-radius: 8px; margin-top: 10px; font-size: 0.9rem; text-align: center; }
    .note { text-align: center; font-size: 0.8rem; color: #64748b; margin-top: 30px; }
  </style>
</head>
<body>
  <div class="container">
    <h1>🚀 Video Downloader</h1>
    <div class="input-group">
      <input id="url" type="url" placeholder="วางลิงก์วิดีโอ (X/Twitter, TikTok, YouTube, ฯลฯ)" autocomplete="off">
      <button onclick="getInfo()">ตรวจสอบและดึงลิงก์</button>
    </div>

    <div id="loader">⏳ กำลังตรวจสอบและสกัดลิงก์วิดีโอ...</div>
    <div id="results"></div>

    <p class="note">ดาวน์โหลดเฉพาะสื่อที่คุณมีสิทธิ์ในการใช้งานอย่างถูกต้องตามกฎหมายเท่านั้น</p>
  </div>

  <script>
    async function getInfo() {
      const urlInput = document.getElementById('url').value.trim();
      const resultsDiv = document.getElementById('results');
      const loader = document.getElementById('loader');
      
      if (!urlInput) return;

      resultsDiv.innerHTML = '';
      loader.style.display = 'block';

      try {
        const res = await fetch('/api/info', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ url: urlInput })
        });
        const data = await res.json();
        loader.style.display = 'none';

        if (!res.ok) throw new Error(data.error || 'ดึงข้อมูลไม่สำเร็จ');

        if (!data.items || data.items.length === 0) {
          resultsDiv.innerHTML = '<div class="err">ไม่พบวิดีโอในลิงก์นี้</div>';
          return;
        }

        data.items.forEach((item, index) => {
          const card = document.createElement('div');
          card.className = 'video-card';
          
          let imgHtml = item.thumbnail ? `<img src="${item.thumbnail}" alt="thumbnail">` : '';
          let titleText = item.title ? (data.items.length > 1 ? `[${index + 1}/${data.items.length}] ${item.title}` : item.title) : `วิดีโอที่ ${index + 1}`;
          
          let btnsHtml = '';
          if (item.video_url) {
            btnsHtml += `<a class="btn btn-video" href="${item.video_url}" target="_blank" download>ดาวน์โหลดวิดีโอ (MP4)</a>`;
          }
          if (item.audio_url) {
            btnsHtml += `<a class="btn btn-audio" href="${item.audio_url}" target="_blank" download>เฉพาะเสียง (Audio)</a>`;
          }

          card.innerHTML = `${imgHtml}<div class="video-title">${titleText}</div><div class="btn-group">${btnsHtml}</div>`;
          resultsDiv.appendChild(card);
        });

      } catch (err) {
        loader.style.display = 'none';
        resultsDiv.innerHTML = `<div class="err">${err.message}</div>`;
      }
    }
  </script>
</body>
</html>"""


def is_valid_url(url):
    return isinstance(url, str) and url.startswith(("http://", "https://"))


@app.get("/")
def index():
    return render_template_string(HTML)


@app.post("/api/info")
def info():
    data = request.get_json(silent=True) or {}
    url = data.get("url", "").strip()

    if not is_valid_url(url):
        return jsonify(error="กรุณากรอก URL ที่ถูกต้อง"), 400

    # กรณีเป็น Direct Media URL (.mp4 หรือโดเมนเก็บไฟล์ตรงอย่าง videy.co)
    if re.search(r'\.(mp4|m3u8|mov|webm)($|\?)', url, re.I) or "videy.co" in url or "twimg.jp" in url:
        return jsonify(items=[{
            "title": "ไฟล์วิดีโอโดยตรง (Direct Video)",
            "thumbnail": None,
            "video_url": url,
            "audio_url": None
        }])

    ydl_opts = {
        "quiet": True,
        "noplaylist": False,
        "extract_flat": False,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=False)

        items = []
        
        # ตรวจสอบว่าเป็น Playlist/หลายวิดีโอในโพสต์เดียว หรือไม่
        if "entries" in info_dict and info_dict["entries"]:
            entries = info_dict["entries"]
        else:
            entries = [info_dict]

        for entry in entries:
            if not entry:
                continue

            v_url = None
            a_url = None

            # สกัดหา URL วิดีโอ/เสียง ที่สมบูรณ์ที่สุด
            formats = entry.get("formats", [])
            for f in reversed(formats):
                f_url = f.get("url")
                if not f_url:
                    continue
                vcodec = f.get("vcodec", "")
                acodec = f.get("acodec", "")

                if not v_url and vcodec != "none":
                    v_url = f_url
                if not a_url and acodec != "none":
                    a_url = f_url
                
                if v_url and a_url:
                    break

            # Fallback หากหา format ย่อยไม่เจอ
            if not v_url:
                v_url = entry.get("url")

            items.append({
                "title": entry.get("title") or "Video",
                "thumbnail": entry.get("thumbnail"),
                "video_url": v_url,
                "audio_url": a_url
            })

        return jsonify(items=items)

    except Exception as e:
        # หาก yt-dlp ล้มเหลว ให้คืนค่าส่งกลับเป็นลิงก์ไฟล์ตรง
        return jsonify(items=[{
            "title": "ลิงก์ไฟล์ตรง (Direct Media)",
            "thumbnail": None,
            "video_url": url,
            "audio_url": None
        }])


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
  
