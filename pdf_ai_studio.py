import os
import fitz  # PyMuPDF
import requests
import json
from gtts import gTTS

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

def get_gemini_key():
    key = os.environ.get("GEMINI_API_KEY", GEMINI_API_KEY).strip()
    if key:
        return key
    config_file = os.path.join(os.path.dirname(__file__), "gemini_key.json")
    if os.path.exists(config_file):
        try:
            with open(config_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("api_key", "").strip()
        except Exception:
            pass
    return ""

def set_local_gemini_key(api_key):
    config_file = os.path.join(os.path.dirname(__file__), "gemini_key.json")
    with open(config_file, "w", encoding="utf-8") as f:
        json.dump({"api_key": api_key.strip()}, f)

def call_gemini_ai(prompt, system_instruction="أنت مستشار وخبيرة مستندات ذكية تجيب باللغة العربية الفصحى بدقة."):
    """الاتصال بمحرك Gemini 1.5 الذكي لمعالجة النصوص والمستندات"""
    key = get_gemini_key()
    if not key:
        return "⚠️ <b>تنبيه: محرك الذكاء الاصطناعي يحتاج إلى مفتاح Gemini API!</b>\n\n🔑 يرجى إدخال مفتاحك في البوت مباشرة عبر إرسال الأمر التالي:\n`/set_gemini_key AIzaSy...`\n\n<i>(يمكنك الحصول على المفتاح مجاناً في 10 ثوانٍ من موقع Google AI Studio الرسمية: aistudio.google.com/app/apikey)</i>"
        
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={key}"
    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [{"parts": [{"text": f"{system_instruction}\n\n{prompt}"}]}],
        "generationConfig": {"temperature": 0.3, "maxOutputTokens": 2048}
    }
    try:
        r = requests.post(url, headers=headers, json=payload, timeout=30)
        if r.status_code == 200:
            data = r.json()
            return data["candidates"][0]["content"]["parts"][0]["text"].strip()
    except Exception as e:
        print(f"[Gemini Error]: {e}")
    return "❌ حدث خطأ مؤقت أثناء الاتصال بمحرك الذكاء الاصطناعي."

def extract_all_text(pdf_path):
    """استخراج كامل النصوص العربية والأجنبية من ملف الـ PDF"""
    doc = fitz.open(pdf_path)
    text_list = []
    for page in doc:
        t = page.get_text()
        if t.strip():
            text_list.append(t.strip())
    doc.close()
    return "\n\n".join(text_list)

def ai_summarize_pdf(pdf_path):
    """💡 التلخيص الذكي الشامل لنقاط وفصول المستند"""
    text = extract_all_text(pdf_path)
    if not text:
        return "⚠️ لم يتم العثور على نص مقروء في المستند. قد يكون الملف عبارة عن صور ممسوحة ضوئياً ويحتاج لتشغيل القارئ الضوئي OCR أولاً."
    
    prompt = (
        f"قم بقراءة وتحليل مستند الـ PDF التالي بعناية، ثم استخرج ملخصاً وافياً ومحكماً في نقاط واضحة:\n\n"
        f"--- نص المستند ---\n{text[:10000]}\n-------------------\n\n"
        f"المطلوب:\n1. عنوان ومحور المستند الأساسي.\n2. أهم 5 إلى 7 نقاط ونتائج رئيسية وردت فيه.\n3. خاتمة موجزة بأسلوب احترافي."
    )
    return call_gemini_ai(prompt, "أنت خبير تلخيص مستندات ووثائق أكاديمية وتجارية.")

def ai_pdf_qa(pdf_path, question):
    """🗣️ محاورة وسؤال المستند مباشرة والإجابة من سياقه الدقيق"""
    text = extract_all_text(pdf_path)
    prompt = (
        f"بناءً على نص مستند الـ PDF المرفق فقط، أجب عن سؤال القارئ بدقة متناهية واذكر التفاصيل أو الأرقام إن وجدت:\n\n"
        f"--- المستند ---\n{text[:12000]}\n---------------\n\n"
        f"❓ سؤال القارئ: {question}\n\n"
        f"أجب بوضوح وموضوعية استناداً إلى نصوص المستند."
    )
    return call_gemini_ai(prompt, "أجب بصدق ودقة اعتماداً على المستند المرفق فقط.")

def ai_grammar_proofread(pdf_path):
    """✨ المحرر والمصحح اللغوي الذكي للمستند وإعادة صياغته"""
    text = extract_all_text(pdf_path)
    prompt = (
        f"قم بتدقيق النص المرفق لغوياً وإملائياً ونحوياً بدقة تامة، وأعد صياغة الجمل الضعيفة لتصبح قوية وبليغة وخالية من أي شوائب:\n\n"
        f"{text[:8000]}"
    )
    return call_gemini_ai(prompt, "أنت لغوي ومحرر مستندات فائق الدقة والبلاغة.")

def ai_translate_pdf(pdf_path, target_lang="العربية"):
    """🌐 ترجمة كاملة للمستند مع الحفاظ على التماسك والفقرات"""
    text = extract_all_text(pdf_path)
    prompt = (
        f"ترجم النص التالي من مستند الـ PDF ترجمة احترافية ودقيقة جداً إلى اللغة ({target_lang}) مع مراعاة المصطلحات المتخصصة والحفاظ على ترتيب الفقرات:\n\n"
        f"{text[:8000]}"
    )
    return call_gemini_ai(prompt, f"أنت مترجم فوري محلف ومحترف تتقن الترجمة إلى {target_lang}.")

def ai_contract_auditor(pdf_path):
    """⚖️ المدقق والمحلل القانوني للعقود والاتفاقيات التجارية"""
    text = extract_all_text(pdf_path)
    prompt = (
        f"قم بدراسة وتحليل بنود هذا العقد أو الاتفاقية قانونياً وتجارياً بتركيز شديد:\n\n"
        f"{text[:10000]}\n\n"
        f"المطلوب تقرير مفصل يشمل:\n"
        f"1. 📑 ملخص أطراف العقد والهدف منه.\n"
        f"2. 🚩 البنود الخطرة أو المقيدة للحرية والتكاليف المخفية (Red Flags) التي يجب الانتباه لها.\n"
        f"3. ⚖️ ملخص التزامات كل طرف بأسلوب واضح ومباشر."
    )
    return call_gemini_ai(prompt, "أنت مستشار ومحامي تجاري وقانوني محترف تكتشف الثغرات والبنود الحساسة.")

def ai_pdf_to_speech(summary_text, output_mp3_path):
    """🎧 تحويل نص الملخص إلى استماع صوتي واضح MP3"""
    tts = gTTS(text=summary_text[:3000], lang="ar", slow=False)
    tts.save(output_mp3_path)
    return output_mp3_path
