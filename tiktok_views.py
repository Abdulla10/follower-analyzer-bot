"""
tiktok_views.py - وحدة زيادة مشاهدات TikTok
تستخدم tikfollowers.com API لإرسال مشاهدات مجانية
الـ cooldown: 15 دقيقة per-username
"""
import requests
import re
import json
import logging
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

TIKFOLLOWERS_BASE = "https://tikfollowers.com"
SEARCH_API = f"{TIKFOLLOWERS_BASE}/api/search"
PROCESS_API = f"{TIKFOLLOWERS_BASE}/api/process"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Content-Type": "application/json",
    "Referer": f"{TIKFOLLOWERS_BASE}/free-tiktok-video-views",
    "Origin": TIKFOLLOWERS_BASE,
    "Accept": "application/json, text/plain, */*",
}


def extract_video_id(url_or_id: str) -> Optional[str]:
    """
    استخراج معرف الفيديو من رابط TikTok أو إرجاعه مباشرة إذا كان ID
    """
    url_or_id = url_or_id.strip()
    
    # إذا كان ID رقمي مباشرة
    if url_or_id.isdigit() and len(url_or_id) >= 15:
        return url_or_id
    
    # استخراج من رابط TikTok العادي
    # مثال: https://www.tiktok.com/@username/video/7106594312292453675
    match = re.search(r'/video/(\d+)', url_or_id)
    if match:
        return match.group(1)
    
    # استخراج من رابط vm.tiktok.com أو vt.tiktok.com المختصر
    if 'vm.tiktok.com' in url_or_id or 'vt.tiktok.com' in url_or_id:
        try:
            r = requests.get(url_or_id, allow_redirects=True, timeout=10, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            })
            match = re.search(r'/video/(\d+)', r.url)
            if match:
                return match.group(1)
        except Exception as e:
            logger.warning(f"Failed to follow redirect for {url_or_id}: {e}")
    
    return None


def send_views(video_url_or_id: str) -> Tuple[bool, str, dict]:
    """
    إرسال مشاهدات لفيديو TikTok
    
    Returns:
        (success: bool, message: str, data: dict)
        
    data يحتوي على:
        - views_sent: عدد المشاهدات المرسلة
        - username: اسم المستخدم
        - video_id: معرف الفيديو
        - current_views: إجمالي المشاهدات الحالية
        - cooldown_minutes: دقائق الانتظار (في حالة الـ cooldown)
        - cooldown_seconds: ثواني الانتظار (في حالة الـ cooldown)
    """
    # استخراج video ID
    video_id = extract_video_id(video_url_or_id)
    
    if not video_id:
        return False, "invalid_url", {}
    
    session = requests.Session()
    session.headers.update(HEADERS)
    
    try:
        # الخطوة 1: البحث عن معلومات الفيديو
        search_payload = {
            "input": video_id,
            "type": "videoDetails"
        }
        
        r = session.post(SEARCH_API, json=search_payload, timeout=20)
        
        if r.status_code != 200:
            return False, "connection_error", {"status_code": r.status_code}
        
        search_data = r.json()
        
        if search_data.get("status") != "success" or not search_data.get("success"):
            msg = search_data.get("message", "")
            return False, "video_not_found", {"message": msg}
        
        # استخراج معلومات الفيديو
        username = search_data.get("username", "")
        stats = search_data.get("stats", {})
        current_views = stats.get("play_count", 0)
        
        # الخطوة 2: إرسال المشاهدات
        process_payload = {**search_data, "type": "video_views"}
        
        r2 = session.post(PROCESS_API, json=process_payload, timeout=30)
        
        if r2.status_code == 429:
            # Cooldown - المستخدم يحتاج للانتظار
            p_data = r2.json()
            msg = p_data.get("message", "")
            
            # استخراج وقت الانتظار
            cooldown_minutes = 0
            cooldown_seconds = 0
            match = re.search(r'(\d+) minute\(s\) and (\d+) second\(s\)', msg)
            if match:
                cooldown_minutes = int(match.group(1))
                cooldown_seconds = int(match.group(2))
            
            return False, "cooldown", {
                "username": username,
                "video_id": video_id,
                "current_views": current_views,
                "cooldown_minutes": cooldown_minutes,
                "cooldown_seconds": cooldown_seconds,
            }
        
        if r2.status_code != 200:
            return False, "process_error", {"status_code": r2.status_code}
        
        process_data = r2.json()
        
        if process_data.get("status") == "success":
            message = process_data.get("message", "")
            # استخراج عدد المشاهدات المرسلة
            views_sent = 0
            match = re.search(r'for (\d+) video_views', message)
            if match:
                views_sent = int(match.group(1))
            
            return True, "success", {
                "views_sent": views_sent,
                "username": username,
                "video_id": video_id,
                "current_views": current_views,
                "stats": stats,
            }
        else:
            msg = process_data.get("message", "")
            return False, "process_failed", {"message": msg, "username": username}
    
    except requests.exceptions.Timeout:
        return False, "timeout", {}
    except requests.exceptions.ConnectionError:
        return False, "connection_error", {}
    except Exception as e:
        logger.error(f"Error in send_views: {e}")
        return False, "unknown_error", {"error": str(e)[:100]}


def format_views_result(success: bool, error_code: str, data: dict, lang: str = "ar") -> str:
    """
    تنسيق نتيجة إرسال المشاهدات للعرض في التيليغرام
    """
    if success:
        views_sent = data.get("views_sent", 0)
        username = data.get("username", "")
        video_id = data.get("video_id", "")
        current_views = data.get("current_views", 0)
        
        if lang == "ar":
            return (
                f"✅ **تم إرسال المشاهدات بنجاح!**\n\n"
                f"👤 الحساب: @{username}\n"
                f"🎬 معرف الفيديو: `{video_id}`\n"
                f"👁️ المشاهدات المُرسلة: **{views_sent:,}**\n"
                f"📊 إجمالي المشاهدات الحالية: **{current_views:,}**\n\n"
                f"⏳ قد تظهر المشاهدات خلال بضع دقائق.\n"
                f"🔄 يمكنك إرسالها مرة أخرى بعد **15 دقيقة** للحصول على المزيد!"
            )
        else:
            return (
                f"✅ **Views Sent Successfully!**\n\n"
                f"👤 Account: @{username}\n"
                f"🎬 Video ID: `{video_id}`\n"
                f"👁️ Views Sent: **{views_sent:,}**\n"
                f"📊 Current Total Views: **{current_views:,}**\n\n"
                f"⏳ Views may appear within a few minutes.\n"
                f"🔄 You can send again after **15 minutes** for more!"
            )
    
    # معالجة الأخطاء
    if error_code == "invalid_url":
        if lang == "ar":
            return (
                "❌ **رابط غير صحيح**\n\n"
                "أرسل رابط فيديو TikTok الكامل، مثال:\n"
                "`https://www.tiktok.com/@username/video/1234567890`\n\n"
                "أو معرف الفيديو الرقمي مباشرة."
            )
        else:
            return (
                "❌ **Invalid URL**\n\n"
                "Send the full TikTok video link, example:\n"
                "`https://www.tiktok.com/@username/video/1234567890`\n\n"
                "Or the numeric video ID directly."
            )
    
    elif error_code == "video_not_found":
        if lang == "ar":
            return (
                "❌ **الفيديو غير موجود**\n\n"
                "تأكد من أن:\n"
                "• الرابط صحيح وكامل\n"
                "• الفيديو عام وليس خاصاً\n"
                "• الحساب غير محذوف\n\n"
                "جرب نسخ الرابط مباشرة من تطبيق TikTok."
            )
        else:
            return (
                "❌ **Video Not Found**\n\n"
                "Make sure:\n"
                "• The link is correct and complete\n"
                "• The video is public, not private\n"
                "• The account is not deleted\n\n"
                "Try copying the link directly from the TikTok app."
            )
    
    elif error_code == "cooldown":
        username = data.get("username", "")
        minutes = data.get("cooldown_minutes", 15)
        seconds = data.get("cooldown_seconds", 0)
        current_views = data.get("current_views", 0)
        
        if lang == "ar":
            return (
                f"⏳ **يرجى الانتظار قليلاً**\n\n"
                f"👤 الحساب: @{username}\n"
                f"📊 المشاهدات الحالية: **{current_views:,}**\n\n"
                f"تم إرسال مشاهدات لهذا الحساب مؤخراً.\n"
                f"يمكنك إرسال المزيد بعد: **{minutes} دقيقة و{seconds} ثانية**\n\n"
                f"💡 يمكنك إرسال مشاهدات لفيديو من حساب مختلف الآن!"
            )
        else:
            return (
                f"⏳ **Please Wait**\n\n"
                f"👤 Account: @{username}\n"
                f"📊 Current Views: **{current_views:,}**\n\n"
                f"Views were recently sent to this account.\n"
                f"You can send more after: **{minutes} min {seconds} sec**\n\n"
                f"💡 You can send views to a different account's video now!"
            )
    
    elif error_code == "timeout":
        if lang == "ar":
            return "❌ **انتهت مهلة الاتصال**\n\nحاول مرة أخرى بعد لحظة."
        else:
            return "❌ **Connection Timeout**\n\nPlease try again in a moment."
    
    elif error_code == "connection_error":
        if lang == "ar":
            return "❌ **خطأ في الاتصال**\n\nتحقق من اتصالك وحاول مرة أخرى."
        else:
            return "❌ **Connection Error**\n\nCheck your connection and try again."
    
    else:
        msg = data.get("message", "") or data.get("error", "")
        if lang == "ar":
            return f"❌ **حدث خطأ**\n\n{msg if msg else 'حاول مرة أخرى لاحقاً.'}"
        else:
            return f"❌ **An Error Occurred**\n\n{msg if msg else 'Please try again later.'}"


# =================== اختبار مباشر ===================
if __name__ == "__main__":
    print("اختبار وحدة tiktok_views.py")
    print("=" * 50)
    
    # اختبار استخراج video ID
    test_urls = [
        "https://www.tiktok.com/@tiktok/video/7106594312292453675",
        "7106594312292453675",
        "https://vm.tiktok.com/ZMkXXXXXX/",
        "invalid_url",
    ]
    
    print("اختبار استخراج Video ID:")
    for url in test_urls:
        vid_id = extract_video_id(url)
        print(f"  {url[:50]} -> {vid_id}")
    
    print("\n" + "=" * 50)
    print("اختبار إرسال المشاهدات:")
    
    success, error_code, data = send_views("7106594312292453675")
    print(f"النتيجة: {success}, كود: {error_code}")
    print(f"البيانات: {json.dumps(data, indent=2, ensure_ascii=False)[:500]}")
    
    print("\n" + "=" * 50)
    print("النص المنسق (عربي):")
    print(format_views_result(success, error_code, data, "ar"))
    
    print("\n" + "=" * 50)
    print("النص المنسق (إنجليزي):")
    print(format_views_result(success, error_code, data, "en"))
