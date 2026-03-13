"""
إعدادات Follower Analyzer Bot
"""

import os

# ==================== إعدادات البوت ====================

# ضع توكن البوت هنا أو في متغير البيئة BOT_TOKEN
BOT_TOKEN = os.environ.get("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")

# اسم البوت
BOT_NAME = "Follower Analyzer Bot"

# اسم مستخدم الدعم الفني (للاشتراك VIP)
SUPPORT_USERNAME = "@YourSupportUsername"

# ==================== إعدادات التحليل ====================

# عدد المنشورات المحللة (مجاني)
FREE_POSTS_LIMIT = 12

# عدد المنشورات المحللة (VIP)
VIP_POSTS_LIMIT = 50

# ==================== إعدادات الطلبات ====================

# مهلة الطلبات بالثواني
REQUEST_TIMEOUT = 15

# تأخير بين الطلبات (لتجنب الحظر)
REQUEST_DELAY = 1.0
