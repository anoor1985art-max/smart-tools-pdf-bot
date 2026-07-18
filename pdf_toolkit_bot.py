import os
import sys
import time
import uuid
import shutil
import threading
from dotenv import load_dotenv
import telebot
from telebot import types
from flask import Flask, request

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
        types.InlineKeyboardButton("📑 تحويل الصورة/الصور إلى مستند PDF وثائقي", callback_data="img_to_pdf_single"),
        types.InlineKeyboardButton("➕ إضافة صورة أخرى لقائمة الدمج في PDF واحد", callback_data="img_add_to_list"),
        types.InlineKeyboardButton("🔍 استخراج النص المكتوب في الصورة (OCR)", callback_data="img_ocr"),
        types.InlineKeyboardButton("🔙 العودة للقائمة الرئيسية", callback_data="main_menu")
    )
    return markup

if bot:
    @bot.message_handler(commands=["start", "help"])
    def send_welcome(message):
        chat_id = message.chat.id
        session = get_user_session(chat_id)
        session["state"] = "idle"
        welcome_txt = (
            "🚀 <b>مرحباً بك في بوت الأدوات الذكية (Smart Tools) ومعمل الـ PDF!</b> 🛠️✨\n\n"
            "مختبرك الشخصي المتكامل الذي يجمع <b>30 أداة احترافية</b> لمعالجة وتحويل وتنظيم مستنداتك وصورك، مدعوماً بمحركات <b>الذكاء الاصطناعي (Gemini AI)</b> للتلخيص، التدقيق، الترجمة، والتحليل القانوني.\n\n"
            "🔥 <b>كيف تبدأ؟</b>\n"
            "1️⃣ <b>الوضع التلقائي الأسرع:</b> أرسل لي أي ملف `PDF` أو `صورة` أو مستند `Word/Excel` وسأعرض لك فوراً الأزرار المناسبة له!\n"
            "2️⃣ <b>الوضع اليدوي التصفحي:</b> اختر الأداة التي تريدها من قائمة الأدوات الشاملة أدناه:"
        )
        bot.send_message(chat_id, welcome_txt, parse_mode="HTML", reply_markup=get_main_menu_markup())

    @bot.message_handler(content_types=["document", "photo"])
    def handle_incoming_files(message):
        chat_id = message.chat.id
        session = get_user_session(chat_id)
        
        status_msg = bot.send_message(chat_id, "📥 <b>جاري استلام وتحليل الملف في معمل السيرفر...</b> ⏳", parse_mode="HTML")
        
        try:
            if message.content_type == "photo":
                file_info = bot.get_file(message.photo[-1].file_id)
                ext = "jpg"
            else:
                file_info = bot.get_file(message.document.file_id)
                ext = message.document.file_name.split(".")[-1].lower() if "." in message.document.file_name else "pdf"
                
            downloaded = bot.download_file(file_info.file_path)
            local_name = f"user_{chat_id}_{uuid.uuid4().hex[:6]}.{ext}"
            local_path = os.path.join(WORK_DIR, local_name)
            with open(local_path, "wb") as f:
                f.write(downloaded)
                
            session["active_file"] = local_path
            
            if ext == "pdf":
                bot.edit_message_text(
                    f"✅ <b>تم استلام مستند الـ PDF بنجاح!</b> 📄\n"
                    f"👇 <i>اختر الآن الإجراء السريع أو الذكي الذي تريد تنفيذه على هذا المستند:</i>",
                    chat_id=chat_id, message_id=status_msg.message_id, parse_mode="HTML",
                    reply_markup=get_smart_actions_for_pdf(local_path)
                )
            elif ext in ["jpg", "jpeg", "png", "webp"]:
                if session.get("state") == "collecting_images_for_merge":
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
                        f"👇 <i>اختر الإجراء المطلوب:</i>",
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

        elif data.startswith("tool_"):
            # إذا اختار أداة من القائمة الشاملة قبل إرسال الملف
            if not session.get("active_file") or not os.path.exists(session["active_file"]):
                session["state"] = data
                bot.answer_callback_query(call.id, "✅ تم اختيار الأداة بنجاح!")
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
                bot.answer_callback_query(call.id, "❌ يرجى إرسال مستند PDF أولاً!")
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
                    bot.answer_callback_query(call.id, "❌ يرجى إرسال ملف وتلخيصه أولاً!")
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
                bot.answer_callback_query(call.id, "❌ يرجى إرسال مستند PDF أولاً!")
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
                bot.answer_callback_query(call.id, "❌ يرجى إرسال العقد أو الاتفاقية أولاً!")
                return
            bot.answer_callback_query(call.id, "⚖️ جاري التحليل القانوني الذكي...")
            status = bot.send_message(chat_id, "⚖️ <b>جاري دراسة بنود العقد واكتشاف البنود الحساسة والثغرات (Red Flags)...</b> ⏳", parse_mode="HTML")
            report = ai_engine.ai_contract_auditor(session["active_file"])
            bot.edit_message_text(f"⚖️ <b>تقرير التدقيق القانوني والتجاري للمستند:</b>\n\n{report}", chat_id=chat_id, message_id=status.message_id, parse_mode="HTML")

        elif data == "quick_ai_proof":
            if not session.get("active_file") or not os.path.exists(session["active_file"]):
                bot.answer_callback_query(call.id, "❌ يرجى إرسال المستند أولاً!")
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

@app.route("/")
def index():
    return "🚀 Ultimate PDF Toolkit & AI Studio Bot is online 24/7!"

if __name__ == "__main__":
    cleanup_t = threading.Thread(target=cleanup_temp_daemon, daemon=True)
    cleanup_t.start()
    
    polling_t = threading.Thread(target=run_polling, daemon=True)
    polling_t.start()
    
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
