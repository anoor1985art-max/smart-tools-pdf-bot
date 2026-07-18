import os
import qrcode
from PIL import Image
import urllib.parse

try:
    import cv2
    import numpy as np
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False

try:
    from pyzbar import pyzbar
    PYZBAR_AVAILABLE = True
except ImportError:
    PYZBAR_AVAILABLE = False


def generate_qr_code(data, output_path, fill_color="black", back_color="white", box_size=10, border=4):
    """
    إنشاء باركود QR عالي الدقة لأي نص أو رابط أو بيانات بطاقة شخصية أو واي فاي
    """
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=box_size,
        border=border,
    )
    qr.add_data(data)
    qr.make(fit=True)

    img = qr.make_image(fill_color=fill_color, back_color=back_color).convert('RGB')
    img.save(output_path, format="PNG")
    return output_path


def create_vcard_data(name, phone, email="", org="", title="", website=""):
    """
    توليد نص بطاقة جهة اتصال (vCard 3.0) بحيث يفتح الهاتف خيار الحفظ فوراً عند المسح
    """
    lines = [
        "BEGIN:VCARD",
        "VERSION:3.0",
        f"FN:{name}",
        f"TEL;TYPE=CELL:{phone}"
    ]
    if email:
        lines.append(f"EMAIL;TYPE=WORK:{email}")
    if org:
        lines.append(f"ORG:{org}")
    if title:
        lines.append(f"TITLE:{title}")
    if website:
        lines.append(f"URL:{website}")
    lines.append("END:VCARD")
    return "\n".join(lines)


def create_wifi_data(ssid, password, auth_type="WPA", hidden=False):
    """
    توليد كود الاتصال السريع بشبكة الواي فاي
    """
    h_flag = "true" if hidden else "false"
    return f"WIFI:S:{ssid};T:{auth_type};P:{password};H:{h_flag};;"


def create_whatsapp_data(phone, message=""):
    """
    توليد رابط واتساب مباشر للاتصال أو المحادثة
    """
    clean_phone = ''.join(filter(str.isdigit, str(phone)))
    url = f"https://wa.me/{clean_phone}"
    if message:
        url += f"?text={urllib.parse.quote(message)}"
    return url


def create_email_data(email, subject="", body=""):
    """
    توليد رابط إرسال إيميل سريع
    """
    url = f"mailto:{email}"
    params = []
    if subject:
        params.append(f"subject={urllib.parse.quote(subject)}")
    if body:
        params.append(f"body={urllib.parse.quote(body)}")
    if params:
        url += "?" + "&".join(params)
    return url


def decode_qr_from_image(image_path):
    """
    قراءة وفك تشفير جميع رموز QR والباركود العادي (Barcodes) من الصورة بدقة مدمجة
    يعيد قائمة من القواميس: [{"type": "QR-Code", "data": "https://..."}]
    """
    results = []
    seen_data = set()

    # 1. محاولة القراءة باستخدام pyzbar أولاً (أسرع وأشمل لجميع أنواع الباركود)
    if PYZBAR_AVAILABLE:
        try:
            pil_img = Image.open(image_path)
            decoded_objects = pyzbar.decode(pil_img)
            for obj in decoded_objects:
                data_str = obj.data.decode('utf-8', errors='replace').strip()
                code_type = obj.type if hasattr(obj, 'type') else "QR-Code/Barcode"
                if data_str and data_str not in seen_data:
                    seen_data.add(data_str)
                    results.append({"type": code_type, "data": data_str})
        except Exception as e:
            print(f"[pyzbar decode error]: {e}")

    # 2. إذا لم يتم العثور أو كانت pyzbar غير متاحة، نستخدم OpenCV QRCodeDetector و BarcodeDetector
    if CV2_AVAILABLE and (not results or len(results) == 0):
        try:
            cv_img = cv2.imread(image_path)
            if cv_img is not None:
                # فحص QR
                qr_detector = cv2.QRCodeDetector()
                data, bbox, _ = qr_detector.detectAndDecode(cv_img)
                if data and data.strip() and data.strip() not in seen_data:
                    seen_data.add(data.strip())
                    results.append({"type": "QR-Code", "data": data.strip()})

                # فحص الباركود التقليدي (إذا دعم النسخة)
                if hasattr(cv2, 'barcode_BarcodeDetector'):
                    barcode_detector = cv2.barcode_BarcodeDetector()
                    ok, decoded_info, decoded_type, _ = barcode_detector.detectAndDecode(cv_img)
                    if ok and decoded_info:
                        for idx, b_data in enumerate(decoded_info):
                            if b_data and b_data.strip() and b_data.strip() not in seen_data:
                                b_type = decoded_type[idx] if idx < len(decoded_type) else "Barcode"
                                seen_data.add(b_data.strip())
                                results.append({"type": str(b_type), "data": b_data.strip()})
        except Exception as e:
            print(f"[OpenCV decode error]: {e}")

    return results
