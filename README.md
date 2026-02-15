# Video Downloader

เว็บแอปพลิเคชันสำหรับดาวน์โหลดวิดีโอจาก Instagram และ YouTube

## คุณสมบัติ
- ดาวน์โหลดวิดีโอจาก Instagram (ต้องใช้ cookies)
- ดาวน์โหลดวิดีโอและเสียงจาก YouTube
- รองรับหลายคุณภาพ (720p, 1080p, 4K)
- ดาวน์โหลดเสียงอย่างเดียวเป็น MP3

## การติดตั้งและรันในเครื่อง

```bash
pip install -r requirements.txt
python app.py
```

เปิดเบราว์เซอร์ที่ http://localhost:5000

## Deploy บน Render

### วิธีที่ 1: ใช้ Dashboard (แนะนำ)

1. สร้างบัญชีที่ [Render.com](https://render.com)
2. คลิก "New +" และเลือก "Web Service"
3. เชื่อมต่อ GitHub repository ของคุณ
4. ตั้งค่าดังนี้:
   - **Name**: ชื่อที่คุณต้องการ
   - **Environment**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app`
5. คลิก "Create Web Service"

### วิธีที่ 2: ใช้ render.yaml

1. Push โค้ดขึ้น GitHub
2. ใน Render Dashboard เลือก "New +" > "Blueprint"
3. เชื่อมต่อ repository ที่มีไฟล์ `render.yaml`
4. Render จะอ่าน config จากไฟล์อัตโนมัติ

## หมายเหตุ

- Render Free Tier จะ sleep หลังไม่มีการใช้งาน 15 นาที
- การเปิดครั้งแรกหลัง sleep อาจใช้เวลา 30-60 วินาที
- สำหรับ Instagram ต้องอัปโหลด cookies ทุกครั้งที่ใช้งาน