# DC Circuit Calculator

โปรแกรมสำหรับคำนวณกระแสไฟฟ้าในวงจรตัวต้านทานด้วยกฎของโอห์ม
และคำนวณกำลังไฟฟ้าที่เกิดขึ้นในวงจร เพื่อช่วยวิเคราะห์วงจร DC เบื้องต้น

## BJT Common-Emitter DC Bias web app (ENG29 2121)

แอป Flask คำนวณจุดทำงานกระแสตรงของอัดยิ่งไบโพolar แบบ common-emitter
ที่ใช้วงจรแบ่งแรงดัน ป้อนค่า VCC, R1, R2, RC, RE, β, VBE แล้วดูผลกับ
หน่วย ตรวจสอบค่าที่ป้อน แจ้งเตือนเมื่ออยู่นอกภูมิภาค active และเทียบ
ผลกับการคำนวณอิสระโดยวิธีโหนด (nodal analysis)

### Run

```
python -m pip install -r requirements.txt
python app.py
```
เปิด http://127.0.0.1:5000/

### Test

```
python -m unittest discover -s tests -t . -v
```
