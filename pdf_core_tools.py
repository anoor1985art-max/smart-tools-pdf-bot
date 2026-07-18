import os
import fitz  # PyMuPDF
from pypdf import PdfReader, PdfWriter
from PIL import Image

def merge_pdfs(pdf_paths, output_path):
    """دمج عدة ملفات PDF بالترتيب المعطى"""
    merged_doc = fitz.open()
    for path in pdf_paths:
        with fitz.open(path) as doc:
            merged_doc.insert_pdf(doc)
    merged_doc.save(output_path, garbage=4, deflate=True)
    merged_doc.close()
    return output_path

def split_pdf(pdf_path, output_dir, start_page=1, end_page=None):
    """تقسيم أو استخراج صفحات محددة من PDF (الترقيم يبدأ من 1)"""
    doc = fitz.open(pdf_path)
    total_pages = len(doc)
    if end_page is None or end_page > total_pages:
        end_page = total_pages
    if start_page < 1:
        start_page = 1
        
    out_doc = fitz.open()
    out_doc.insert_pdf(doc, from_page=start_page-1, to_page=end_page-1)
    output_path = os.path.join(output_dir, f"split_p{start_page}_to_p{end_page}.pdf")
    out_doc.save(output_path, garbage=4, deflate=True)
    out_doc.close()
    doc.close()
    return output_path

def compress_pdf(pdf_path, output_path):
    """ضغط ملف PDF وتقليل حجمه مع الحفاظ على أعلى جودة قراءة"""
    doc = fitz.open(pdf_path)
    # استخدام خيارات الضغط المتقدمة في PyMuPDF
    doc.save(output_path, garbage=4, deflate=True, clean=True)
    doc.close()
    return output_path

def rotate_pdf(pdf_path, output_path, angle=90):
    """تدوير صفحات PDF بالزاوية المحددة (90، 180، 270)"""
    doc = fitz.open(pdf_path)
    for page in doc:
        page.set_rotation((page.rotation + angle) % 360)
    doc.save(output_path, garbage=4, deflate=True)
    doc.close()
    return output_path

def add_watermark_text(pdf_path, output_path, text="CONFIDENTIAL", opacity=0.3):
    """إضافة علامة مائية نصية مائلة على جميع صفحات المستند لحماية الحقوق"""
    doc = fitz.open(pdf_path)
    for page in doc:
        rect = page.rect
        # وضع النص في منتصف الصفحة بزاوية مائلة
        point = fitz.Point(rect.width / 4, rect.height / 2)
        page.insert_text(point, text, fontsize=45, color=(0.7, 0.1, 0.1), rotate=45, fill_opacity=opacity)
    doc.save(output_path, garbage=4, deflate=True)
    doc.close()
    return output_path

def protect_pdf(pdf_path, output_path, password):
    """تشفير وحماية مستند PDF بكلمة مرور"""
    doc = fitz.open(pdf_path)
    perm = fitz.PDF_PERM_PRINT | fitz.PDF_PERM_COPY
    doc.save(output_path, encryption=fitz.PDF_ENCRYPT_AES_256, owner_pw=password, user_pw=password, permissions=perm)
    doc.close()
    return output_path

def unlock_pdf(pdf_path, output_path, password=""):
    """فك تشفير ملف PDF وإزالة الحماية منه"""
    doc = fitz.open(pdf_path)
    if doc.is_encrypted:
        success = doc.authenticate(password)
        if not success:
            raise Exception("كلمة المرور غير صحيحة أو الملف محمي بتشفير خاص.")
    doc.save(output_path)
    doc.close()
    return output_path

def add_page_numbers(pdf_path, output_path):
    """إضافة أرقام صفحات تلقائية أسفل منتصف كل صفحة"""
    doc = fitz.open(pdf_path)
    for idx, page in enumerate(doc, start=1):
        rect = page.rect
        text = f"- {idx} -"
        point = fitz.Point(rect.width / 2 - 15, rect.height - 25)
        page.insert_text(point, text, fontsize=11, color=(0.3, 0.3, 0.3))
    doc.save(output_path, garbage=4, deflate=True)
    doc.close()
    return output_path

def extract_images_from_pdf(pdf_path, output_dir):
    """استخراج جميع الصور الموجودة داخل مستند الـ PDF بصيغة JPG عالية الدقة"""
    doc = fitz.open(pdf_path)
    extracted_files = []
    for page_index in range(len(doc)):
        page = doc[page_index]
        image_list = page.get_images(full=True)
        for img_index, img in enumerate(image_list, start=1):
            xref = img[0]
            base_image = doc.extract_image(xref)
            image_bytes = base_image["image"]
            image_ext = base_image["ext"]
            img_filename = os.path.join(output_dir, f"page_{page_index+1}_img_{img_index}.{image_ext}")
            with open(img_filename, "wb") as f:
                f.write(image_bytes)
            extracted_files.append(img_filename)
    doc.close()
    return extracted_files
