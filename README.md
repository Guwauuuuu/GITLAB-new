# DC Circuit Calculator

โปรแกรมสำหรับคำนวณกระแสไฟฟ้าในวงจรตัวต้านทานด้วยกฎของโอห์ม
และคำนวณกำลังไฟฟ้าที่เกิดขึ้นในวงจร เพื่อช่วยวิเคราะห์วงจร DC เบื้องต้น

## BJT Common-Emitter DC Bias web app (ENG29 2121)

แอป Flask คำนวณจุดทำงานกระแสตรงของอัดยิ่งไบโพolar แบบ common-emitter
ที่ใช้วงจรแบ่งแรงดัน ป้อนค่า VCC, R1, R2, RC, RE, β, VBE แล้วดูผลกับ
หน่วย ตรวจสอบค่าที่ป้อน แจ้งเตือนเมื่ออยู่นอกภูมิภาค active และเทียบ
ผลกับการคำนวณอิสระโดยวิธีโหนด (nodal analysis)

รองรับ 3 โหมดแหล่งจ่ายเดียว:

- **Voltage Divider Bias** — ใช้ `R1`, `R2`, `RC`, `RE`
- **Fixed Bias** — ใช้ `RB`, `RC` (emitter ต่อลงกราวด์)
- **Emitter Bias** — ใช้ `RB`, `RC`, `RE`

เลือกโหมดจากปุ่ม **Bias Mode** ในฟอร์ม (ช่องกรอกทั้ง 8 ช่องแสดงตลอดทุกโหมด)

### ติดตั้งแพ็กเกจ

ต้องมี Python 3.10 ขึ้นไป และ `pip` ใช้ได้

```powershell
python -m pip install -r requirements.txt
```

ไฟล์ `requirements.txt` ระบุแพ็กเกจที่ต้องใช้ (Flask) — ถ้าติดตั้งใหม่ทั้งเครื่อง
แนะนำให้สร้าง virtual environment ก่อน:

```powershell
python -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
```

### รันเซิร์ฟเวอร์ Flask

วิธีง่ายสุด (Windows): ดับเบิลคลิก `start_app.bat` — เบราว์เซอร์จะเปิดเอง
และให้เปิดหน้าต่าง terminal ค้างไว้ระหว่างใช้งาน (กด Ctrl+C เพื่อหยุด)

ถ้ามีเซิร์ฟเวอร์รันอยู่แล้ว สคริปต์จะเปิดเบราว์เซอร์ให้ทันทีโดยไม่สตาร์ทซ้ำ
ถ้าพอร์ต 5000 ถูกใช้อยู่ (เช่นโปรแกรมอื่น) จะเลือกพอร์ตว่างถัดไปให้อัตโนมัติ
และพิมพ์ URL ที่ใช้จริงในหน้าต่างนั้น

หรือรันใน terminal (หลังติดตั้งแพ็กเกจแล้ว):

```
python app.py
```

ต้องเปิด terminal นี้ค้างไว้ตลอดการใช้งาน และเปิด http://127.0.0.1:5000/

เปลี่ยนพอร์ตหรือให้เครื่องอื่นใน LAN เข้าถึงได้:

```
set PORT=5001
set HOST=0.0.0.0
python app.py
```

### วิธีใช้งาน 3 โหมด

1. เปิด http://127.0.0.1:5000/ แล้วเลือกโหมดจากปุ่ม **Bias Mode**
2. กรอกค่ากลางที่ใช้ร่วมทุกโหมด: V<sub>CC</sub>, R<sub>C</sub>, β, V<sub>BE</sub>
3. กรอกค่าตัวต้านทานของโหมดนั้น แล้วเลือกหน่วย `Ω`, `kΩ` หรือ `MΩ` ให้ตรงกับค่าที่กรอก
4. กด **Calculate DC Bias**
5. อ่านผล V<sub>B</sub>, V<sub>E</sub>, V<sub>C</sub>, V<sub>CE</sub>, I<sub>B</sub>, I<sub>C</sub>, I<sub>E</sub>

| โหมด | ช่องที่ใช้คำนวณ | หมายเหตุ |
| --- | --- | --- |
| **Voltage Divider Bias** | R1, R2, R<sub>C</sub>, R<sub>E</sub> | ค่าเริ่มต้นของแอป, มี Thevenin equivalent และตรวจสอบไขว้ด้วย nodal analysis |
| **Fixed Bias** | R<sub>B</sub>, R<sub>C</sub> | emitter ต่อลงกราวด์ (V<sub>E</sub> = 0), ไม่ต้องกรอก R<sub>E</sub> |
| **Emitter Bias** | R<sub>B</sub>, R<sub>C</sub>, R<sub>E</sub> | มี R<sub>E</sub> ต่อลงกราวด์ ทำให้ไบแอสเสถียรกว่า Fixed Bias |

ข้อควรรู้:

- ฟอร์มแสดงช่องกรอกครบทั้ง 8 ช่องทุกโหมด ช่องที่โหมดนั้นไม่ใช้จะถูกมองข้าม (ไม่ถูกตรวจค่า) เช่น R<sub>E</sub> ในโหมด Fixed Bias
- หน่วย `kΩ` และ `MΩ` จะถูกแปลงเป็น `Ω` ก่อนเข้าสมการ (เช่น 100 kΩ = 100000 Ω, 1 MΩ = 1000000 Ω)
- β ต้องมีค่าอย่างน้อย 1, ตัวต้านทานและ V<sub>CC</sub> ต้องมากกว่า 0 และ V<sub>BE</sub> ต้องน้อยกว่า V<sub>CC</sub>
- ถ้าค่าไม่ถูกต้อง หน้าเว็บจะแสดงข้อความแจ้งเตือนและคงค่าที่กรอกไว้ให้แก้
- ผลลัพธ์จะบอกภูมิภาคการทำงาน: active / saturation / cutoff

### Common-Emitter Amplifier Simulator (ngspice)

หน้า `/ce-simulator` ต่อยอดจาก Lab 3 โดยรัน **ngspice จริง** ผ่าน
`ngspice_con -b` สำหรับวงจร common-emitter แบบ voltage-divider bias ที่มี
`RE` ต่อลงกราวด์โดยไม่ขนาน bypass capacitor พร้อม `Cin`, `Cout` และ `RL`

ต้องติดตั้ง ngspice และมี `ngspice_con` อยู่ใน `PATH` ก่อนใช้งาน
(ตรวจด้วยคำสั่ง `ngspice_con -v`)

ค่าเริ่มต้นของวงจรอ้างอิง:

| พารามิเตอร์ | ค่าเริ่มต้น |
| --- | --- |
| V<sub>CC</sub> | 12 V |
| R1 / R2 | 100 kΩ / 22 kΩ |
| R<sub>C</sub> / R<sub>E</sub> | 2.2 kΩ / 1 kΩ (ไม่ bypass) |
| R<sub>L</sub> | 10 kΩ |
| C<sub>in</sub> / C<sub>out</sub> | 10 µF / 10 µF |
| แหล่งสัญญาณ | 10 mV peak, 1 kHz sine |
| โมเดล BJT | Q2N2222 (Gummel-Poon ของ ngspice) |

โหมดการวิเคราะห์:

- **DC Operating Point (`.op`)** — ค่า V<sub>B</sub>, V<sub>E</sub>, V<sub>C</sub>,
  V<sub>CE</sub>, I<sub>B</sub>, I<sub>C</sub> จาก SPICE พร้อมสถานะ
  active / saturation / cutoff
- **AC Frequency Response (`.ac`)** — กวาดความถี่ 10 Hz ถึง 10 MHz
  พล็อต Gain Magnitude (dB) และ Phase (องศา) โดย `Vin` อ้างอิงคือแหล่งจ่าย
  AC 1 V ที่โหนดก่อน `Cin` (จึงได้ |Vout/Vin| โดยตรง)
- **Transient (`.tran`)** — จำลอง SIN source ที่ปรับแอมพลิจูดและความถี่ได้
  พล็อต Vin(t) และ Vout(t) ให้เห็นการกลับเฟส 180°

ผลจาก SPICE จะแสดงแยกจาก **ค่าอ้างอิงเชิงวิเคราะห์ของ Lab 3** (`bjt.py`)
อย่างชัดเจน โดยค่าอ้างอิงใช้ β/V<sub>BE</sub> ที่กรอกในฟอร์ม ไม่ใช่โมเดล
Q2N2222 ของ SPICE

ทุกครั้งที่รัน ระบบจะล้างกราฟและผลลัพธ์เดิมก่อน แล้วแสดงสถานะ
Running → Success/Error พร้อมชื่อ engine และโมเดล หาก ngspice ผิดพลาด,
timeout, หรือผลลัพธ์มีค่า NaN/Inf ระบบจะรายงาน error ตามจริงและไม่วาดกราฟ
หลอก ค่าที่ไม่ถูกต้อง เช่น R<sub>E</sub> = 0 จะถูกปฏิเสธก่อนเรียก ngspice

### ถ้าเปิดเว็บไม่ได้

- ต้องรัน `start_app.bat` หรือ `python app.py` ค้างไว้ก่อน อย่าปิดหน้าต่าง terminal
  ระหว่างใช้งาน
- ใช้ `http://127.0.0.1:5000/` (ไม่ใช่ `https://`) — ถ้า `localhost` ไม่ขึ้น
  ให้ใช้ `127.0.0.1` แทน
- ถ้าเจอ `Address already in use` แปลว่ามีเซิร์ฟเวอร์รันอยู่แล้ว ให้เปิด
  http://127.0.0.1:5000/ ได้เลย หรือเปลี่ยนพอร์ต:
  `set PORT=5001 && python app.py`
- ถ้าเบราว์เซอร์ไม่เปิดเอง ให้ดูบรรทัด `Local:` ในหน้าต่าง terminal แล้วเปิด
  URL นั้น (ถ้าพอร์ต 5000 ไม่ว่าง URL อาจเป็น 5001, 5002, ...)
- เปิดจากมือถือ/เครื่องอื่นในวง LAN ให้ใช้ URL บรรทัด `Network:` ที่พิมพ์ตอน
  สตาร์ท และอนุญาต Python ผ่าน Windows Firewall

### Test

```
python -m unittest discover -s tests -t . -v
```

ผลตรวจรับผ่าน Browser (ตาราง A1–A5) ดูได้ที่ [`docs/validation.md`](docs/validation.md)
