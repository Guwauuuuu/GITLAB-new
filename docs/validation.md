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
