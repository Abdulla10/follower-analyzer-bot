"""
Follower Analyzer Bot - البوت الرئيسي
بوت تيليغرام لتحليل حسابات Instagram وTikTok
"""

import logging
import os
import asyncio
import json
import tempfile
import glob
import requests
from datetime import datetime
from typing import Optional

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    KeyboardButton,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    filters,
    ContextTypes,
)
from telegram.constants import ParseMode

from analyzer import analyze_account, format_number
from username_hunter import hunt_username
from delete_guides import DELETE_GUIDES
from extra_features import (
    check_email_breach, build_breach_report,
    scan_website, build_website_report,
    lookup_phone, build_phone_report,
    reverse_image_search, build_reverse_image_report,
    shorten_url, build_shorturl_report,
)

# ===================== الإعدادات =====================

BOT_TOKEN = os.environ.get("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "0"))

# ===================== نظام الإحصائيات =====================

STATS_FILE = "stats.json"

def load_stats() -> dict:
    if os.path.exists(STATS_FILE):
        try:
            with open(STATS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            pass
    return {"users": {}, "total_analyses": 0, "total_comparisons": 0}

def save_stats(stats: dict):
    with open(STATS_FILE, "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)

def register_user(user_id: int, username: str, full_name: str):
    stats = load_stats()
    uid = str(user_id)
    if uid not in stats["users"]:
        stats["users"][uid] = {
            "username": username or "",
            "full_name": full_name or "",
            "joined": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "analyses": 0,
            "comparisons": 0,
            "lang": "ar",
        }
    save_stats(stats)

def get_user_lang(context: ContextTypes.DEFAULT_TYPE) -> str:
    """الحصول على لغة المستخدم من user_data"""
    return context.user_data.get("lang", "ar")

def increment_analysis(user_id: int):
    stats = load_stats()
    uid = str(user_id)
    if uid in stats["users"]:
        stats["users"][uid]["analyses"] = stats["users"][uid].get("analyses", 0) + 1
    stats["total_analyses"] = stats.get("total_analyses", 0) + 1
    save_stats(stats)

def increment_comparison(user_id: int):
    stats = load_stats()
    uid = str(user_id)
    if uid in stats["users"]:
        stats["users"][uid]["comparisons"] = stats["users"][uid].get("comparisons", 0) + 1
    stats["total_comparisons"] = stats.get("total_comparisons", 0) + 1
    save_stats(stats)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# حالات المحادثة
(
    MAIN_MENU,
    WAITING_PLATFORM_ANALYZE,
    WAITING_USERNAME_ANALYZE,
    WAITING_PLATFORM_COMPARE_1,
    WAITING_USERNAME_COMPARE_1,
    WAITING_PLATFORM_COMPARE_2,
    WAITING_USERNAME_COMPARE_2,
    WAITING_DOWNLOAD_URL,
    WAITING_HUNT_USERNAME,
    WAITING_TIKTOK_INFO,
    WAITING_BREACH_EMAIL,
    WAITING_WEBSITE_URL,
    WAITING_PHONE_NUMBER,
    WAITING_REVERSE_IMAGE,
    WAITING_SHORTEN_URL,
) = range(15)


# ===================== النصوص ثنائية اللغة =====================

TEXTS = {
    "ar": {
        "welcome": (
            "🔍 *مرحباً بك في Follower Analyzer Bot!*\n\n"
            "أنا بوت متخصص في تحليل حسابات السوشيال ميديا، أساعدك على:\n\n"
            "📊 معرفة *جودة المتابعين* ونسبتهم الحقيقية\n"
            "💬 حساب *معدل التفاعل* الدقيق\n"
            "📈 تحليل *نمو الحساب* وطبيعته\n"
            "⭐ *تقييم شامل* للحساب\n"
            "⬇️ *تحميل فيديوهات TikTok* بدون علامة مائية\n\n"
            "المنصات المدعومة للتحليل: Instagram 📸 | TikTok 🎵\n\n"
            "اختر من القائمة أدناه للبدء 👇"
        ),
        "help": (
            "📖 *دليل استخدام Follower Analyzer Bot*\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "🔍 *تحليل حساب*\n"
            "اختر المنصة (Instagram أو TikTok) ثم أرسل اسم المستخدم وسيعطيك البوت تقريراً كاملاً.\n\n"
            "🔄 *مقارنة حسابين*\n"
            "قارن بين حسابين على نفس المنصة أو منصات مختلفة.\n\n"
            "⬇️ *تحميل فيديوهات TikTok*\n"
            "أرسل رابط فيديو TikTok وسيتم إرساله لك بدون علامة مائية وبجودة عالية.\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "📌 *ملاحظات:*\n"
            "• يعمل البوت مع الحسابات العامة فقط\n"
            "• التحليل يشمل آخر 12 منشور\n"
            "• معدل التفاعل = (متوسط الإعجابات + متوسط التعليقات) ÷ عدد المتابعين × 100\n"
            "• حد حجم الفيديو للتحميل: 50MB\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━"
        ),
        "btn_analyze": "🔍 تحليل حساب",
        "btn_compare": "🔄 مقارنة حسابين",
        "btn_download": "⬇️ تحميل محتوى",
        "btn_help": "📖 المساعدة",
        "btn_back": "🔙 القائمة الرئيسية",
        "btn_back_short": "🔙 رجوع",
        "btn_lang": "🌐 English",
        "btn_analyze_another": "🔍 تحليل حساب آخر",
        "btn_compare_short": "🔄 مقارنة",
        "btn_home": "🏠 القائمة الرئيسية",
        "choose_platform_analyze": "🔍 *تحليل حساب*\n\nاختر المنصة التي تريد تحليلها:",
        "choose_platform_compare": "🔄 *مقارنة حسابين*\n\nاختر منصة الحساب الأول:",
        "send_username_analyze": "📝 *تحليل {platform}*\n\nأرسل اسم المستخدم (username) للحساب الذي تريد تحليله:\n\n_مثال: `cristiano` أو `@cristiano`_",
        "send_username_compare1": "🔄 *مقارنة - الحساب الأول ({platform})*\n\nأرسل اسم المستخدم للحساب الأول:",
        "send_username_compare2": "🔄 *مقارنة - الحساب الثاني ({platform})*\n\nأرسل اسم المستخدم للحساب الثاني:",
        "invalid_username": "⚠️ اسم المستخدم غير صحيح. أرسل اسم مستخدم صالح.",
        "analyzing": "⏳ جاري تحليل حساب @{username} على {platform}...\n\n🔄 جلب البيانات...",
        "analyzing2": "⏳ جاري تحليل حساب @{username}...\n\n✅ تم جلب البيانات\n🔄 جاري التحليل...",
        "analyze_error": "❌ حدث خطأ أثناء التحليل. تأكد من:\n• صحة اسم المستخدم\n• أن الحساب عام وليس خاصاً\n• المحاولة مرة أخرى لاحقاً",
        "saved_account1": "✅ تم حفظ الحساب الأول: @{username} ({platform})\n\nاختر منصة الحساب الثاني:",
        "comparing": "⏳ جاري تحليل ومقارنة الحسابين...\n\n🔄 تحليل @{username}...",
        "comparing2": "⏳ جاري تحليل ومقارنة الحسابين...\n\n✅ تم تحليل @{u1}\n🔄 تحليل @{u2}...",
        "comparing3": "⏳ جاري تحليل ومقارنة الحسابين...\n\n✅ تم تحليل @{u1}\n✅ تم تحليل @{u2}\n🔄 إعداد التقرير المقارن...",
        "compare_error": "❌ حدث خطأ أثناء المقارنة. تأكد من صحة أسماء المستخدمين وأن الحسابات عامة.",
        "download_text": (
            "⬇️ *تحميل فيديوهات TikTok*\n\n"
            "أرسل رابط الفيديو من TikTok وسيتم إرساله لك فوراً بدون علامة مائية وبجودة HD.\n\n"
            "🎵 *TikTok* — فيديوهات بدون واترمارك HD\n\n"
            "💡 أمثلة على الروابط المدعومة:\n"
            "`https://vm.tiktok.com/xxxxx`\n"
            "`https://www.tiktok.com/@user/video/xxxxx`\n\n"
            "_ملاحظة: الحد الأقصى للحجم 50MB_"
        ),
        "invalid_url": (
            "⚠️ *الرابط غير مدعوم*\n\n"
            "هذه الميزة تدعم TikTok فقط حالياً.\n\n"
            "🎵 أرسل رابطاً من TikTok مثل:\n"
            "`https://vm.tiktok.com/xxxxx`\n"
            "`https://www.tiktok.com/@user/video/xxxxx`"
        ),
        "downloading1": "⏳ جاري تحميل المحتوى من TikTok 🎵...\n🔄 يرجى الانتظار...",
        "downloading2": "⏳ جاري تحميل المحتوى من TikTok 🎵...\n🔄 جلب رابط الفيديو...",
        "downloading3": "⏳ جاري تحميل المحتوى من TikTok 🎵...\n📥 تحميل الفيديو...",
        "too_large": "⚠️ حجم الفيديو كبير جداً (أكثر من 50MB).\nتيليغرام يسمح بحد 50MB فقط.\nجرب فيديو أقصر.",
        "sending": "✅ تم التحميل! جاري الإرسال...",
        "download_fail": "❌ فشل تحميل الفيديو. حاول مرة أخرى.",
        "tiktok_fail": "❌ تعذر التحميل من TikTok\n\n{error}",
        "unexpected_error": "❌ حدث خطأ غير متوقع. حاول مرة أخرى.",
        "unknown_msg": "🤔 لم أفهم طلبك. استخدم القائمة الرئيسية:",
        "maintenance": "⛔️ البوت تحت الصيانة حالياً. يرجى المحاولة لاحقاً 🔧",
        "banned": "⛔️ لقد تم حظرك من استخدام هذا البوت.",
        # تقرير التحليل
        "report_title": "{icon} *تقرير تحليل {platform}*",
        "report_account_info": "👤 *معلومات الحساب*",
        "report_name": "• الاسم: {name}",
        "report_username": "• المعرف: @{username}",
        "report_followers": "• المتابعون: `{followers}`",
        "report_following": "• المتابَعون: `{following}`",
        "report_posts": "• عدد المنشورات: `{posts}`",
        "report_total_likes": "❤️ إجمالي الإعجابات: `{likes}`",
        "report_engagement": "📊 *تحليل التفاعل* _(آخر {posts} منشور)_",
        "report_avg_likes": "• متوسط الإعجابات: `{likes}`",
        "report_avg_comments": "• متوسط التعليقات: `{comments}`",
        "report_engagement_rate": "• معدل التفاعل: `{rate}%` — {label}",
        "report_followers_analysis": "👥 *تحليل المتابعين* _(تقديري)_",
        "report_real": "• المتابعون الحقيقيون: `{pct}%`",
        "report_inactive": "• المتابعون غير النشطين: `{pct}%`",
        "report_fake": "• المتابعون الوهميون: `{pct}%`",
        "report_growth": "📈 *تحليل نمو الحساب*",
        "report_rating": "🏆 *التقييم النهائي*",
        "report_rating_line": "{color} *{label}* — النقاط: `{score}/100`",
        "report_source_note": "\n_⚠️ ملاحظة: البيانات تقديرية (الحساب غير متاح عبر API)_",
        "eng_excellent": "ممتاز 🔥",
        "eng_good": "جيد ✅",
        "eng_average": "متوسط ⚠️",
        "eng_poor": "ضعيف ❌",
        # تقرير المقارنة
        "compare_title": "🔄 *تقرير المقارنة*",
        "compare_detail": "📊 *المقارنة التفصيلية*",
        "compare_followers": "👥 المتابعون:",
        "compare_engagement": "💬 معدل التفاعل:",
        "compare_avg_likes": "❤️ متوسط الإعجابات:",
        "compare_real": "👤 المتابعون الحقيقيون:",
        "compare_rating": "🏆 التقييم النهائي:",
        "compare_winner": "🏆 الفائز: @{username} ({icon})",
        "compare_tie": "🤝 تعادل بين الحسابين",
        # Username Hunt
        "btn_hunt": "🔥 Username Hunt",
        "hunt_intro": (
            "🔥 *Username Hunt — خريطة الهوية الرقمية*\n\n"
            "أرسل اسم المستخدم وسأبحث عنه على أكثر من *25 منصة* في نفس الوقت.\n\n"
            "💡 مثال: `cristiano` أو `elonmusk`\n\n"
            "_لا تضع @ في البداية_"
        ),
        "hunt_searching": "🔍 جاري البحث عن `{username}` على {total} منصة...\n\n⏳ يرجى الانتظار (قد يستغرق 15-20 ثانية)",
        "hunt_found_title": "🔥 *نتائج Username Hunt*",
        "hunt_username_label": "🎯 اليوزر: `@{username}`",
        "hunt_found_count": "✅ وُجد على *{found}* منصة من أصل *{total}* منصة مفحوصة",
        "hunt_found_platforms": "📍 *المنصات التي وُجد فيها:*",
        "hunt_not_found": "❌ *لم يُعثر على هذا اليوزر على أي منصة.*\n\nتأكد من صحة الاسم وحاول مرة أخرى.",
        "hunt_search_another": "🔍 بحث عن يوزر آخر",
        "hunt_error": "❌ حدث خطأ أثناء البحث. حاول مرة أخرى.",
        # دليل الحذف
        "btn_delete_guide": "🗑️ دليل الحذف",
        "delete_guide_intro": (
            "🗑️ *دليل حذف الحسابات*\n\n"
            "اختر المنصة التي تريد حذف حسابك منها:\n\n"
            "⚠️ جميع الخطوات دقيقة ومحدّثة. تأكد من رغبتك في الحذف قبل المتابعة."
        ),
        "delete_guide_back": "🗑️ اختر منصة أخرى",
        # TikTok Info
        "btn_tiktok_info": "🎵 معلومات TikTok",
        "tiktok_info_intro": (
            "🎵 *معلومات حساب TikTok التفصيلية*\n\n"
            "أرسل اسم المستخدم وسأجلب لك جميع المعلومات التفصيلية.\n\n"
            "💡 مثال: `charlidamelio` أو `wl4`\n\n"
            "_لا تضع @ في البداية_"
        ),
        "tiktok_info_loading": "🔍 جاري جلب معلومات `{username}`...",
        "tiktok_info_not_found": "❌ لم يوجد حساب بهذا الاسم. تأكد من صحة اليوزر وحاول مرة أخرى.",
        "tiktok_info_error": "❌ حدث خطأ أثناء جلب المعلومات. حاول مرة أخرى.",
        "tiktok_info_again": "🎵 بحث عن حساب آخر",
        # الميزات الجديدة
        "btn_breach": "🔐 كاشف التسريبات",
        "btn_website": "🌐 فاحص الموقع",
        "btn_phone": "📱 معلومات الرقم",
        "btn_reverse_image": "🖼️ بحث عكسي بالصورة",
        "btn_shorten": "🔗 مختصر الروابط",
        "breach_intro": (
            "🔐 *كاشف التسريبات*\n\n"
            "أرسل إيميلك وسأتحقق إذا كان ظهر في أي اختراق أو تسريب بيانات.\n\n"
            "💡 مثال: `example@gmail.com`\n\n"
            "_جميع البيانات مشفرة ولا تُحفظ_"
        ),
        "breach_loading": "🔍 جاري فحص الإيميل `{email}`...",
        "breach_again": "🔐 فحص إيميل آخر",
        "website_intro": (
            "🌐 *فاحص الموقع*\n\n"
            "أرسل رابط أي موقع وسأفحصه وأعطيك تقريراً كاملاً.\n\n"
            "💡 مثال: `google.com` أو `https://example.com`"
        ),
        "website_loading": "🔍 جاري فحص الموقع `{url}`...",
        "website_again": "🌐 فحص موقع آخر",
        "phone_intro": (
            "📱 *معلومات الرقم*\n\n"
            "أرسل رقم الجوال بالصيغة الدولية وسأعطيك معلوماته.\n\n"
            "💡 مثال: `+966501234567` أو `+1234567890`\n\n"
            "_يكشف الدولة والشركة ونوع الخط فقط — لا يكشف هوية الشخص_"
        ),
        "phone_loading": "🔍 جاري جلب معلومات الرقم...",
        "phone_again": "📱 فحص رقم آخر",
        "reverse_image_intro": (
            "🖼️ *البحث العكسي بالصورة*\n\n"
            "أرسل أي صورة وسأعطيك روابط للبحث عنها على أكبر محركات البحث.\n\n"
            "💡 مفيد لـ:\n"
            "• كشف الحسابات المزيفة\n"
            "• معرفة مصدر الصورة\n"
            "• البحث عن شخص"
        ),
        "reverse_image_loading": "🔍 جاري إعداد روابط البحث...",
        "reverse_image_again": "🖼️ بحث عن صورة أخرى",
        "shorten_intro": (
            "🔗 *مختصر الروابط*\n\n"
            "أرسل أي رابط طويل وسأختصره لك فوراً.\n\n"
            "💡 مثال: `https://www.example.com/very/long/url?param=value`"
        ),
        "shorten_loading": "⏳ جاري اختصار الرابط...",
        "shorten_again": "🔗 اختصار رابط آخر",
    },
    "en": {
        "welcome": (
            "🔍 *Welcome to Follower Analyzer Bot!*\n\n"
            "I'm a social media account analysis bot. I help you:\n\n"
            "📊 Check *follower quality* and real follower ratio\n"
            "💬 Calculate the exact *engagement rate*\n"
            "📈 Analyze *account growth* patterns\n"
            "⭐ Get a *full account rating*\n"
            "⬇️ *Download TikTok videos* without watermark\n\n"
            "Supported platforms for analysis: Instagram 📸 | TikTok 🎵\n\n"
            "Choose from the menu below to get started 👇"
        ),
        "help": (
            "📖 *Follower Analyzer Bot — Help Guide*\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "🔍 *Analyze Account*\n"
            "Choose a platform (Instagram or TikTok), send the username, and get a full report.\n\n"
            "🔄 *Compare Two Accounts*\n"
            "Compare two accounts on the same or different platforms.\n\n"
            "⬇️ *Download TikTok Videos*\n"
            "Send a TikTok link and receive it without watermark in HD quality.\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "📌 *Notes:*\n"
            "• Works with public accounts only\n"
            "• Analysis covers the last 12 posts\n"
            "• Engagement rate = (avg likes + avg comments) ÷ followers × 100\n"
            "• Max video download size: 50MB\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━"
        ),
        "btn_analyze": "🔍 Analyze Account",
        "btn_compare": "🔄 Compare Accounts",
        "btn_download": "⬇️ Download Content",
        "btn_help": "📖 Help",
        "btn_back": "🔙 Main Menu",
        "btn_back_short": "🔙 Back",
        "btn_lang": "🌐 العربية",
        "btn_analyze_another": "🔍 Analyze Another",
        "btn_compare_short": "🔄 Compare",
        "btn_home": "🏠 Main Menu",
        "choose_platform_analyze": "🔍 *Analyze Account*\n\nChoose the platform you want to analyze:",
        "choose_platform_compare": "🔄 *Compare Two Accounts*\n\nChoose the platform for the first account:",
        "send_username_analyze": "📝 *Analyze {platform}*\n\nSend the username of the account you want to analyze:\n\n_Example: `cristiano` or `@cristiano`_",
        "send_username_compare1": "🔄 *Compare — First Account ({platform})*\n\nSend the username of the first account:",
        "send_username_compare2": "🔄 *Compare — Second Account ({platform})*\n\nSend the username of the second account:",
        "invalid_username": "⚠️ Invalid username. Please send a valid username.",
        "analyzing": "⏳ Analyzing @{username} on {platform}...\n\n🔄 Fetching data...",
        "analyzing2": "⏳ Analyzing @{username}...\n\n✅ Data fetched\n🔄 Analyzing...",
        "analyze_error": "❌ An error occurred. Please make sure:\n• The username is correct\n• The account is public\n• Try again later",
        "saved_account1": "✅ First account saved: @{username} ({platform})\n\nChoose the platform for the second account:",
        "comparing": "⏳ Analyzing and comparing both accounts...\n\n🔄 Analyzing @{username}...",
        "comparing2": "⏳ Analyzing and comparing both accounts...\n\n✅ Analyzed @{u1}\n🔄 Analyzing @{u2}...",
        "comparing3": "⏳ Analyzing and comparing both accounts...\n\n✅ Analyzed @{u1}\n✅ Analyzed @{u2}\n🔄 Preparing comparison report...",
        "compare_error": "❌ An error occurred during comparison. Make sure both usernames are correct and accounts are public.",
        "download_text": (
            "⬇️ *Download TikTok Videos*\n\n"
            "Send a TikTok video link and receive it instantly in HD without watermark.\n\n"
            "🎵 *TikTok* — HD videos, no watermark\n\n"
            "💡 Supported link examples:\n"
            "`https://vm.tiktok.com/xxxxx`\n"
            "`https://www.tiktok.com/@user/video/xxxxx`\n\n"
            "_Note: Max file size is 50MB_"
        ),
        "invalid_url": (
            "⚠️ *Unsupported link*\n\n"
            "This feature supports TikTok only.\n\n"
            "🎵 Send a TikTok link like:\n"
            "`https://vm.tiktok.com/xxxxx`\n"
            "`https://www.tiktok.com/@user/video/xxxxx`"
        ),
        "downloading1": "⏳ Downloading from TikTok 🎵...\n🔄 Please wait...",
        "downloading2": "⏳ Downloading from TikTok 🎵...\n🔄 Fetching video link...",
        "downloading3": "⏳ Downloading from TikTok 🎵...\n📥 Downloading video...",
        "too_large": "⚠️ Video is too large (over 50MB).\nTelegram allows max 50MB.\nTry a shorter video.",
        "sending": "✅ Downloaded! Sending now...",
        "download_fail": "❌ Failed to download the video. Please try again.",
        "tiktok_fail": "❌ Could not download from TikTok\n\n{error}",
        "unexpected_error": "❌ An unexpected error occurred. Please try again.",
        "unknown_msg": "🤔 I didn't understand that. Use the main menu:",
        "maintenance": "⛔️ The bot is currently under maintenance. Please try again later 🔧",
        "banned": "⛔️ You have been banned from using this bot.",
        # report
        "report_title": "{icon} *{platform} Analysis Report*",
        "report_account_info": "👤 *Account Info*",
        "report_name": "• Name: {name}",
        "report_username": "• Username: @{username}",
        "report_followers": "• Followers: `{followers}`",
        "report_following": "• Following: `{following}`",
        "report_posts": "• Posts: `{posts}`",
        "report_total_likes": "❤️ Total Likes: `{likes}`",
        "report_engagement": "📊 *Engagement Analysis* _(last {posts} posts)_",
        "report_avg_likes": "• Avg Likes: `{likes}`",
        "report_avg_comments": "• Avg Comments: `{comments}`",
        "report_engagement_rate": "• Engagement Rate: `{rate}%` — {label}",
        "report_followers_analysis": "👥 *Follower Analysis* _(estimated)_",
        "report_real": "• Real Followers: `{pct}%`",
        "report_inactive": "• Inactive Followers: `{pct}%`",
        "report_fake": "• Fake Followers: `{pct}%`",
        "report_growth": "📈 *Account Growth Analysis*",
        "report_rating": "🏆 *Final Rating*",
        "report_rating_line": "{color} *{label}* — Score: `{score}/100`",
        "report_source_note": "\n_⚠️ Note: Data is estimated (account not available via API)_",
        "eng_excellent": "Excellent 🔥",
        "eng_good": "Good ✅",
        "eng_average": "Average ⚠️",
        "eng_poor": "Poor ❌",
        # comparison
        "compare_title": "🔄 *Comparison Report*",
        "compare_detail": "📊 *Detailed Comparison*",
        "compare_followers": "👥 Followers:",
        "compare_engagement": "💬 Engagement Rate:",
        "compare_avg_likes": "❤️ Avg Likes:",
        "compare_real": "👤 Real Followers:",
        "compare_rating": "🏆 Final Rating:",
        "compare_winner": "🏆 Winner: @{username} ({icon})",
        "compare_tie": "🤝 It's a tie!",
        # Username Hunt
        "btn_hunt": "🔥 Username Hunt",
        "hunt_intro": (
            "🔥 *Username Hunt — Digital Identity Map*\n\n"
            "Send a username and I'll search for it across *25+ platforms* simultaneously.\n\n"
            "💡 Example: `cristiano` or `elonmusk`\n\n"
            "_Don't include @ at the beginning_"
        ),
        "hunt_searching": "🔍 Searching for `{username}` across {total} platforms...\n\n⏳ Please wait (may take 15-20 seconds)",
        "hunt_found_title": "🔥 *Username Hunt Results*",
        "hunt_username_label": "🎯 Username: `@{username}`",
        "hunt_found_count": "✅ Found on *{found}* out of *{total}* platforms checked",
        "hunt_found_platforms": "📍 *Platforms found on:*",
        "hunt_not_found": "❌ *This username was not found on any platform.*\n\nMake sure the name is correct and try again.",
        "hunt_search_another": "🔍 Search another username",
        "hunt_error": "❌ An error occurred during the search. Please try again.",
        # Delete Guide
        "btn_delete_guide": "🗑️ Delete Guide",
        "delete_guide_intro": (
            "🗑️ *Account Deletion Guide*\n\n"
            "Choose the platform you want to delete your account from:\n\n"
            "⚠️ All steps are accurate and up to date. Make sure you want to delete before proceeding."
        ),
        "delete_guide_back": "🗑️ Choose another platform",
        # TikTok Info
        "btn_tiktok_info": "🎵 TikTok Info",
        "tiktok_info_intro": (
            "🎵 *TikTok Account Detailed Info*\n\n"
            "Send a username and I'll fetch all detailed information.\n\n"
            "💡 Example: `charlidamelio` or `wl4`\n\n"
            "_Don't include @ at the beginning_"
        ),
        "tiktok_info_loading": "🔍 Fetching info for `{username}`...",
        "tiktok_info_not_found": "❌ No account found with this username. Check the spelling and try again.",
        "tiktok_info_error": "❌ An error occurred while fetching info. Please try again.",
        "tiktok_info_again": "🎵 Search another account",
        # New Features
        "btn_breach": "🔐 Breach Checker",
        "btn_website": "🌐 Website Scanner",
        "btn_phone": "📱 Phone Lookup",
        "btn_reverse_image": "🖼️ Reverse Image Search",
        "btn_shorten": "🔗 URL Shortener",
        "breach_intro": (
            "🔐 *Data Breach Checker*\n\n"
            "Send your email and I'll check if it appeared in any data breach.\n\n"
            "💡 Example: `example@gmail.com`\n\n"
            "_All data is encrypted and not stored_"
        ),
        "breach_loading": "🔍 Checking email `{email}`...",
        "breach_again": "🔐 Check another email",
        "website_intro": (
            "🌐 *Website Scanner*\n\n"
            "Send any website URL and I'll scan it and give you a full report.\n\n"
            "💡 Example: `google.com` or `https://example.com`"
        ),
        "website_loading": "🔍 Scanning website `{url}`...",
        "website_again": "🌐 Scan another website",
        "phone_intro": (
            "📱 *Phone Lookup*\n\n"
            "Send a phone number in international format and I'll fetch its info.\n\n"
            "💡 Example: `+966501234567` or `+1234567890`\n\n"
            "_Shows country, carrier, and line type only — does not reveal identity_"
        ),
        "phone_loading": "🔍 Fetching phone number info...",
        "phone_again": "📱 Check another number",
        "reverse_image_intro": (
            "🖼️ *Reverse Image Search*\n\n"
            "Send any image and I'll give you links to search for it on major search engines.\n\n"
            "💡 Useful for:\n"
            "• Detecting fake accounts\n"
            "• Finding image source\n"
            "• Searching for a person"
        ),
        "reverse_image_loading": "🔍 Preparing search links...",
        "reverse_image_again": "🖼️ Search another image",
        "shorten_intro": (
            "🔗 *URL Shortener*\n\n"
            "Send any long URL and I'll shorten it instantly.\n\n"
            "💡 Example: `https://www.example.com/very/long/url?param=value`"
        ),
        "shorten_loading": "⏳ Shortening URL...",
        "shorten_again": "🔗 Shorten another URL",
    }
}

def t(context, key: str, **kwargs) -> str:
    """ترجمة نص حسب لغة المستخدم"""
    lang = get_user_lang(context)
    text = TEXTS.get(lang, TEXTS["ar"]).get(key, TEXTS["ar"].get(key, key))
    if kwargs:
        text = text.format(**kwargs)
    return text


# ===================== لوحات المفاتيح =====================

def get_main_keyboard(context):
    lang = get_user_lang(context)
    tx = TEXTS[lang]
    keyboard = [
        [
            InlineKeyboardButton(tx["btn_analyze"], callback_data="analyze"),
            InlineKeyboardButton(tx["btn_compare"], callback_data="compare"),
        ],
        [
            InlineKeyboardButton(tx["btn_download"], callback_data="download"),
            InlineKeyboardButton(tx["btn_hunt"], callback_data="hunt"),
        ],
        [
            InlineKeyboardButton(tx["btn_tiktok_info"], callback_data="tiktok_info"),
            InlineKeyboardButton(tx["btn_delete_guide"], callback_data="delete_guide"),
        ],
        [
            InlineKeyboardButton(tx["btn_breach"], callback_data="breach"),
            InlineKeyboardButton(tx["btn_website"], callback_data="website_scan"),
        ],
        [
            InlineKeyboardButton(tx["btn_phone"], callback_data="phone_lookup"),
            InlineKeyboardButton(tx["btn_reverse_image"], callback_data="reverse_image"),
        ],
        [
            InlineKeyboardButton(tx["btn_shorten"], callback_data="shorten_url"),
            InlineKeyboardButton(tx["btn_help"], callback_data="help"),
        ],
        [
            InlineKeyboardButton(tx["btn_lang"], callback_data="switch_lang"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_platform_keyboard(action: str, context):
    lang = get_user_lang(context)
    tx = TEXTS[lang]
    keyboard = [
        [
            InlineKeyboardButton("📸 Instagram", callback_data=f"platform_{action}_instagram"),
            InlineKeyboardButton("🎵 TikTok", callback_data=f"platform_{action}_tiktok"),
        ],
        [InlineKeyboardButton(tx["btn_back_short"], callback_data="back_main")],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_back_keyboard(context):
    lang = get_user_lang(context)
    tx = TEXTS[lang]
    keyboard = [[InlineKeyboardButton(tx["btn_back"], callback_data="back_main")]]
    return InlineKeyboardMarkup(keyboard)


def get_delete_guide_keyboard(context):
    """لوحة مفاتيح اختيار المنصة لدليل الحذف"""
    keyboard = [
        [
            InlineKeyboardButton("📸 Instagram", callback_data="dg_instagram"),
            InlineKeyboardButton("🎵 TikTok", callback_data="dg_tiktok"),
        ],
        [
            InlineKeyboardButton("🐦 Twitter / X", callback_data="dg_twitter"),
            InlineKeyboardButton("👻 Snapchat", callback_data="dg_snapchat"),
        ],
        [
            InlineKeyboardButton("📘 Facebook", callback_data="dg_facebook"),
            InlineKeyboardButton("▶️ YouTube", callback_data="dg_youtube"),
        ],
        [
            InlineKeyboardButton("✈️ Telegram", callback_data="dg_telegram"),
            InlineKeyboardButton("💼 LinkedIn", callback_data="dg_linkedin"),
        ],
        [
            InlineKeyboardButton("🤖 Reddit", callback_data="dg_reddit"),
            InlineKeyboardButton("🐙 GitHub", callback_data="dg_github"),
        ],
        [
            InlineKeyboardButton(TEXTS[get_user_lang(context)]["btn_back"], callback_data="back_main"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_analyze_again_keyboard(platform: str, context):
    lang = get_user_lang(context)
    tx = TEXTS[lang]
    keyboard = [
        [
            InlineKeyboardButton(tx["btn_analyze_another"], callback_data=f"platform_analyze_{platform}"),
            InlineKeyboardButton(tx["btn_compare_short"], callback_data="compare"),
        ],
        [InlineKeyboardButton(tx["btn_home"], callback_data="back_main")],
    ]
    return InlineKeyboardMarkup(keyboard)


# ===================== معالجات الأوامر =====================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.effective_user
    stats = load_stats()
    if stats.get("maintenance", False) and user.id != ADMIN_ID:
        lang = context.user_data.get("lang", "ar")
        await update.message.reply_text(TEXTS[lang]["maintenance"])
        return MAIN_MENU
    if str(user.id) in stats.get("banned", []):
        lang = context.user_data.get("lang", "ar")
        await update.message.reply_text(TEXTS[lang]["banned"])
        return MAIN_MENU
    register_user(user.id, user.username, user.full_name)
    # تعيين اللغة الافتراضية إذا لم تكن محددة
    if "lang" not in context.user_data:
        context.user_data["lang"] = "ar"
    context.user_data.pop("analyze_platform", None)
    context.user_data.pop("compare_platform_1", None)
    context.user_data.pop("compare_platform_2", None)
    context.user_data.pop("compare_username_1", None)
    await update.message.reply_text(
        t(context, "welcome"),
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=get_main_keyboard(context),
    )
    return MAIN_MENU


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if ADMIN_ID == 0 or user.id != ADMIN_ID:
        await update.message.reply_text("⛔️ هذا الأمر مخصص لمالك البوت فقط.")
        return
    stats = load_stats()
    total_users = len(stats["users"])
    total_analyses = stats.get("total_analyses", 0)
    total_comparisons = stats.get("total_comparisons", 0)
    recent_users = list(stats["users"].items())[-10:]
    recent_text = ""
    for uid, udata in reversed(recent_users):
        uname = f"@{udata['username']}" if udata.get('username') else udata.get('full_name', uid)
        joined = udata.get('joined', '')
        analyses = udata.get('analyses', 0)
        recent_text += f"\n• {uname} | تحليلات: {analyses} | {joined}"
    report = f"""
📊 *إحصائيات البوت*
━━━━━━━━━━━━━━━━━━━━━━━

👥 إجمالي المستخدمين: `{total_users}`
🔍 إجمالي التحليلات: `{total_analyses}`
🔄 إجمالي المقارنات: `{total_comparisons}`

━━━━━━━━━━━━━━━━━━━━━━━
🕒 *آخر المستخدمين:*
{recent_text if recent_text else 'لا يوجد مستخدمون بعد'}
━━━━━━━━━━━━━━━━━━━━━━━
"""
    await update.message.reply_text(report.strip(), parse_mode=ParseMode.MARKDOWN)


async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if ADMIN_ID == 0 or user.id != ADMIN_ID:
        await update.message.reply_text("⛔️ هذا الأمر مخصص لمالك البوت فقط.")
        return
    msg = " ".join(context.args) if context.args else ""
    if not msg:
        await update.message.reply_text("⚠️ اكتب الرسالة بعد الأمر:\n/broadcast نص الرسالة")
        return
    stats = load_stats()
    success = 0
    failed = 0
    for uid in stats["users"]:
        try:
            await context.bot.send_message(chat_id=int(uid), text=f"📢 *رسالة من المطور:*\n\n{msg}", parse_mode=ParseMode.MARKDOWN)
            success += 1
        except:
            failed += 1
    await update.message.reply_text(f"✅ تم الإرسال لـ `{success}` مستخدم\n❌ فشل: `{failed}`", parse_mode=ParseMode.MARKDOWN)


async def ban_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if ADMIN_ID == 0 or user.id != ADMIN_ID:
        await update.message.reply_text("⛔️ هذا الأمر مخصص لمالك البوت فقط.")
        return
    if not context.args:
        await update.message.reply_text("⚠️ اكتب: /ban USER_ID")
        return
    ban_id = context.args[0]
    stats = load_stats()
    if "banned" not in stats:
        stats["banned"] = []
    if ban_id not in stats["banned"]:
        stats["banned"].append(ban_id)
        save_stats(stats)
        await update.message.reply_text(f"✅ تم حظر المستخدم `{ban_id}`", parse_mode=ParseMode.MARKDOWN)
    else:
        await update.message.reply_text("⚠️ هذا المستخدم محظور مسبقاً.")


async def unban_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if ADMIN_ID == 0 or user.id != ADMIN_ID:
        await update.message.reply_text("⛔️ هذا الأمر مخصص لمالك البوت فقط.")
        return
    if not context.args:
        await update.message.reply_text("⚠️ اكتب: /unban USER_ID")
        return
    unban_id = context.args[0]
    stats = load_stats()
    if "banned" in stats and unban_id in stats["banned"]:
        stats["banned"].remove(unban_id)
        save_stats(stats)
        await update.message.reply_text(f"✅ تم رفع الحظر عن المستخدم `{unban_id}`", parse_mode=ParseMode.MARKDOWN)
    else:
        await update.message.reply_text("⚠️ هذا المستخدم ليس محظوراً.")


async def users_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if ADMIN_ID == 0 or user.id != ADMIN_ID:
        await update.message.reply_text("⛔️ هذا الأمر مخصص لمالك البوت فقط.")
        return
    stats = load_stats()
    users_list = stats.get("users", {})
    if not users_list:
        await update.message.reply_text("لا يوجد مستخدمون بعد.")
        return
    text = f"👥 *قائمة المستخدمين ({len(users_list)})*\n━━━━━━━━━━━━━━━━━━━━━━━\n"
    banned = stats.get("banned", [])
    for uid, udata in list(users_list.items())[-20:]:
        uname = f"@{udata['username']}" if udata.get('username') else udata.get('full_name', uid)
        ban_icon = " 🚫" if uid in banned else ""
        text += f"\n• {uname} | ID: `{uid}`{ban_icon}"
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)


async def topusers_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if ADMIN_ID == 0 or user.id != ADMIN_ID:
        await update.message.reply_text("⛔️ هذا الأمر مخصص لمالك البوت فقط.")
        return
    stats = load_stats()
    users_list = stats.get("users", {})
    sorted_users = sorted(users_list.items(), key=lambda x: x[1].get("analyses", 0) + x[1].get("comparisons", 0), reverse=True)[:10]
    text = "🏆 *أكثر المستخدمين نشاطاً*\n━━━━━━━━━━━━━━━━━━━━━━━\n"
    medals = ["🥇","🥈","🥉","4️⃣","5️⃣","6️⃣","7️⃣","8️⃣","9️⃣","🔟"]
    for i, (uid, udata) in enumerate(sorted_users):
        uname = f"@{udata['username']}" if udata.get('username') else udata.get('full_name', uid)
        total = udata.get('analyses', 0) + udata.get('comparisons', 0)
        text += f"\n{medals[i]} {uname}: `{total}` عملية"
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)


async def maintenance_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if ADMIN_ID == 0 or user.id != ADMIN_ID:
        await update.message.reply_text("⛔️ هذا الأمر مخصص لمالك البوت فقط.")
        return
    stats = load_stats()
    current = stats.get("maintenance", False)
    stats["maintenance"] = not current
    save_stats(stats)
    status = "🔴 مفعّل" if stats["maintenance"] else "🟢 معطّل"
    await update.message.reply_text(f"⚙️ وضع الصيانة: {status}")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        t(context, "help"),
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=get_back_keyboard(context),
    )
    return MAIN_MENU


# ===================== معالجات الأزرار =====================

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    data = query.data

    # تبديل اللغة
    if data == "switch_lang":
        current = context.user_data.get("lang", "ar")
        context.user_data["lang"] = "en" if current == "ar" else "ar"
        await query.edit_message_text(
            t(context, "welcome"),
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_main_keyboard(context),
        )
        return MAIN_MENU

    # القائمة الرئيسية
    if data == "back_main":
        context.user_data.pop("analyze_platform", None)
        context.user_data.pop("compare_platform_1", None)
        context.user_data.pop("compare_platform_2", None)
        context.user_data.pop("compare_username_1", None)
        await query.edit_message_text(
            t(context, "welcome"),
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_main_keyboard(context),
        )
        return MAIN_MENU

    elif data == "analyze":
        await query.edit_message_text(
            t(context, "choose_platform_analyze"),
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_platform_keyboard("analyze", context),
        )
        return WAITING_PLATFORM_ANALYZE

    elif data == "compare":
        await query.edit_message_text(
            t(context, "choose_platform_compare"),
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_platform_keyboard("compare1", context),
        )
        return WAITING_PLATFORM_COMPARE_1

    elif data == "help":
        await query.edit_message_text(
            t(context, "help"),
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_back_keyboard(context),
        )
        return MAIN_MENU

    elif data == "download":
        await query.edit_message_text(
            t(context, "download_text"),
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_back_keyboard(context),
        )
        return WAITING_DOWNLOAD_URL

    elif data == "hunt":
        await query.edit_message_text(
            t(context, "hunt_intro"),
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_back_keyboard(context),
        )
        return WAITING_HUNT_USERNAME

    elif data == "hunt_again":
        await query.edit_message_text(
            t(context, "hunt_intro"),
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_back_keyboard(context),
        )
        return WAITING_HUNT_USERNAME

    elif data == "tiktok_info" or data == "tiktok_info_again":
        await query.edit_message_text(
            t(context, "tiktok_info_intro"),
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_back_keyboard(context),
        )
        return WAITING_TIKTOK_INFO

    elif data == "delete_guide":
        await query.edit_message_text(
            t(context, "delete_guide_intro"),
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_delete_guide_keyboard(context),
        )
        return MAIN_MENU

    elif data.startswith("dg_") and not data.startswith("dg_steps_"):
        platform_key = data[3:]  # إزالة بادئة dg_
        guide = DELETE_GUIDES.get(platform_key)
        if guide:
            lang = get_user_lang(context)
            what_you_lose = guide[lang]["what_you_lose"]
            keyboard = [
                [InlineKeyboardButton(
                    "🗑️ نعم، أريد الحذف — أرني الخطوات" if lang == "ar" else "🗑️ Yes, I want to delete — Show steps",
                    callback_data=f"dg_steps_{platform_key}"
                )],
                [InlineKeyboardButton(
                    t(context, "delete_guide_back"),
                    callback_data="delete_guide"
                )],
                [InlineKeyboardButton(t(context, "btn_back"), callback_data="back_main")],
            ]
            await query.edit_message_text(
                what_you_lose,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(keyboard),
            )
        return MAIN_MENU

    elif data.startswith("dg_steps_"):
        platform_key = data[9:]  # إزالة بادئة dg_steps_
        guide = DELETE_GUIDES.get(platform_key)
        if guide:
            lang = get_user_lang(context)
            steps = guide[lang]["steps"]
            url = guide["url"]
            keyboard = [
                [InlineKeyboardButton(
                    "🔗 رابط الحذف المباشر" if lang == "ar" else "🔗 Direct Deletion Link",
                    url=url
                )],
                [InlineKeyboardButton(
                    t(context, "delete_guide_back"),
                    callback_data="delete_guide"
                )],
                [InlineKeyboardButton(t(context, "btn_back"), callback_data="back_main")],
            ]
            await query.edit_message_text(
                steps,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(keyboard),
                disable_web_page_preview=True,
            )
        return MAIN_MENU

    # الميزات الجديدة
    elif data in ("breach", "breach_again"):
        await query.edit_message_text(
            t(context, "breach_intro"),
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_back_keyboard(context),
        )
        return WAITING_BREACH_EMAIL

    elif data in ("website_scan", "website_again"):
        await query.edit_message_text(
            t(context, "website_intro"),
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_back_keyboard(context),
        )
        return WAITING_WEBSITE_URL

    elif data in ("phone_lookup", "phone_again"):
        await query.edit_message_text(
            t(context, "phone_intro"),
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_back_keyboard(context),
        )
        return WAITING_PHONE_NUMBER

    elif data in ("reverse_image", "reverse_image_again"):
        await query.edit_message_text(
            t(context, "reverse_image_intro"),
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_back_keyboard(context),
        )
        return WAITING_REVERSE_IMAGE

    elif data in ("shorten_url", "shorten_again"):
        await query.edit_message_text(
            t(context, "shorten_intro"),
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_back_keyboard(context),
        )
        return WAITING_SHORTEN_URL

    # اختيار المنصة للتحليل
    elif data.startswith("platform_analyze_"):
        platform = data.replace("platform_analyze_", "")
        context.user_data["analyze_platform"] = platform
        platform_name = "Instagram 📸" if platform == "instagram" else "TikTok 🎵"
        await query.edit_message_text(
            t(context, "send_username_analyze", platform=platform_name),
            parse_mode=ParseMode.MARKDOWN,
        )
        return WAITING_USERNAME_ANALYZE

    # اختيار المنصة للمقارنة - الحساب الأول
    elif data.startswith("platform_compare1_"):
        platform = data.replace("platform_compare1_", "")
        context.user_data["compare_platform_1"] = platform
        platform_name = "Instagram 📸" if platform == "instagram" else "TikTok 🎵"
        await query.edit_message_text(
            t(context, "send_username_compare1", platform=platform_name),
            parse_mode=ParseMode.MARKDOWN,
        )
        return WAITING_USERNAME_COMPARE_1

    # اختيار المنصة للمقارنة - الحساب الثاني
    elif data.startswith("platform_compare2_"):
        platform = data.replace("platform_compare2_", "")
        context.user_data["compare_platform_2"] = platform
        platform_name = "Instagram 📸" if platform == "instagram" else "TikTok 🎵"
        await query.edit_message_text(
            t(context, "send_username_compare2", platform=platform_name),
            parse_mode=ParseMode.MARKDOWN,
        )
        return WAITING_USERNAME_COMPARE_2

    return MAIN_MENU


# ===================== معالجات الرسائل =====================

async def receive_username_analyze(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    username = update.message.text.strip().lstrip("@")
    platform = context.user_data.get("analyze_platform", "instagram")

    if not username or len(username) < 2:
        await update.message.reply_text(t(context, "invalid_username"))
        return WAITING_USERNAME_ANALYZE

    loading_msg = await update.message.reply_text(
        t(context, "analyzing", username=username, platform=platform.capitalize()),
    )

    try:
        result = analyze_account(username, platform)
        increment_analysis(update.effective_user.id)

        await loading_msg.edit_text(
            t(context, "analyzing2", username=username),
        )
        await asyncio.sleep(1)

        report = build_report(result, context)

        await loading_msg.delete()
        await update.message.reply_text(
            report,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_analyze_again_keyboard(platform, context),
        )

    except Exception as e:
        logger.error(f"خطأ في التحليل: {e}")
        await loading_msg.edit_text(
            t(context, "analyze_error"),
            reply_markup=get_back_keyboard(context),
        )

    return MAIN_MENU


async def receive_username_compare_1(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    username = update.message.text.strip().lstrip("@")
    if not username or len(username) < 2:
        await update.message.reply_text(t(context, "invalid_username"))
        return WAITING_USERNAME_COMPARE_1

    context.user_data["compare_username_1"] = username
    platform_1 = context.user_data.get("compare_platform_1", "instagram")
    await update.message.reply_text(
        t(context, "saved_account1", username=username, platform=platform_1.capitalize()),
        reply_markup=get_platform_keyboard("compare2", context),
    )
    return WAITING_PLATFORM_COMPARE_2


async def receive_username_compare_2(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    username_2 = update.message.text.strip().lstrip("@")
    if not username_2 or len(username_2) < 2:
        await update.message.reply_text(t(context, "invalid_username"))
        return WAITING_USERNAME_COMPARE_2

    username_1 = context.user_data.get("compare_username_1", "")
    platform_1 = context.user_data.get("compare_platform_1", "instagram")
    platform_2 = context.user_data.get("compare_platform_2", "instagram")

    loading_msg = await update.message.reply_text(
        t(context, "comparing", username=username_1),
    )

    try:
        result_1 = analyze_account(username_1, platform_1)
        await loading_msg.edit_text(
            t(context, "comparing2", u1=username_1, u2=username_2),
        )

        result_2 = analyze_account(username_2, platform_2)

        await loading_msg.edit_text(
            t(context, "comparing3", u1=username_1, u2=username_2),
        )

        await asyncio.sleep(1)

        comparison = build_comparison_report(result_1, result_2, context)

        await loading_msg.delete()
        await update.message.reply_text(
            comparison,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_back_keyboard(context),
        )
        increment_comparison(update.effective_user.id)

    except Exception as e:
        logger.error(f"خطأ في المقارنة: {e}")
        await loading_msg.edit_text(
            t(context, "compare_error"),
            reply_markup=get_back_keyboard(context),
        )

    return MAIN_MENU


# ===================== بناء التقارير =====================

def build_report(data: dict, context) -> str:
    platform = data.get("platform", "")
    username = data.get("username", "")
    full_name = data.get("full_name", username)
    followers = data.get("followers", 0)
    following = data.get("following", 0)
    posts_count = data.get("posts_count", 0)
    avg_likes = data.get("avg_likes", 0)
    avg_comments = data.get("avg_comments", 0)
    engagement_rate = data.get("engagement_rate", 0.0)
    posts_analyzed = data.get("posts_analyzed", 0)
    is_verified = data.get("is_verified", False)
    data_source = data.get("data_source", "estimated")

    follower_analysis = data.get("follower_analysis", {})
    growth_analysis = data.get("growth_analysis", {})
    rating = data.get("rating", {})

    platform_icon = "📸" if platform == "Instagram" else "🎵"
    verified_badge = " ✅" if is_verified else ""
    source_note = "" if data_source == "live" else t(context, "report_source_note")

    if engagement_rate >= 6:
        engagement_label = t(context, "eng_excellent")
    elif engagement_rate >= 3:
        engagement_label = t(context, "eng_good")
    elif engagement_rate >= 1:
        engagement_label = t(context, "eng_average")
    else:
        engagement_label = t(context, "eng_poor")

    real_pct = follower_analysis.get("real_percentage", 0)
    inactive_pct = follower_analysis.get("inactive_percentage", 0)
    fake_pct = follower_analysis.get("fake_percentage", 0)

    growth_icon = growth_analysis.get("growth_icon", "✅")
    growth_label = growth_analysis.get("growth_label", "")

    rating_icon = rating.get("icon", "⭐")
    rating_label = rating.get("label", "")
    rating_color = rating.get("color", "🟡")
    rating_score = rating.get("score", 0)

    engagement_bar = _build_progress_bar(min(engagement_rate, 10), 10)
    real_bar = _build_progress_bar(real_pct, 100)

    tiktok_extra = ""
    if platform == "TikTok" and "total_likes" in data:
        tiktok_extra = t(context, "report_total_likes", likes=format_number(data['total_likes'])) + "\n"

    report = f"""
{t(context, "report_title", icon=platform_icon, platform=platform)}
━━━━━━━━━━━━━━━━━━━━━━━

{t(context, "report_account_info")}
{t(context, "report_name", name=full_name + verified_badge)}
{t(context, "report_username", username=username)}
{t(context, "report_followers", followers=format_number(followers))}
{t(context, "report_following", following=format_number(following))}
{t(context, "report_posts", posts=format_number(posts_count))}
{tiktok_extra}
━━━━━━━━━━━━━━━━━━━━━━━

{t(context, "report_engagement", posts=posts_analyzed)}
{t(context, "report_avg_likes", likes=format_number(avg_likes))}
{t(context, "report_avg_comments", comments=format_number(avg_comments))}
{t(context, "report_engagement_rate", rate=engagement_rate, label=engagement_label)}
{engagement_bar}

━━━━━━━━━━━━━━━━━━━━━━━

{t(context, "report_followers_analysis")}
{t(context, "report_real", pct=real_pct)}
{real_bar}
{t(context, "report_inactive", pct=inactive_pct)}
{t(context, "report_fake", pct=fake_pct)}

━━━━━━━━━━━━━━━━━━━━━━━

{t(context, "report_growth")}
{growth_icon} {growth_label}

━━━━━━━━━━━━━━━━━━━━━━━

{t(context, "report_rating")}
{t(context, "report_rating_line", color=rating_color, label=rating_label, score=rating_score)}
{rating_icon}
{source_note}
━━━━━━━━━━━━━━━━━━━━━━━
_Follower Analyzer Bot_ 🤖
"""
    return report.strip()


def build_comparison_report(data1: dict, data2: dict, context) -> str:
    def get_winner(val1, val2, higher_is_better=True):
        if higher_is_better:
            return "1" if val1 > val2 else ("2" if val2 > val1 else "=")
        else:
            return "1" if val1 < val2 else ("2" if val2 < val1 else "=")

    def winner_icon(w, account_num):
        if w == str(account_num):
            return "🏆"
        elif w == "=":
            return "🤝"
        return "  "

    u1 = data1.get("username", "")
    u2 = data2.get("username", "")
    p1 = data1.get("platform", "")
    p2 = data2.get("platform", "")
    p1_icon = "📸" if p1 == "Instagram" else "🎵"
    p2_icon = "📸" if p2 == "Instagram" else "🎵"

    f1 = data1.get("followers", 0)
    f2 = data2.get("followers", 0)
    e1 = data1.get("engagement_rate", 0)
    e2 = data2.get("engagement_rate", 0)
    r1 = data1.get("follower_analysis", {}).get("real_percentage", 0)
    r2 = data2.get("follower_analysis", {}).get("real_percentage", 0)
    s1 = data1.get("rating", {}).get("score", 0)
    s2 = data2.get("rating", {}).get("score", 0)
    al1 = data1.get("avg_likes", 0)
    al2 = data2.get("avg_likes", 0)

    w_followers = get_winner(f1, f2)
    w_engagement = get_winner(e1, e2)
    w_real = get_winner(r1, r2)
    w_score = get_winner(s1, s2)
    w_likes = get_winner(al1, al2)

    score_1_wins = sum(1 for w in [w_followers, w_engagement, w_real, w_score, w_likes] if w == "1")
    score_2_wins = sum(1 for w in [w_followers, w_engagement, w_real, w_score, w_likes] if w == "2")

    if score_1_wins > score_2_wins:
        overall_winner = t(context, "compare_winner", username=u1, icon=p1_icon)
    elif score_2_wins > score_1_wins:
        overall_winner = t(context, "compare_winner", username=u2, icon=p2_icon)
    else:
        overall_winner = t(context, "compare_tie")

    report = f"""
{t(context, "compare_title")}
━━━━━━━━━━━━━━━━━━━━━━━

{p1_icon} *@{u1}*  VS  {p2_icon} *@{u2}*

━━━━━━━━━━━━━━━━━━━━━━━

{t(context, "compare_detail")}

{t(context, "compare_followers")}
{winner_icon(w_followers, 1)} @{u1}: `{format_number(f1)}`
{winner_icon(w_followers, 2)} @{u2}: `{format_number(f2)}`

{t(context, "compare_engagement")}
{winner_icon(w_engagement, 1)} @{u1}: `{e1}%`
{winner_icon(w_engagement, 2)} @{u2}: `{e2}%`

{t(context, "compare_avg_likes")}
{winner_icon(w_likes, 1)} @{u1}: `{format_number(al1)}`
{winner_icon(w_likes, 2)} @{u2}: `{format_number(al2)}`

{t(context, "compare_real")}
{winner_icon(w_real, 1)} @{u1}: `{r1}%`
{winner_icon(w_real, 2)} @{u2}: `{r2}%`

{t(context, "compare_rating")}
{winner_icon(w_score, 1)} @{u1}: `{s1}/100` — {data1.get('rating', {}).get('label', '')}
{winner_icon(w_score, 2)} @{u2}: `{s2}/100` — {data2.get('rating', {}).get('label', '')}

━━━━━━━━━━━━━━━━━━━━━━━

{overall_winner}

━━━━━━━━━━━━━━━━━━━━━━━
_Follower Analyzer Bot_ 🤖
"""
    return report.strip()


def _build_progress_bar(value: float, max_value: float, length: int = 10) -> str:
    filled = int((value / max_value) * length)
    filled = max(0, min(filled, length))
    bar = "█" * filled + "░" * (length - filled)
    return f"`[{bar}]`"


# ===================== تحميل المحتوى =====================

def download_tiktok(url: str) -> dict:
    """تحميل فيديو TikTok باستخدام tikwm.com API"""
    try:
        r = requests.post(
            "https://tikwm.com/api/",
            data={"url": url, "hd": "1"},
            timeout=30,
            headers={"User-Agent": "Mozilla/5.0"}
        )
        data = r.json()
        if data.get("code") == 0:
            video_data = data.get("data", {})
            video_url = video_data.get("hdplay") or video_data.get("play")
            title = video_data.get("title", "TikTok Video")
            duration = video_data.get("duration", 0)
            return {
                "success": True,
                "url": video_url,
                "title": title,
                "duration": duration,
                "platform": "TikTok 🎵",
            }
        else:
            return {"success": False, "error": data.get("msg", "فشل التحميل")}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def receive_download_url(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    import shutil

    url = update.message.text.strip()
    url_lower = url.lower()
    supported_domains = [
        "tiktok.com", "vm.tiktok.com", "vt.tiktok.com", "m.tiktok.com",
    ]
    is_valid = url_lower.startswith("http") and any(d in url_lower for d in supported_domains)
    if not is_valid:
        await update.message.reply_text(
            t(context, "invalid_url"),
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_back_keyboard(context),
        )
        return WAITING_DOWNLOAD_URL

    loading_msg = await update.message.reply_text(t(context, "downloading1"))

    try:
        tmpdir_to_clean = None

        await loading_msg.edit_text(t(context, "downloading2"))
        result = await asyncio.get_event_loop().run_in_executor(
            None, download_tiktok, url
        )

        if result["success"]:
            video_url = result["url"]
            title = result.get("title", "TikTok Video")
            duration = result.get("duration", 0)

            await loading_msg.edit_text(t(context, "downloading3"))

            video_response = requests.get(
                video_url,
                timeout=60,
                stream=True,
                headers={"User-Agent": "Mozilla/5.0", "Referer": "https://www.tiktok.com/"}
            )

            if video_response.status_code == 200:
                tmpdir_to_clean = tempfile.mkdtemp()
                file_path = os.path.join(tmpdir_to_clean, "tiktok_video.mp4")
                with open(file_path, "wb") as f:
                    for chunk in video_response.iter_content(chunk_size=8192):
                        f.write(chunk)

                file_size = os.path.getsize(file_path)

                if file_size > 50 * 1024 * 1024:
                    await loading_msg.edit_text(
                        t(context, "too_large"),
                        reply_markup=get_back_keyboard(context),
                    )
                    shutil.rmtree(tmpdir_to_clean, ignore_errors=True)
                    return WAITING_DOWNLOAD_URL

                await loading_msg.edit_text(t(context, "sending"))

                caption = (
                    f"⬇️ *{title[:100]}*\n"
                    f"📱 TikTok 🎵\n"
                    f"💾 {file_size / (1024*1024):.1f} MB\n"
                    f"⏱ {duration // 60}:{duration % 60:02d}\n\n"
                    f"_Follower Analyzer Bot_ 🤖"
                )

                with open(file_path, "rb") as f:
                    await update.message.reply_video(
                        video=f,
                        caption=caption,
                        parse_mode=ParseMode.MARKDOWN,
                        supports_streaming=True,
                        reply_markup=get_back_keyboard(context),
                    )

                await loading_msg.delete()
                shutil.rmtree(tmpdir_to_clean, ignore_errors=True)
            else:
                await loading_msg.edit_text(
                    t(context, "download_fail"),
                    reply_markup=get_back_keyboard(context),
                )
        else:
            await loading_msg.edit_text(
                t(context, "tiktok_fail", error=result.get("error", "")),
                reply_markup=get_back_keyboard(context),
            )

    except Exception as e:
        logger.error(f"خطأ غير متوقع في التحميل: {e}")
        try:
            await loading_msg.edit_text(
                t(context, "unexpected_error"),
                reply_markup=get_back_keyboard(context),
            )
        except:
            pass

    return WAITING_DOWNLOAD_URL


# ===================== Username Hunt =====================

async def receive_hunt_username(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """استقبال اسم المستخدم والبحث عنه على جميع المنصات"""
    username = update.message.text.strip().lstrip("@").strip()

    if not username or len(username) < 2:
        await update.message.reply_text(t(context, "invalid_username"))
        return WAITING_HUNT_USERNAME

    from username_hunter import PLATFORMS
    total = len(PLATFORMS)

    loading_msg = await update.message.reply_text(
        t(context, "hunt_searching", username=username, total=total),
        parse_mode=ParseMode.MARKDOWN,
    )

    try:
        results = await asyncio.get_event_loop().run_in_executor(
            None, hunt_username, username
        )

        found_list = results["found"]
        total_found = results["total_found"]
        total_checked = results["total_checked"]

        await loading_msg.delete()

        if total_found == 0:
            await update.message.reply_text(
                t(context, "hunt_not_found"),
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=get_hunt_keyboard(context),
            )
            return WAITING_HUNT_USERNAME

        # بناء التقرير
        report = build_hunt_report(username, found_list, total_found, total_checked, context)

        await update.message.reply_text(
            report,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_hunt_keyboard(context),
            disable_web_page_preview=True,
        )

    except Exception as e:
        logger.error(f"خطأ في Username Hunt: {e}")
        try:
            await loading_msg.edit_text(
                t(context, "hunt_error"),
                reply_markup=get_back_keyboard(context),
            )
        except:
            pass

    return WAITING_HUNT_USERNAME


def get_hunt_keyboard(context):
    lang = get_user_lang(context)
    tx = TEXTS[lang]
    keyboard = [
        [InlineKeyboardButton(tx["hunt_search_another"], callback_data="hunt_again")],
        [InlineKeyboardButton(tx["btn_back"], callback_data="back_main")],
    ]
    return InlineKeyboardMarkup(keyboard)


def build_hunt_report(username: str, found_list: list, total_found: int, total_checked: int, context) -> str:
    """بناء تقرير Username Hunt"""
    # تجميع المنصات حسب الفئة
    categories = {}
    category_names_ar = {
        "social": "📱 التواصل الاجتماعي",
        "professional": "💼 المهني",
        "tech": "💻 التقنية والبرمجة",
        "creative": "🎨 الإبداع والفن",
        "community": "🎮 المجتمعات",
        "blog": "📝 التدوين والمحتوى",
        "other": "🔗 أخرى",
    }
    category_names_en = {
        "social": "📱 Social Media",
        "professional": "💼 Professional",
        "tech": "💻 Tech & Dev",
        "creative": "🎨 Creative",
        "community": "🎮 Communities",
        "blog": "📝 Blogging",
        "other": "🔗 Other",
    }
    lang = get_user_lang(context)
    category_names = category_names_ar if lang == "ar" else category_names_en

    for item in found_list:
        cat = item["category"]
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(item)

    platforms_text = ""
    for cat, items in categories.items():
        cat_label = category_names.get(cat, cat)
        platforms_text += f"\n{cat_label}\n"
        for item in items:
            platforms_text += f"{item['icon']} [{item['platform']}]({item['url']})\n"

    # حساب نسبة الانتشار
    spread_pct = round((total_found / total_checked) * 100)
    if spread_pct >= 60:
        spread_label = "🔥 انتشار واسع جداً" if lang == "ar" else "🔥 Very Wide Spread"
    elif spread_pct >= 30:
        spread_label = "✅ انتشار جيد" if lang == "ar" else "✅ Good Spread"
    elif spread_pct >= 10:
        spread_label = "⚠️ انتشار محدود" if lang == "ar" else "⚠️ Limited Spread"
    else:
        spread_label = "🔵 انتشار ضعيف" if lang == "ar" else "🔵 Low Spread"

    report = f"""
{t(context, 'hunt_found_title')}
━━━━━━━━━━━━━━━━━━━━━━━

{t(context, 'hunt_username_label', username=username)}
{t(context, 'hunt_found_count', found=total_found, total=total_checked)}
🌐 {spread_label}

━━━━━━━━━━━━━━━━━━━━━━━

{t(context, 'hunt_found_platforms')}
{platforms_text}
━━━━━━━━━━━━━━━━━━━━━━━
_Follower Analyzer Bot_ 🤖
"""
    return report.strip()


# ===================== TikTok Info =====================

def guess_tiktok_country(bio: str, bio_link: str, nickname: str, lang_ui: str) -> str:
    """استنتاج الدولة من البايو والرابط والاسم"""
    import re
    text = f"{bio} {bio_link} {nickname}".lower()

    # كشف اللغة العربية
    arabic_chars = len(re.findall(r'[\u0600-\u06FF]', bio + nickname))
    is_arabic = arabic_chars > 3

    # كلمات دالة على دول محددة
    country_hints = [
        # السعودية
        (['سعودي', 'سعودية', 'saudi', 'ksa', 'السعودية', 'الرياض', 'riyadh', 'jeddah', 'جدة', 'مكة', 'mecca'], 'SA', 'المملكة العربية السعودية 🇸🇦', 'Saudi Arabia 🇸🇦'),
        # الإمارات
        (['إمارات', 'امارات', 'uae', 'dubai', 'دبي', 'abu dhabi', 'ابوظبي', 'شارجة', 'sharjah'], 'AE', 'الإمارات 🇦🇪', 'UAE 🇦🇪'),
        # الكويت
        (['كويت', 'kuwait', 'q8'], 'KW', 'الكويت 🇰🇼', 'Kuwait 🇰🇼'),
        # قطر
        (['قطر', 'qatar', 'الدوحة', 'doha'], 'QA', 'قطر 🇶🇦', 'Qatar 🇶🇦'),
        # البحرين
        (['بحرين', 'bahrain', 'bh'], 'BH', 'البحرين 🇧🇭', 'Bahrain 🇧🇭'),
        # عمان
        (['عمان', 'oman', 'مسقط', 'muscat'], 'OM', 'عُمان 🇴🇲', 'Oman 🇴🇲'),
        # مصر
        (['مصر', 'egypt', 'القاهرة', 'cairo', 'اسكندرية', 'alexandria'], 'EG', 'مصر 🇪🇬', 'Egypt 🇪🇬'),
        # الأردن
        (['اردن', 'أردن', 'jordan', 'عمان', 'amman'], 'JO', 'الأردن 🇯🇴', 'Jordan 🇯🇴'),
        # العراق
        (['عراق', 'iraq', 'بغداد', 'baghdad', 'بصرة', 'basra'], 'IQ', 'العراق 🇮🇶', 'Iraq 🇮🇶'),
        # سوريا
        (['سوريا', 'syria', 'دمشق', 'damascus', 'حلب', 'aleppo'], 'SY', 'سوريا 🇸🇾', 'Syria 🇸🇾'),
        # لبنان
        (['لبنان', 'lebanon', 'بيروت', 'beirut'], 'LB', 'لبنان 🇱🇧', 'Lebanon 🇱🇧'),
        # المغرب
        (['مغرب', 'morocco', 'الرباط', 'rabat', 'الدار البيضاء', 'casablanca'], 'MA', 'المغرب 🇲🇦', 'Morocco 🇲🇦'),
        # تونس
        (['تونس', 'tunisia', 'تونس العاصمة'], 'TN', 'تونس 🇹🇳', 'Tunisia 🇹🇳'),
        # الجزائر
        (['جزائر', 'algeria', 'الجزائر العاصمة'], 'DZ', 'الجزائر 🇩🇿', 'Algeria 🇩🇿'),
        # اليمن
        (['يمن', 'yemen', 'صنعاء', 'sanaa'], 'YE', 'اليمن 🇾🇪', 'Yemen 🇾🇪'),
        # الولايات المتحدة
        (['usa', 'united states', 'america', 'new york', 'los angeles', 'california', 'texas', 'florida'], 'US', 'الولايات المتحدة 🇺🇸', 'United States 🇺🇸'),
        # المملكة المتحدة
        (['uk', 'united kingdom', 'england', 'london', 'britain', 'manchester'], 'GB', 'المملكة المتحدة 🇬🇧', 'United Kingdom 🇬🇧'),
        # تركيا
        (['تركيا', 'turkey', 'istanbul', 'اسطنبول', 'ankara'], 'TR', 'تركيا 🇹🇷', 'Turkey 🇹🇷'),
        # باكستان
        (['pakistan', 'pk', 'karachi', 'lahore', 'islamabad'], 'PK', 'باكستان 🇵🇰', 'Pakistan 🇵🇰'),
        # الهند
        (['india', 'hindi', 'mumbai', 'delhi', 'bangalore'], 'IN', 'الهند 🇮🇳', 'India 🇮🇳'),
    ]

    for keywords, code, name_ar, name_en in country_hints:
        for kw in keywords:
            if kw in text:
                return name_ar if lang_ui == 'ar' else name_en

    # إذا البايو عربي بدون تحديد دولة
    if is_arabic:
        return 'دولة عربية 🇸🇦🇦🇪' if lang_ui == 'ar' else 'Arab Country 🇸🇦'

    return 'غير محدد ⚠️' if lang_ui == 'ar' else 'Unknown ⚠️'


def fetch_tiktok_user_info(username: str) -> dict:
    """جلب معلومات مستخدم TikTok من tikwm API"""
    try:
        url = "https://www.tikwm.com/api/user/info"
        params = {"unique_id": username}
        headers = {"User-Agent": "Mozilla/5.0"}
        resp = requests.get(url, params=params, headers=headers, timeout=15)
        data = resp.json()
        if data.get("code") == 0 and data.get("data"):
            return {"success": True, "data": data["data"]}
        return {"success": False, "error": data.get("msg", "Not found")}
    except Exception as e:
        return {"success": False, "error": str(e)}


def build_tiktok_info_report(info: dict, context) -> str:
    """بناء تقرير معلومات TikTok التفصيلي"""
    import datetime
    lang = get_user_lang(context)
    user = info.get("user", {})
    stats = info.get("stats", {})

    # البيانات الأساسية
    uid = user.get("id", "N/A")
    unique_id = user.get("uniqueId", "N/A")
    nickname = user.get("nickname", "N/A")
    bio = user.get("signature", "").strip()
    sec_uid = user.get("secUid", "N/A")
    verified = user.get("verified", False)
    private = user.get("privateAccount", False)
    open_fav = user.get("openFavorite", False)
    create_ts = user.get("createTime", 0)
    bio_link = user.get("bioLink", {}).get("link", "") if isinstance(user.get("bioLink"), dict) else ""
    ins_id = user.get("ins_id", "")
    twitter_id = user.get("twitter_id", "")
    yt_title = user.get("youtube_channel_title", "")
    comment_setting = user.get("commentSetting")
    duet_setting = user.get("duetSetting")
    stitch_setting = user.get("stitchSetting")

    # الإحصائيات
    followers = stats.get("followerCount", 0)
    following = stats.get("followingCount", 0)
    hearts = stats.get("heartCount", 0)
    videos = stats.get("videoCount", 0)

    # تحويل timestamp
    if create_ts:
        create_date = datetime.datetime.utcfromtimestamp(create_ts).strftime("%Y-%m-%d %H:%M:%S")
    else:
        create_date = "N/A"

    # دوال المساعدة
    def yes_no(val, lang):
        if val:
            return ("✅ نعم" if lang == "ar" else "✅ Yes")
        return ("❌ لا" if lang == "ar" else "❌ No")

    def setting_label(val, lang):
        mapping = {
            0: ("🌎 الجميع" if lang == "ar" else "🌎 Everyone"),
            1: ("👥 المتابعون" if lang == "ar" else "👥 Friends"),
            2: ("🔒 مغلق" if lang == "ar" else "🔒 Off"),
        }
        if val is None:
            return "🌎 Everyone" if lang == "en" else "🌎 الجميع"
        return mapping.get(val, str(val))

    # استنتاج الدولة
    country_guess = guess_tiktok_country(bio, bio_link, nickname, lang)

    if lang == "ar":
        report = f"""
🎵 *معلومات حساب TikTok*
━━━━━━━━━━━━━━━━━━━━━━━

👤 *معلومات الحساب*
🔑 المعرّف: `{uid}`
👤 اليوزر: `@{unique_id}`
🏷️ الاسم المعروض: `{nickname}`
📝 البايو: {bio if bio else '—'}
🌍 الدولة: {country_guess}
📅 تاريخ الإنشاء: `{create_date} UTC`
✅ موثّق: {yes_no(verified, lang)}

━━━━━━━━━━━━━━━━━━━━━━━

📊 *الإحصائيات*
👥 المتابعون: `{format_number(followers)}`
👀 يتابع: `{format_number(following)}`
❤️ الإعجابات: `{format_number(hearts)}`
🎥 الفيديوهات: `{format_number(videos)}`

━━━━━━━━━━━━━━━━━━━━━━━

🔒 *إعدادات الخصوصية*
🔐 حساب خاص: {yes_no(private, lang)}
⭐ المفضلات ظاهرة: {yes_no(open_fav, lang)}
💬 التعليقات: {setting_label(comment_setting, lang)}
🎭 الديوت: {setting_label(duet_setting, lang)}
✂️ الستيتش: {setting_label(stitch_setting, lang)}
"""
    else:
        report = f"""
🎵 *TikTok Account Info*
━━━━━━━━━━━━━━━━━━━━━━━

👤 *Account Details*
🔑 Account ID: `{uid}`
👤 Username: `@{unique_id}`
🏷️ Nickname: `{nickname}`
📝 Bio: {bio if bio else '—'}
🌍 Country: {country_guess}
📅 Created: `{create_date} UTC`
✅ Verified: {yes_no(verified, lang)}

━━━━━━━━━━━━━━━━━━━━━━━

📊 *Statistics*
👥 Followers: `{format_number(followers)}`
👀 Following: `{format_number(following)}`
❤️ Likes: `{format_number(hearts)}`
🎥 Videos: `{format_number(videos)}`

━━━━━━━━━━━━━━━━━━━━━━━

🔒 *Privacy Settings*
🔐 Private Account: {yes_no(private, lang)}
⭐ Open Favorites: {yes_no(open_fav, lang)}
💬 Comments: {setting_label(comment_setting, lang)}
🎭 Duet: {setting_label(duet_setting, lang)}
✂️ Stitch: {setting_label(stitch_setting, lang)}
"""

    # إضافة الروابط الاجتماعية إن وجدت
    social_links = []
    if bio_link:
        social_links.append(f"🔗 [{'الموقع' if lang == 'ar' else 'Website'}]({bio_link})")
    if ins_id:
        social_links.append(f"📸 [Instagram](https://instagram.com/{ins_id})")
    if twitter_id:
        social_links.append(f"🐦 [Twitter](https://twitter.com/{twitter_id})")
    if yt_title:
        social_links.append(f"▶️ YouTube: {yt_title}")

    if social_links:
        section_title = "🔗 *روابط أخرى*" if lang == "ar" else "🔗 *Other Links*"
        report += f"━━━━━━━━━━━━━━━━━━━━━━━\n\n{section_title}\n" + "\n".join(social_links) + "\n"

    # Secret UID
    report += f"\n━━━━━━━━━━━━━━━━━━━━━━━\n"
    report += f"🔐 Secret UID:\n`{sec_uid}`\n"
    report += f"\n━━━━━━━━━━━━━━━━━━━━━━━\n"
    report += "_Follower Analyzer Bot_ 🤖"

    return report.strip()


async def receive_tiktok_info(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """استقبال يوزر TikTok وجلب معلوماته التفصيلية"""
    username = update.message.text.strip().lstrip("@").strip()

    if not username or len(username) < 2:
        await update.message.reply_text(
            t(context, "tiktok_info_not_found"),
            reply_markup=get_back_keyboard(context),
        )
        return WAITING_TIKTOK_INFO

    loading_msg = await update.message.reply_text(
        t(context, "tiktok_info_loading", username=username),
        parse_mode=ParseMode.MARKDOWN,
    )

    try:
        result = await asyncio.get_event_loop().run_in_executor(
            None, fetch_tiktok_user_info, username
        )

        if not result["success"]:
            await loading_msg.edit_text(
                t(context, "tiktok_info_not_found"),
                reply_markup=get_back_keyboard(context),
            )
            return WAITING_TIKTOK_INFO

        report = build_tiktok_info_report(result["data"], context)

        lang = get_user_lang(context)
        tx = TEXTS[lang]
        keyboard = [
            [InlineKeyboardButton(tx["tiktok_info_again"], callback_data="tiktok_info_again")],
            [InlineKeyboardButton(tx["btn_back"], callback_data="back_main")],
        ]

        await loading_msg.delete()
        await update.message.reply_text(
            report,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard),
            disable_web_page_preview=True,
        )

    except Exception as e:
        logger.error(f"خطأ في TikTok Info: {e}")
        try:
            await loading_msg.edit_text(
                t(context, "tiktok_info_error"),
                reply_markup=get_back_keyboard(context),
            )
        except:
            pass

    return WAITING_TIKTOK_INFO


## ===================== الميزات الجديدة =====================

async def receive_breach_email(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    email = update.message.text.strip()
    if "@" not in email or "." not in email:
        await update.message.reply_text(
            "⚠️ إيميل غير صحيح. أرسل إيميل صحيح مثل: example@gmail.com",
            reply_markup=get_back_keyboard(context),
        )
        return WAITING_BREACH_EMAIL

    loading_msg = await update.message.reply_text(
        t(context, "breach_loading", email=email),
        parse_mode=ParseMode.MARKDOWN,
    )
    try:
        result = await asyncio.get_event_loop().run_in_executor(None, check_email_breach, email)
        report = build_breach_report(result, email, get_user_lang(context))
        lang = get_user_lang(context)
        keyboard = [
            [InlineKeyboardButton(TEXTS[lang]["breach_again"], callback_data="breach_again")],
            [InlineKeyboardButton(TEXTS[lang]["btn_back"], callback_data="back_main")],
        ]
        await loading_msg.delete()
        await update.message.reply_text(
            report, parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard),
            disable_web_page_preview=True,
        )
    except Exception as e:
        logger.error(f"خطأ في Breach Checker: {e}")
        await loading_msg.edit_text("❌ حدث خطأ. حاول مرة أخرى.", reply_markup=get_back_keyboard(context))
    return WAITING_BREACH_EMAIL


async def receive_website_url(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    url = update.message.text.strip()
    if not url.startswith("http"):
        url = "https://" + url

    loading_msg = await update.message.reply_text(
        t(context, "website_loading", url=url[:50]),
        parse_mode=ParseMode.MARKDOWN,
    )
    try:
        result = await asyncio.get_event_loop().run_in_executor(None, scan_website, url)
        report = build_website_report(result, url, get_user_lang(context))
        lang = get_user_lang(context)
        keyboard = [
            [InlineKeyboardButton(TEXTS[lang]["website_again"], callback_data="website_again")],
            [InlineKeyboardButton(TEXTS[lang]["btn_back"], callback_data="back_main")],
        ]
        await loading_msg.delete()
        await update.message.reply_text(
            report, parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard),
            disable_web_page_preview=True,
        )
    except Exception as e:
        logger.error(f"خطأ في Website Scanner: {e}")
        await loading_msg.edit_text("❌ حدث خطأ. حاول مرة أخرى.", reply_markup=get_back_keyboard(context))
    return WAITING_WEBSITE_URL


async def receive_phone_number(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    phone = update.message.text.strip()

    loading_msg = await update.message.reply_text(
        t(context, "phone_loading"),
        parse_mode=ParseMode.MARKDOWN,
    )
    try:
        result = await asyncio.get_event_loop().run_in_executor(None, lookup_phone, phone)
        report = build_phone_report(result, phone, get_user_lang(context))
        lang = get_user_lang(context)
        keyboard = [
            [InlineKeyboardButton(TEXTS[lang]["phone_again"], callback_data="phone_again")],
            [InlineKeyboardButton(TEXTS[lang]["btn_back"], callback_data="back_main")],
        ]
        await loading_msg.delete()
        await update.message.reply_text(
            report, parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
    except Exception as e:
        logger.error(f"خطأ في Phone Lookup: {e}")
        await loading_msg.edit_text("❌ حدث خطأ. حاول مرة أخرى.", reply_markup=get_back_keyboard(context))
    return WAITING_PHONE_NUMBER


async def receive_reverse_image(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not update.message.photo:
        await update.message.reply_text(
            "⚠️ أرسل صورة وليس نصاً.",
            reply_markup=get_back_keyboard(context),
        )
        return WAITING_REVERSE_IMAGE

    loading_msg = await update.message.reply_text(
        t(context, "reverse_image_loading"),
        parse_mode=ParseMode.MARKDOWN,
    )
    try:
        # تحميل الصورة ورفعها
        photo = update.message.photo[-1]
        file = await context.bot.get_file(photo.file_id)
        file_url = file.file_path

        result = await asyncio.get_event_loop().run_in_executor(None, reverse_image_search, file_url)
        report = build_reverse_image_report(result, get_user_lang(context))
        lang = get_user_lang(context)
        keyboard = [
            [InlineKeyboardButton(TEXTS[lang]["reverse_image_again"], callback_data="reverse_image_again")],
            [InlineKeyboardButton(TEXTS[lang]["btn_back"], callback_data="back_main")],
        ]
        await loading_msg.delete()
        await update.message.reply_text(
            report, parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard),
            disable_web_page_preview=True,
        )
    except Exception as e:
        logger.error(f"خطأ في Reverse Image: {e}")
        await loading_msg.edit_text("❌ حدث خطأ. حاول مرة أخرى.", reply_markup=get_back_keyboard(context))
    return WAITING_REVERSE_IMAGE


async def receive_shorten_url(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    url = update.message.text.strip()
    if not url.startswith("http"):
        url = "https://" + url

    loading_msg = await update.message.reply_text(
        t(context, "shorten_loading"),
        parse_mode=ParseMode.MARKDOWN,
    )
    try:
        result = await asyncio.get_event_loop().run_in_executor(None, shorten_url, url)
        report = build_shorturl_report(result, url, get_user_lang(context))
        lang = get_user_lang(context)
        keyboard = [
            [InlineKeyboardButton(TEXTS[lang]["shorten_again"], callback_data="shorten_again")],
            [InlineKeyboardButton(TEXTS[lang]["btn_back"], callback_data="back_main")],
        ]
        await loading_msg.delete()
        await update.message.reply_text(
            report, parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard),
            disable_web_page_preview=True,
        )
    except Exception as e:
        logger.error(f"خطأ في URL Shortener: {e}")
        await loading_msg.edit_text("❌ حدث خطأ. حاول مرة أخرى.", reply_markup=get_back_keyboard(context))
    return WAITING_SHORTEN_URL


# ===================== معالج باك_ماين المستقل =====================

async def back_to_main_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """معالج مستقل لزر القائمة الرئيسية - يعمل من أي رسالة"""
    query = update.callback_query
    await query.answer()
    context.user_data.pop("analyze_platform", None)
    context.user_data.pop("compare_platform_1", None)
    context.user_data.pop("compare_platform_2", None)
    context.user_data.pop("compare_username_1", None)
    try:
        await query.edit_message_text(
            t(context, "welcome"),
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_main_keyboard(context),
        )
    except Exception:
        await query.message.reply_text(
            t(context, "welcome"),
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_main_keyboard(context),
        )
    return MAIN_MENU


async def switch_lang_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """معالج مستقل لتبديل اللغة - يعمل من أي رسالة"""
    query = update.callback_query
    await query.answer()
    current = context.user_data.get("lang", "ar")
    context.user_data["lang"] = "en" if current == "ar" else "ar"
    try:
        await query.edit_message_text(
            t(context, "welcome"),
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_main_keyboard(context),
        )
    except Exception:
        await query.message.reply_text(
            t(context, "welcome"),
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_main_keyboard(context),
        )
    return MAIN_MENU


# ===================== معالج الرسائل غير المعروفة =====================

async def unknown_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        t(context, "unknown_msg"),
        reply_markup=get_main_keyboard(context),
    )
    return MAIN_MENU


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error(f"خطأ: {context.error}")


# ===================== تشغيل البوت =====================

def main():
    if BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        print("❌ خطأ: يجب تعيين BOT_TOKEN في متغيرات البيئة أو في الكود مباشرة.")
        print("   export BOT_TOKEN='your_token_here'")
        return

    app = Application.builder().token(BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            MAIN_MENU: [
                CallbackQueryHandler(button_handler),
                CommandHandler("help", help_command),
            ],
            WAITING_PLATFORM_ANALYZE: [
                CallbackQueryHandler(button_handler),
            ],
            WAITING_USERNAME_ANALYZE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_username_analyze),
                CallbackQueryHandler(button_handler),
            ],
            WAITING_PLATFORM_COMPARE_1: [
                CallbackQueryHandler(button_handler),
            ],
            WAITING_USERNAME_COMPARE_1: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_username_compare_1),
                CallbackQueryHandler(button_handler),
            ],
            WAITING_PLATFORM_COMPARE_2: [
                CallbackQueryHandler(button_handler),
            ],
            WAITING_USERNAME_COMPARE_2: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_username_compare_2),
                CallbackQueryHandler(button_handler),
            ],
            WAITING_DOWNLOAD_URL: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_download_url),
                CallbackQueryHandler(button_handler),
            ],
            WAITING_HUNT_USERNAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_hunt_username),
                CallbackQueryHandler(button_handler),
            ],
            WAITING_TIKTOK_INFO: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_tiktok_info),
                CallbackQueryHandler(button_handler),
            ],
            WAITING_BREACH_EMAIL: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_breach_email),
                CallbackQueryHandler(button_handler),
            ],
            WAITING_WEBSITE_URL: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_website_url),
                CallbackQueryHandler(button_handler),
            ],
            WAITING_PHONE_NUMBER: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_phone_number),
                CallbackQueryHandler(button_handler),
            ],
            WAITING_REVERSE_IMAGE: [
                MessageHandler(filters.PHOTO, receive_reverse_image),
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_reverse_image),
                CallbackQueryHandler(button_handler),
            ],
            WAITING_SHORTEN_URL: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_shorten_url),
                CallbackQueryHandler(button_handler),
            ],
        },
        fallbacks=[
            CommandHandler("start", start),
            CommandHandler("stats", stats_command),
            CommandHandler("broadcast", broadcast_command),
            CommandHandler("ban", ban_command),
            CommandHandler("unban", unban_command),
            CommandHandler("users", users_command),
            CommandHandler("topusers", topusers_command),
            CommandHandler("maintenance", maintenance_command),
            CommandHandler("help", help_command),
            MessageHandler(filters.TEXT & ~filters.COMMAND, unknown_message),
        ],
        allow_reentry=True,
    )

    app.add_handler(conv_handler)
    # معالجات مستقلة تعمل من أي رسالة
    app.add_handler(CallbackQueryHandler(back_to_main_handler, pattern="^back_main$"))
    app.add_handler(CallbackQueryHandler(switch_lang_handler, pattern="^switch_lang$"))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("stats", stats_command))
    app.add_handler(CommandHandler("broadcast", broadcast_command))
    app.add_handler(CommandHandler("ban", ban_command))
    app.add_handler(CommandHandler("unban", unban_command))
    app.add_handler(CommandHandler("users", users_command))
    app.add_handler(CommandHandler("topusers", topusers_command))
    app.add_handler(CommandHandler("maintenance", maintenance_command))
    app.add_error_handler(error_handler)

    print("🤖 Follower Analyzer Bot يعمل الآن...")
    print("اضغط Ctrl+C للإيقاف")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
