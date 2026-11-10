# DC Circuit Calculator

โปรแกรมสำหรับคำนวณกระแสไฟฟ้าในวงจรตัวต้านทานด้วยกฎของโอห์ม
และคำนวณกำลังไฟฟ้าที่เกิดขึ้นในวงจร เพื่อช่วยวิเคราะห์วงจร DC เบื้องต้น

## BJT Common-Emitter DC Bias web app (ENG29 2121)

แอป Flask คำนวณจุดทำงานกระแสตรงของอัดยิ่งไบโพolar แบบ common-emitter
ที่ใช้วงจรแบ่งแรงดัน ป้อนค่า VCC, R1, R2, RC, RE, β, VBE แล้วดูผลกับ
หน่วย ตรวจสอบค่าที่ป้อน แจ้งเตือนเมื่ออยู่นอกภูมิภาค active และเทียบ
ผลกับการคำนวณอิสระโดยวิธีโหนด (nodal analysis)

### Run

วิธีง่ายสุด (Windows): ดับเบิลคลิก `run.bat` แล้วเปิด
http://127.0.0.1:5000/ ในเบราว์เซอร์ (ปิดหน้าต่าง terminal เมื่อเลิกใช้)

หรือรันใน terminal:

```
python -m pip install -r requirements.txt
python app.py
```

เปิด http://127.0.0.1:5000/

เปลี่ยนพอร์ตหรือให้เครื่องอื่นใน LAN เข้าถึงได้:

```
set PORT=5001
set HOST=0.0.0.0
python app.py
```

### ให้เพื่อนเปิดด้วย

**A. เพื่อนอยู่ Wi-Fi / ฮอตสปอตเดียวกัน**

1. ดับเบิลคลิก `run_lan.bat` (ถ้าเคยรัน `run.bat` อยู่ ให้ปิดก่อน)
2. ดูบรรทัด `Network: http://<เลขไอพี>:5000/` แล้วส่งลิงก์นั้นให้เพื่อน
3. ถ้าเพื่อนเปิดไม่ได้ ให้อนุญาต Python ผ่าน Firewall — เปิด PowerShell
   แบบ Run as administrator แล้วรัน:

   ```
   New-NetFirewallRule -DisplayName "BJT Bias App 5000" -Direction Inbound -Protocol TCP -LocalPort 5000 -Action Allow -Profile Private,Public
   ```

4. ฮอตสปอตบางตัว (โดยเฉพาะ iPhone) ปิดการเชื่อมต่อระหว่างเครื่องไว้
   ถ้าเพื่อนยังเข้าไม่ได้ ให้ใช้วิธี B

**B. เพื่อนอยู่นอกเครือข่าย (เปิดได้จากที่ไหนก็ได้)**

ต้องมี Cloudflare Tunnel (ติดตั้งครั้งเดียว):

```
winget install --id Cloudflare.cloudflared
cloudflared tunnel --url http://127.0.0.1:5000
```

แล้วส่งลิงก์ `https://....trycloudflare.com` ที่ cloudflared พิมพ์ออกมาให้เพื่อน
(ใช้ได้เฉพาะตอนที่ทั้ง `run.bat` และ tunnel เปิดอยู่; กด Ctrl+C เพื่อปิด)

ข้อควรระวัง: ลิงก์นี้เป็น public — ใครมีลิงก์ก็เข้าได้ระหว่างที่ยังเปิดอยู่

### ถ้าเปิดเว็บไม่ได้

- ต้องรัน `run.bat` หรือ `python app.py` ค้างไว้ก่อน อย่าปิดหน้าต่าง terminal
  ระหว่างใช้งาน
- ใช้ `http://127.0.0.1:5000/` (ไม่ใช่ `https://`) — ถ้า `localhost` ไม่ขึ้น
  ให้ใช้ `127.0.0.1` แทน
- ถ้าเจอ `Address already in use` แปลว่ามีเซิร์ฟเวอร์รันอยู่แล้ว ให้เปิด
  http://127.0.0.1:5000/ ได้เลย หรือเปลี่ยนพอร์ต:
  `set PORT=5001 && python app.py`
- เปิดจากมือถือ/เครื่องอื่นในวง LAN ให้ใช้ URL บรรทัด `Network:` ที่พิมพ์ตอน
  สตาร์ท และอนุญาต Python ผ่าน Windows Firewall

### Test

```
python -m unittest discover -s tests -t . -v
```
