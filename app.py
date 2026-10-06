import os, re, requests
from flask import Flask, request, jsonify, render_template_string, Response, stream_with_context
import yt_dlp

app = Flask(__name__)

HTML = """<!doctype html>
<html lang="th">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Media Downloader Pro</title>
  <style>
    :root {
      --bg: #0b0f19;
      --card-bg: #151c2c;
      --border: #232d42;
      --accent: #38bdf8;
      --accent-hover: #0284c7;
      --text: #f1f5f9;
      --text-sub: #94a3b8;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; font-family: system-ui, -apple-system, sans-serif; }
    body { background: var(--bg); color: var(--text); min-height: 100vh; padding: 24px 16px; display: flex; justify-content: center; align-items: flex-start; }
    .container { width: 100%; max-width: 640px; margin-top: 10px; }
    .header { text-align: center; margin-bottom: 24px; }
    .header h1 { font-size: 1.75rem; color: var(--accent); font-weight: 700; margin-bottom: 6px; }
    .header p { color: var(--text-sub); font-size: 0.9rem; }
    
    .input-box { background: var(--card-bg); border: 1px solid var(--border); border-radius: 16px; padding: 8px; display: flex; flex-direction: column; gap: 8px; box-shadow: 0 10px 25px -5px rgba(0,0,0,0.3); }
    input { width: 100%; padding: 14px; border-radius: 10px; border: none; background: transparent; color: #fff; font-size: 1rem; outline: none; }
    button { padding: 14px; border: 0; border-radius: 10px; background: var(--accent); color: #000; font-weight: 700; font-size: 1rem; cursor: pointer; transition: 0.2s; }
    button:hover { background: #7dd3fc; }
    
    #loader { display: none; text-align: center; margin: 24px 0; color: var(--accent); font-weight: 600; }
    .spinner { display: inline-block; width: 20px; height: 20px; border: 3px solid rgba(56,189,248,0.3); border-radius: 50%; border-top-color: var(--accent); animation: spin 0.8s linear infinite; vertical-align: middle; margin-right: 8px; }
    @keyframes spin { to { transform: rotate(360deg); } }

    .video-card { background: var(--card-bg); border-radius: 16px; padding: 16px; margin-bottom: 16px; border: 1px solid var(--border); overflow: hidden; }
    .media-preview { width: 100%; border-radius: 10px; margin-bottom: 12px; background: #000; max-height: 360px; object-fit: contain; }
    .video-title { font-size: 1rem; font-weight: 600; margin-bottom: 12px; line-height: 1.4; color: var(--text); word-break: break-word; }
    
    .btn-group { display: flex; gap: 8px; flex-wrap: wrap; }
    a.btn, button.btn-copy { flex: 1; min-width: 130px; text-align: center; padding: 12px; border-radius: 10px; text-decoration: none; font-weight: 600; font-size: 0.9rem; transition: 0.2s; border: none; cursor: pointer; }
    .btn-video { background: #22c55e; color: #000; }
    .btn-video:hover { background: #4ade80; }
    .btn-audio { background: #a855f7; color: #fff; }
    .btn-audio:hover { background: #c084fc; }
    .btn-copy { background: #334155; color: #fff; }
    .btn-copy:hover { background: #475569; }

    .err { color: #f87171; background: #2d1517; border: 1px solid #7f1d1d; padding: 14px; border-radius: 12px; margin-top: 16px; font-size: 0.9rem; text-align: center; }
    .note { text-align: center; font-size: 0.8rem; color: var(--text-sub); margin-top: 32px; }
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <h1>🚀 Media Downloader Pro</h1>
      <p>รองรับ Twitter/X, TikTok, YouTube, ลิงก์ย่อ และลิงก์ตรงทุกประเภท</p>
    </div>

    <div class="input-box">
      <input id="url" type="url" placeholder="วางลิงก์ที่นี่ (เช่น https://x.com/... หรือ t.co/...)" autocomplete="off">
      <button onclick="getInfo()">ตรวจสอบและดึงวิดีโอ</button>
    </div>

    <div id="loader"><span class="spinner"></span> กำลังติดตามและดึงข้อมูลวิดีโอ...</div>
    <div id="results"></div>

    <p class="note">ดาวน์โหลดเฉพาะสื่อที่คุณได้รับอนุญาตอย่างถูกต้องตามกฎหมายเท่านั้น</p>
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
          
          let previewHtml = '';
          if (item.thumbnail) {
            previewHtml = `<img class="media-preview" src="${item.thumbnail}" alt="preview">`;
          } else if (item.video_url) {
            previewHtml = `<video class="media-preview" src="/api/proxy?url=${encodeURIComponent(item.video_url)}" controls preload="metadata"></video>`;
          }

          let titleText = item.title ? (data.items.length > 1 ? `[${index + 1}/${data.items.length}] ${item.title}` : item.title) : `วิดีโอรายการที่ ${index + 1}`;
          
          let btnsHtml = '';
          if (item.video_url) {
            const proxyVUrl = window.location.origin + '/api/proxy?url=' + encodeURIComponent(item.video_url) + '&type=video';
            btnsHtml += `<a class="btn btn-video" href="${proxyVUrl}" target="_blank" download>⬇️ ดาวน์โหลด (MP4)</a>`;
            btnsHtml += `<button class="btn btn-copy" onclick="copyLink('${proxyVUrl}', this)">📋 คัดลอกลิงก์</button>`;
          }
          if (item.audio_url) {
            const proxyAUrl = window.location.origin + '/api/proxy?url=' + encodeURIComponent(item.audio_url) + '&type=audio';
            btnsHtml += `<a class="btn btn-audio" href="${proxyAUrl}" target="_blank" download>🎵 เฉพาะเสียง</a>`;
          }

          card.innerHTML = `${previewHtml}<div class="video-title">${titleText}</div><div class="btn-group">${btnsHtml}</div>`;
          resultsDiv.appendChild(card);
        });

      } catch (err) {
        loader.style.display = 'none';
        resultsDiv.innerHTML = `<div class="err">${err.message}</div>`;
      }
    }

    function copyLink(url, btn) {
      navigator.clipboard.writeText(url).then(() => {
        const orig = btn.innerText;
        btn.innerText = '✅ คัดลอกแล้ว!';
        setTimeout(() => btn.innerText = orig, 2000);
      });
    }
  </script>
</body>
</html>"""


def resolve_final_url(url):
    """สกัดติดตามลิงก์ซ้อนลิงก์ (Nested / Shortened URLs) หา URL ปลายทางจริง"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    }
    try:
        res = requests.head(url, headers=headers, allow_redirects=True, timeout=8)
        return res.url
    except Exception:
        try:
            res = requests.get(url, headers=headers, allow_redirects=True, timeout=8, stream=True)
            return res.url
        except Exception:
            return url


def is_valid_url(url):
    return isinstance(url, str) and url.startswith(("http://", "https://"))


@app.get("/")
def index():
    return render_template_string(HTML)


@app.post("/api/info")
def info():
    data = request.get_json(silent=True) or {}
    raw_url = data.get("url", "").strip()

    if not is_valid_url(raw_url):
        return jsonify(error="กรุณากรอก URL ที่ถูกต้อง"), 400

    # แกะลิงก์ซ้อนลิงก์ก่อนประมวลผล
    final_url = resolve_final_url(raw_url)

    # กรณีเป็น Direct Media URL (.mp4, videy.co, twimg.jp)
    if re.search(r'\.(mp4|m3u8|mov|webm)($|\?)', final_url, re.I) or "videy.co" in final_url or "twimg.jp" in final_url:
        return jsonify(items=[{
            "title": "ไฟล์วิดีโอโดยตรง (Direct Video)",
            "thumbnail": None,
            "video_url": final_url,
            "audio_url": None
        }])

    ydl_opts = {
        "quiet": True,
        "noplaylist": False,
        "extract_flat": False,
        "http_headers": {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9",
        }
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(final_url, download=False)

        items = []
        entries = info_dict.get("entries") if "entries" in info_dict and info_dict["entries"] else [info_dict]

        for entry in entries:
            if not entry:
                continue

            v_url = None
            a_url = None

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

            if not v_url:
                v_url = entry.get("url")

            items.append({
                "title": entry.get("title") or "Video",
                "thumbnail": entry.get("thumbnail"),
                "video_url": v_url,
                "audio_url": a_url
            })

        return jsonify(items=items)

    except Exception:
        return jsonify(items=[{
            "title": "ลิงก์สื่อภายนอก (Direct Link)",
            "thumbnail": None,
            "video_url": final_url,
            "audio_url": None
        }])


@app.get("/api/proxy")
def proxy():
    target_url = request.args.get("url", "")
    mode = request.args.get("type", "video")

    if not is_valid_url(target_url):
        return "Invalid URL", 400

    # ปรับแต่ง Headers ให้รองรับการดาวน์โหลดสื่อ Twitter/X และ CDN อื่นๆ ไม่โดนบล็อก
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "*/*",
        "Accept-Encoding": "identity",
        "Referer": "https://x.com/" if "twimg" in target_url or "twitter" in target_url else target_url,
    }

    try:
        req = requests.get(target_url, headers=headers, stream=True, timeout=20)
        ext = "mp3" if mode == "audio" else "mp4"
        filename = f"video_download.{ext}"

        def generate():
            for chunk in req.iter_content(chunk_size=16384):
                if chunk:
                    yield chunk

        content_type = req.headers.get("Content-Type", "video/mp4" if ext == "mp4" else "audio/mpeg")
        
        # ป้องกันการส่งไฟล์ประเภท text/html กลับไป
        if "text/html" in content_type.lower():
            content_type = "video/mp4"

        response = Response(
            stream_with_context(generate()),
            content_type=content_type,
            status=req.status_code
        )
        response.headers["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response

    except Exception as e:
        return f"Download Error: {str(e)}", 500


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
      
