"""
extra_features.py — وحدة الميزات الإضافية لبوت SocialAnalyzer
تشمل:
1. كاشف التسريبات (Data Breach Checker)
2. فاحص الموقع (Website Scanner)
3. معلومات الرقم (Phone Lookup)
4. عكس البحث بالصورة (Reverse Image Search)
5. مختصر الروابط (URL Shortener)
"""

import requests
import json
import socket
import ssl
import re
import phonenumbers
from phonenumbers import geocoder, carrier, timezone as pn_timezone
from datetime import datetime


# ===================== 1. كاشف التسريبات =====================

def check_email_breach(email: str) -> dict:
    """يفحص إذا كان الإيميل تسرّب في اختراقات مواقع"""
    try:
        r = requests.get(
            f'https://leakcheck.io/api/public?check={email}',
            timeout=15,
            headers={'User-Agent': 'SocialAnalyzerBot/1.0'}
        )
        if r.status_code == 200:
            data = r.json()
            if data.get('success'):
                found = data.get('found', 0)
                sources = data.get('sources', [])
                fields = data.get('fields', [])
                return {
                    'success': True,
                    'found': found,
                    'sources': sources[:10],  # أول 10 مصادر
                    'fields': fields,
                    'email': email
                }
        return {'success': False, 'error': 'فشل الاتصال بالخدمة'}
    except Exception as e:
        return {'success': False, 'error': str(e)}


def build_breach_report(data: dict, email: str = '', lang: str = 'ar') -> str:
    """يبني تقرير كاشف التسريبات"""
    email = data.get('email', '')
    
    if not data.get('success'):
        if lang == 'ar':
            return f"❌ فشل فحص الإيميل: {data.get('error', 'خطأ غير معروف')}"
        return f"❌ Failed to check email: {data.get('error', 'Unknown error')}"
    
    found = data.get('found', 0)
    sources = data.get('sources', [])
    fields = data.get('fields', [])
    
    # ترجمة الحقول المسرّبة
    field_translations = {
        'ar': {
            'password': '🔑 كلمة المرور',
            'email': '📧 الإيميل',
            'username': '👤 اسم المستخدم',
            'phone': '📱 رقم الجوال',
            'name': '📛 الاسم',
            'first_name': '📛 الاسم الأول',
            'last_name': '📛 اسم العائلة',
            'ip': '🌐 عنوان IP',
            'address': '🏠 العنوان',
            'city': '🏙️ المدينة',
            'country': '🌍 الدولة',
            'dob': '📅 تاريخ الميلاد',
            'gender': '👥 الجنس',
            'zip': '📮 الرمز البريدي',
        },
        'en': {
            'password': '🔑 Password',
            'email': '📧 Email',
            'username': '👤 Username',
            'phone': '📱 Phone',
            'name': '📛 Name',
            'first_name': '📛 First Name',
            'last_name': '📛 Last Name',
            'ip': '🌐 IP Address',
            'address': '🏠 Address',
            'city': '🏙️ City',
            'country': '🌍 Country',
            'dob': '📅 Date of Birth',
            'gender': '👥 Gender',
            'zip': '📮 ZIP Code',
        }
    }
    
    ft = field_translations.get(lang, field_translations['ar'])
    
    if lang == 'ar':
        if found == 0:
            status_icon = "✅"
            status_text = "لم يُعثر على تسريبات"
            safety = "إيميلك آمن ولم يظهر في أي اختراق معروف."
        elif found < 5:
            status_icon = "⚠️"
            status_text = f"وُجد في {found} تسريب"
            safety = "إيميلك ظهر في بعض الاختراقات. غيّر كلمة المرور فوراً."
        else:
            status_icon = "🚨"
            status_text = f"وُجد في {found}+ تسريب"
            safety = "إيميلك مُعرّض للخطر بشكل كبير! غيّر كلمة المرور فوراً وفعّل المصادقة الثنائية."

        report = f"""
🔐 *تقرير كاشف التسريبات*
━━━━━━━━━━━━━━━━━━━━━━━

📧 الإيميل: `{email}`
{status_icon} الحالة: *{status_text}*

⚠️ {safety}
"""
        if found > 0 and sources:
            report += "\n📋 *المواقع المخترقة:*\n"
            for s in sources[:8]:
                name = s.get('name', 'غير معروف')
                date = s.get('date', '')
                date_str = f" ({date})" if date else ""
                report += f"• {name}{date_str}\n"
            if found > 8:
                report += f"• وأكثر من {found - 8} موقع آخر...\n"
        
        if fields:
            report += "\n🗂️ *البيانات المسرّبة:*\n"
            for f in fields[:8]:
                report += f"• {ft.get(f, f)}\n"
        
        report += "\n━━━━━━━━━━━━━━━━━━━━━━━"
        report += "\n💡 *نصيحة:* غيّر كلمة المرور في كل المواقع المذكورة وفعّل المصادقة الثنائية (2FA)"
    else:
        if found == 0:
            status_icon = "✅"
            status_text = "No breaches found"
            safety = "Your email is safe and hasn't appeared in any known breach."
        elif found < 5:
            status_icon = "⚠️"
            status_text = f"Found in {found} breach(es)"
            safety = "Your email appeared in some breaches. Change your password immediately."
        else:
            status_icon = "🚨"
            status_text = f"Found in {found}+ breaches"
            safety = "Your email is highly compromised! Change your password immediately and enable 2FA."

        report = f"""
🔐 *Data Breach Report*
━━━━━━━━━━━━━━━━━━━━━━━

📧 Email: `{email}`
{status_icon} Status: *{status_text}*

⚠️ {safety}
"""
        if found > 0 and sources:
            report += "\n📋 *Breached Sites:*\n"
            for s in sources[:8]:
                name = s.get('name', 'Unknown')
                date = s.get('date', '')
                date_str = f" ({date})" if date else ""
                report += f"• {name}{date_str}\n"
            if found > 8:
                report += f"• And {found - 8}+ more sites...\n"
        
        if fields:
            report += "\n🗂️ *Leaked Data Types:*\n"
            for f in fields[:8]:
                report += f"• {ft.get(f, f)}\n"
        
        report += "\n━━━━━━━━━━━━━━━━━━━━━━━"
        report += "\n💡 *Tip:* Change your password on all listed sites and enable 2FA"
    
    return report.strip()


# ===================== 2. فاحص الموقع =====================

def scan_website(url: str) -> dict:
    """يفحص الموقع ويعطي معلومات تفصيلية"""
    # تنظيف الرابط
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    
    try:
        domain = re.sub(r'https?://', '', url).split('/')[0].split('?')[0]
    except:
        domain = url
    
    result = {
        'url': url,
        'domain': domain,
        'ip': None,
        'ssl_valid': False,
        'ssl_expires': None,
        'status_code': None,
        'server': None,
        'response_time': None,
        'security_headers': {},
        'safe': True,
        'error': None
    }
    
    # 1. فحص DNS
    try:
        result['ip'] = socket.gethostbyname(domain)
    except:
        result['error'] = 'الدومين غير موجود'
        return result
    
    # 2. فحص SSL
    try:
        ctx = ssl.create_default_context()
        conn = ctx.wrap_socket(socket.socket(), server_hostname=domain)
        conn.settimeout(5)
        conn.connect((domain, 443))
        cert = conn.getpeercert()
        result['ssl_valid'] = True
        result['ssl_expires'] = cert.get('notAfter', '')
        conn.close()
    except:
        result['ssl_valid'] = False
    
    # 3. فحص HTTP
    try:
        import time
        start = time.time()
        r = requests.get(url, timeout=15, allow_redirects=True,
                        headers={'User-Agent': 'Mozilla/5.0 (compatible; SocialAnalyzerBot/1.0)'})
        result['response_time'] = round((time.time() - start) * 1000)
        result['status_code'] = r.status_code
        result['server'] = r.headers.get('Server', 'Unknown')
        
        # فحص headers الأمان
        result['security_headers'] = {
            'X-Frame-Options': r.headers.get('X-Frame-Options', None),
            'X-XSS-Protection': r.headers.get('X-XSS-Protection', None),
            'Strict-Transport-Security': r.headers.get('Strict-Transport-Security', None),
            'Content-Security-Policy': r.headers.get('Content-Security-Policy', None),
        }
        
        # تقييم الأمان
        if r.status_code >= 400:
            result['safe'] = False
    except requests.exceptions.SSLError:
        result['ssl_valid'] = False
        result['safe'] = False
    except Exception as e:
        result['error'] = str(e)
    
    return result


def build_website_report(data: dict, url: str = '', lang: str = 'ar') -> str:
    """يبني تقرير فاحص الموقع"""
    url = data.get('url', '')
    domain = data.get('domain', '')
    
    if data.get('error'):
        if lang == 'ar':
            return f"❌ فشل فحص الموقع: {data['error']}"
        return f"❌ Failed to scan website: {data['error']}"
    
    ssl_icon = "🔒" if data.get('ssl_valid') else "🔓"
    safe_icon = "✅" if data.get('safe') else "⚠️"
    
    # تقييم سرعة الاستجابة
    rt = data.get('response_time')
    if rt:
        if rt < 500:
            speed_icon = "🟢"
            speed_text_ar = "سريع جداً"
            speed_text_en = "Very Fast"
        elif rt < 1500:
            speed_icon = "🟡"
            speed_text_ar = "متوسط"
            speed_text_en = "Average"
        else:
            speed_icon = "🔴"
            speed_text_ar = "بطيء"
            speed_text_en = "Slow"
    else:
        speed_icon = "❓"
        speed_text_ar = "غير معروف"
        speed_text_en = "Unknown"
    
    # فحص headers الأمان
    headers = data.get('security_headers', {})
    security_score = sum(1 for v in headers.values() if v) 
    
    if lang == 'ar':
        report = f"""
🌐 *تقرير فاحص الموقع*
━━━━━━━━━━━━━━━━━━━━━━━

🔗 الموقع: `{domain}`
🌍 عنوان IP: `{data.get('ip', 'غير معروف')}`
📡 حالة الموقع: `{data.get('status_code', 'غير معروف')}`
{ssl_icon} شهادة SSL: {'✅ صالحة' if data.get('ssl_valid') else '❌ غير صالحة أو منتهية'}
"""
        if data.get('ssl_expires'):
            report += f"📅 انتهاء SSL: `{data['ssl_expires']}`\n"
        
        report += f"""
{speed_icon} سرعة الاستجابة: `{rt}ms` ({speed_text_ar})
🖥️ الخادم: `{data.get('server', 'غير معروف')}`
{safe_icon} تقييم الأمان: `{security_score}/4` نقاط

🛡️ *رؤوس الأمان:*
"""
        header_names = {
            'X-Frame-Options': 'حماية الإطارات',
            'X-XSS-Protection': 'حماية XSS',
            'Strict-Transport-Security': 'HTTPS إلزامي',
            'Content-Security-Policy': 'سياسة المحتوى',
        }
        for h, v in headers.items():
            icon = "✅" if v else "❌"
            report += f"• {icon} {header_names.get(h, h)}\n"
        
        report += "\n━━━━━━━━━━━━━━━━━━━━━━━"
    else:
        report = f"""
🌐 *Website Scanner Report*
━━━━━━━━━━━━━━━━━━━━━━━

🔗 Website: `{domain}`
🌍 IP Address: `{data.get('ip', 'Unknown')}`
📡 Status Code: `{data.get('status_code', 'Unknown')}`
{ssl_icon} SSL Certificate: {'✅ Valid' if data.get('ssl_valid') else '❌ Invalid or Expired'}
"""
        if data.get('ssl_expires'):
            report += f"📅 SSL Expires: `{data['ssl_expires']}`\n"
        
        report += f"""
{speed_icon} Response Time: `{rt}ms` ({speed_text_en})
🖥️ Server: `{data.get('server', 'Unknown')}`
{safe_icon} Security Score: `{security_score}/4` points

🛡️ *Security Headers:*
"""
        for h, v in headers.items():
            icon = "✅" if v else "❌"
            report += f"• {icon} {h}\n"
        
        report += "\n━━━━━━━━━━━━━━━━━━━━━━━"
    
    return report.strip()


# ===================== 3. معلومات الرقم =====================

def lookup_phone(phone: str) -> dict:
    """يجلب معلومات رقم الجوال"""
    try:
        # تنظيف الرقم
        phone_clean = re.sub(r'[^\d+]', '', phone)
        if not phone_clean.startswith('+'):
            phone_clean = '+' + phone_clean
        
        parsed = phonenumbers.parse(phone_clean)
        
        if not phonenumbers.is_valid_number(parsed):
            return {'success': False, 'error': 'رقم غير صالح'}
        
        # نوع الرقم
        num_type = phonenumbers.number_type(parsed)
        type_map = {
            0: {'ar': 'ثابت', 'en': 'Fixed Line'},
            1: {'ar': 'موبايل', 'en': 'Mobile'},
            2: {'ar': 'ثابت أو موبايل', 'en': 'Fixed or Mobile'},
            3: {'ar': 'رقم مجاني', 'en': 'Toll Free'},
            4: {'ar': 'رقم مدفوع', 'en': 'Premium Rate'},
            5: {'ar': 'شبكة مشتركة', 'en': 'Shared Cost'},
            6: {'ar': 'VoIP', 'en': 'VoIP'},
            7: {'ar': 'رقم شخصي', 'en': 'Personal Number'},
            10: {'ar': 'UAN', 'en': 'UAN'},
        }
        type_info = type_map.get(num_type, {'ar': 'غير معروف', 'en': 'Unknown'})
        
        return {
            'success': True,
            'phone': phone_clean,
            'national': phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.NATIONAL),
            'international': phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.INTERNATIONAL),
            'country_ar': geocoder.description_for_number(parsed, 'ar') or 'غير معروف',
            'country_en': geocoder.description_for_number(parsed, 'en') or 'Unknown',
            'carrier_ar': carrier.name_for_number(parsed, 'ar') or 'غير معروف',
            'carrier_en': carrier.name_for_number(parsed, 'en') or 'Unknown',
            'timezone': list(pn_timezone.time_zones_for_number(parsed)),
            'type_ar': type_info['ar'],
            'type_en': type_info['en'],
            'country_code': parsed.country_code,
            'valid': phonenumbers.is_valid_number(parsed),
            'possible': phonenumbers.is_possible_number(parsed),
        }
    except phonenumbers.phonenumberutil.NumberParseException:
        return {'success': False, 'error': 'تعذّر تحليل الرقم. تأكد من إدخاله بالصيغة الدولية مثل: +966501234567'}
    except Exception as e:
        return {'success': False, 'error': str(e)}


def build_phone_report(data: dict, phone: str = '', lang: str = 'ar') -> str:
    """يبني تقرير معلومات الرقم"""
    if not data.get('success'):
        if lang == 'ar':
            return f"❌ {data.get('error', 'خطأ غير معروف')}"
        return f"❌ {data.get('error', 'Unknown error')}"
    
    tz = ', '.join(data.get('timezone', [])) or ('غير معروف' if lang == 'ar' else 'Unknown')
    
    if lang == 'ar':
        report = f"""
📱 *تقرير معلومات الرقم*
━━━━━━━━━━━━━━━━━━━━━━━

📞 الرقم: `{data['international']}`
🌍 الدولة: *{data['country_ar']}*
📡 شركة الاتصالات: *{data['carrier_ar']}*
📋 نوع الخط: *{data['type_ar']}*
🕐 المنطقة الزمنية: `{tz}`
🔢 كود الدولة: `+{data['country_code']}`

📝 *الصيغ:*
• المحلية: `{data['national']}`
• الدولية: `{data['international']}`

✅ الرقم صالح وقابل للاتصال

━━━━━━━━━━━━━━━━━━━━━━━
⚠️ هذه المعلومات عامة فقط ولا تكشف هوية صاحب الرقم"""
    else:
        report = f"""
📱 *Phone Lookup Report*
━━━━━━━━━━━━━━━━━━━━━━━

📞 Number: `{data['international']}`
🌍 Country: *{data['country_en']}*
📡 Carrier: *{data['carrier_en']}*
📋 Line Type: *{data['type_en']}*
🕐 Timezone: `{tz}`
🔢 Country Code: `+{data['country_code']}`

📝 *Formats:*
• National: `{data['national']}`
• International: `{data['international']}`

✅ Valid and reachable number

━━━━━━━━━━━━━━━━━━━━━━━
⚠️ This is general info only and does not reveal the owner's identity"""
    
    return report.strip()


# ===================== 4. عكس البحث بالصورة =====================

def reverse_image_search(image_url: str) -> dict:
    """يُنشئ روابط البحث العكسي للصورة"""
    encoded_url = requests.utils.quote(image_url, safe='')
    
    return {
        'success': True,
        'image_url': image_url,
        'google_lens': f'https://lens.google.com/uploadbyurl?url={encoded_url}',
        'tineye': f'https://tineye.com/search?url={encoded_url}',
        'yandex': f'https://yandex.com/images/search?url={encoded_url}&rpt=imageview',
        'bing': f'https://www.bing.com/images/search?view=detailv2&iss=sbi&q=imgurl:{encoded_url}',
    }


def build_reverse_image_report(data: dict, image_url: str = '', lang: str = 'ar') -> str:
    """يبني تقرير عكس البحث بالصورة"""
    if not data.get('success'):
        if lang == 'ar':
            return "❌ فشل إنشاء روابط البحث"
        return "❌ Failed to generate search links"
    
    if lang == 'ar':
        report = f"""
🖼️ *عكس البحث بالصورة*
━━━━━━━━━━━━━━━━━━━━━━━

اضغط على أي محرك بحث للعثور على مصدر الصورة:

🔍 [Google Lens]({data['google_lens']})
🔍 [TinEye]({data['tineye']})
🔍 [Yandex Images]({data['yandex']})
🔍 [Bing Images]({data['bing']})

━━━━━━━━━━━━━━━━━━━━━━━
💡 *نصيحة:* Google Lens وYandex هما الأفضل لكشف الحسابات المزيفة"""
    else:
        report = f"""
🖼️ *Reverse Image Search*
━━━━━━━━━━━━━━━━━━━━━━━

Click any search engine to find the image source:

🔍 [Google Lens]({data['google_lens']})
🔍 [TinEye]({data['tineye']})
🔍 [Yandex Images]({data['yandex']})
🔍 [Bing Images]({data['bing']})

━━━━━━━━━━━━━━━━━━━━━━━
💡 *Tip:* Google Lens and Yandex are best for detecting fake accounts"""
    
    return report.strip()


# ===================== 5. مختصر الروابط =====================

def shorten_url(url: str) -> dict:
    """يختصر الرابط عبر is.gd"""
    try:
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        
        r = requests.get(
            f'https://is.gd/create.php?format=json&url={requests.utils.quote(url, safe="")}',
            timeout=10
        )
        if r.status_code == 200:
            data = r.json()
            if 'shorturl' in data:
                return {
                    'success': True,
                    'original': url,
                    'short': data['shorturl'],
                    'service': 'is.gd'
                }
        
        # بديل: TinyURL
        r2 = requests.get(
            f'https://tinyurl.com/api-create.php?url={requests.utils.quote(url, safe="")}',
            timeout=10
        )
        if r2.status_code == 200 and r2.text.startswith('http'):
            return {
                'success': True,
                'original': url,
                'short': r2.text.strip(),
                'service': 'TinyURL'
            }
        
        return {'success': False, 'error': 'فشل اختصار الرابط'}
    except Exception as e:
        return {'success': False, 'error': str(e)}


def build_shorturl_report(data: dict, url: str = '', lang: str = 'ar') -> str:
    """يبني تقرير مختصر الروابط"""
    if not data.get('success'):
        if lang == 'ar':
            return f"❌ فشل اختصار الرابط: {data.get('error', 'خطأ غير معروف')}"
        return f"❌ Failed to shorten URL: {data.get('error', 'Unknown error')}"
    
    original = data.get('original', '')
    short = data.get('short', '')
    service = data.get('service', '')
    
    # اختصار الرابط الأصلي إذا كان طويلاً
    orig_display = original[:50] + '...' if len(original) > 50 else original
    
    if lang == 'ar':
        report = f"""
🔗 *مختصر الروابط*
━━━━━━━━━━━━━━━━━━━━━━━

📎 الرابط الأصلي:
`{orig_display}`

✂️ الرابط المختصر:
`{short}`

🛠️ الخدمة: {service}

━━━━━━━━━━━━━━━━━━━━━━━
💡 انسخ الرابط المختصر وشاركه بسهولة"""
    else:
        report = f"""
🔗 *URL Shortener*
━━━━━━━━━━━━━━━━━━━━━━━

📎 Original URL:
`{orig_display}`

✂️ Short URL:
`{short}`

🛠️ Service: {service}

━━━━━━━━━━━━━━━━━━━━━━━
💡 Copy the short URL and share it easily"""
    
    return report.strip()
