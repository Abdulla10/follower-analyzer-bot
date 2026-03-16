"""
Username Hunter - البحث عن اليوزر على أشهر المنصات
يفحص وجود اليوزر على 25+ منصة بشكل متوازٍ
"""

import requests
import concurrent.futures
from typing import Optional

# قائمة المنصات مع روابطها وطريقة الفحص
PLATFORMS = [
    # التواصل الاجتماعي
    {
        "name": "Instagram",
        "url": "https://www.instagram.com/{}/",
        "icon": "📸",
        "category": "social",
        "check_type": "status",
        "not_found_strings": ["Sorry, this page isn't available", "Page Not Found"],
    },
    {
        "name": "TikTok",
        "url": "https://www.tiktok.com/@{}",
        "icon": "🎵",
        "category": "social",
        "check_type": "status",
        "not_found_strings": ["Couldn't find this account"],
    },
    {
        "name": "Twitter / X",
        "url": "https://twitter.com/{}",
        "icon": "🐦",
        "category": "social",
        "check_type": "status",
        "not_found_strings": ["This account doesn't exist", "account suspended"],
    },
    {
        "name": "YouTube",
        "url": "https://www.youtube.com/@{}",
        "icon": "▶️",
        "category": "social",
        "check_type": "status",
        "not_found_strings": ["404", "This page isn't available"],
    },
    {
        "name": "Facebook",
        "url": "https://www.facebook.com/{}",
        "icon": "👤",
        "category": "social",
        "check_type": "status",
        "not_found_strings": ["Page Not Found", "This content isn't available"],
    },
    {
        "name": "Snapchat",
        "url": "https://www.snapchat.com/add/{}",
        "icon": "👻",
        "category": "social",
        "check_type": "status",
        "not_found_strings": ["Sorry, we couldn't find that Snapchatter"],
    },
    {
        "name": "Pinterest",
        "url": "https://www.pinterest.com/{}/",
        "icon": "📌",
        "category": "social",
        "check_type": "status",
        "not_found_strings": ["User not found", "404"],
    },
    {
        "name": "LinkedIn",
        "url": "https://www.linkedin.com/in/{}/",
        "icon": "💼",
        "category": "professional",
        "check_type": "status",
        "not_found_strings": ["Page not found", "This page doesn't exist"],
    },
    # التقنية والبرمجة
    {
        "name": "GitHub",
        "url": "https://github.com/{}",
        "icon": "💻",
        "category": "tech",
        "check_type": "status",
        "not_found_strings": ["Not Found"],
    },
    {
        "name": "GitLab",
        "url": "https://gitlab.com/{}",
        "icon": "🦊",
        "category": "tech",
        "check_type": "status",
        "not_found_strings": ["404", "The page you're looking for could not be found"],
    },
    {
        "name": "Dev.to",
        "url": "https://dev.to/{}",
        "icon": "📝",
        "category": "tech",
        "check_type": "status",
        "not_found_strings": ["404", "Not Found"],
    },
    {
        "name": "Replit",
        "url": "https://replit.com/@{}",
        "icon": "🔁",
        "category": "tech",
        "check_type": "status",
        "not_found_strings": ["404", "User not found"],
    },
    # الإبداع والفن
    {
        "name": "Behance",
        "url": "https://www.behance.net/{}",
        "icon": "🎨",
        "category": "creative",
        "check_type": "status",
        "not_found_strings": ["404", "Page Not Found"],
    },
    {
        "name": "Dribbble",
        "url": "https://dribbble.com/{}",
        "icon": "🏀",
        "category": "creative",
        "check_type": "status",
        "not_found_strings": ["Whoops", "404"],
    },
    {
        "name": "SoundCloud",
        "url": "https://soundcloud.com/{}",
        "icon": "🎧",
        "category": "creative",
        "check_type": "status",
        "not_found_strings": ["404", "We can't find that user"],
    },
    {
        "name": "Spotify",
        "url": "https://open.spotify.com/user/{}",
        "icon": "🎶",
        "category": "creative",
        "check_type": "status",
        "not_found_strings": ["404", "Page not found"],
    },
    # المنتديات والمجتمعات
    {
        "name": "Reddit",
        "url": "https://www.reddit.com/user/{}",
        "icon": "🤖",
        "category": "community",
        "check_type": "status",
        "not_found_strings": ["Sorry, nobody on Reddit goes by that name"],
    },
    {
        "name": "Twitch",
        "url": "https://www.twitch.tv/{}",
        "icon": "🎮",
        "category": "community",
        "check_type": "status",
        "not_found_strings": ["Sorry. Unless you've got a time machine"],
    },
    {
        "name": "Steam",
        "url": "https://steamcommunity.com/id/{}",
        "icon": "🕹️",
        "category": "community",
        "check_type": "status",
        "not_found_strings": ["The specified profile could not be found"],
    },
    {
        "name": "Telegram",
        "url": "https://t.me/{}",
        "icon": "✈️",
        "category": "community",
        "check_type": "status",
        "not_found_strings": ["If you have Telegram, you can contact"],
        "found_strings": ["View in Telegram", "Open in Telegram"],
    },
    # التدوين والمحتوى
    {
        "name": "Medium",
        "url": "https://medium.com/@{}",
        "icon": "📰",
        "category": "blog",
        "check_type": "status",
        "not_found_strings": ["404", "Page not found"],
    },
    {
        "name": "Substack",
        "url": "https://{}.substack.com",
        "icon": "📧",
        "category": "blog",
        "check_type": "status",
        "not_found_strings": ["404", "This publication does not exist"],
    },
    {
        "name": "Linktree",
        "url": "https://linktr.ee/{}",
        "icon": "🌳",
        "category": "blog",
        "check_type": "status",
        "not_found_strings": ["Sorry, this page isn't available", "404"],
    },
    # أخرى
    {
        "name": "ProductHunt",
        "url": "https://www.producthunt.com/@{}",
        "icon": "🚀",
        "category": "other",
        "check_type": "status",
        "not_found_strings": ["404", "Oops"],
    },
    {
        "name": "Patreon",
        "url": "https://www.patreon.com/{}",
        "icon": "💰",
        "category": "other",
        "check_type": "status",
        "not_found_strings": ["404", "Page Not Found"],
    },
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


def check_platform(username: str, platform: dict) -> dict:
    """فحص وجود اليوزر على منصة واحدة"""
    url = platform["url"].format(username)
    try:
        resp = requests.get(
            url,
            headers=HEADERS,
            timeout=8,
            allow_redirects=True,
        )
        status = resp.status_code
        content = resp.text.lower()

        # إذا كانت هناك نصوص تدل على الوجود
        if "found_strings" in platform:
            for s in platform["found_strings"]:
                if s.lower() in content:
                    return {
                        "platform": platform["name"],
                        "icon": platform["icon"],
                        "category": platform["category"],
                        "url": url,
                        "found": True,
                    }

        # إذا كانت هناك نصوص تدل على الغياب
        for s in platform.get("not_found_strings", []):
            if s.lower() in content:
                return {
                    "platform": platform["name"],
                    "icon": platform["icon"],
                    "category": platform["category"],
                    "url": url,
                    "found": False,
                }

        # الاعتماد على كود الحالة
        if status == 200:
            return {
                "platform": platform["name"],
                "icon": platform["icon"],
                "category": platform["category"],
                "url": url,
                "found": True,
            }
        elif status in (404, 410):
            return {
                "platform": platform["name"],
                "icon": platform["icon"],
                "category": platform["category"],
                "url": url,
                "found": False,
            }
        else:
            return {
                "platform": platform["name"],
                "icon": platform["icon"],
                "category": platform["category"],
                "url": url,
                "found": None,  # غير محدد
            }

    except Exception:
        return {
            "platform": platform["name"],
            "icon": platform["icon"],
            "category": platform["category"],
            "url": url,
            "found": None,
        }


def hunt_username(username: str) -> dict:
    """
    البحث عن اليوزر على جميع المنصات بشكل متوازٍ
    يُعيد قاموساً يحتوي على:
    - found: قائمة المنصات التي وُجد فيها اليوزر
    - not_found: قائمة المنصات التي لم يوجد فيها
    - unknown: قائمة المنصات غير المحددة
    - total_found: عدد المنصات التي وُجد فيها
    - total_checked: إجمالي المنصات المفحوصة
    """
    results = {"found": [], "not_found": [], "unknown": [], "total_found": 0, "total_checked": len(PLATFORMS)}

    with concurrent.futures.ThreadPoolExecutor(max_workers=15) as executor:
        futures = {
            executor.submit(check_platform, username, platform): platform
            for platform in PLATFORMS
        }
        for future in concurrent.futures.as_completed(futures):
            try:
                result = future.result()
                if result["found"] is True:
                    results["found"].append(result)
                    results["total_found"] += 1
                elif result["found"] is False:
                    results["not_found"].append(result)
                else:
                    results["unknown"].append(result)
            except Exception:
                pass

    # ترتيب النتائج حسب الفئة
    category_order = {"social": 0, "professional": 1, "tech": 2, "creative": 3, "community": 4, "blog": 5, "other": 6}
    results["found"].sort(key=lambda x: category_order.get(x["category"], 99))

    return results
