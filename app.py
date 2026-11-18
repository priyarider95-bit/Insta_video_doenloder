from flask import Flask, render_template_string, request, jsonify, send_file
import yt_dlp
import os
import threading
import time

app = Flask(__name__)

download_progress = {}

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0"><meta name="google-site-verification" content="YhC7qvJ2THwDehwk9YCsYdGuUvA86PvjzzTQLGc_Elk" />
    <title>InstaMaster - Fast Downloader</title>
    <style>
        body { background-color: #0b0b0b; color: #ffffff; font-family: Arial, sans-serif; text-align: center; margin: 0; padding: 10px; }
        .header-box { border: 2px solid #ff1a1a; border-radius: 12px; padding: 15px; margin: 10px auto; max-width: 420px; box-shadow: 0 0 15px rgba(255, 26, 26, 0.6); background: #111; }
        .header-box h1 { color: #ff1a1a; margin: 0; font-size: 26px; text-shadow: 0 0 10px rgba(255, 26, 26, 0.8); }
        .header-box p { color: #888; font-size: 11px; letter-spacing: 2px; margin: 5px 0 0 0; }
        .card { border: 2px solid #ff1a1a; border-radius: 12px; padding: 15px; margin: 15px auto; max-width: 420px; box-shadow: 0 0 12px rgba(255, 26, 26, 0.4); background: #111; text-align: left; }
        .card h3 { color: #ff3333; margin-top: 0; font-size: 16px; }
        input[type="text"] { width: 100%; padding: 12px; background: #1a1a1a; border: 1px solid #ff1a1a; color: white; border-radius: 8px; box-sizing: border-box; margin-bottom: 12px; outline: none; }
        .download-btn { background: linear-gradient(to bottom, #ff3333, #cc0000); color: white; border: none; width: 100%; padding: 14px; font-weight: bold; font-size: 15px; border-radius: 8px; cursor: pointer; box-shadow: 0 0 10px rgba(255, 51, 51, 0.6); }
        .save-btn { display: none; background: linear-gradient(to bottom, #00cc44, #009933); color: white; text-decoration: none; text-align: center; width: 100%; padding: 14px; font-weight: bold; font-size: 15px; border-radius: 8px; box-shadow: 0 0 10px rgba(0, 204, 68, 0.6); margin-top: 12px; box-sizing: border-box; }
        .progress-box { border: 2px solid #ff1a1a; border-radius: 12px; padding: 15px; margin: 15px auto; max-width: 420px; box-shadow: 0 0 12px rgba(255, 26, 26, 0.4); background: #111; text-align: left; }
        .progress-box h3 { color: #ff3333; margin-top: 0; font-size: 16px; }
        .progress-bar-bg { background: #222; border-radius: 6px; height: 10px; width: 100%; margin: 10px 0; overflow: hidden; }
        .progress-bar-fill { background: #ff3333; height: 100%; width: 0%; box-shadow: 0 0 8px #ff3333; transition: width 0.3s ease; }
        .info-row { display: flex; justify-content: space-between; font-size: 12px; color: #bbb; margin-top: 8px; }
        .footer { color: #666; font-size: 10px; margin-top: 20px; letter-spacing: 1px; }
    </style>
</head>
<body>

    <div class="header-box">
        <h1>▶ InstaMaster</h1>
        <p>INSTAGRAM VIDEO DOWNLOADER</p>
    </div>

    <div class="card">
        <h3>🔗 Video Downloader</h3>
        <form id="downloadForm">
            <input type="text" id="urlInput" name="url" placeholder="Paste Instagram video link here..." required>
            <button type="submit" class="download-btn" id="submitBtn">↓ DOWNLOAD NOW</button>
        </form>
        <a id="saveBtn" class="save-btn" href="#" target="_blank">📥 SAVE TO CHROME DOWNLOADS</a>
    </div>

    <div class="progress-box">
        <h3>📊 LIVE DOWNLOAD PROGRESS</h3>
        <div class="info-row">
            <span id="statusText">Status: Waiting</span>
            <span id="percentText">0%</span>
        </div>
        <div class="progress-bar-bg">
            <div id="progressBar" class="progress-bar-fill"></div>
        </div>
        <div class="info-row">
            <span id="downloadedText">Downloaded: 0 MB</span>
            <span id="speedText">Speed: -- MB/s</span>
        </div>
    </div>

    <div class="footer">
        CLIPMASTER © 2026 | TURBO EDITION
    </div>

    <script>
        document.getElementById('downloadForm').addEventListener('submit', function(e) {
            e.preventDefault();
            const url = document.getElementById('urlInput').value;
            document.getElementById('submitBtn').innerText = "Processing...";
            document.getElementById('saveBtn').style.display = 'none';
            
            fetch('/start-download', {
                method: 'POST',
                headers: {'Content-Type': 'application/x-www-form-urlencoded'},
                body: 'url=' + encodeURIComponent(url)
            }).then(res => res.json()).then(data => {
                if(data.task_id) {
                    trackProgress(data.task_id);
                }
            });
        });

        function trackProgress(taskId) {
            const interval = setInterval(() => {
                fetch('/progress/' + taskId).then(res => res.json()).then(data => {
                    document.getElementById('statusText').innerText = "Status: " + data.status;
                    document.getElementById('percentText').innerText = data.percent;
                    document.getElementById('progressBar').style.width = data.percent;
                    document.getElementById('downloadedText').innerText = "Downloaded: " + data.downloaded;
                    document.getElementById('speedText').innerText = "Speed: " + data.speed;

                    if(data.status === 'Completed') {
                        clearInterval(interval);
                        document.getElementById('submitBtn').innerText = "↓ DOWNLOAD NOW";
                        const saveBtn = document.getElementById('saveBtn');
                        saveBtn.href = '/download-file?file=' + encodeURIComponent(data.filename);
                        saveBtn.style.display = 'block';
                    } else if(data.status === 'Error') {
                        clearInterval(interval);
                        document.getElementById('submitBtn').innerText = "↓ DOWNLOAD NOW";
                        alert("Download Failed! Check link or try another video.");
                    }
                });
            }, 800);
        }
    </script>
</body>
</html>
"""

def progress_hook(d):
    task_id = d.get('task_id')
    if task_id in download_progress:
        if d['status'] == 'downloading':
            download_progress[task_id]['status'] = 'Downloading (Turbo)'
            download_progress[task_id]['percent'] = d.get('_percent_str', '0%').strip()
            download_progress[task_id]['downloaded'] = d.get('_downloaded_bytes_str', '0 MB')
            download_progress[task_id]['speed'] = d.get('_speed_str', '-- MB/s')
        elif d['status'] == 'finished':
            download_progress[task_id]['status'] = 'Finalizing'
            download_progress[task_id]['percent'] = '100%'

def background_download(url, task_id):
    os.makedirs('downloads', exist_ok=True)
    
    # Fast format option to prevent slow merging loops
    ydl_opts = {
        'outtmpl': 'downloads/%(id)s.%(ext)s',
        'format': 'best[ext=mp4]/best',
    }

    def hook_wrapper(d):
        d['task_id'] = task_id
        progress_hook(d)

    ydl_opts['progress_hooks'] = [hook_wrapper]

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            download_progress[task_id]['filename'] = filename
            download_progress[task_id]['status'] = 'Completed'
            download_progress[task_id]['percent'] = '100%'
    except Exception as e:
        print("Error:", e)
        download_progress[task_id]['status'] = 'Error'

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/start-download', methods=['POST'])
def start_download():
    url = request.form.get('url')
    task_id = str(time.time())
    
    download_progress[task_id] = {
        'status': 'Starting',
        'percent': '0%',
        'downloaded': '0 MB',
        'speed': '-- MB/s',
        'filename': ''
    }
    
    t = threading.Thread(target=background_download, args=(url, task_id))
    t.start()
    
    return jsonify({'task_id': task_id})

@app.route('/progress/<task_id>')
def get_progress(task_id):
    if task_id in download_progress:
        return jsonify(download_progress[task_id])
    return jsonify({'status': 'Not Found'})

@app.route('/download-file')
def download_file():
    file_path = request.args.get('file')
    if file_path and os.path.exists(file_path):
        # as_attachment=True forces Chrome to save it into phone download history
        return send_file(file_path, as_attachment=True)
    return "File not found", 404

if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)

