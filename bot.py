"""
Follower Analyzer Bot - البوت الرئيسي
بوت تيليغرام لتحليل حسابات Instagram وTikTok
"""

import logging
import os
import asyncio
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

# ===================== الإعدادات =====================

BOT_TOKEN = os.environ.get("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")

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
) = range(7)


# ===================== النصوص والرسائل =====================

WELCOME_TEXT = """
🔍 *مرحباً بك في Follower Analyzer Bot!*

أنا بوت متخصص في تحليل حسابات السوشيال ميديا، أساعدك على:

📊 معرفة *جودة المتابعين* ونسبتهم الحقيقية
💬 حساب *معدل التفاعل* الدقيق
📈 تحليل *نمو الحساب* وطبيعته
⭐ *تقييم شامل* للحساب

المنصات المدعومة: Instagram 📸 | TikTok 🎵

اختر من القائمة أدناه للبدء 👇
"""

HELP_TEXT = """
📖 *دليل استخدام Follower Analyzer Bot*

━━━━━━━━━━━━━━━━━━━━━━━

🔍 *تحليل حساب*
اختر المنصة (Instagram أو TikTok) ثم أرسل اسم المستخدم وسيعطيك البوت تقريراً كاملاً.

🔄 *مقارنة حسابين*
قارن بين حسابين على نفس المنصة أو منصات مختلفة.

━━━━━━━━━━━━━━━━━━━━━━━

📌 *ملاحظات:*
• يعمل البوت مع الحسابات العامة فقط
• التحليل يشمل آخر 12 منشور
• معدل التفاعل = (متوسط الإعجابات + متوسط التعليقات) ÷ عدد المتابعين × 100

━━━━━━━━━━━━━━━━━━━━━━━
"""

VIP_TEXT = """
👑 *اشتراك VIP - Follower Analyzer Bot*

━━━━━━━━━━━━━━━━━━━━━━━

🆓 *الخطة المجانية (الحالية):*
✅ تحليل الحسابات العامة
✅ تقرير أساسي للتفاعل
✅ تحليل المتابعين
✅ مقارنة حسابين

━━━━━━━━━━━━━━━━━━━━━━━

💎 *خطة VIP:*
✅ كل مميزات الخطة المجانية
✅ تحليل أعمق لآخر 50 منشور
✅ تتبع نمو الحساب أسبوعياً
✅ تقرير PDF مفصّل
✅ مقارنة حتى 5 حسابات
✅ تنبيهات تلقائية للتغييرات
✅ أولوية في الدعم الفني

💰 *السعر: 9.99$ / شهر*

📩 للاشتراك تواصل مع: @YourSupportUsername
"""


# ===================== لوحات المفاتيح =====================

def get_main_keyboard():
    keyboard = [
        [
            InlineKeyboardButton("🔍 تحليل حساب", callback_data="analyze"),
            InlineKeyboardButton("🔄 مقارنة حسابين", callback_data="compare"),
        ],
        [
            InlineKeyboardButton("📖 المساعدة", callback_data="help"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_platform_keyboard(action: str):
    keyboard = [
        [
            InlineKeyboardButton("📸 Instagram", callback_data=f"platform_{action}_instagram"),
            InlineKeyboardButton("🎵 TikTok", callback_data=f"platform_{action}_tiktok"),
        ],
        [InlineKeyboardButton("🔙 رجوع", callback_data="back_main")],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_back_keyboard():
    keyboard = [[InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="back_main")]]
    return InlineKeyboardMarkup(keyboard)


def get_analyze_again_keyboard(platform: str):
    keyboard = [
        [
            InlineKeyboardButton("🔍 تحليل حساب آخر", callback_data=f"platform_analyze_{platform}"),
            InlineKeyboardButton("🔄 مقارنة", callback_data="compare"),
        ],
        [InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="back_main")],
    ]
    return InlineKeyboardMarkup(keyboard)


# ===================== معالجات الأوامر =====================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """أمر البدء"""
    context.user_data.clear()
    await update.message.reply_text(
        WELCOME_TEXT,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=get_main_keyboard(),
    )
    return MAIN_MENU


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """أمر المساعدة"""
    await update.message.reply_text(
        HELP_TEXT,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=get_back_keyboard(),
    )
    return MAIN_MENU


# ===================== معالجات الأزرار =====================

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """معالج جميع أزرار Inline"""
    query = update.callback_query
    await query.answer()
    data = query.data

    # القائمة الرئيسية
    if data == "back_main":
        context.user_data.clear()
        await query.edit_message_text(
            WELCOME_TEXT,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_main_keyboard(),
        )
        return MAIN_MENU

    elif data == "analyze":
        await query.edit_message_text(
            "🔍 *تحليل حساب*\n\nاختر المنصة التي تريد تحليلها:",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_platform_keyboard("analyze"),
        )
        return WAITING_PLATFORM_ANALYZE

    elif data == "compare":
        await query.edit_message_text(
            "🔄 *مقارنة حسابين*\n\nاختر منصة الحساب الأول:",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_platform_keyboard("compare1"),
        )
        return WAITING_PLATFORM_COMPARE_1

    elif data == "help":
        await query.edit_message_text(
            HELP_TEXT,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_back_keyboard(),
        )
        return MAIN_MENU

    # اختيار المنصة للتحليل
    elif data.startswith("platform_analyze_"):
        platform = data.replace("platform_analyze_", "")
        context.user_data["analyze_platform"] = platform
        platform_name = "Instagram 📸" if platform == "instagram" else "TikTok 🎵"
        await query.edit_message_text(
            f"📝 *تحليل {platform_name}*\n\n"
            f"أرسل اسم المستخدم (username) للحساب الذي تريد تحليله:\n\n"
            f"_مثال: `cristiano` أو `@cristiano`_",
            parse_mode=ParseMode.MARKDOWN,
        )
        return WAITING_USERNAME_ANALYZE

    # اختيار المنصة للمقارنة - الحساب الأول
    elif data.startswith("platform_compare1_"):
        platform = data.replace("platform_compare1_", "")
        context.user_data["compare_platform_1"] = platform
        platform_name = "Instagram 📸" if platform == "instagram" else "TikTok 🎵"
        await query.edit_message_text(
            f"🔄 *مقارنة - الحساب الأول ({platform_name})*\n\n"
            f"أرسل اسم المستخدم للحساب الأول:",
            parse_mode=ParseMode.MARKDOWN,
        )
        return WAITING_USERNAME_COMPARE_1

    # اختيار المنصة للمقارنة - الحساب الثاني
    elif data.startswith("platform_compare2_"):
        platform = data.replace("platform_compare2_", "")
        context.user_data["compare_platform_2"] = platform
        platform_name = "Instagram 📸" if platform == "instagram" else "TikTok 🎵"
        await query.edit_message_text(
            f"🔄 *مقارنة - الحساب الثاني ({platform_name})*\n\n"
            f"أرسل اسم المستخدم للحساب الثاني:",
            parse_mode=ParseMode.MARKDOWN,
        )
        return WAITING_USERNAME_COMPARE_2

    return MAIN_MENU


# ===================== معالجات الرسائل =====================

async def receive_username_analyze(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """استقبال اسم المستخدم للتحليل"""
    username = update.message.text.strip().lstrip("@")
    platform = context.user_data.get("analyze_platform", "instagram")

    if not username or len(username) < 2:
        await update.message.reply_text(
            "⚠️ اسم المستخدم غير صحيح. أرسل اسم مستخدم صالح.",
        )
        return WAITING_USERNAME_ANALYZE

    # رسالة الانتظار
    loading_msg = await update.message.reply_text(
        f"⏳ جاري تحليل حساب @{username} على {platform.capitalize()}...\n\n"
        "🔄 جلب البيانات...",
    )

    try:
        # تحليل الحساب
        result = analyze_account(username, platform)

        # تحديث رسالة الانتظار
        await loading_msg.edit_text(
            f"⏳ جاري تحليل حساب @{username}...\n\n"
            "✅ تم جلب البيانات\n"
            "🔄 جاري التحليل...",
        )

        await asyncio.sleep(1)

        # بناء التقرير
        report = build_report(result)

        await loading_msg.delete()
        await update.message.reply_text(
            report,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_analyze_again_keyboard(platform),
        )

    except Exception as e:
        logger.error(f"خطأ في التحليل: {e}")
        await loading_msg.edit_text(
            "❌ حدث خطأ أثناء التحليل. تأكد من:\n"
            "• صحة اسم المستخدم\n"
            "• أن الحساب عام وليس خاصاً\n"
            "• المحاولة مرة أخرى لاحقاً",
            reply_markup=get_back_keyboard(),
        )

    return MAIN_MENU


async def receive_username_compare_1(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """استقبال اسم المستخدم الأول للمقارنة"""
    username = update.message.text.strip().lstrip("@")
    if not username or len(username) < 2:
        await update.message.reply_text("⚠️ اسم مستخدم غير صحيح. أعد المحاولة.")
        return WAITING_USERNAME_COMPARE_1

    context.user_data["compare_username_1"] = username
    platform_1 = context.user_data.get("compare_platform_1", "instagram")

    await update.message.reply_text(
        f"✅ تم حفظ الحساب الأول: @{username} ({platform_1.capitalize()})\n\n"
        "اختر منصة الحساب الثاني:",
        reply_markup=get_platform_keyboard("compare2"),
    )
    return WAITING_PLATFORM_COMPARE_2


async def receive_username_compare_2(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """استقبال اسم المستخدم الثاني للمقارنة"""
    username_2 = update.message.text.strip().lstrip("@")
    if not username_2 or len(username_2) < 2:
        await update.message.reply_text("⚠️ اسم مستخدم غير صحيح. أعد المحاولة.")
        return WAITING_USERNAME_COMPARE_2

    username_1 = context.user_data.get("compare_username_1", "")
    platform_1 = context.user_data.get("compare_platform_1", "instagram")
    platform_2 = context.user_data.get("compare_platform_2", "instagram")

    loading_msg = await update.message.reply_text(
        f"⏳ جاري تحليل ومقارنة الحسابين...\n\n"
        f"🔄 تحليل @{username_1}...",
    )

    try:
        result_1 = analyze_account(username_1, platform_1)
        await loading_msg.edit_text(
            f"⏳ جاري تحليل ومقارنة الحسابين...\n\n"
            f"✅ تم تحليل @{username_1}\n"
            f"🔄 تحليل @{username_2}...",
        )

        result_2 = analyze_account(username_2, platform_2)

        await loading_msg.edit_text(
            f"⏳ جاري تحليل ومقارنة الحسابين...\n\n"
            f"✅ تم تحليل @{username_1}\n"
            f"✅ تم تحليل @{username_2}\n"
            f"🔄 إعداد التقرير المقارن...",
        )

        await asyncio.sleep(1)

        comparison = build_comparison_report(result_1, result_2)

        await loading_msg.delete()
        await update.message.reply_text(
            comparison,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_back_keyboard(),
        )

    except Exception as e:
        logger.error(f"خطأ في المقارنة: {e}")
        await loading_msg.edit_text(
            "❌ حدث خطأ أثناء المقارنة. تأكد من صحة أسماء المستخدمين وأن الحسابات عامة.",
            reply_markup=get_back_keyboard(),
        )

    return MAIN_MENU


# ===================== بناء التقارير =====================

def build_report(data: dict) -> str:
    """بناء تقرير التحليل الكامل"""
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
    source_note = "" if data_source == "live" else "\n_⚠️ ملاحظة: البيانات تقديرية (الحساب غير متاح عبر API)_"

    # تحديد مستوى التفاعل
    if engagement_rate >= 6:
        engagement_label = "ممتاز 🔥"
    elif engagement_rate >= 3:
        engagement_label = "جيد ✅"
    elif engagement_rate >= 1:
        engagement_label = "متوسط ⚠️"
    else:
        engagement_label = "ضعيف ❌"

    real_pct = follower_analysis.get("real_percentage", 0)
    inactive_pct = follower_analysis.get("inactive_percentage", 0)
    fake_pct = follower_analysis.get("fake_percentage", 0)

    growth_icon = growth_analysis.get("growth_icon", "✅")
    growth_label = growth_analysis.get("growth_label", "نمو طبيعي")

    rating_icon = rating.get("icon", "⭐")
    rating_label = rating.get("label", "جيد")
    rating_color = rating.get("color", "🟡")
    rating_score = rating.get("score", 0)

    # بناء شريط التقدم للتفاعل
    engagement_bar = _build_progress_bar(min(engagement_rate, 10), 10)
    real_bar = _build_progress_bar(real_pct, 100)

    # TikTok لديه إجمالي الإعجابات
    tiktok_extra = ""
    if platform == "TikTok" and "total_likes" in data:
        tiktok_extra = f"❤️ إجمالي الإعجابات: `{format_number(data['total_likes'])}`\n"

    report = f"""
{platform_icon} *تقرير تحليل {platform}*
━━━━━━━━━━━━━━━━━━━━━━━

👤 *معلومات الحساب*
• الاسم: {full_name}{verified_badge}
• المعرف: @{username}
• المتابعون: `{format_number(followers)}`
• المتابَعون: `{format_number(following)}`
• عدد المنشورات: `{format_number(posts_count)}`
{tiktok_extra}
━━━━━━━━━━━━━━━━━━━━━━━

📊 *تحليل التفاعل* _(آخر {posts_analyzed} منشور)_
• متوسط الإعجابات: `{format_number(avg_likes)}`
• متوسط التعليقات: `{format_number(avg_comments)}`
• معدل التفاعل: `{engagement_rate}%` — {engagement_label}
{engagement_bar}

━━━━━━━━━━━━━━━━━━━━━━━

👥 *تحليل المتابعين* _(تقديري)_
• المتابعون الحقيقيون: `{real_pct}%`
{real_bar}
• المتابعون غير النشطين: `{inactive_pct}%`
• المتابعون الوهميون: `{fake_pct}%`

━━━━━━━━━━━━━━━━━━━━━━━

📈 *تحليل نمو الحساب*
{growth_icon} {growth_label}

━━━━━━━━━━━━━━━━━━━━━━━

🏆 *التقييم النهائي*
{rating_color} *{rating_label}* — النقاط: `{rating_score}/100`
{rating_icon}
{source_note}
━━━━━━━━━━━━━━━━━━━━━━━
_Follower Analyzer Bot_ 🤖
"""
    return report.strip()


def build_comparison_report(data1: dict, data2: dict) -> str:
    """بناء تقرير المقارنة بين حسابين"""
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
    ac1 = data1.get("avg_comments", 0)
    ac2 = data2.get("avg_comments", 0)

    w_followers = get_winner(f1, f2)
    w_engagement = get_winner(e1, e2)
    w_real = get_winner(r1, r2)
    w_score = get_winner(s1, s2)
    w_likes = get_winner(al1, al2)

    # الفائز العام
    score_1_wins = sum(1 for w in [w_followers, w_engagement, w_real, w_score, w_likes] if w == "1")
    score_2_wins = sum(1 for w in [w_followers, w_engagement, w_real, w_score, w_likes] if w == "2")

    if score_1_wins > score_2_wins:
        overall_winner = f"🏆 الفائز: @{u1} ({p1_icon})"
    elif score_2_wins > score_1_wins:
        overall_winner = f"🏆 الفائز: @{u2} ({p2_icon})"
    else:
        overall_winner = "🤝 تعادل بين الحسابين"

    report = f"""
🔄 *تقرير المقارنة*
━━━━━━━━━━━━━━━━━━━━━━━

{p1_icon} *@{u1}*  VS  {p2_icon} *@{u2}*

━━━━━━━━━━━━━━━━━━━━━━━

📊 *المقارنة التفصيلية*

👥 المتابعون:
{winner_icon(w_followers, 1)} @{u1}: `{format_number(f1)}`
{winner_icon(w_followers, 2)} @{u2}: `{format_number(f2)}`

💬 معدل التفاعل:
{winner_icon(w_engagement, 1)} @{u1}: `{e1}%`
{winner_icon(w_engagement, 2)} @{u2}: `{e2}%`

❤️ متوسط الإعجابات:
{winner_icon(w_likes, 1)} @{u1}: `{format_number(al1)}`
{winner_icon(w_likes, 2)} @{u2}: `{format_number(al2)}`

👤 المتابعون الحقيقيون:
{winner_icon(w_real, 1)} @{u1}: `{r1}%`
{winner_icon(w_real, 2)} @{u2}: `{r2}%`

🏆 التقييم النهائي:
{winner_icon(w_score, 1)} @{u1}: `{s1}/100` — {data1.get('rating', {}).get('label', '')}
{winner_icon(w_score, 2)} @{u2}: `{s2}/100` — {data2.get('rating', {}).get('label', '')}

━━━━━━━━━━━━━━━━━━━━━━━

{overall_winner}

━━━━━━━━━━━━━━━━━━━━━━━
_Follower Analyzer Bot_ 🤖
"""
    return report.strip()


def _build_progress_bar(value: float, max_value: float, length: int = 10) -> str:
    """بناء شريط تقدم نصي"""
    filled = int((value / max_value) * length)
    filled = max(0, min(filled, length))
    bar = "█" * filled + "░" * (length - filled)
    return f"`[{bar}]`"


# ===================== معالج الرسائل غير المعروفة =====================

async def unknown_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """معالجة الرسائل غير المتوقعة"""
    await update.message.reply_text(
        "🤔 لم أفهم طلبك. استخدم القائمة الرئيسية:",
        reply_markup=get_main_keyboard(),
    )
    return MAIN_MENU


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """معالج الأخطاء العامة"""
    logger.error(f"خطأ: {context.error}")


# ===================== تشغيل البوت =====================

def main():
    if BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        print("❌ خطأ: يجب تعيين BOT_TOKEN في متغيرات البيئة أو في الكود مباشرة.")
        print("   export BOT_TOKEN='your_token_here'")
        return

    app = Application.builder().token(BOT_TOKEN).build()

    # ConversationHandler الرئيسي
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
        },
        fallbacks=[
            CommandHandler("start", start),
            MessageHandler(filters.TEXT & ~filters.COMMAND, unknown_message),
        ],
        allow_reentry=True,
    )

    app.add_handler(conv_handler)
    app.add_handler(CommandHandler("help", help_command))
    app.add_error_handler(error_handler)

    print("🤖 Follower Analyzer Bot يعمل الآن...")
    print("اضغط Ctrl+C للإيقاف")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
