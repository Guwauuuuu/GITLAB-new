# DC Circuit Calculator

โปรแกรมสำหรับคำนวณกระแสไฟฟ้าในวงจรตัวต้านทานด้วยกฎของโอห์ม
และคำนวณกำลังไฟฟ้าที่เกิดขึ้นในวงจร เพื่อช่วยวิเคราะห์วงจร DC เบื้องต้น

## BJT Common-Emitter DC Bias web app (ENG29 2121)

แอป Flask คำนวณจุดทำงานกระแสตรงของทรานซิสเตอร์ไบโพลาร์แบบ common-emitter
ที่ใช้วงจรแบ่งแรงดัน ป้อนค่า VCC, R1, R2, RC, RE, β, VBE แล้วดูผลกับ
หน่วย ตรวจสอบค่าที่ป้อน แจ้งเตือนเมื่ออยู่นอกภูมิภาค active และเทียบ
ผลกับการคำนวณอิสระโดยวิธีโหนด (nodal analysis)

รองรับ 3 โหมดแหล่งจ่ายเดียว:

- **Voltage Divider Bias** — ใช้ `R1`, `R2`, `RC`, `RE`
- **Fixed Bias** — ใช้ `RB`, `RC` (emitter ต่อลงกราวด์)
- **Emitter Bias** — ใช้ `RB`, `RC`, `RE`

เลือกโหมดจากปุ่ม **Bias Mode** ในฟอร์ม (ช่องกรอกทั้ง 8 ช่องแสดงตลอดทุกโหมด)

### สิ่งที่ต้องมี (Windows)

- Windows 10/11 (PowerShell หรือ Command Prompt)
- Python 3.10 ขึ้นไป และ `pip`
- ngspice เวอร์ชัน Windows ที่มี `ngspice_con.exe` (ดูหัวข้อถัดไป)
- เบราว์เซอร์รุ่นใหม่ (Chrome/Edge/Firefox)

ตรวจ Python ก่อนเริ่ม:

```powershell
py -3 --version
# ถ้าไม่มี py ให้ใช้:
python --version
```

### ติดตั้งแพ็กเกจ Python

แนะนำให้สร้าง virtual environment ในโฟลเดอร์โปรเจกต์:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

ถ้า PowerShell ไม่ยอมรัน `Activate.ps1` ให้เปิดสิทธิ์เฉพาะหน้าต่างนั้นก่อน:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

หรือใช้ Command Prompt:

```bat
.venv\Scripts\activate.bat
python -m pip install -r requirements.txt
```

`requirements.txt` ระบุ `Flask>=3.0,<4` ส่วน ngspice ไม่ได้ติดตั้งผ่าน `pip`
แอปเรียกโปรแกรม `ngspice_con` ผ่าน `PATH`

### ติดตั้ง ngspice และตรวจสอบ `ngspice_con` ใน PATH

1. ดาวน์โหลด Windows build จากหน้าอย่างเป็นทางการของ ngspice:
   <https://ngspice.sourceforge.io/download.html>
2. แตกไฟล์ไปยังโฟลเดอร์ที่ไม่มีช่องว่าง เช่น `C:\tools\ngspice-47`
   และตรวจว่ามีไฟล์ `C:\tools\ngspice-47\bin\ngspice_con.exe`
3. เพิ่มโฟลเดอร์ `bin` ลง `PATH` ของผู้ใช้ (เปิด terminal ใหม่หลังตั้งค่า):

```powershell
$ngspiceBin = "C:\tools\ngspice-47\bin"
$userPath = [Environment]::GetEnvironmentVariable("Path", "User")
[Environment]::SetEnvironmentVariable("Path", "$userPath;$ngspiceBin", "User")
```

หรือเพิ่มชั่วคราวเฉพาะหน้าต่าง terminal ปัจจุบัน:

```powershell
$env:Path += ";C:\tools\ngspice-47\bin"
```

4. ตรวจสอบว่าคำสั่งชี้ไปที่ ngspice จริง:

```powershell
Get-Command ngspice_con
ngspice_con -v
```

ผลที่ถูกต้องจะแสดงเวอร์ชัน เช่น `ngspice-47` และ path ของ `ngspice_con.exe`
ถ้าไม่พบคำสั่งนี้ แอปจะแสดง engine error และจะไม่สร้างผลลัพธ์ปลอม

> หมายเหตุ: แอปใช้ `ngspice_con` (console build) ไม่ใช่ `ngspice` GUI
> และเรียกเป็น `ngspice_con -b` ใน temporary directory ของแต่ละรอบ

### รันเซิร์ฟเวอร์ Flask

วิธีง่ายสุด (Windows): ดับเบิลคลิก `start_app.bat` — สคริปต์จะติดตั้ง Flask
ให้ถ้ายังไม่มี แล้วเปิดเบราว์เซอร์ให้เอง ให้เปิดหน้าต่าง terminal ค้างไว้
ระหว่างใช้งาน (กด Ctrl+C เพื่อหยุด)

ถ้ามีเซิร์ฟเวอร์รันอยู่แล้ว สคริปต์จะเปิดเบราว์เซอร์ให้ทันทีโดยไม่สตาร์ทซ้ำ
ถ้าพอร์ต 5000 ถูกใช้อยู่ (เช่นโปรแกรมอื่น) จะเลือกพอร์ตว่างถัดไปให้อัตโนมัติ
และพิมพ์ URL ที่ใช้จริงในหน้าต่างนั้น

หรือรันเองใน terminal (หลัง activate venv และติดตั้งแพ็กเกจแล้ว):

```powershell
python app.py
```

ต้องเปิด terminal นี้ค้างไว้ตลอดการใช้งาน แล้วเปิด
<http://127.0.0.1:5000/> ในเบราว์เซอร์

เปลี่ยนพอร์ต ให้เครื่องอื่นใน LAN เข้าถึง หรือให้เบราว์เซอร์เปิดเอง:

```powershell
$env:PORT = "5001"
$env:HOST = "0.0.0.0"
$env:OPEN_BROWSER = "1"
python app.py
```

หรือใช้ Command Prompt:

```bat
set PORT=5001
set HOST=0.0.0.0
set OPEN_BROWSER=1
python app.py
```

### เปิดใช้งานในเบราว์เซอร์

หลังเซิร์ฟเวอร์รันแล้ว เปิดได้ 2 หน้า:

| หน้า | URL | ใช้ทำอะไร |
| --- | --- | --- |
| Lab 3 DC Bias | <http://127.0.0.1:5000/> | คำนวณ V<sub>B</sub>, V<sub>E</sub>, V<sub>C</sub>, V<sub>CE</sub>, I<sub>B</sub>, I<sub>C</sub>, I<sub>E</sub> ด้วยสมการ analytical ของ Lab 3 |
| CE Simulator v1 | <http://127.0.0.1:5000/ce-simulator> | รัน ngspice จริงสำหรับ `.op`, `.ac`, `.tran` และดูผล SPICE แยกจาก analytical reference |

ขั้นตอนใช้งาน CE Simulator:

1. เปิด `/ce-simulator`
2. เลือก **Analysis Mode**: DC Operating Point, AC Frequency Response หรือ Transient
3. ตรวจ/แก้ค่า V<sub>CC</sub>, R1, R2, R<sub>C</sub>, R<sub>E</sub>, R<sub>L</sub>, C<sub>in</sub>, C<sub>out</sub>, source amplitude/frequency
4. กด **Run ngspice Simulation**
5. อ่านผลจาก engine status (`ngspice_con`, model `Q2N2222`) และกราฟ/ตาราง
6. จำไว้ว่า **Real ngspice output** กับการ์ด **Lab 3 analytical reference** เป็นคนละแหล่งข้อมูล

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

> หมายเหตุ: หน้า `/ce-simulator` ใช้ค่าดีฟอลต์ของ **Reference CE Stage**
> โดยตรง ไม่มี dropdown แยกชื่อ “CE Reference” — หากต้องการรันเคสอ้างอิง
> ให้คงค่าเริ่มต้นตามตารางด้านล่าง

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
  `$env:PORT = "5001"; python app.py` (PowerShell) หรือ
  `set PORT=5001 && python app.py` (Command Prompt)
- ถ้าเบราว์เซอร์ไม่เปิดเอง ให้ดูบรรทัด `Local:` ในหน้าต่าง terminal แล้วเปิด
  URL นั้น (ถ้าพอร์ต 5000 ไม่ว่าง URL อาจเป็น 5001, 5002, ...)
- เปิดจากมือถือ/เครื่องอื่นในวง LAN ให้ใช้ URL บรรทัด `Network:` ที่พิมพ์ตอน
  สตาร์ท และอนุญาต Python ผ่าน Windows Firewall

### ตรวจสอบคุณภาพ (Tests)

รันชุดทดสอบทั้งหมดจากโฟลเดอร์โปรเจกต์ (หลัง activate venv):

```powershell
python -m unittest discover -s tests -t . -v
```

ชุดนี้ครอบคลุมสูตร Lab 3, การแปลงหน่วย, โหมด Fixed/Emitter/Divider, route และ API
ของ CE Simulator, การ validate ค่าอินพุต และการเรียก ngspice จริง

ทดสอบสมการไฟฟ้าแบบ regression แยกต่างหาก:

```powershell
python -m unittest test_electrical.py -v
```

ตรวจ syntax ของ JavaScript ฝั่งหน้าเว็บ (ต้องมี Node.js):

```powershell
node --check static/ce_sim.js
```

### หลักฐานการตรวจรับ

- **Lab 3 (A1–A5):** ผลตรวจ DC Bias ผ่าน Browser อยู่ในหัวข้อแรกของ
  [`docs/validation.md`](docs/validation.md)
- **Lab 4 (B1–B8):** ตารางผลตรวจ CE Simulator v1 พร้อม ngspice-47, โมเดล
  Q2N2222, ค่าที่วัดได้จริง และสถานะ PASS อยู่ในไฟล์เดียวกัน
- **ภาพหลักฐาน:** ภาพหน้าจอทุกเคสอยู่ใน [`docs/captures/`](docs/captures/)
  (`b1-*.png` ถึง `b8-mobile-390-ac.png`)
- **กฎแหล่งที่มาของผลลัพธ์:** ดู [`AGENTS.md`](AGENTS.md) — แยกผล ngspice จริง
  ออกจากค่าอ้างอิง analytical ของ Lab 3 อย่างชัดเจน
