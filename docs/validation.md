# ผลตรวจรับ (Validation) — BJT DC Bias Web App

**วันที่ตรวจ:** 2026-11-17
**เว็บที่ตรวจ:** http://127.0.0.1:5000/
**วิธีตรวจ:** Playwright MCP (Browser automation)
**ผู้ตรวจ:** ทีมพัฒนา (ตรวจผ่าน Browser เท่านั้น ไม่ได้ใช้ `curl` และไม่ได้อ่านโค้ดเพื่อเป็นค่าอ้างอิง)

## เกณฑ์ Tolerance ของกลุ่ม

| ปริมาณ | ยอมรับได้ |
| --- | --- |
| I<sub>C</sub> | ต่างไม่เกิน ±0.01 mA |
| V<sub>CE</sub> | ต่างไม่เกิน ±0.02 V |

## ค่ากลางที่ใช้ทุกกรณี

V<sub>CC</sub> = 12 V, R<sub>C</sub> = 2.2 kΩ, β = 100, V<sub>BE</sub> = 0.70 V

## เครื่องมือและลำดับขั้นที่ใช้

1. `browser_navigate` → เปิด `http://127.0.0.1:5000/`
2. `browser_snapshot` → อ่านฟอร์มและเก็บ `ref` ของช่องอินพุต
3. `browser_select_option` → เลือก Bias Mode (เฉพาะโหมดที่ไม่ใช่ค่าเริ่มต้น)
4. `browser_snapshot` → ยืนยันโหมดที่ถูกเลือกจริง
5. `browser_fill_form` → กรอกค่าตามหน่วยบนฟอร์ม (Ω / kΩ)
6. `browser_click` → กดปุ่ม `Calculate DC Bias`
7. `browser_snapshot` → อ่านหน้าผลลัพธ์ใหม่ทุกครั้ง (ไม่ใช้ snapshot รอบก่อนเป็นผลของรอบถัดไป)
8. `browser_network_requests` → ตรวจ HTTP status (ใช้กับกรณี A5)

## ตารางผลตรวจ A1–A5

| ID | วิธีตรวจ | อินพุต (ตามหน่วยบนฟอร์ม) | ค่าคาดหมาย | ผลที่เห็นพร้อมหน่วย | สถานะ | หลักฐาน |
| --- | --- | --- | --- | --- | --- | --- |
| A1 | Playwright MCP: navigate → snapshot → fill_form → click → snapshot ใหม่ | Mode = Voltage Divider<br>V<sub>CC</sub> = 12 V<br>R1 = 100 kΩ<br>R2 = 22 kΩ<br>R<sub>C</sub> = 2.2 kΩ<br>R<sub>E</sub> = 1 kΩ<br>β = 100<br>V<sub>BE</sub> = 0.70 V | I<sub>C</sub> = 1.23 mA<br>V<sub>CE</sub> = 8.05 V | I<sub>C</sub> = **1.23 mA**<br>V<sub>CE</sub> = **8.052 V**<br>V<sub>B</sub> = 1.942 V<br>V<sub>E</sub> = 1.242 V<br>V<sub>C</sub> = 9.294 V<br>I<sub>B</sub> = 12.3 µA<br>I<sub>E</sub> = 1.24 mA | **PASS**<br>ΔI<sub>C</sub> = 0.00 mA<br>ΔV<sub>CE</sub> = 0.002 V | POST `/calculate` = 200 OK<br>snapshot: `rowheader "IC"` → cell `1.23 mA` (f3e133), `rowheader "VCE"` → cell `8.052 V` (f3e125)<br>Thevenin: V<sub>BB</sub> = 2.164 V, R<sub>B</sub> = 18.03 kΩ<br>nodal check: ✓ 8.052 V vs 8.052 V |
| A2 | Playwright MCP: navigate → snapshot → select_option `Fixed Bias` → snapshot → fill_form (ไม่กรอก R<sub>E</sub>) → click → snapshot ใหม่ | Mode = Fixed Bias<br>V<sub>CC</sub> = 12 V<br>R<sub>B</sub> = 1000 kΩ (1 MΩ)<br>R<sub>C</sub> = 2.2 kΩ<br>β = 100<br>V<sub>BE</sub> = 0.70 V | I<sub>C</sub> = 1.13 mA<br>V<sub>CE</sub> = 9.51 V | I<sub>C</sub> = **1.13 mA**<br>V<sub>CE</sub> = **9.514 V**<br>V<sub>B</sub> = 0.700 V<br>V<sub>E</sub> = 0.000 V<br>V<sub>C</sub> = 9.514 V<br>I<sub>B</sub> = 11.3 µA<br>I<sub>E</sub> = 1.14 mA | **PASS**<br>ΔI<sub>C</sub> = 0.00 mA<br>ΔV<sub>CE</sub> = 0.004 V | หลังเลือกโหมด snapshot แสดง `option "Fixed Bias" [selected]`<br>snapshot ผล: `rowheader "IC"` → cell `1.13 mA` (f5e136), `rowheader "VCE"` → cell `9.514 V` (f5e128)<br>หมายเหตุบนหน้า: “Fixed bias: R<sub>B</sub> from V<sub>CC</sub> to base, emitter grounded.” |
| A3 | Playwright MCP: navigate → snapshot → select_option `Emitter Bias` → snapshot → fill_form → click → snapshot ใหม่ | Mode = Emitter Bias<br>V<sub>CC</sub> = 12 V<br>R<sub>B</sub> = 1000 kΩ<br>R<sub>C</sub> = 2.2 kΩ<br>R<sub>E</sub> = 1 kΩ<br>β = 100<br>V<sub>BE</sub> = 0.70 V | I<sub>C</sub> = 1.03 mA<br>V<sub>CE</sub> = 8.71 V | I<sub>C</sub> = **1.03 mA**<br>V<sub>CE</sub> = **8.705 V**<br>V<sub>B</sub> = 1.737 V<br>V<sub>E</sub> = 1.037 V<br>V<sub>C</sub> = 9.742 V<br>I<sub>B</sub> = 10.3 µA<br>I<sub>E</sub> = 1.04 mA | **PASS**<br>ΔI<sub>C</sub> = 0.00 mA<br>ΔV<sub>CE</sub> = 0.005 V | snapshot แสดง `option "Emitter Bias" [selected]`<br>`rowheader "IC"` → cell `1.03 mA` (f7e137), `rowheader "VCE"` → cell `8.705 V` (f7e129)<br>หมายเหตุบนหน้า: “Emitter bias: R<sub>B</sub> from V<sub>CC</sub> to base, R<sub>E</sub> to ground.” |
| A4 | Playwright MCP: navigate → snapshot → select_option `Emitter Bias` → snapshot → fill_form (R<sub>E</sub> = 2 kΩ) → click → snapshot ใหม่ | Mode = Emitter Bias<br>V<sub>CC</sub> = 12 V<br>R<sub>B</sub> = 1000 kΩ<br>R<sub>C</sub> = 2.2 kΩ<br>R<sub>E</sub> = **2 kΩ**<br>β = 100<br>V<sub>BE</sub> = 0.70 V | I<sub>C</sub> ลดจาก A3 เหลือ 0.94 mA<br>V<sub>CE</sub> = 8.03 V | I<sub>C</sub> = **0.94 mA** (ลดจาก A3 = 1.03 mA)<br>V<sub>CE</sub> = **8.033 V**<br>V<sub>B</sub> = 2.599 V<br>V<sub>E</sub> = 1.899 V<br>V<sub>C</sub> = 9.932 V<br>I<sub>B</sub> = 9.4 µA<br>I<sub>E</sub> = 0.95 mA | **PASS**<br>ΔI<sub>C</sub> = 0.00 mA<br>ΔV<sub>CE</sub> = 0.003 V<br>ทิศทาง: ลดลงตามคาด | snapshot แสดง `option "Emitter Bias" [selected]`<br>`rowheader "IC"` → cell `0.94 mA`, `rowheader "VCE"` → cell `8.033 V`<br>เทียบกับ A3: 1.03 mA → 0.94 mA |
| A5 | Playwright MCP: navigate → snapshot → select_option `Fixed Bias` → snapshot → fill_form ค่าถูกต้อง → click → snapshot (ยืนยันว่ามีผลก่อน) → fill_form `R_B = 0` → click → snapshot ใหม่ + network log | Mode = Fixed Bias<br>V<sub>CC</sub> = 12 V<br>R<sub>B</sub> = **0** (kΩ)<br>R<sub>C</sub> = 2.2 kΩ<br>β = 100<br>V<sub>BE</sub> = 0.70 V | แจ้งเตือนให้แก้ R<sub>B</sub><br>เว็บไม่ล่ม<br>ไม่แสดงผลเดิมค้าง | alert: **“RB must be greater than 0”**<br>ไม่มีตารางผลลัพธ์ (ไม่มี row V<sub>B</sub>/V<sub>E</sub>/V<sub>C</sub>/V<sub>CE</sub>/I<sub>B</sub>/I<sub>C</sub>/I<sub>E</sub>)<br>ค่าที่กรอกยังคงอยู่ (R<sub>B</sub> = `0`)<br>POST ตอบ **400 BAD REQUEST** (ไม่ใช่ 500) | **PASS** | ก่อนส่งค่าผิด: มีผลจริง I<sub>C</sub> = 1.13 mA, V<sub>CE</sub> = 9.514 V<br>หลังส่ง R<sub>B</sub> = 0: snapshot มี `alert` (f12e20) = “RB must be greater than 0”, ไม่พบแถวผลลัพธ์ และไม่พบข้อความ `1.13 mA` / `9.514 V`<br>`browser_network_requests`: `[POST] http://127.0.0.1:5000/calculate => [400] BAD REQUEST` |

## สรุปผล

- ผ่านครบ **5/5 เคส** (A1–A5)
- A1 ตรงกับค่าอ้างอิงของ Lab 2 (I<sub>C</sub> = 1.23 mA, V<sub>CE</sub> = 8.05 V)
- A5 ตรวจแล้วว่าไม่มีผลลัพธ์เดิมค้างหลังส่งค่าผิด และเซิร์ฟเวอร์ตอบ 400 โดยไม่ crash
- ทุกค่าที่รายงานอ่านจาก snapshot หลังการ submit ของเคสนั้น ๆ (ไม่ใช้ผลรอบก่อนหน้า)

## ข้อสังเกต

- หน้าแรกของแอปมี console error 1 รายการตอนโหลด (คาดว่าเป็น favicon 404) ไม่กระทบการคำนวณหรือการส่งฟอร์ม
- ไฟล์นี้บันทึกผลการตรวจด้วย Browser เท่านั้น ไม่ได้แก้ไขไฟล์โปรแกรมใด ๆ ในรอบนี้

---

# ผลตรวจรอบที่ 2 — Dark UI, Mode Selector, Live Circuit, MΩ

**วันที่ตรวจ:** 2026-11-17
**เว็บที่ตรวจ:** http://127.0.0.1:5000/ (เซิร์ฟเวอร์ที่รันโค้ดหลังเพิ่ม MΩ / mode selector / live circuit / dark theme)
**วิธีตรวจ:** Playwright MCP เท่านั้น (ไม่มี `curl` และไม่ได้ใช้ค่าจาก unittest เป็นผลตรวจ)
**เทสอัตโนมัติประกอบ:** `python -m unittest tests.test_app` → **29 tests OK**

## สิ่งที่เปลี่ยนในรอบนี้

1. Bias Mode เป็นปุ่มเลือก 3 ปุ่มเท่ากัน (Voltage Divider / Fixed / Emitter) แทน `<select>`
2. ฟอร์มแสดงเฉพาะช่องที่โหมดนั้นใช้ (Divider: R1, R2, R<sub>E</sub> / Fixed: R<sub>B</sub> / Emitter: R<sub>B</sub>, R<sub>E</sub>)
3. วงจร SVG ใช้ค่าที่ผู้ใช้กรอกจริง ทั้งระหว่างพิมพ์และหลังกด Calculate และซ่อนอุปกรณ์ที่โหมดไม่ใช้
4. เพิ่มหน่วย `MΩ` ในช่องหน่วยของตัวต้านทานทั้ง 5 ช่อง
5. ธีมมืด (dark theme) ทั้งหน้าและวงจร

## ลำดับขั้นที่ใช้ตรวจ

1. `browser_navigate` → เปิด `http://127.0.0.1:5000/`
2. `browser_click` ที่ `<label for="mode_*">` เพื่อเลือกโหมด (ปุ่ม radio ถูกซ่อนด้วยสไตล์ แต่ยังคีย์บอร์ดและ label ใช้งานได้)
3. `browser_fill_form` → กรอกค่าด้วย selector `input#<ชื่อ field>`
4. `browser_select_option` → เลือกหน่วย `select#<ชื่อ field>_unit` (Ω / kΩ / MΩ)
5. `browser_evaluate` → อ่านค่าที่แสดงบน SVG, computed `display` ของแต่ละช่อง, และค่าที่ป้อนในตารางผล
6. `browser_click` → กด `Calculate DC Bias`
7. อ่านหน้าผลลัพธ์ใหม่ทุกครั้ง และ `browser_network_requests` สำหรับเคส error

## ตารางผลตรวจ A1–A5 (รอบที่ 2)

| ID | โหมด / อินพุต | ค่าคาดหมาย | ผลที่เห็น | สถานะ |
| --- | --- | --- | --- | --- |
| A1 | Divider<br>V<sub>CC</sub> 12 V, R1 100 kΩ, R2 22 kΩ, R<sub>C</sub> 2.2 kΩ, R<sub>E</sub> 1 kΩ, β 100, V<sub>BE</sub> 0.70 V | I<sub>C</sub> 1.23 mA<br>V<sub>CE</sub> 8.052 V | I<sub>C</sub> **1.23 mA**<br>V<sub>CE</sub> **8.052 V**<br>V<sub>B</sub> 1.942 V · V<sub>E</sub> 1.242 V · V<sub>C</sub> 9.294 V<br>I<sub>B</sub> 12.3 µA · I<sub>E</sub> 1.24 mA<br>nodal check ✓ | **PASS** |
| A2 | Fixed<br>R<sub>B</sub> = **1 MΩ** (หน่วย MΩ), R<sub>C</sub> 2.2 kΩ, β 100, V<sub>BE</sub> 0.70 V | I<sub>C</sub> 1.13 mA<br>V<sub>CE</sub> 9.514 V | I<sub>C</sub> **1.13 mA**<br>V<sub>CE</sub> **9.514 V**<br>V<sub>B</sub> 0.700 V · V<sub>E</sub> 0.000 V<br>หน่วย MΩ ยังถูกเลือกหลัง POST | **PASS** |
| A3 | Emitter<br>R<sub>B</sub> 1000 kΩ, R<sub>C</sub> 2.2 kΩ, R<sub>E</sub> 1 kΩ | I<sub>C</sub> 1.03 mA<br>V<sub>CE</sub> 8.705 V | I<sub>C</sub> **1.03 mA**<br>V<sub>CE</sub> **8.705 V**<br>V<sub>B</sub> 1.737 V · V<sub>E</sub> 1.037 V · V<sub>C</sub> 9.742 V | **PASS** |
| A4 | Emitter<br>เปลี่ยน R<sub>E</sub> เป็น 2 kΩ | I<sub>C</sub> ลดลง<br>V<sub>CE</sub> 8.033 V | I<sub>C</sub> **0.94 mA** (ลดจาก A3)<br>V<sub>CE</sub> **8.033 V**<br>SVG เปลี่ยนเป็น `RE = 2 kΩ` ทันทีโดยไม่ต้องกด Calculate | **PASS** |
| A5 | Fixed<br>R<sub>B</sub> = **0** kΩ | แจ้งเตือน, ไม่มีผลค้าง, HTTP 400 | ข้อความ **“RB must be greater than 0”**<br>ไม่มีตารางผลลัพธ์<br>โหมดยังเป็น Fixed Bias และค่าที่กรอกยังอยู่<br>`[POST] /calculate => 400 BAD REQUEST` | **PASS** |

## ผลตรวจพฤติกรรม UI ใหม่

| หัวข้อ | วิธีตรวจ | ผลที่เห็น | สถานะ |
| --- | --- | --- | --- |
| ปุ่มเลือกโหมด 3 ปุ่ม | snapshot + click ที่ label | มี `radio` 3 ตัว (`mode_divider`, `mode_fixed`, `mode_emitter`) ปุ่มที่เลือกถูกไฮไลต์สีทอง และเปลี่ยนโหมดทันทีโดยไม่ reload | **PASS** |
| ซ่อนช่องที่ไม่ใช้ | อ่าน computed `display` ของทุก `[data-field]` | Divider → เห็น V<sub>CC</sub>, R1, R2, R<sub>C</sub>, R<sub>E</sub>, β, V<sub>BE</sub><br>Fixed → เห็น V<sub>CC</sub>, R<sub>B</sub>, R<sub>C</sub>, β, V<sub>BE</sub><br>Emitter → เห็น V<sub>CC</sub>, R<sub>B</sub>, R<sub>C</sub>, R<sub>E</sub>, β, V<sub>BE</sub> | **PASS** |
| วงจรอัปเดตระหว่างพิมพ์ | พิมพ์ค่าแล้วอ่านข้อความใน `<tspan data-slot>` ก่อนกด Calculate | `VCC = 12 V`, `R1 = 100 kΩ`, `R2 = 22 kΩ`, `RC = 2.2 kΩ`, `RE = 1 kΩ`, `β = 100`, `VBE = 0.70 V` — มีช่องว่างหน้าตัวเลขทุกจุด | **PASS** |
| วงจรซ่อนอุปกรณ์ตามโหมด | อ่านคลาส `is-hidden` ของ `[data-component]` | Divider → ซ่อน RB<br>Fixed → ซ่อน R1, R2, RE, divider-tap<br>Emitter → ซ่อน R1, R2, divider-tap | **PASS** |
| ค่าเริ่มต้นว่าง | เปิดหน้าครั้งแรก | ทุกช่องว่าง และ SVG แสดง `= —` (ไม่ใช่ `undefined`/`null`) | **PASS** |
| หน่วย MΩ | เลือก MΩ ที่ R<sub>B</sub> แล้วคำนวณ | ได้ผลเท่ากับ R<sub>B</sub> = 1,000,000 Ω (I<sub>C</sub> 1.13 mA, V<sub>CE</sub> 9.514 V) | **PASS** |
| ธีมมืด | เปิดหน้าและหน้าผลลัพธ์ | พื้นหลังดำ/เทาเข้ม การ์ดและช่องกรอกเข้ม ตัวอักษรสว่าง ปุ่ม Calculate และตัวเลขผลเป็นสีทอง วงจรใช้เส้นสีอ่อนตัดกับพื้น | **PASS** |

## ภาพหลักฐาน (โฟลเดอร์ `.playwright-mcp/`, ไม่ได้ commit)

- `dark-form.png` — ฟอร์มโหมด Divider (ค่าว่าง) บนธีมมืด
- `dark-result-divider.png` — ผล A1 พร้อมตาราง Thevenin และ nodal check
- `dark-fixed-fields.png` — โหมด Fixed แสดงเฉพาะช่องที่ใช้
- `dark-emitter-live.png` — โหมด Emitter กับวงจรที่อัปเดตจากค่าที่พิมพ์
- `dark-error-fixed.png` — หน้า 400 หลัง R<sub>B</sub> = 0 (โหมดและค่ายังอยู่)

## ข้อสังเกตจากการตรวจรอบนี้

- ปุ่ม radio ถูกซ่อนด้วย `opacity: 0` และรับคลิกผ่าน `<label>` (ผู้ใช้ทั่วไปคลิกที่ป้ายชื่อ) — คีย์บอร์ดยังโฟกัสและเปลี่ยนโหมดได้ตามปกติ
- ฟอร์มใช้ `novalidate` เพื่อให้ Python เป็นผู้ตรวจค่าเพียงผู้เดียว: ถ้าผู้ใช้พิมพ์ค่าไม่ครบ (เช่น `1e`) ไว้ในช่องที่โหมดใหม่ซ่อนไว้ ปุ่ม Calculate ยังกดได้และไม่ค้าง (ตรวจแล้ว: R1 = `1e` → สลับเป็น Fixed → คำนวณได้ I<sub>C</sub> 1.13 mA, V<sub>CE</sub> 9.514 V)
- ระหว่างตรวจพบและแก้ 3 บุก่อนปิดรอบ: ช่องว่างหน้าค่าใน SVG, R1/R2 ที่ซ่อนรวมกันเป็นกลุ่มเดียว, และสไตล์ `.field { display: grid }` ที่ทำให้แอตทริบิวต์ `hidden` ไม่ทำงาน (เพิ่มกฎ `[hidden] { display: none !important; }`) — ทั้งสามมีเทสครอบแล้ว

## รอบที่ 3 — ทุกช่องแสดงตลอดเวลา (17 พ.ย. 2026)

เปลี่ยนพฤติกรรม: ฟอร์มแสดงช่องกรอกครบ 8 ช่อง (V<sub>CC</sub>, R1, R2, R<sub>B</sub>, R<sub>C</sub>, R<sub>E</sub>, β, V<sub>BE</sub>) ทุกโหมด
และ `app.py` อ่าน/ตรวจค่าเฉพาะช่องที่โหมดนั้นใช้ (`MODE_FIELDS`) ค่าที่ค้างในช่องอื่นถูกข้ามทั้งหมด
รูปวงจร SVG ยังแสดงเฉพาะอุปกรณ์ของโหมดที่เลือกตามเดิม

### ตารางผลตรวจ B1–B5

| ID | การกระทำ | ค่าคาดหมาย | ผลที่เห็น | สถานะ |
| --- | --- | --- | --- | --- |
| B1 | เปิด `/` กรอก R1 = 100 kΩ, R2 = 22 kΩ แล้วคลิกป้าย **Fixed Bias** | ช่องทั้ง 8 ยังแสดง, ค่า R1/R2 ยังอยู่, SVG ซ่อน R1/R2/divider-tap และแสดง R<sub>B</sub> | 8/8 ช่อง `display: grid` ไม่มี `hidden`; R1 = 100, R2 = 22 ยังอยู่; `r1`/`r2`/`divider-tap` = `is-hidden`, `rb` แสดง | **PASS** |
| B2 | โหมด Fixed: R1 = -5 kΩ, R2 = 0, R<sub>E</sub> = 0 (ค่าเสียที่โหมดนี้ไม่ใช้), R<sub>B</sub> = 1 MΩ, R<sub>C</sub> = 2.2 kΩ, β 100, V<sub>BE</sub> 0.70 V → Calculate | HTTP 200, ไม่มี error, I<sub>C</sub> 1.13 mA, V<sub>CE</sub> 9.514 V | ไม่มีกล่อง error; I<sub>C</sub> **1.13 mA**, V<sub>CE</sub> **9.514 V**; ค่า R1 = -5, R2 = 0, R<sub>E</sub> = 0 ยังคงอยู่และไม่ถูกตรวจ; หน่วย MΩ ของ R<sub>B</sub> ยังถูกเลือก | **PASS** |
| B3 | โหมด Emitter: R<sub>B</sub> 1000 kΩ, R<sub>C</sub> 2.2 kΩ, R<sub>E</sub> 1 kΩ (R1 = -5, R2 = 0 ค้างอยู่) → Calculate | HTTP 200, I<sub>C</sub> 1.03 mA, V<sub>CE</sub> 8.705 V | I<sub>C</sub> **1.03 mA**, V<sub>CE</sub> **8.705 V**; 8/8 ช่องแสดง; SVG ซ่อน R1/R2/tap แสดง R<sub>B</sub> และ R<sub>E</sub> | **PASS** |
| B4 | โหมด Divider: V<sub>CC</sub> 12 V, R1 100 kΩ, R2 22 kΩ, R<sub>C</sub> 2.2 kΩ, R<sub>E</sub> 1 kΩ, β 100, V<sub>BE</sub> 0.70 V → Calculate | ผลเท่ารอบที่ 2: I<sub>C</sub> 1.23 mA, V<sub>CE</sub> 8.052 V | I<sub>C</sub> **1.23 mA**, V<sub>CE</sub> **8.052 V**; 8/8 ช่องแสดง; SVG แสดง R1/R2/tap/R<sub>E</sub> ซ่อน R<sub>B</sub> | **PASS** |
| B5 | โหมด Fixed: R<sub>B</sub> = 0 kΩ → Calculate | แจ้งเตือน, POST 400, ไม่มีตารางผล, ค่าและโหมดยังอยู่ | **“RB must be greater than 0”**; ไม่มี `.result-table`; `[POST] /calculate => [400] BAD REQUEST`; โหมด Fixed, R<sub>B</sub> = 0 (kΩ) และ R1 = 100 ยังอยู่; 8/8 ช่องแสดง | **PASS** |

### ตารางผลตรวจพฤติกรรม UI รอบที่ 3

| หัวข้อ | วิธีตรวจ | ผลที่เห็น | สถานะ |
| --- | --- | --- | --- |
| ทุกช่องแสดงตลอดเวลา | อ่าน `hidden` และ computed `display` ของทั้ง 8 `div.field` หลัง POST ทุกโหมด | เห็นครบ V<sub>CC</sub>, R1, R2, R<sub>B</sub>, R<sub>C</sub>, R<sub>E</sub>, β, V<sub>BE</sub> ทั้ง Divider/Fixed/Emitter (ไม่เหลือ `data-field` หรือแอตทริบิวต์ `hidden` ในฟอร์ม) | **PASS** |
| ค่าที่โหมดไม่ใช้ถูกข้าม | ส่ง R1 = -5 kΩ, R2 = 0, R<sub>E</sub> = 0 พร้อมโหมด Fixed (B2) | คำนวณผ่านด้วย I<sub>C</sub> 1.13 mA ไม่มี error | **PASS** |
| รูปวงจรยังตรงโหมด | อ่านคลาสของ `[data-component]` ทั้ง 3 โหมด | Divider → R1/R2/tap/R<sub>E</sub>; Fixed → R<sub>B</sub>; Emitter → R<sub>B</sub>/R<sub>E</sub> | **PASS** |

### ภาพหลักฐานรอบที่ 3 (โฟลเดอร์ `.playwright-mcp/`, ไม่ได้ commit)

- `b1-fixed-all-fields.png` — โหมด Fixed แสดงช่องครบ 8 ช่องพร้อมค่า R1/R2 ที่ค้างจากโหมด Divider
- `b5-error-all-fields.png` — หน้า 400 หลัง R<sub>B</sub> = 0 โดยทุกช่องยังแสดงและค่ายังอยู่

### ข้อสังเกตจากการตรวจรอบที่ 3

- ช่องกรอกเป็น `type="number"` เบราว์เซอร์จึงตัดค่าที่ไม่ใช่ตัวเลข (เช่น `1e`) ทิ้งเป็นค่าว่าง การทดสอบค่าเสียที่โหมดไม่ใช้จึงใช้ค่าที่ parse ได้แต่ผิดเงื่อนไข (-5, 0) ซึ่งแรงกว่าเดิม เพราะถ้าโค้ดเผลอตรวจช่องนั้นจะได้ 400 ทันที
- หน่วย MΩ/kΩ ของช่องที่โหมดไม่ใช้ยังถูกส่งไปกับฟอร์มแต่ไม่ถูกอ่าน (`MODE_FIELDS` เป็นตัวกำหนด) จึงไม่มีทางรั่วเข้าสมการ


