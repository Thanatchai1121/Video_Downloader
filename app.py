from flask import Flask, render_template, request, jsonify, send_file, Response
import yt_dlp
from pytubefix import YouTube
from pytubefix.cli import on_progress
import os
import uuid
import tempfile
import shutil
from pathlib import Path
from werkzeug.utils import secure_filename

# Import ffmpeg จาก imageio-ffmpeg
try:
    from imageio_ffmpeg import get_ffmpeg_exe
    FFMPEG_PATH = get_ffmpeg_exe()
except ImportError:
    FFMPEG_PATH = None

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

# ลบ route check-cookie เพราะไม่ใช้แล้ว (เช็คที่ browser แทน)

@app.route('/upload-cookie', methods=['POST'])
def upload_cookie():
    try:
        if 'cookie' not in request.files:
            return jsonify({'error': 'ไม่พบไฟล์'}), 400
        
        platform = request.form.get('platform', 'instagram')
        file = request.files['cookie']
        
        if file.filename == '':
            return jsonify({'error': 'ไม่ได้เลือกไฟล์'}), 400
        
        if not file.filename.endswith('.txt'):
            return jsonify({'error': 'กรุณาอัปโหลดไฟล์ .txt เท่านั้น'}), 400
        
        # อ่านเนื้อหาไฟล์และส่งกลับไปเก็บที่ browser
        cookie_content = file.read().decode('utf-8')
        
        return jsonify({
            'success': True, 
            'message': 'อ่าน Cookies สำเร็จ',
            'platform': platform,
            'content': cookie_content
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/download', methods=['POST'])
def download():
    temp_dir = None
    cookie_file = None
    try:
        data = request.json
        url = data.get('url')
        cookies = data.get('cookies')  # รับ cookies จาก client
        
        if not url:
            return jsonify({'error': 'กรุณาใส่ URL'}), 400
        
        if not cookies:
            return jsonify({'error': 'กรุณาอัปโหลด Instagram Cookies ก่อนใช้งาน'}), 400
        
        # สร้าง temp directory และไฟล์ cookies ชั่วคราว
        temp_dir = tempfile.mkdtemp()
        unique_id = str(uuid.uuid4())[:8]
        cookie_file = os.path.join(temp_dir, f'cookies_{unique_id}.txt')
        
        # เขียน cookies ลงไฟล์ชั่วคราว
        with open(cookie_file, 'w', encoding='utf-8') as f:
            f.write(cookies)
        
        output_path = os.path.join(temp_dir, f'{unique_id}')
        
        ydl_opts = {
            'format': 'best',
            'outtmpl': f'{output_path}.%(ext)s',
            'quiet': False,
            'no_warnings': False,
            'cookiefile': cookie_file,
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            },
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
        
        # หาไฟล์ที่ดาวน์โหลดจริงๆ (อาจมีนามสกุลต่างจากที่คาดไว้)
        if not os.path.exists(filename):
            # ค้นหาไฟล์ที่มี unique_id ใน temp_dir
            downloaded_files = [f for f in os.listdir(temp_dir) if f.startswith(unique_id) and not f.endswith('.txt')]
            if downloaded_files:
                filename = os.path.join(temp_dir, downloaded_files[0])
            else:
                if temp_dir and os.path.exists(temp_dir):
                    shutil.rmtree(temp_dir)
                return jsonify({'error': 'ไม่พบไฟล์ที่ดาวน์โหลด'}), 500
        
        # ส่งไฟล์และลบทันที
        def generate():
            try:
                with open(filename, 'rb') as f:
                    while chunk := f.read(8192):
                        yield chunk
            finally:
                # ลบ temp directory หลังส่งเสร็จ (รวม cookies)
                if temp_dir and os.path.exists(temp_dir):
                    shutil.rmtree(temp_dir)
        
        # สร้าง response พร้อม encode ชื่อไฟล์ให้ถูกต้อง
        from urllib.parse import quote
        title = info.get('title', 'video')
        # ตรวจสอบนามสกุลไฟล์จริง
        file_ext = os.path.splitext(filename)[1] or '.mp4'
        filename_encoded = quote(f"{title}{file_ext}")
        
        # กำหนด mimetype ตามนามสกุลไฟล์
        mimetype = 'video/mp4'
        if file_ext.lower() in ['.jpg', '.jpeg']:
            mimetype = 'image/jpeg'
        elif file_ext.lower() == '.png':
            mimetype = 'image/png'
        
        response = Response(generate(), mimetype=mimetype)
        response.headers['Content-Disposition'] = f"attachment; filename*=UTF-8''{filename_encoded}"
        return response
        
    except Exception as e:
        # ลบ temp directory ถ้าเกิด error
        if temp_dir and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
        return jsonify({'error': str(e)}), 500

# ลบ route /file/<filename> เพราะไม่ใช้แล้ว

@app.route('/youtube-info', methods=['POST'])
def youtube_info():
    try:
        url = request.json.get('url')
        if not url:
            return jsonify({'error': 'กรุณาใส่ URL'}), 400
        
        # ใช้ pytubefix แทน
        yt = YouTube(url, use_oauth=False, allow_oauth_cache=False)
        
        formats = []
        
        # เพิ่มตัวเลือกเสียงอย่างเดียว
        audio_stream = yt.streams.get_audio_only()
        if audio_stream and audio_stream.filesize:
            audio_size_mb = round(audio_stream.filesize / (1024*1024), 1)
            audio_size = f" ({audio_size_mb} MB)"
        else:
            audio_size = ""
        
        formats.append({
            'format_id': 'audio',
            'label': f'🎵 เสียงอย่างเดียว (MP3){audio_size}',
            'ext': 'mp3',
            'has_audio': True,
            'height': 99999  # ให้อยู่บนสุด
        })
        
        # รวบรวมคุณภาพวิดีโอที่มีเสียงในตัว (progressive)
        progressive_qualities = {}
        
        for stream in yt.streams.filter(progressive=True, file_extension='mp4'):
            if stream.resolution:
                height = int(stream.resolution.replace('p', ''))
                if height not in progressive_qualities:
                    progressive_qualities[height] = {
                        'itag': stream.itag,
                        'has_audio': True,
                        'filesize': stream.filesize
                    }
        
        # รวบรวมคุณภาพวิดีโออย่างเดียว (adaptive) - ต้องรวมเสียง
        adaptive_qualities = {}
        
        for stream in yt.streams.filter(progressive=False, file_extension='mp4', type='video'):
            if stream.resolution:
                height = int(stream.resolution.replace('p', ''))
                if height not in progressive_qualities:  # ถ้ายังไม่มีใน progressive
                    adaptive_qualities[height] = {
                        'itag': stream.itag,
                        'has_audio': False,
                        'filesize': stream.filesize
                    }
        
        print(f"\n=== DEBUG: PyTubeFix Qualities ===")
        print(f"Progressive (มีเสียง): {sorted(progressive_qualities.keys())}")
        print(f"Adaptive (ไม่มีเสียง): {sorted(adaptive_qualities.keys())}")
        print("=== END DEBUG ===\n")
        
        # เพิ่มตัวเลือกที่มีเสียงก่อน (progressive)
        for height in progressive_qualities.keys():
            label = f"{height}p"
            if height >= 2160:
                label += " (4K)"
            elif height >= 1440:
                label += " (2K)"
            elif height >= 1080:
                label += " (Full HD)"
            elif height >= 720:
                label += " (HD)"
            
            # แสดงขนาดไฟล์จริงจาก YouTube metadata
            filesize = progressive_qualities[height].get('filesize')
            if filesize:
                size_mb = round(filesize / (1024*1024), 1)
                size_str = f" ({size_mb} MB)"
            else:
                size_str = ""
            
            formats.append({
                'format_id': str(progressive_qualities[height]['itag']),
                'label': f"📹 {label}{size_str}",
                'height': height,
                'has_audio': True
            })
        
        # เพิ่มตัวเลือกคุณภาพสูง (adaptive) - รวมเสียงอัตโนมัติ
        for height in adaptive_qualities.keys():
            label = f"{height}p"
            if height >= 2160:
                label += " (4K)"
            elif height >= 1440:
                label += " (2K)"
            elif height >= 1080:
                label += " (Full HD)"
            elif height >= 720:
                label += " (HD)"
            
            # คำนวณขนาดรวม (วิดีโอ + เสียง) จาก metadata จริง
            video_size = adaptive_qualities[height].get('filesize', 0)
            audio_size = audio_stream.filesize if audio_stream and audio_stream.filesize else 0
            
            if video_size and audio_size:
                total_size_mb = round((video_size + audio_size) / (1024*1024), 1)
                size_str = f" ({total_size_mb} MB)"
            elif video_size:
                size_mb = round(video_size / (1024*1024), 1)
                size_str = f" (~{size_mb} MB)"
            else:
                size_str = ""
            
            formats.append({
                'format_id': str(adaptive_qualities[height]['itag']),
                'label': f"📹 {label}{size_str}",
                'height': height,
                'has_audio': False
            })
        
        # เรียงตาม height จากสูงไปต่ำ
        formats.sort(key=lambda x: x['height'], reverse=True)
        
        return jsonify({
            'success': True,
            'title': yt.title,
            'formats': formats
        })
            
    except Exception as e:
        print(f"\n=== ERROR ===")
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        print("=== END ERROR ===\n")
        return jsonify({'error': str(e)}), 500

@app.route('/youtube-download', methods=['POST'])
def youtube_download():
    temp_dir = None
    try:
        url = request.json.get('url')
        format_id = request.json.get('format_id')
        
        if not url or not format_id:
            return jsonify({'error': 'ข้อมูลไม่ครบถ้วน'}), 400
        
        # สร้าง temp directory
        temp_dir = tempfile.mkdtemp()
        unique_id = str(uuid.uuid4())[:8]
        
        # ใช้ pytubefix
        yt = YouTube(url, use_oauth=False, allow_oauth_cache=False)
        
        if format_id == 'audio':
            # ดาวน์โหลดเสียงอย่างเดียว
            stream = yt.streams.get_audio_only()
            output_file = stream.download(
                output_path=temp_dir,
                filename=f'{unique_id}.mp3'
            )
            mimetype = 'audio/mpeg'
            ext = 'mp3'
        else:
            # ดาวน์โหลดวิดีโอ
            itag = int(format_id)
            stream = yt.streams.get_by_itag(itag)
            
            if not stream:
                if temp_dir and os.path.exists(temp_dir):
                    shutil.rmtree(temp_dir)
                return jsonify({'error': 'ไม่พบ stream ที่เลือก'}), 400
            
            # ตรวจสอบว่ามีเสียงในตัวหรือไม่
            if stream.is_progressive:
                # มีเสียงในตัวแล้ว ดาวน์โหลดเลย
                output_file = stream.download(
                    output_path=temp_dir,
                    filename=f'{unique_id}.mp4'
                )
            else:
                # ไม่มีเสียง ต้องรวมกับเสียง
                audio_stream = yt.streams.get_audio_only()
                
                # ดาวน์โหลดวิดีโอและเสียงแยกกัน
                video_file = stream.download(
                    output_path=temp_dir,
                    filename=f'{unique_id}_video.mp4'
                )
                audio_file = audio_stream.download(
                    output_path=temp_dir,
                    filename=f'{unique_id}_audio.mp4'
                )
                
                # รวมวิดีโอและเสียง (ต้องมี ffmpeg)
                output_file = os.path.join(temp_dir, f'{unique_id}.mp4')
                
                # ใช้ ffmpeg จาก imageio-ffmpeg
                if FFMPEG_PATH:
                    try:
                        import subprocess
                        subprocess.run([
                            FFMPEG_PATH, '-i', video_file, '-i', audio_file,
                            '-c:v', 'copy', '-c:a', 'aac', output_file, '-y'
                        ], check=True, capture_output=True, text=True)
                        
                        # ลบไฟล์ชั่วคราว
                        os.remove(video_file)
                        os.remove(audio_file)
                    except:
                        # ffmpeg error - ใช้ไฟล์วิดีโออย่างเดียว
                        os.remove(audio_file)
                        output_file = video_file
                else:
                    # ไม่มี ffmpeg
                    os.remove(audio_file)
                    output_file = video_file
            
            mimetype = 'video/mp4'
            ext = 'mp4'
        
        # ส่งไฟล์และลบทันที
        def generate():
            try:
                with open(output_file, 'rb') as f:
                    while chunk := f.read(8192):
                        yield chunk
            finally:
                if temp_dir and os.path.exists(temp_dir):
                    shutil.rmtree(temp_dir)
        
        # สร้าง response พร้อม encode ชื่อไฟล์ให้ถูกต้อง
        from urllib.parse import quote
        filename_encoded = quote(f"{yt.title}.{ext}")
        
        response = Response(generate(), mimetype=mimetype)
        response.headers['Content-Disposition'] = f"attachment; filename*=UTF-8''{filename_encoded}"
        return response
        
    except Exception as e:
        if temp_dir and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
        print(f"Download error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)
