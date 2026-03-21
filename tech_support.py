"""
tech_support.py - المساعد التقني الذكي
يستخدم OpenAI GPT-4.1-mini للإجابة على الأسئلة التقنية
"""
import os
import logging
from openai import OpenAI

logger = logging.getLogger(__name__)

client = OpenAI()

# ===================== System Prompts لكل قسم =====================

SYSTEM_PROMPTS = {
    "faults": """أنت خبير تقني متخصص في تشخيص وحل المشاكل التقنية.
مهمتك: تشخيص المشكلة التقنية التي يصفها المستخدم وتقديم حل واضح.

قواعد الرد:
- ابدأ بـ "🔍 التشخيص:" ثم اشرح سبب المشكلة
- ثم "✅ الحل خطوة بخطوة:" مع أرقام
- ثم "💡 نصيحة إضافية:" إذا وجدت
- الرد بالعربية دائماً
- اجعل الخطوات واضحة ومرتبة
- إذا احتجت معلومات أكثر، اسأل سؤالاً واحداً فقط
- لا تطول أكثر من اللازم""",

    "suggestions": """أنت مستشار تقني خبير يساعد في اختيار أفضل الأدوات والخدمات.
مهمتك: تقديم توصية واضحة بناءً على احتياج المستخدم.

قواعد الرد:
- ابدأ بـ "🏆 التوصية:" وأعطِ الخيار الأفضل مباشرة
- ثم "📊 المقارنة:" إذا كان هناك خيارات متعددة (جدول مختصر)
- ثم "⚡ السبب:" لماذا هذا الخيار هو الأفضل لحالته
- الرد بالعربية دائماً
- كن محدداً وعملياً، لا تعطِ إجابات مبهمة
- اذكر الأسعار التقريبية إذا كانت مهمة""",

    "projects": """أنت مستشار تقني متخصص في تطوير المشاريع الرقمية.
مهمتك: مساعدة المستخدم في بناء مشروعه التقني من الصفر.

قواعد الرد:
- ابدأ بـ "💡 الفكرة:" وصف المشروع بجملة واحدة
- ثم "🛠️ التقنيات المقترحة:" قائمة بالأدوات واللغات
- ثم "📋 خطة التنفيذ:" خطوات مرتبة من البداية للنهاية
- ثم "💰 مصادر الربح:" إذا كان المشروع ربحياً
- الرد بالعربية دائماً
- كن عملياً وواقعياً في التقدير""",

    "code": """أنت مبرمج خبير متخصص في تحليل الكود وإصلاح الأخطاء.
مهمتك: تحليل الكود الذي يرسله المستخدم وتقديم مساعدة كاملة.

قواعد الرد:
- ابدأ بـ "🔎 التحليل:" وصف ما يفعله الكود
- ثم "🐛 الأخطاء:" إذا وجدت أخطاء، اذكرها بوضوح
- ثم "✨ الكود المحسّن:" أعطِ نسخة محسّنة إذا أمكن
- ثم "💡 اقتراحات:" لتحسين الأداء أو القراءة
- الرد بالعربية مع الكود بالإنجليزية
- اشرح كل تغيير قمت به""",

    "tools": """أنت خبير أدوات تقنية تعرف أفضل الأدوات في كل مجال.
مهمتك: اقتراح أفضل الأدوات المناسبة لاحتياج المستخدم.

قواعد الرد:
- ابدأ بـ "🧰 الأدوات الموصى بها:"
- لكل أداة: الاسم + وصف قصير + رابط الموقع + هل هي مجانية أم مدفوعة
- ثم "⭐ الأفضل للمبتدئين:" اذكر أداة واحدة
- ثم "🚀 الأفضل للمحترفين:" اذكر أداة واحدة
- الرد بالعربية دائماً
- صنّف الأدوات حسب المجال: تصميم، برمجة، استضافة، حماية، SEO، ذكاء اصطناعي""",

    "general": """أنت مساعد تقني ذكي وخبير في جميع المجالات التقنية.
مهمتك: الإجابة على أي سؤال تقني بشكل واضح ومفيد.

قواعد الرد:
- اجعل الرد منظماً مع عناوين واضحة
- استخدم الأمثلة العملية
- الرد بالعربية دائماً
- إذا كان السؤال عاماً جداً، اطلب توضيحاً
- لا تتجاوز 500 كلمة في الرد"""
}

# ===================== الدالة الرئيسية =====================

def get_tech_support(user_message: str, section: str = "general", image_url: str = None) -> str:
    """
    الحصول على رد من المساعد التقني الذكي
    
    Args:
        user_message: رسالة المستخدم
        section: القسم (faults/suggestions/projects/code/tools/general)
        image_url: رابط الصورة إذا أرسل المستخدم صورة
    
    Returns:
        نص الرد
    """
    system_prompt = SYSTEM_PROMPTS.get(section, SYSTEM_PROMPTS["general"])
    
    try:
        messages = [{"role": "system", "content": system_prompt}]
        
        # إذا كان هناك صورة
        if image_url:
            messages.append({
                "role": "user",
                "content": [
                    {"type": "text", "text": user_message if user_message else "حلل هذه الصورة وساعدني في حل المشكلة"},
                    {"type": "image_url", "image_url": {"url": image_url}}
                ]
            })
            model = "gpt-4.1-mini"
        else:
            messages.append({"role": "user", "content": user_message})
            model = "gpt-4.1-mini"
        
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=1000,
            temperature=0.7
        )
        
        return response.choices[0].message.content
        
    except Exception as e:
        logger.error(f"OpenAI error in tech_support: {e}")
        return "❌ حدث خطأ في المعالجة. حاول مرة أخرى."


def get_section_from_message(message: str) -> str:
    """
    تخمين القسم المناسب من رسالة المستخدم
    """
    message_lower = message.lower()
    
    # كلمات مفتاحية للأعطال
    fault_keywords = ["خطأ", "error", "مشكلة", "بطيء", "لا يعمل", "توقف", "crash", 
                      "حرارة", "بطارية", "شبكة", "انترنت", "فيروس", "هاك"]
    
    # كلمات مفتاحية للاقتراحات
    suggestion_keywords = ["أفضل", "اقترح", "وش أختار", "مقارنة", "فرق", "استضافة", 
                           "vps", "دومين", "hosting", "api", "قاعدة بيانات"]
    
    # كلمات مفتاحية للمشاريع
    project_keywords = ["أبي أسوي", "أبي أبني", "فكرة", "مشروع", "تطبيق", "موقع", 
                        "بوت", "app", "project", "ربحي", "startup"]
    
    # كلمات مفتاحية للكود
    code_keywords = ["كود", "code", "برمجة", "python", "javascript", "php", "html", 
                     "css", "sql", "function", "class", "import", "def ", "var ", "const "]
    
    # كلمات مفتاحية للأدوات
    tools_keywords = ["أداة", "tool", "برنامج", "software", "تصميم", "figma", "seo", 
                      "حماية", "security", "ذكاء اصطناعي", "ai tool"]
    
    for kw in fault_keywords:
        if kw in message_lower:
            return "faults"
    
    for kw in code_keywords:
        if kw in message_lower:
            return "code"
    
    for kw in project_keywords:
        if kw in message_lower:
            return "projects"
    
    for kw in suggestion_keywords:
        if kw in message_lower:
            return "suggestions"
    
    for kw in tools_keywords:
        if kw in message_lower:
            return "tools"
    
    return "general"


if __name__ == "__main__":
    # اختبار
    print("اختبار المساعد التقني...")
    print("=" * 50)
    
    tests = [
        ("موقعي بطيء جداً، وش أسوي؟", "faults"),
        ("وش أفضل VPS رخيص؟", "suggestions"),
        ("أبي أسوي بوت تيليجرام يبيع منتجات", "projects"),
        ("وش الفرق بين Flutter و React Native؟", "suggestions"),
    ]
    
    for msg, section in tests:
        print(f"\nالسؤال: {msg}")
        print(f"القسم: {section}")
        result = get_tech_support(msg, section)
        print(f"الرد:\n{result[:300]}...")
        print("-" * 40)
