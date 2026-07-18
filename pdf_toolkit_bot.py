import os
import sys
import time
import uuid
import shutil
import threading
from dotenv import load_dotenv
import telebot
from telebot import types
from flask import Flask, request, render_template_string, send_from_directory

load_dotenv()
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
bot = telebot.TeleBot(TOKEN) if TOKEN else None
app = Flask(__name__)

# مجلد العمل والملفات المؤقتة
WORK_DIR = os.path.join(os.path.dirname(__file__), "storage_temp")
os.makedirs(WORK_DIR, exist_ok=True)

# تخزين حالات وحقائب المستخدمين
# user_files: {chat_id: {"active_file": path, "merge_list": [path1, path2], "state": state_str}}
user_data = {}

def get_user_session(chat_id):
    if chat_id not in user_data:
        user_data[chat_id] = {"active_file": None, "merge_list": [], "state": "idle"}
    return user_data[chat_id]

# ==========================================
# تنظيف السيرفر التلقائي (Daemon Cleaner)
# ==========================================
def cleanup_temp_daemon():
    while True:
        try:
            now = time.time()
            for root, dirs, files in os.walk(WORK_DIR):
                for f in files:
                    fp = os.path.join(root, f)
                    if now - os.path.getmtime(fp) > 7200: # حذف بعد ساعتين لحماية الخصوصية ومساحة الخادم
                        try:
                            os.remove(fp)
                        except Exception:
                            pass
        except Exception as e:
            print(f"[Cleanup Daemon Error]: {e}")
        time.sleep(1800)

# ==========================================
# قوائم وأزرار البوت الرئيسية والذكية
# ==========================================
def get_main_menu_markup():
    """لوحة الأدوات الشاملة: عناوين ثابتة للأقسام وأسفل كل عنوان أدواته مباشرة، وكل زر يأخذ صفاً كاملاً"""
    markup = types.InlineKeyboardMarkup(row_width=1)
    
    markup.add(types.InlineKeyboardButton("📚 دليل وشرح وظائف جميع الأدوات والـ QR (شامل)", callback_data="open_tools_guide"))
    
    # --- القسم 1: أدوات الدمج والتقسيم والضغط ---
    markup.add(types.InlineKeyboardButton("━━━ 🧩 أدوات الدمج والتقسيم والتنظيم ━━━", callback_data="ignore"))
    markup.add(types.InlineKeyboardButton("📥 دمج ملفات PDF", callback_data="tool_merge"))
    markup.add(types.InlineKeyboardButton("✂️ تقسيم واستخراج صفحات", callback_data="tool_split"))
    markup.add(types.InlineKeyboardButton("🗜️ ضغط وتقليل الحجم", callback_data="tool_compress"))
    markup.add(types.InlineKeyboardButton("🔄 تدوير صفحات المستند", callback_data="tool_rotate"))
    markup.add(types.InlineKeyboardButton("📑 تنظيم وحذف صفحات", callback_data="tool_organize"))
    markup.add(types.InlineKeyboardButton("🔢 أرقام الصفحات", callback_data="tool_pageno"))
    
    # --- القسم 2: التحويل المتبادل ---
    markup.add(types.InlineKeyboardButton("━━━ 🔄 التحويل المتبادل والصور ━━━", callback_data="ignore"))
    markup.add(types.InlineKeyboardButton("🖼️ صور JPG إلى PDF", callback_data="tool_img2pdf"))
    markup.add(types.InlineKeyboardButton("📸 PDF إلى صور JPG", callback_data="tool_pdf2img"))
    markup.add(types.InlineKeyboardButton("📄 Word إلى PDF", callback_data="tool_word2pdf"))
    markup.add(types.InlineKeyboardButton("📝 PDF إلى Word (DOCX)", callback_data="tool_pdf2word"))
    markup.add(types.InlineKeyboardButton("📊 Excel إلى PDF", callback_data="tool_excel2pdf"))
    markup.add(types.InlineKeyboardButton("🌐 HTML إلى PDF", callback_data="tool_html2pdf"))
    
    # --- القسم 3: استوديو الذكاء الاصطناعي والـ OCR ---
    markup.add(types.InlineKeyboardButton("━━━ 🤖 استوديو الذكاء الاصطناعي والـ OCR ━━━", callback_data="ignore"))
    markup.add(types.InlineKeyboardButton("💡 الملخص الذكي الفوري", callback_data="quick_ai_sum"))
    markup.add(types.InlineKeyboardButton("🗣️ محاورة وسؤال المستند Q&A", callback_data="quick_ai_qa"))
    markup.add(types.InlineKeyboardButton("✨ التدقيق اللغوي وإعادة الصياغة", callback_data="quick_ai_proof"))
    markup.add(types.InlineKeyboardButton("🌐 ترجمة مستند PDF بالكامل", callback_data="tool_ai_trans"))
    markup.add(types.InlineKeyboardButton("🔍 القارئ الضوئي واستخراج النص OCR", callback_data="tool_ocr"))
    markup.add(types.InlineKeyboardButton("⚖️ التدقيق القانوني للعقود", callback_data="quick_ai_audit"))
    markup.add(types.InlineKeyboardButton("🎧 تفريغ الملخص لاستماع صوتي", callback_data="quick_speech"))
    markup.add(types.InlineKeyboardButton("🎯 صناعة أسئلة مراجعة للطلاب", callback_data="tool_ai_quiz"))
    
    # --- القسم 4: الأمان والتشفير والإصلاح ---
    markup.add(types.InlineKeyboardButton("━━━ 🔐 التشفير والحماية والتوقيع والإصلاح ━━━", callback_data="ignore"))
    markup.add(types.InlineKeyboardButton("🔒 قفل بكلمة سر", callback_data="tool_protect"))
    markup.add(types.InlineKeyboardButton("🔓 فك حماية PDF", callback_data="tool_unlock"))
    markup.add(types.InlineKeyboardButton("✍️ توقيع إلكتروني", callback_data="tool_sign"))
    markup.add(types.InlineKeyboardButton("🏷️ علامة مائية", callback_data="tool_watermark"))
    markup.add(types.InlineKeyboardButton("🔧 إصلاح ملف PDF تالف", callback_data="tool_repair"))
    markup.add(types.InlineKeyboardButton("⚖️ مقارنة نسختين وتحديد الفروقات", callback_data="tool_compare"))
    
    # --- القسم 5: أدوات ومولد الباركود والـ QR والقياس الذكي ---
    markup.add(types.InlineKeyboardButton("━━━ 🔳 أدوات الـ QR والباركود والقياس الذكي ━━━", callback_data="ignore"))
    markup.add(types.InlineKeyboardButton("📐 مسطرة وقياس المساحات عبر كاميرا الجوال (Smart AR Ruler)", callback_data="tool_ruler"))
    markup.add(types.InlineKeyboardButton("📲 إنشاء QR لنص أو رابط أو يوتيوب", callback_data="qr_text_url"))
    markup.add(types.InlineKeyboardButton("💬 إنشاء QR لواتساب أو اتصال مباشر", callback_data="qr_whatsapp"))
    markup.add(types.InlineKeyboardButton("📶 إنشاء QR لشبكة واي فاي (WiFi)", callback_data="qr_wifi"))
    markup.add(types.InlineKeyboardButton("📇 إنشاء QR لبطاقة أعمال (vCard)", callback_data="qr_vcard"))
    markup.add(types.InlineKeyboardButton("🎨 إنشاء QR ملون ومخصص", callback_data="qr_custom_color"))
    markup.add(types.InlineKeyboardButton("🎬 تحويل ملف (صورة، صوت، أو فيديو) إلى QR دائم", callback_data="qr_media_file"))
    markup.add(types.InlineKeyboardButton("🔍 قراءة وفك تشفير أي QR أو باركود من صورة", callback_data="qr_decode_action"))
    
    return markup

def get_smart_actions_for_pdf(pdf_path):
    """الأزرار السريعة التلقائية عند إرسال ملف PDF (كل زر يأخذ صفاً كاملاً)"""
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(types.InlineKeyboardButton("🗜️ ضغط وتصغير الحجم", callback_data="quick_compress"))
    markup.add(types.InlineKeyboardButton("✂️ تقسيم واستخراج صفحات", callback_data="quick_split"))
    markup.add(types.InlineKeyboardButton("📝 تحويل إلى Word (DOCX)", callback_data="quick_to_word"))
    markup.add(types.InlineKeyboardButton("🖼️ استخراج جميع الصور", callback_data="quick_to_img"))
    markup.add(types.InlineKeyboardButton("💡 التلخيص الذكي الفوري", callback_data="quick_ai_sum"))
    markup.add(types.InlineKeyboardButton("🗣️ محاورة وسؤال المستند Q&A", callback_data="quick_ai_qa"))
    markup.add(types.InlineKeyboardButton("✨ التصحيح اللغوي وإعادة الصياغة", callback_data="quick_ai_proof"))
    markup.add(types.InlineKeyboardButton("⚖️ فحص وتدقيق العقد ذكياً", callback_data="quick_ai_audit"))
    markup.add(types.InlineKeyboardButton("🔒 قفل بكلمة سر", callback_data="quick_protect"))
    markup.add(types.InlineKeyboardButton("🎧 تحويل الملخص لاستماع صوتي", callback_data="quick_speech"))
    markup.add(types.InlineKeyboardButton("🔙 العودة للقائمة الشاملة", callback_data="main_menu"))
    return markup

def get_smart_actions_for_image(img_path):
    """الأزرار السريعة عند إرسال صورة أو عدة صور"""
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("📐 قياس الأطوال والمساحة هندسياً من الصورة (AI Vision Ruler)", callback_data="img_ai_ruler"),
        types.InlineKeyboardButton("🔍 قراءة وفك تشفير باركود/QR من الصورة", callback_data="qr_decode_img"),
        types.InlineKeyboardButton("🔳 تحويل الصورة إلى باركود QR دائم (QR Link)", callback_data="qr_convert_active_media"),
        types.InlineKeyboardButton("📑 تحويل الصورة/الصور إلى مستند PDF وثائقي", callback_data="img_to_pdf_single"),
        types.InlineKeyboardButton("➕ إضافة صورة أخرى لقائمة الدمج في PDF واحد", callback_data="img_add_to_list"),
        types.InlineKeyboardButton("🔍 استخراج النص المكتوب في الصورة (OCR)", callback_data="img_ocr"),
        types.InlineKeyboardButton("🔙 العودة للقائمة الرئيسية", callback_data="main_menu")
    )
    return markup

def get_smart_actions_for_media(media_path, media_type):
    """الأزرار السريعة عند إرسال مقطع صوتي أو فيديو"""
    markup = types.InlineKeyboardMarkup(row_width=1)
    type_name = "الصوتي" if media_type in ["audio", "voice"] else "المرئي (الفيديو)"
    markup.add(
        types.InlineKeyboardButton(f"🔳 تحويل المقطع {type_name} إلى باركود QR دائم للمشاركة", callback_data="qr_convert_active_media"),
        types.InlineKeyboardButton("🔙 العودة للقائمة الرئيسية", callback_data="main_menu")
    )
    return markup

def process_media_to_qr_flow(chat_id, local_path, status_msg):
    import qr_tools
    bot.edit_message_text("⏳ <b>جاري رفع المقطع إلى السحابة السريعة وتوليد باركود QR دائم للمشاهدة المباشرة...</b> 🚀🔳", chat_id=chat_id, message_id=status_msg.message_id, parse_mode="HTML")
    try:
        out_qr = os.path.join(WORK_DIR, f"qr_media_{uuid.uuid4().hex[:6]}.png")
        _, cloud_url = qr_tools.convert_media_to_qr(local_path, out_qr)
        bot.delete_message(chat_id, status_msg.message_id)
        with open(out_qr, "rb") as f:
            bot.send_photo(chat_id, f, caption=f"✅ <b>تم تحويل المقطع/الصورة إلى باركود QR دائم للمشاركة السريعة بنجاح!</b> 🎬🔳✨\n\n🌐 <b>الرابط المباشر الدائم للمشاهدة/الاستماع:</b>\n`{cloud_url}`\n\n⚡ <i>بمسح هذا الرمز بكاميرا أي هاتف في العالم، سيتم فتح وتشغيل المقطع أو الصورة فوراً في متصفحه!</i>", parse_mode="HTML", reply_markup=types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="main_menu")))
    except Exception as e:
        bot.edit_message_text(f"❌ خطأ أثناء إنشاء باركود الـ QR للمقطع: {e}", chat_id=chat_id, message_id=status_msg.message_id)

if bot:
    @bot.message_handler(commands=["start", "help"])
    def send_welcome(message):
        chat_id = message.chat.id
        session = get_user_session(chat_id)
        session["state"] = "idle"
        welcome_txt = (
            "🚀 <b>مرحباً بك في بوت الأدوات الذكية (Smart Tools) ومعمل الـ PDF!</b> 🛠️✨\n\n"
            "مختبرك الشخصي المتكامل الذي يجمع <b>36 أداة احترافية</b> لمعالجة وتحويل وتنظيم مستنداتك وصورك، بالإضافة إلى <b>قسم مولد وقارئ رموز الـ QR والباركود الذكي</b>، ومدعوماً بمحركات <b>الذكاء الاصطناعي (Gemini AI)</b> للتلخيص، التدقيق، الترجمة، والتحليل القانوني.\n\n"
            "🔥 <b>كيف تبدأ؟</b>\n"
            "1️⃣ <b>الوضع التلقائي الأسرع:</b> أرسل لي أي ملف `PDF` أو `صورة` أو مستند `Word/Excel` وسأعرض لك فوراً الأزرار المناسبة له!\n"
            "2️⃣ <b>الوضع اليدوي التصفحي:</b> اختر الأداة التي تريدها من قائمة الأدوات الشاملة أدناه أو اضغط زر الدليل لمعرفة وظيفة كل أداة:"
        )
        bot.send_message(chat_id, welcome_txt, parse_mode="HTML", reply_markup=get_main_menu_markup())

    @bot.message_handler(commands=["tools_guide", "tools", "guide", "desc"])
    def handle_tools_guide(message):
        import tools_descriptions as tdesc
        bot.send_message(
            message.chat.id,
            "📚 <b>موسوعة ودليل وظائف جميع أدوات البوت والـ QR (36+ أداة):</b>\n\n"
            "اختر القسم الذي تريد معرفة تفاصيل وشرح وظائف أدواته من القائمة أدناه:",
            parse_mode="HTML",
            reply_markup=tdesc.get_tools_guide_markup()
        )

    @bot.message_handler(commands=["set_gemini_key"])
    def handle_set_gemini_key(message):
        parts = message.text.strip().split(maxsplit=1)
        if len(parts) < 2 or not parts[1].startswith("AIza"):
            bot.reply_to(message, "⚠️ <b>صيغة المفتاح غير واضحة!</b>\nيرجى إرسال الأمر متبوعاً بمفتاحك مباشرة، مثال:\n`/set_gemini_key AIzaSyXXXXXXXXXXXXXXXXXXXXXXXXXXX`\n\n<i>(يمكنك الحصول على المفتاح مجاناً في 10 ثوانٍ من موقع Google AI Studio: https://aistudio.google.com/app/apikey)</i>", parse_mode="HTML")
            return
        import pdf_ai_studio as ai_engine
        ai_engine.set_local_gemini_key(parts[1])
        bot.reply_to(message, "✅ <b>تم حفظ وتفعيل مفتاح Gemini API بنجاح!</b> 🧠✨\n\n🎯 أصبحت الآن جميع أدوات الذكاء الاصطناعي في البوت جاهزة ومفعلة بنسبة 100%:\n• ⚖️ التدقيق القانوني وتحليل العقود والاتفاقيات\n• 💡 التلخيص الذكي الشامل الفوري\n• 🗣️ محاورة وسؤال المستند Q&A\n• ✨ التدقيق اللغوي وإعادة الصياغة\n• 🌐 الترجمة الفورية للمستندات", parse_mode="HTML")

    @bot.message_handler(content_types=["web_app_data"])
    def handle_web_app_data(message):
        data_text = message.web_app_data.data
        bot.send_message(
            message.chat.id,
            f"✅ <b>تم استلام تقرير القياس والمساحة من كاميرا الهاتف (Smart AR Ruler) بنجاح!</b> 📐✨\n━━━━━━━━━━━━━━━━━━\n\n"
            f"<code>{data_text}</code>\n\n"
            f"💡 <i>تم حفظ هذه القياسات بدقة في محادثتك، ويمكنك الرجوع إليها أو مشاركتها في أي وقت!</i>",
            parse_mode="HTML",
            reply_markup=types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="main_menu"))
        )

    @bot.message_handler(content_types=["document", "photo", "audio", "voice", "video"])
    def handle_incoming_files(message):
        chat_id = message.chat.id
        session = get_user_session(chat_id)
        
        status_msg = bot.send_message(chat_id, "📥 <b>جاري استلام وتحليل الملف في معمل السيرفر...</b> ⏳", parse_mode="HTML")
        
        try:
            if message.content_type == "photo":
                file_info = bot.get_file(message.photo[-1].file_id)
                ext = "jpg"
            elif message.content_type == "audio":
                file_info = bot.get_file(message.audio.file_id)
                ext = message.audio.file_name.split(".")[-1].lower() if message.audio.file_name and "." in message.audio.file_name else "mp3"
            elif message.content_type == "voice":
                file_info = bot.get_file(message.voice.file_id)
                ext = "ogg"
            elif message.content_type == "video":
                file_info = bot.get_file(message.video.file_id)
                ext = message.video.file_name.split(".")[-1].lower() if message.video.file_name and "." in message.video.file_name else "mp4"
            else:
                file_info = bot.get_file(message.document.file_id)
                ext = message.document.file_name.split(".")[-1].lower() if "." in message.document.file_name else "pdf"
                
            downloaded = bot.download_file(file_info.file_path)
            local_name = f"user_{chat_id}_{uuid.uuid4().hex[:6]}.{ext}"
            local_path = os.path.join(WORK_DIR, local_name)
            with open(local_path, "wb") as f:
                f.write(downloaded)
                
            session["active_file"] = local_path
            
            if message.content_type in ["audio", "voice", "video"]:
                if session.get("state") == "waiting_qr_media_file":
                    process_media_to_qr_flow(chat_id, local_path, status_msg)
                    session["state"] = "idle"
                else:
                    bot.edit_message_text(
                        f"🎬 <b>تم استلام المقطع بنجاح!</b> 🎵\n"
                        f"👇 <i>اختر الآن الإجراء الذي تريد تنفيذه على هذا المقطع:</i>",
                        chat_id=chat_id, message_id=status_msg.message_id, parse_mode="HTML",
                        reply_markup=get_smart_actions_for_media(local_path, message.content_type)
                    )
            elif ext == "pdf":
                bot.edit_message_text(
                    f"✅ <b>تم استلام مستند الـ PDF بنجاح!</b> 📄\n"
                    f"👇 <i>اختر الآن الإجراء السريع أو الذكي الذي تريد تنفيذه على هذا المستند:</i>",
                    chat_id=chat_id, message_id=status_msg.message_id, parse_mode="HTML",
                    reply_markup=get_smart_actions_for_pdf(local_path)
                )
            elif ext in ["jpg", "jpeg", "png", "webp"]:
                if session.get("state") == "waiting_qr_media_file":
                    process_media_to_qr_flow(chat_id, local_path, status_msg)
                    session["state"] = "idle"
                elif session.get("state") == "waiting_ruler_photo":
                    import pdf_ai_studio as ai_engine
                    bot.edit_message_text("📐 <b>جاري فحص الصورة وحساب الأطوال والمساحة هندسياً عبر الذكاء الاصطناعي...</b> ⏳", chat_id=chat_id, message_id=status_msg.message_id, parse_mode="HTML")
                    report = ai_engine.ai_image_ruler_and_area(local_path)
                    bot.send_message(chat_id, f"📐 <b>تقرير الأطوال والمساحة الهندسي (AI Vision Ruler):</b>\n━━━━━━━━━━━━━━━━━━\n\n{report}", parse_mode="HTML", reply_markup=types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="main_menu")))
                    session["state"] = "idle"
                elif session.get("state") == "waiting_qr_image_decode":
                    import qr_tools
                    bot.edit_message_text("🔍 <b>جاري فحص وقراءة وفك تشفير الباركود من الصورة...</b> ⏳", chat_id=chat_id, message_id=status_msg.message_id, parse_mode="HTML")
                    results = qr_tools.decode_qr_from_image(local_path)
                    if not results:
                        bot.send_message(chat_id, "❌ <b>لم يتم العثور على أي رمز QR أو باركود واضح في هذه الصورة!</b>\nيرجى التأكد من وضوح الصورة وإرسالها مجدداً، أو اختيار أداة أخرى من القائمة الرئيسية.", parse_mode="HTML", reply_markup=types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="main_menu")))
                    else:
                        msg_txt = f"🎯 <b>تم استخراج وفك تشفير محتوى الباركود بنجاح ({len(results)} رمز):</b>\n━━━━━━━━━━━━━━━━━━\n"
                        for idx, item in enumerate(results, 1):
                            msg_txt += f"<b>{idx}. النوع ({item['type']}):</b>\n<code>{item['data']}</code>\n\n"
                        bot.send_message(chat_id, msg_txt, parse_mode="HTML", reply_markup=types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="main_menu")))
                    session["state"] = "idle"
                elif session.get("state") == "collecting_images_for_merge":
                    session["merge_list"].append(local_path)
                    bot.edit_message_text(
                        f"🖼️ <b>تم إضافة الصورة لرقم ({len(session['merge_list'])}) في قائمة الدمج!</b>\n"
                        f"أرسل صورة أخرى، أو اضغط الزر أدناه لإنشاء كتاب الـ PDF الآن:",
                        chat_id=chat_id, message_id=status_msg.message_id, parse_mode="HTML",
                        reply_markup=types.InlineKeyboardMarkup().add(
                            types.InlineKeyboardButton("✨ دمج الصور وتحويلها إلى PDF الآن", callback_data="finish_img_merge")
                        )
                    )
                else:
                    bot.edit_message_text(
                        f"🖼️ <b>تم استلام الصورة بنجاح!</b> 📸\n"
                        f"👇 <i>اختر الإجراء المطلوب (تحويل أو قراءة باركود):</i>",
                        chat_id=chat_id, message_id=status_msg.message_id, parse_mode="HTML",
                        reply_markup=get_smart_actions_for_image(local_path)
                    )
            elif ext in ["doc", "docx"]:
                bot.edit_message_text(
                    f"📝 <b>تم استلام مستند Word بنجاح!</b> 📄\n"
                    f"اضغط الزر أدناه لتحويله فوراً إلى مستند PDF منظم وثابت التنسيق:",
                    chat_id=chat_id, message_id=status_msg.message_id, parse_mode="HTML",
                    reply_markup=types.InlineKeyboardMarkup().add(
                        types.InlineKeyboardButton("🚀 تحويل مستند Word إلى PDF الآن", callback_data="convert_word_pdf")
                    )
                )
            elif ext in ["xls", "xlsx"]:
                bot.edit_message_text(
                    f"📊 <b>تم استلام جدول Excel بنجاح!</b> 📑\n"
                    f"اضغط الزر أدناه لتحويله إلى مستند PDF منسق وسهل القراءة:",
                    chat_id=chat_id, message_id=status_msg.message_id, parse_mode="HTML",
                    reply_markup=types.InlineKeyboardMarkup().add(
                        types.InlineKeyboardButton("🚀 تحويل جدول Excel إلى PDF الآن", callback_data="convert_excel_pdf")
                    )
                )
            else:
                bot.edit_message_text("⚠️ صيغة الملف غير مدعومة مباشرة في الأزرار السريعة، يرجى اختيار الأداة من القائمة الرئيسية أولاً.", chat_id=chat_id, message_id=status_msg.message_id)
        except Exception as e:
            bot.edit_message_text(f"❌ حدث خطأ أثناء استلام أو معالجة الملف: {e}", chat_id=chat_id, message_id=status_msg.message_id)

    @bot.callback_query_handler(func=lambda call: True)
    def handle_all_callbacks(call):
        chat_id = call.message.chat.id
        data = call.data
        session = get_user_session(chat_id)
        
        # استيراد وحدات العمل
        import pdf_core_tools as core
        import pdf_converters as conv
        import pdf_ai_studio as ai_engine
        import qr_tools

        if data == "ignore":
            bot.answer_callback_query(call.id, "👆 هذا عنوان قسم، اختر إحدى الأدوات الموجودة أسفله مباشرة:")
            return

        elif data == "main_menu":
            bot.edit_message_text(
                "🏠 <b>القائمة الشاملة لبوت الأدوات الذكية (Smart Tools) ومعمل الـ PDF:</b>\n\n"
                "اختر الأداة المطلوبة من القائمة أدناه، أو أرسل ملفك مباشرة:",
                chat_id=chat_id, message_id=call.message.message_id, parse_mode="HTML",
                reply_markup=get_main_menu_markup()
            )
            return

        elif data == "open_tools_guide":
            import tools_descriptions as tdesc
            bot.edit_message_text(
                "📚 <b>موسوعة ودليل وظائف جميع أدوات البوت والـ QR (36+ أداة):</b>\n\n"
                "اختر القسم الذي تريد معرفة تفاصيل وشرح وظائف أدواته من القائمة أدناه:",
                chat_id=chat_id, message_id=call.message.message_id, parse_mode="HTML",
                reply_markup=tdesc.get_tools_guide_markup()
            )
            return

        elif data.startswith("guide_sec_"):
            import tools_descriptions as tdesc
            bot.edit_message_text(
                tdesc.get_category_guide_text(data),
                chat_id=chat_id, message_id=call.message.message_id, parse_mode="HTML",
                reply_markup=tdesc.get_tools_guide_markup()
            )
            return

        elif data in ["qr_text_url", "qr_whatsapp", "qr_wifi", "qr_vcard", "qr_custom_color", "qr_decode_action", "qr_media_file"]:
            import tools_descriptions as tdesc
            info = tdesc.TOOL_DETAILS.get(data)
            bot.answer_callback_query(call.id, f"✅ تم اختيار: {info['title'][:20] if info else 'أداة QR'}...")
            if data == "qr_text_url":
                session["state"] = "waiting_qr_text_url"
            elif data == "qr_whatsapp":
                session["state"] = "waiting_qr_whatsapp"
            elif data == "qr_wifi":
                session["state"] = "waiting_qr_wifi"
            elif data == "qr_vcard":
                session["state"] = "waiting_qr_vcard"
            elif data == "qr_custom_color":
                session["state"] = "waiting_qr_custom_color"
            elif data == "qr_decode_action":
                session["state"] = "waiting_qr_image_decode"
            elif data == "qr_media_file":
                session["state"] = "waiting_qr_media_file"
                
            if info:
                bot.send_message(
                    chat_id,
                    f"🛠️ <b>{info['title']}</b>\n"
                    f"━━━━━━━━━━━━━━━━━━\n\n"
                    f"📖 <b>وظيفة الأداة وتفاصيلها:</b>\n"
                    f"{info['desc']}\n\n"
                    f"📌 <b>ما المطلوب منك الآن لإتمام العمل؟</b>\n"
                    f"{info['input_need']}",
                    parse_mode="HTML"
                )
            return

        elif data == "qr_decode_img":
            if not session.get("active_file") or not os.path.exists(session["active_file"]):
                bot.answer_callback_query(call.id, "❌ يرجى إرسال الصورة أولاً!")
                return
            bot.answer_callback_query(call.id, "🔍 جاري قراءة وفك تشفير الباركود...")
            status = bot.send_message(chat_id, "⏳ <b>جاري فحص وقراءة وفك تشفير الباركود والـ QR الموجود في الصورة...</b> 🔍", parse_mode="HTML")
            results = qr_tools.decode_qr_from_image(session["active_file"])
            bot.delete_message(chat_id, status.message_id)
            if not results:
                bot.send_message(chat_id, "❌ <b>لم يتم العثور على أي باركود أو رمز QR واضح في هذه الصورة!</b>\nيرجى التأكد من وضوح الرمز وإرسال الصورة مجدداً.", parse_mode="HTML", reply_markup=types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="main_menu")))
            else:
                msg_txt = f"🎯 <b>تم استخراج محتوى الباركود بنجاح ({len(results)} رمز):</b>\n━━━━━━━━━━━━━━━━━━\n"
                for idx, item in enumerate(results, 1):
                    msg_txt += f"<b>{idx}. ({item['type']}):</b>\n<code>{item['data']}</code>\n\n"
                bot.send_message(chat_id, msg_txt, parse_mode="HTML", reply_markup=types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="main_menu")))
            return

        elif data == "qr_convert_active_media":
            if not session.get("active_file") or not os.path.exists(session["active_file"]):
                bot.answer_callback_query(call.id, "❌ يرجى إرسال المقطع أو الصورة أولاً!")
                return
            bot.answer_callback_query(call.id, "🚀 جاري توليد باركود الـ QR الدائم...")
            status = bot.send_message(chat_id, "⏳ <b>جاري رفع المقطع إلى السحابة وتوليد باركود QR دائم للمشاهدة/الاستماع المباشر...</b> 🚀🔳", parse_mode="HTML")
            try:
                out_qr = os.path.join(WORK_DIR, f"qr_media_{uuid.uuid4().hex[:6]}.png")
                _, cloud_url = qr_tools.convert_media_to_qr(session["active_file"], out_qr)
                bot.delete_message(chat_id, status.message_id)
                with open(out_qr, "rb") as f:
                    bot.send_photo(chat_id, f, caption=f"✅ <b>تم تحويل المقطع/الصورة إلى باركود QR دائم للمشاركة السريعة بنجاح!</b> 🎬🔳✨\n\n🌐 <b>الرابط المباشر الدائم للمشاهدة/الاستماع:</b>\n`{cloud_url}`\n\n⚡ <i>بمسح هذا الرمز بكاميرا أي هاتف في العالم، سيتم فتح وتشغيل المقطع أو الصورة فوراً!</i>", parse_mode="HTML", reply_markup=types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="main_menu")))
            except Exception as e:
                bot.edit_message_text(f"❌ خطأ أثناء إنشاء باركود الـ QR: {e}", chat_id=chat_id, message_id=status.message_id)
            return

        elif data == "ruler_from_photo":
            session["state"] = "waiting_ruler_photo"
            bot.answer_callback_query(call.id, "📸 تم اختيار وضع القياس من صورة")
            bot.send_message(
                chat_id,
                "📸 <b>قياس الأطوال والمساحة من صورة عبر الذكاء الاصطناعي (AI Vision Ruler):</b>\n\n"
                "✏️ أرسل الآن صورة الغرفة، السطح، أو الشيء الذي تريد قياس أبعاده ومساحته (ويفضل وجود عنصر معروف مثل ورقة A4 أو بطاقة أو بلاطة بجانبه للمعايرة الدقيقة):",
                parse_mode="HTML"
            )
            return

        elif data == "img_ai_ruler":
            if not session.get("active_file") or not os.path.exists(session["active_file"]):
                bot.answer_callback_query(call.id, "❌ يرجى إرسال الصورة أولاً!")
                return
            bot.answer_callback_query(call.id, "📐 جاري حساب الأطوال والمساحة...")
            status = bot.send_message(chat_id, "📐 <b>جاري فحص الصورة وحساب الأطوال والمساحة هندسياً عبر الذكاء الاصطناعي...</b> ⏳", parse_mode="HTML")
            import pdf_ai_studio as ai_engine
            report = ai_engine.ai_image_ruler_and_area(session["active_file"])
            bot.edit_message_text(f"📐 <b>تقرير الأطوال والمساحة الهندسي (AI Vision Ruler):</b>\n━━━━━━━━━━━━━━━━━━\n\n{report}", chat_id=chat_id, message_id=status.message_id, parse_mode="HTML", reply_markup=types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="main_menu")))
            return

        elif data.startswith("tool_"):
            # إذا اختار أداة من القائمة الشاملة قبل إرسال الملف
            if not session.get("active_file") or not os.path.exists(session["active_file"]):
                session["state"] = data
                import tools_descriptions as tdesc
                info = tdesc.TOOL_DETAILS.get(data)
                bot.answer_callback_query(call.id, f"✅ تم اختيار: {info['title'][:20] if info else data}...")
                if info:
                    if data == "tool_ruler":
                        render_url = os.environ.get("RENDER_EXTERNAL_URL", "https://smart-tools-pdf-bot.onrender.com")
                        ruler_markup = types.InlineKeyboardMarkup(row_width=1)
                        ruler_markup.add(
                            types.InlineKeyboardButton("📲 1. فتح كاميرا القياس مباشرة (Telegram WebApp)", web_app=types.WebAppInfo(url=f"{render_url}/ruler")),
                            types.InlineKeyboardButton("🌐 2. فتح كاميرا القياس في متصفح الهاتف (سفاري/كروم)", url=f"{render_url}/ruler"),
                            types.InlineKeyboardButton("📸 3. قياس أطوال ومساحة من صورة (AI Vision Ruler)", callback_data="ruler_from_photo"),
                            types.InlineKeyboardButton("🔙 العودة للقائمة الرئيسية", callback_data="main_menu")
                        )
                        bot.send_message(
                            chat_id,
                            f"🛠️ <b>{info['title']}</b>\n"
                            f"━━━━━━━━━━━━━━━━━━\n\n"
                            f"📖 <b>وظيفة الأداة وتفاصيلها:</b>\n"
                            f"{info['desc']}\n\n"
                            f"📌 <b>اختر الآن طريقة القياس وتشغيل الكاميرا من الأزرار أدناه:</b>",
                            parse_mode="HTML",
                            reply_markup=ruler_markup
                        )
                    else:
                        bot.send_message(
                            chat_id,
                            f"🛠️ <b>{info['title']}</b>\n"
                            f"━━━━━━━━━━━━━━━━━━\n\n"
                            f"📖 <b>وظيفة الأداة وتفاصيلها:</b>\n"
                            f"{info['desc']}\n\n"
                            f"📌 <b>ما المطلوب منك الآن لإتمام العمل؟</b>\n"
                            f"{info['input_need']}",
                            parse_mode="HTML"
                        )
                else:
                    bot.send_message(
                        chat_id,
                        f"🎯 <b>لقد اخترت الأداة:</b> `{data}`\n\n"
                        f"📤 <i>أرسل الآن ملف الـ `PDF` أو `الصورة` أو `المستند` المطلوب لنقوم بتنفيذ هذه الأداة عليه فوراً!</i>",
                        parse_mode="HTML"
                    )
                return

        elif data in ["quick_compress", "tool_compress"]:
            if not session.get("active_file") or not os.path.exists(session["active_file"]):
                bot.answer_callback_query(call.id, "❌ يرجى إرسال ملف الـ PDF أولاً!")
                return
            bot.answer_callback_query(call.id, "🗜️ جاري ضغط وتحسين حجم الملف...")
            status = bot.send_message(chat_id, "⏳ <b>جاري ضغط حجم مستند الـ PDF بأقصى جودة قراءة...</b> 🗜️", parse_mode="HTML")
            out_path = os.path.join(WORK_DIR, f"compressed_{uuid.uuid4().hex[:6]}.pdf")
            core.compress_pdf(session["active_file"], out_path)
            with open(out_path, "rb") as f:
                bot.send_document(chat_id, f, caption="✅ <b>تم ضغط وتقليل حجم الملف بنجاح!</b> 🗜️✨", parse_mode="HTML")
            bot.delete_message(chat_id, status.message_id)

        elif data in ["quick_to_word", "tool_pdf2word"]:
            if not session.get("active_file") or not os.path.exists(session["active_file"]):
                bot.answer_callback_query(call.id, "❌ يرجى إرسال ملف الـ PDF أولاً!")
                return
            bot.answer_callback_query(call.id, "📝 جاري تحويل الـ PDF إلى Word...")
            status = bot.send_message(chat_id, "⏳ <b>جاري تحويل نصوص المستند إلى ملف Word (`.docx`)...</b> 📝", parse_mode="HTML")
            out_path = os.path.join(WORK_DIR, f"converted_{uuid.uuid4().hex[:6]}.docx")
            conv.pdf_to_word_text(session["active_file"], out_path)
            with open(out_path, "rb") as f:
                bot.send_document(chat_id, f, caption="✅ <b>تم تحويل المستند إلى Word بنجاح وسهولة التعديل!</b> 📝✨", parse_mode="HTML")
            bot.delete_message(chat_id, status.message_id)

        elif data in ["quick_to_img", "tool_pdf2img"]:
            if not session.get("active_file") or not os.path.exists(session["active_file"]):
                bot.answer_callback_query(call.id, "❌ يرجى إرسال ملف الـ PDF أولاً!")
                return
            bot.answer_callback_query(call.id, "🖼️ جاري تحويل الصفحات إلى صور عالية الدقة...")
            status = bot.send_message(chat_id, "⏳ <b>جاري استخراج وتحويل جميع صفحات الـ PDF إلى صور (`JPG`)...</b> 🖼️", parse_mode="HTML")
            imgs = conv.pdf_to_images(session["active_file"], WORK_DIR)
            for idx, img in enumerate(imgs[:10], start=1):
                with open(img, "rb") as f:
                    bot.send_photo(chat_id, f, caption=f"📄 صفحة رقم {idx}")
            if len(imgs) > 10:
                bot.send_message(chat_id, f"ℹ️ تم إرسال أول 10 صفحات لك من إجمالي ({len(imgs)}) صفحة.")
            bot.delete_message(chat_id, status.message_id)

        elif data == "quick_ai_sum":
            if not session.get("active_file") or not os.path.exists(session["active_file"]):
                import tools_descriptions as tdesc
                info = tdesc.TOOL_DETAILS.get("quick_ai_sum")
                session["state"] = "quick_ai_sum"
                bot.answer_callback_query(call.id, f"✅ تم اختيار: {info['title'][:20]}...")
                bot.send_message(chat_id, f"🛠️ <b>{info['title']}</b>\n━━━━━━━━━━━━━━━━━━\n\n📖 <b>وظيفة الأداة وتفاصيلها:</b>\n{info['desc']}\n\n📌 <b>ما المطلوب منك الآن لإتمام العمل؟</b>\n{info['input_need']}", parse_mode="HTML")
                return
            bot.answer_callback_query(call.id, "💡 جاري تحليل التلخيص بالذكاء الاصطناعي...")
            status = bot.send_message(chat_id, "🧠 <b>جاري دراسة نصوص المستند وتوليد الملخص المركز عبر الذكاء الاصطناعي...</b> ⏳", parse_mode="HTML")
            summary = ai_engine.ai_summarize_pdf(session["active_file"])
            session["last_summary"] = summary
            bot.edit_message_text(
                f"💡 <b>الملخص الذكي الشامل للمستند:</b>\n\n{summary}\n\n👇 <i>يمكنك تحويل هذا الملخص إلى استماع صوتي عبر الزر أدناه:</i>",
                chat_id=chat_id, message_id=status.message_id, parse_mode="HTML",
                reply_markup=types.InlineKeyboardMarkup().add(
                    types.InlineKeyboardButton("🎧 تفريغ الملخص إلى استماع صوتي MP3", callback_data="quick_speech"),
                    types.InlineKeyboardButton("🔙 قائمة خيارات الملف", callback_data="show_active_options")
                )
            )

        elif data == "quick_speech":
            summary = session.get("last_summary")
            if not summary:
                if not session.get("active_file") or not os.path.exists(session["active_file"]):
                    import tools_descriptions as tdesc
                    info = tdesc.TOOL_DETAILS.get("quick_speech")
                    session["state"] = "quick_speech"
                    bot.answer_callback_query(call.id, f"✅ تم اختيار: {info['title'][:20]}...")
                    bot.send_message(chat_id, f"🛠️ <b>{info['title']}</b>\n━━━━━━━━━━━━━━━━━━\n\n📖 <b>وظيفة الأداة وتفاصيلها:</b>\n{info['desc']}\n\n📌 <b>ما المطلوب منك الآن لإتمام العمل؟</b>\n{info['input_need']}", parse_mode="HTML")
                    return
                bot.answer_callback_query(call.id, "⏳ جاري التلخيص أولاً ثم التحويل للصوت...")
                status = bot.send_message(chat_id, "⏳ <b>جاري إعداد الملخص وتحويله إلى مقطع استماع صوتي فائق الوضوح...</b> 🎧", parse_mode="HTML")
                summary = ai_engine.ai_summarize_pdf(session["active_file"])
            else:
                status = bot.send_message(chat_id, "🎧 <b>جاري تسجيل وهندسة الملف الصوتي الآن...</b> ⏳", parse_mode="HTML")
                
            out_mp3 = os.path.join(WORK_DIR, f"speech_{uuid.uuid4().hex[:6]}.mp3")
            ai_engine.ai_pdf_to_speech(summary, out_mp3)
            with open(out_mp3, "rb") as f:
                bot.send_audio(chat_id, f, caption="🎧 <b>الاستماع الصوتي لملخص ومحتوى المستند</b> ✨", parse_mode="HTML")
            bot.delete_message(chat_id, status.message_id)

        elif data == "quick_ai_qa":
            if not session.get("active_file") or not os.path.exists(session["active_file"]):
                import tools_descriptions as tdesc
                info = tdesc.TOOL_DETAILS.get("quick_ai_qa")
                session["state"] = "quick_ai_qa"
                bot.answer_callback_query(call.id, f"✅ تم اختيار: {info['title'][:20]}...")
                bot.send_message(chat_id, f"🛠️ <b>{info['title']}</b>\n━━━━━━━━━━━━━━━━━━\n\n📖 <b>وظيفة الأداة وتفاصيلها:</b>\n{info['desc']}\n\n📌 <b>ما المطلوب منك الآن لإتمام العمل؟</b>\n{info['input_need']}", parse_mode="HTML")
                return
            session["state"] = "waiting_pdf_question"
            bot.send_message(
                chat_id,
                "❓ <b>وضع الحوار مع المستند (PDF Q&A):</b>\n\n"
                "✏️ أرسل لي الآن أي سؤال يخطر ببالك حول الأرقام، البنود، أو المعلومات الموجودة في هذا الملف وسأجيبك فوراً من سياقه الدقيق:",
                parse_mode="HTML"
            )

        elif data == "quick_ai_audit":
            if not session.get("active_file") or not os.path.exists(session["active_file"]):
                import tools_descriptions as tdesc
                info = tdesc.TOOL_DETAILS.get("quick_ai_audit")
                session["state"] = "quick_ai_audit"
                bot.answer_callback_query(call.id, f"✅ تم اختيار: {info['title'][:20]}...")
                bot.send_message(chat_id, f"🛠️ <b>{info['title']}</b>\n━━━━━━━━━━━━━━━━━━\n\n📖 <b>وظيفة الأداة وتفاصيلها:</b>\n{info['desc']}\n\n📌 <b>ما المطلوب منك الآن لإتمام العمل؟</b>\n{info['input_need']}", parse_mode="HTML")
                return
            bot.answer_callback_query(call.id, "⚖️ جاري التحليل القانوني الذكي...")
            status = bot.send_message(chat_id, "⚖️ <b>جاري دراسة بنود العقد واكتشاف البنود الحساسة والثغرات (Red Flags)...</b> ⏳", parse_mode="HTML")
            report = ai_engine.ai_contract_auditor(session["active_file"])
            bot.edit_message_text(f"⚖️ <b>تقرير التدقيق القانوني والتجاري للمستند:</b>\n\n{report}", chat_id=chat_id, message_id=status.message_id, parse_mode="HTML")

        elif data == "quick_ai_proof":
            if not session.get("active_file") or not os.path.exists(session["active_file"]):
                import tools_descriptions as tdesc
                info = tdesc.TOOL_DETAILS.get("quick_ai_proof")
                session["state"] = "quick_ai_proof"
                bot.answer_callback_query(call.id, f"✅ تم اختيار: {info['title'][:20]}...")
                bot.send_message(chat_id, f"🛠️ <b>{info['title']}</b>\n━━━━━━━━━━━━━━━━━━\n\n📖 <b>وظيفة الأداة وتفاصيلها:</b>\n{info['desc']}\n\n📌 <b>ما المطلوب منك الآن لإتمام العمل؟</b>\n{info['input_need']}", parse_mode="HTML")
                return
            bot.answer_callback_query(call.id, "✨ جاري التدقيق وإعادة الصياغة...")
            status = bot.send_message(chat_id, "✨ <b>جاري تدقيق النصوص لغوياً ونحوياً وإعادة صياغة الجمل الضعيفة...</b> ⏳", parse_mode="HTML")
            corrected = ai_engine.ai_grammar_proofread(session["active_file"])
            bot.edit_message_text(f"✨ <b>النص المصحح والمعاد صياغته باحترافية:</b>\n\n{corrected[:4000]}", chat_id=chat_id, message_id=status.message_id, parse_mode="HTML")

        elif data == "show_active_options":
            if session.get("active_file") and os.path.exists(session["active_file"]):
                bot.edit_message_text("👆 <i>قائمة أدوات المستند النشط:</i>", chat_id=chat_id, message_id=call.message.message_id, parse_mode="HTML", reply_markup=get_smart_actions_for_pdf(session["active_file"]))

    @bot.message_handler(func=lambda message: True)
    def handle_text_inputs(message):
        chat_id = message.chat.id
        text = message.text.strip()
        session = get_user_session(chat_id)
        
        import pdf_ai_studio as ai_engine
        
        if session.get("state") == "waiting_pdf_question":
            if not session.get("active_file") or not os.path.exists(session["active_file"]):
                bot.send_message(chat_id, "❌ الملف المختار لم يعد موجوداً في الذاكرة، يرجى إرساله مجدداً.")
                session["state"] = "idle"
                return
            status = bot.send_message(chat_id, "💡 <b>جاري البحث في أعماق المستند عن جواب سؤالك...</b> ⏳", parse_mode="HTML")
            ans = ai_engine.ai_pdf_qa(session["active_file"], text)
            bot.delete_message(chat_id, status.message_id)
            bot.send_message(
                chat_id,
                f"❓ <b>سؤالك:</b> {text}\n\n💡 <b>جواب المساعد الذكي من المستند:</b>\n{ans}\n\n👇 <i>يمكنك إرسال سؤال آخر عن نفس الملف مباشرة، أو الضغط أدناه للعودة:</i>",
                parse_mode="HTML",
                reply_markup=types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("🔙 العودة لأدوات الملف", callback_data="show_active_options"))
            )
            return

        import qr_tools

        if session.get("state") == "waiting_qr_text_url":
            status = bot.send_message(chat_id, "⏳ <b>جاري رسم وإنشاء باركود الـ QR...</b> 🔳", parse_mode="HTML")
            out_path = os.path.join(WORK_DIR, f"qr_{uuid.uuid4().hex[:6]}.png")
            qr_tools.generate_qr_code(text, out_path)
            bot.delete_message(chat_id, status.message_id)
            with open(out_path, "rb") as f:
                bot.send_photo(chat_id, f, caption=f"✅ <b>تم إنشاء رمز الـ QR بنجاح!</b> 🔳✨\n\n📝 <b>المحتوى:</b>\n`{text}`", parse_mode="HTML", reply_markup=types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="main_menu")))
            session["state"] = "idle"
            return

        elif session.get("state") == "waiting_qr_whatsapp":
            status = bot.send_message(chat_id, "⏳ <b>جاري إنشاء باركود الواتساب...</b> 🔳", parse_mode="HTML")
            parts = [p.strip() for p in text.split(",", 1)]
            phone = parts[0]
            msg = parts[1] if len(parts) > 1 else ""
            url = qr_tools.create_whatsapp_data(phone, msg)
            out_path = os.path.join(WORK_DIR, f"qr_wa_{uuid.uuid4().hex[:6]}.png")
            qr_tools.generate_qr_code(url, out_path)
            bot.delete_message(chat_id, status.message_id)
            with open(out_path, "rb") as f:
                bot.send_photo(chat_id, f, caption=f"✅ <b>تم إنشاء باركود الواتساب المباشر بنجاح!</b> 💬✨\n\n📱 <b>الرقم:</b> `{phone}`\n🌐 <b>الرابط المباشر:</b>\n`{url}`", parse_mode="HTML", reply_markup=types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="main_menu")))
            session["state"] = "idle"
            return

        elif session.get("state") == "waiting_qr_wifi":
            status = bot.send_message(chat_id, "⏳ <b>جاري إنشاء باركود الواي فاي (WiFi QR)...</b> 🔳", parse_mode="HTML")
            parts = [p.strip() for p in text.split(",", 1)]
            ssid = parts[0]
            pwd = parts[1] if len(parts) > 1 else ""
            wifi_data = qr_tools.create_wifi_data(ssid, pwd)
            out_path = os.path.join(WORK_DIR, f"qr_wifi_{uuid.uuid4().hex[:6]}.png")
            qr_tools.generate_qr_code(wifi_data, out_path)
            bot.delete_message(chat_id, status.message_id)
            with open(out_path, "rb") as f:
                bot.send_photo(chat_id, f, caption=f"✅ <b>تم إنشاء باركود الاتصال السريع بالواي فاي بنجاح!</b> 📶✨\n\n📡 <b>اسم الشبكة:</b> `{ssid}`\n🔑 <i>بمسح الرمز سيتصل الهاتف بالشبكة حالاً دون كتابة كلمة السر!</i>", parse_mode="HTML", reply_markup=types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="main_menu")))
            session["state"] = "idle"
            return

        elif session.get("state") == "waiting_qr_vcard":
            status = bot.send_message(chat_id, "⏳ <b>جاري إنشاء بطاقة الأعمال الرقمية (vCard QR)...</b> 🔳", parse_mode="HTML")
            parts = [p.strip() for p in text.split(",")]
            name = parts[0]
            phone = parts[1] if len(parts) > 1 else ""
            email = parts[2] if len(parts) > 2 else ""
            vcard_data = qr_tools.create_vcard_data(name, phone, email)
            out_path = os.path.join(WORK_DIR, f"qr_vcard_{uuid.uuid4().hex[:6]}.png")
            qr_tools.generate_qr_code(vcard_data, out_path)
            bot.delete_message(chat_id, status.message_id)
            with open(out_path, "rb") as f:
                bot.send_photo(chat_id, f, caption=f"✅ <b>تم إنشاء بطاقة الأعمال الرقمية (vCard) بنجاح!</b> 📇✨\n\n👤 <b>الاسم:</b> {name}\n📱 <b>الهاتف:</b> `{phone}`\n<i>بمسح الرمز سيظهر خيار حفظ جهة الاتصال بالهاتف فوراً!</i>", parse_mode="HTML", reply_markup=types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="main_menu")))
            session["state"] = "idle"
            return

        elif session.get("state") == "waiting_qr_custom_color":
            status = bot.send_message(chat_id, "⏳ <b>جاري إنشاء باركود الـ QR الملون...</b> 🎨🔳", parse_mode="HTML")
            parts = [p.strip() for p in text.rsplit(",", 1)]
            content_data = parts[0]
            color_name = parts[1].lower() if len(parts) > 1 and parts[1] else "blue"
            out_path = os.path.join(WORK_DIR, f"qr_color_{uuid.uuid4().hex[:6]}.png")
            try:
                qr_tools.generate_qr_code(content_data, out_path, fill_color=color_name, back_color="white")
            except Exception:
                qr_tools.generate_qr_code(content_data, out_path, fill_color="black", back_color="white")
            bot.delete_message(chat_id, status.message_id)
            with open(out_path, "rb") as f:
                bot.send_photo(chat_id, f, caption=f"✅ <b>تم إنشاء باركود الـ QR باللون ({color_name}) بنجاح!</b> 🎨✨\n\n📝 <b>المحتوى:</b>\n`{content_data}`", parse_mode="HTML", reply_markup=types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="main_menu")))
            session["state"] = "idle"
            return


def run_polling():
    if not bot:
        print("[ERROR] TELEGRAM_BOT_TOKEN missing.")
        return
    while True:
        try:
            print("[INFO] PDF Toolkit & AI Studio Bot is polling Telegram...")
            bot.infinity_polling(timeout=60, long_polling_timeout=60)
        except Exception as e:
            print(f"[ERROR] Restart polling due to: {e}")
            time.sleep(5)

RULER_HTML = """<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>📐 مسطرة وكاميرا قياس الأطوال والمساحة الذكية (Smart AR Ruler)</title>
    <script src="https://telegram.org/js/telegram-web-app.js"></script>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; -webkit-tap-highlight-color: transparent; }
        body { background: #0b0f19; color: #ffffff; overflow: hidden; height: 100vh; width: 100vw; display: flex; flex-direction: column; }
        #camera-container { position: relative; flex: 1; width: 100%; overflow: hidden; background: #111; display: flex; align-items: center; justify-content: center; }
        video { position: absolute; width: 100%; height: 100%; object-fit: cover; }
        canvas { position: absolute; top: 0; left: 0; width: 100%; height: 100%; z-index: 10; cursor: crosshair; }
        
        .header-bar { position: absolute; top: 0; left: 0; right: 0; z-index: 20; background: rgba(11, 15, 25, 0.85); backdrop-filter: blur(10px); padding: 12px 16px; border-bottom: 1px solid rgba(255,255,255,0.1); display: flex; flex-direction: column; gap: 8px; }
        .title-row { display: flex; justify-content: space-between; align-items: center; }
        .title-row h1 { font-size: 16px; color: #00f2fe; display: flex; align-items: center; gap: 6px; }
        .points-badge { background: #1e293b; padding: 4px 10px; border-radius: 20px; font-size: 13px; font-weight: bold; border: 1px solid #38bdf8; color: #38bdf8; }
        
        .stats-box { background: rgba(30, 41, 59, 0.9); border: 1px solid rgba(0, 242, 254, 0.4); border-radius: 12px; padding: 10px 14px; font-size: 14px; box-shadow: 0 4px 15px rgba(0,0,0,0.5); }
        .stats-row { display: flex; justify-content: space-between; margin-bottom: 4px; }
        .stats-row:last-child { margin-bottom: 0; }
        .stat-val { color: #38bdf8; font-weight: bold; }
        
        .calibration-bar { position: absolute; bottom: 85px; left: 10px; right: 10px; z-index: 20; background: rgba(15, 23, 42, 0.9); backdrop-filter: blur(10px); border: 1px solid rgba(255,255,255,0.15); border-radius: 14px; padding: 10px 14px; display: flex; flex-direction: column; gap: 8px; }
        .cal-header { font-size: 12px; color: #94a3b8; display: flex; justify-content: space-between; }
        .cal-buttons { display: flex; gap: 6px; overflow-x: auto; padding-bottom: 2px; }
        .cal-btn { background: #334155; border: none; color: white; padding: 6px 12px; border-radius: 8px; font-size: 12px; white-space: nowrap; cursor: pointer; transition: 0.2s; }
        .cal-btn.active { background: #00f2fe; color: #0f172a; font-weight: bold; box-shadow: 0 0 10px rgba(0,242,254,0.5); }
        .slider-row { display: flex; align-items: center; gap: 10px; }
        .slider-row input[type=range] { flex: 1; accent-color: #00f2fe; }
        
        .bottom-actions { position: absolute; bottom: 12px; left: 12px; right: 12px; z-index: 20; display: flex; gap: 10px; }
        .action-btn { flex: 1; padding: 12px; border-radius: 12px; border: none; font-weight: bold; font-size: 14px; cursor: pointer; display: flex; align-items: center; justify-content: center; gap: 6px; transition: 0.2s; box-shadow: 0 4px 12px rgba(0,0,0,0.4); }
        .btn-reset { background: #ef4444; color: white; }
        .btn-custom { background: #3b82f6; color: white; }
        .btn-send { background: #10b981; color: white; }
        .action-btn:active { transform: scale(0.97); }
    </style>
</head>
<body>
    <div id="camera-container">
        <video id="cameraVideo" autoplay playsinline></video>
        <canvas id="overlayCanvas"></canvas>
        
        <div class="header-bar">
            <div class="title-row">
                <h1>📐 مسطرة وكاميرا القياس الذكية</h1>
                <span class="points-badge" id="pointsCount">النقاط: 0 / 4</span>
            </div>
            <div class="stats-box" id="statsBox">
                <div class="stats-row"><span>ℹ️ الإرشاد:</span><span class="stat-val" id="guidanceText">اضغط على الشاشة لتحديد النقطة 1</span></div>
                <div class="stats-row" id="lengthRow" style="display:none;"><span>📏 الطول والمسافة:</span><span class="stat-val" id="lengthVal">0 سم</span></div>
                <div class="stats-row" id="areaRow" style="display:none;"><span>🔲 المساحة المقدرة:</span><span class="stat-val" id="areaVal">0 م²</span></div>
            </div>
        </div>

        <div class="calibration-bar">
            <div class="cal-header">
                <span>🎯 وضع المعايرة (لضبط دقة القياس الحقيقي):</span>
                <span id="scaleDisplay">30 بيكسل = 1 سم</span>
            </div>
            <div class="cal-buttons">
                <button class="cal-btn active" onclick="setPreset('card', this)">💳 بطاقة (8.5 سم)</button>
                <button class="cal-btn" onclick="setPreset('a4', this)">📄 ورقة A4 (21 سم)</button>
                <button class="cal-btn" onclick="setPreset('tile40', this)">🔲 بلاطة (40 سم)</button>
                <button class="cal-btn" onclick="setPreset('door90', this)">🚪 باب (90 سم)</button>
            </div>
            <div class="slider-row">
                <span style="font-size:11px; color:#cbd5e1;">تعديل المقياس:</span>
                <input type="range" id="scaleSlider" min="5" max="150" value="30" oninput="updateScaleFromSlider(this.value)">
            </div>
        </div>

        <div class="bottom-actions">
            <button class="action-btn btn-reset" onclick="resetPoints()">🔄 مسح النقاط</button>
            <button class="action-btn btn-custom" onclick="calibrateManual()">✏️ إدخال طول معلوم</button>
            <button class="action-btn btn-send" onclick="sendReportToBot()">📤 إرسال للبوت</button>
        </div>
    </div>

    <script>
        const video = document.getElementById('cameraVideo');
        const canvas = document.getElementById('overlayCanvas');
        const ctx = canvas.getContext('2d');
        let points = [];
        let pixelsPerCm = 30.0;
        
        async function startCamera() {
            try {
                const stream = await navigator.mediaDevices.getUserMedia({
                    video: { facingMode: { exact: "environment" }, width: { ideal: 1920 }, height: { ideal: 1080 } }
                });
                video.srcObject = stream;
            } catch (err) {
                try {
                    const streamFallback = await navigator.mediaDevices.getUserMedia({
                        video: { facingMode: "environment" }
                    });
                    video.srcObject = streamFallback;
                } catch (e) {
                    alert('⚠️ يرجى السماح للمتصفح أو التليجرام بالوصول لكاميرا الهاتف لعمل المسطرة الذكية.');
                }
            }
        }

        function resizeCanvas() {
            canvas.width = canvas.parentElement.clientWidth;
            canvas.height = canvas.parentElement.clientHeight;
            draw();
        }
        window.addEventListener('resize', resizeCanvas);

        canvas.addEventListener('click', (e) => {
            if (points.length >= 4) {
                alert('⚠️ تم الوصول للحد الأقصى (4 نقاط). يمكنك مسح النقاط وحساب أبعاد جديدة أو تعديل المعايرة.');
                return;
            }
            const rect = canvas.getBoundingClientRect();
            const x = e.clientX - rect.left;
            const y = e.clientY - rect.top;
            points.push({x, y});
            updateStats();
            draw();
        });

        function resetPoints() {
            points = [];
            updateStats();
            draw();
        }

        function setPreset(type, btn) {
            document.querySelectorAll('.cal-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            if (type === 'card') pixelsPerCm = 35.0;
            else if (type === 'a4') pixelsPerCm = 25.0;
            else if (type === 'tile40') pixelsPerCm = 15.0;
            else if (type === 'door90') pixelsPerCm = 10.0;
            document.getElementById('scaleSlider').value = pixelsPerCm;
            document.getElementById('scaleDisplay').innerText = `${pixelsPerCm.toFixed(1)} بيكسل = 1 سم`;
            updateStats();
            draw();
        }

        function updateScaleFromSlider(val) {
            pixelsPerCm = parseFloat(val);
            document.getElementById('scaleDisplay').innerText = `${pixelsPerCm.toFixed(1)} بيكسل = 1 سم`;
            updateStats();
            draw();
        }

        function calibrateManual() {
            if (points.length < 2) {
                alert('⚠️ يرجى تحديد نقطتين (1 و 2) على جسم أو مسافة تعرف طولها الحقيقي أولاً قبل إدخال الطول المعلوم.');
                return;
            }
            const distPx = Math.hypot(points[1].x - points[0].x, points[1].y - points[0].y);
            const knownCm = prompt('📏 أدخل الطول الحقيقي بين النقطة 1 والنقطة 2 بالسنتيمتر (مثلاً: 30 أو 100 أو 250):', '30');
            if (knownCm && !isNaN(knownCm) && parseFloat(knownCm) > 0) {
                pixelsPerCm = distPx / parseFloat(knownCm);
                document.getElementById('scaleSlider').value = Math.min(150, Math.max(5, pixelsPerCm));
                document.getElementById('scaleDisplay').innerText = `${pixelsPerCm.toFixed(1)} بيكسل = 1 سم`;
                updateStats();
                draw();
                alert(`✅ تم ضبط المعايرة بنجاح! الآن أصبح الطول بين 1 و 2 بالضبط ${parseFloat(knownCm)} سم.`);
            }
        }

        function updateStats() {
            document.getElementById('pointsCount').innerText = `النقاط: ${points.length} / 4`;
            const gText = document.getElementById('guidanceText');
            const lRow = document.getElementById('lengthRow');
            const lVal = document.getElementById('lengthVal');
            const aRow = document.getElementById('areaRow');
            const aVal = document.getElementById('areaVal');

            if (points.length === 0) {
                gText.innerText = 'اضغط على الكاميرا لتحديد النقطة الأولى (1)';
                lRow.style.display = 'none';
                aRow.style.display = 'none';
            } else if (points.length === 1) {
                gText.innerText = 'اضغط لتحديد النقطة الثانية (2) وحساب الطول';
                lRow.style.display = 'none';
                aRow.style.display = 'none';
            } else if (points.length === 2) {
                gText.innerText = 'يمكنك تحديد نقطة ثالثة (3) لحساب المحيط والمساحة';
                lRow.style.display = 'flex';
                aRow.style.display = 'none';
                const distPx = Math.hypot(points[1].x - points[0].x, points[1].y - points[0].y);
                const cm = distPx / pixelsPerCm;
                const m = cm / 100.0;
                lVal.innerText = `${m.toFixed(2)} متر (${cm.toFixed(1)} سم)`;
            } else if (points.length === 3 || points.length === 4) {
                gText.innerText = points.length === 3 ? 'مثلث متصل. اضغط نقطة 4 لحساب مضلع رباعي' : 'مضلع رباعي مكتمل (الحد الأقصى 4 نقاط)';
                lRow.style.display = 'flex';
                aRow.style.display = 'flex';
                
                let periPx = 0;
                for (let i = 0; i < points.length; i++) {
                    const next = (i + 1) % points.length;
                    periPx += Math.hypot(points[next].x - points[i].x, points[next].y - points[i].y);
                }
                const periCm = periPx / pixelsPerCm;
                const periM = periCm / 100.0;
                lVal.innerText = `المحيط: ${periM.toFixed(2)} متر (${periCm.toFixed(1)} سم)`;

                let areaPx2 = 0;
                for (let i = 0; i < points.length; i++) {
                    const next = (i + 1) % points.length;
                    areaPx2 += (points[i].x * points[next].y - points[next].x * points[i].y);
                }
                areaPx2 = Math.abs(areaPx2) / 2.0;
                const areaCm2 = areaPx2 / (pixelsPerCm * pixelsPerCm);
                const areaM2 = areaCm2 / 10000.0;
                aVal.innerText = `${areaM2.toFixed(3)} متر² (${areaCm2.toFixed(0)} سم²)`;
            }
        }

        function draw() {
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            if (points.length === 0) return;

            if (points.length > 1) {
                ctx.beginPath();
                ctx.moveTo(points[0].x, points[0].y);
                for (let i = 1; i < points.length; i++) {
                    ctx.lineTo(points[i].x, points[i].y);
                }
                if (points.length >= 3) {
                    ctx.closePath();
                    ctx.fillStyle = 'rgba(0, 242, 254, 0.18)';
                    ctx.fill();
                }
                ctx.strokeStyle = '#00f2fe';
                ctx.lineWidth = 3;
                ctx.stroke();

                for (let i = 0; i < points.length; i++) {
                    if (points.length === 2 && i === 1) break;
                    const next = (i + 1) % points.length;
                    if (points.length === 2 && i === 1) continue;
                    const pA = points[i];
                    const pB = points[next];
                    const midX = (pA.x + pB.x) / 2;
                    const midY = (pA.y + pB.y) / 2;
                    const distPx = Math.hypot(pB.x - pA.x, pB.y - pA.y);
                    const cm = distPx / pixelsPerCm;
                    const m = cm / 100.0;
                    const label = cm >= 100 ? `${m.toFixed(2)}m` : `${cm.toFixed(1)}cm`;

                    ctx.save();
                    ctx.fillStyle = 'rgba(15, 23, 42, 0.85)';
                    ctx.strokeStyle = '#38bdf8';
                    ctx.lineWidth = 1;
                    ctx.font = 'bold 13px Tahoma';
                    const textWidth = ctx.measureText(label).width;
                    ctx.fillRect(midX - textWidth/2 - 6, midY - 12, textWidth + 12, 22);
                    ctx.strokeRect(midX - textWidth/2 - 6, midY - 12, textWidth + 12, 22);
                    ctx.fillStyle = '#ffffff';
                    ctx.fillText(label, midX - textWidth/2, midY + 4);
                    ctx.restore();
                }
            }

            points.forEach((p, index) => {
                ctx.beginPath();
                ctx.arc(p.x, p.y, 14, 0, Math.PI * 2);
                ctx.fillStyle = '#00f2fe';
                ctx.fill();
                ctx.lineWidth = 3;
                ctx.strokeStyle = '#ffffff';
                ctx.stroke();

                ctx.fillStyle = '#0f172a';
                ctx.font = 'bold 14px Tahoma';
                ctx.textAlign = 'center';
                ctx.textBaseline = 'middle';
                ctx.fillText((index + 1).toString(), p.x, p.y);
            });
        }

        function sendReportToBot() {
            if (points.length < 2) {
                alert('⚠️ يرجى تحديد نقطتين على الأقل لحساب الطول والمسافة قبل الإرسال.');
                return;
            }
            const lVal = document.getElementById('lengthVal').innerText;
            const aVal = document.getElementById('areaVal').innerText;
            const msg = `📐 تقرير قياس كاميرا الجوال (AR Ruler):\n• أطوال/محيط النقاط (${points.length}): ${lVal}\n` + (points.length >= 3 ? `• المساحة المحسوبة: ${aVal}\n` : '') + `• المقياس المعاير: ${pixelsPerCm.toFixed(1)} px/cm`;
            
            if (window.Telegram && window.Telegram.WebApp && window.Telegram.WebApp.initData) {
                window.Telegram.WebApp.sendData(msg);
                window.Telegram.WebApp.close();
            } else {
                navigator.clipboard.writeText(msg);
                alert('✅ تم نسخ نتيجة القياس بنجاح! يمكنك لصقها وإرسالها في محادثة التليجرام:\n\n' + msg);
            }
        }

        window.onload = () => {
            startCamera();
            setTimeout(resizeCanvas, 300);
        };
    </script>
</body>
</html>"""

@app.route("/ruler")
def serve_ruler_webapp():
    return render_template_string(RULER_HTML)

@app.route("/")
def index():
    return "🚀 Ultimate PDF Toolkit & AI Studio Bot is online 24/7!"

@app.route("/media/<filename>")
def serve_media(filename):
    return send_from_directory(WORK_DIR, filename)

if __name__ == "__main__":
    cleanup_t = threading.Thread(target=cleanup_temp_daemon, daemon=True)
    cleanup_t.start()
    
    polling_t = threading.Thread(target=run_polling, daemon=True)
    polling_t.start()
    
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
