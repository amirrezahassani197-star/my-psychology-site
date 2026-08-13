"""
تولید گزارش PDF فارسی - نسخه اصلاح‌شده (RTL + Shaping)
"""

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor, white
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_JUSTIFY
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.graphics.shapes import Drawing, Rect, String
import os
from datetime import datetime
import uuid

# --- کتابخانه‌های اصلاح فارسی ---
try:
    import arabic_reshaper
    from bidi.algorithm import get_display
    HAS_RTL_SUPPORT = True
except ImportError:
    HAS_RTL_SUPPORT = False
    print("⚠️ لطفاً نصب کنید: pip install arabic-reshaper python-bidi")

# ============================================================
# تنظیمات فونت
# ============================================================
FONT_PATH = os.path.join(os.path.dirname(__file__), "static", "Vazirmatn-Regular.ttf")
if os.path.exists(FONT_PATH):
    pdfmetrics.registerFont(TTFont('Vazir', FONT_PATH))
    FONT_NAME = 'Vazir'
else:
    FONT_NAME = 'Helvetica' # Fallback

# ============================================================
# تابع جادویی اصلاح متن
# ============================================================
def fix(text):
    if not text: return ""
    if HAS_RTL_SUPPORT:
        return get_display(arabic_reshaper.reshape(str(text)))
    return str(text)

# ============================================================
# رنگ‌ها
# ============================================================
COLORS = {
    "primary": HexColor("#6366f1"), "severe": HexColor("#ef4444"),
    "moderate": HexColor("#f97316"), "mild": HexColor("#f59e0b"),
    "inactive": HexColor("#22c55e"), "bg_light": HexColor("#f8fafc"),
    "text_dark": HexColor("#1e293b"), "text_gray": HexColor("#64748b"),
    "border": HexColor("#e2e8f0")
}

def create_styles():
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='FaTitle', fontName=FONT_NAME, fontSize=20, leading=26, alignment=TA_CENTER, textColor=COLORS["primary"], spaceAfter=20))
    styles.add(ParagraphStyle(name='FaHeading', fontName=FONT_NAME, fontSize=13, leading=19, alignment=TA_RIGHT, textColor=COLORS["text_dark"], spaceBefore=10, spaceAfter=6))
    styles.add(ParagraphStyle(name='FaBody', fontName=FONT_NAME, fontSize=10, leading=16, alignment=TA_RIGHT, textColor=COLORS["text_dark"], spaceAfter=4))
    styles.add(ParagraphStyle(name='FaSmall', fontName=FONT_NAME, fontSize=8, leading=12, alignment=TA_CENTER, textColor=COLORS["text_gray"]))
    styles.add(ParagraphStyle(name='FaCenter', fontName=FONT_NAME, fontSize=10, leading=14, alignment=TA_CENTER, textColor=COLORS["text_gray"], spaceAfter=4))
    return styles

def draw_header_footer(canvas, doc):
    canvas.saveState()
    width, height = A4
    canvas.setFillColor(COLORS["primary"])
    canvas.rect(0, height - 20*mm, width, 20*mm, fill=1, stroke=0)
    canvas.setFillColor(white)
    canvas.setFont(FONT_NAME, 11)
    canvas.drawRightString(width - 15*mm, height - 13*mm, fix("گزارش آزمون طرحواره یانگ"))
    canvas.setFont(FONT_NAME, 8)
    canvas.drawString(15*mm, height - 13*mm, f"Date: {datetime.now().strftime('%Y/%m/%d')}")
    canvas.setFillColor(COLORS["text_gray"])
    canvas.setFont(FONT_NAME, 7)
    canvas.drawCentredString(width/2, 10*mm, fix(f"صفحه {doc.page}"))
    canvas.restoreState()

def generate_chart_drawing(results):
    sorted_items = sorted(results.values(), key=lambda x: x["score"], reverse=True)
    num_items = len(sorted_items)
    drawing_height = max(320, num_items * 20 + 40)
    drawing = Drawing(450, drawing_height)
    start_y = drawing_height - 20
    for i, item in enumerate(sorted_items):  # ← همه طرحواره‌ها
        y = start_y - i * 18
        bar_width = (item["score"] / 6.0) * 250
        color = COLORS["severe"] if item["score"] >= 4 else COLORS["moderate"] if item["score"] >= 3 else COLORS["mild"] if item["score"] >= 2 else COLORS["inactive"]
        
        drawing.add(Rect(160, y, bar_width, 12, fillColor=color, strokeColor=None))
        # نام طرحواره (سمت راست)
        drawing.add(String(440, y + 2, fix(item["name"]), fontName=FONT_NAME, fontSize=8, textAnchor="end", fillColor=COLORS["text_dark"]))
        # نمره (کنار نوار)
        drawing.add(String(165 + bar_width, y + 2, str(item["score"]), fontName=FONT_NAME, fontSize=8, fillColor=COLORS["text_dark"]))
    return drawing

def generate_pdf(results, summary, test_type="ysq_s3", output_path=None):
    if not output_path:
        os.makedirs("reports", exist_ok=True)
        output_path = os.path.join("reports", f"report_{uuid.uuid4().hex[:6]}.pdf")

    doc = SimpleDocTemplate(output_path, pagesize=A4, rightMargin=15*mm, leftMargin=15*mm, topMargin=25*mm, bottomMargin=15*mm)
    styles = create_styles()
    story = []

    # عنوان
    # عنوان داینامیک بر اساس نوع آزمون
    if test_type == "ysq_l3":
        en_title = "Young Schema Questionnaire - Long Form (YSQ-L3)"
        fa_subtitle = "نسخه جامع (۲۲۲+ سوال)"
    else:
        en_title = "Young Schema Questionnaire - Short Form (YSQ-S3)"
        fa_subtitle = "نسخه کوتاه (۹۰ سوال)"

    story.append(Spacer(1, 10*mm))
    story.append(Paragraph(fix("گزارش تفسیری آزمون طرحواره یانگ"), styles['FaTitle']))
    story.append(Paragraph(fix(fa_subtitle), styles['FaCenter'])) # <-- اینجا از استایل جدید استفاده کردیم
    story.append(Paragraph(en_title, styles['FaSmall']))
    story.append(Spacer(1, 5*mm))

    # جدول خلاصه
    story.append(Paragraph(fix("خلاصه نتایج"), styles['FaHeading']))
    data = [
        [fix("میانگین کلی"), str(summary.get("overall_average", "-"))],
        [fix("طرحواره‌های شدید"), str(summary.get("severe_count", 0))],
        [fix("طرحواره‌های متوسط"), str(summary.get("moderate_count", 0))],
        [fix("طرحواره‌های خفیف"), str(summary.get("mild_count", 0))],
        [fix("طرحواره‌های غیرفعال"), str(summary.get("inactive_count", 0))]
    ]
    t = Table(data, colWidths=[100*mm, 40*mm])
    t.setStyle(TableStyle([
        ('FONTNAME', (0,0), (-1,-1), FONT_NAME), ('FONTSIZE', (0,0), (-1,-1), 10),
        ('ALIGN', (0,0), (-1,-1), 'RIGHT'), ('BACKGROUND', (0,0), (-1,-1), COLORS["bg_light"]),
        ('GRID', (0,0), (-1,-1), 0.5, COLORS["border"]), ('TOPPADDING', (0,0), (-1,-1), 6), ('BOTTOMPADDING', (0,0), (-1,-1), 6)
    ]))
    story.append(t)
    story.append(Spacer(1, 8*mm))

    # نمودار
    story.append(Paragraph(fix("پروفایل طرحواره‌ها"), styles['FaHeading']))
    try: story.append(generate_chart_drawing(results))
    except: pass
    story.append(PageBreak())

    # تحلیل‌ها
    story.append(Paragraph(fix("تحلیل تفصیلی طرحواره‌ها"), styles['FaHeading']))
    sorted_res = sorted(results.values(), key=lambda x: x["score"], reverse=True)
    
    for item in sorted_res:
        title = f"{item['name']} ({item['code']}) - {item['score']} ({item['level']})"
        story.append(Paragraph(fix(title), styles['FaHeading']))
        
        details = [
            ("دسته:", item.get("category", "")),
            ("توضیح:", item.get("description", "")),
            ("ریشه:", item.get("childhood_origin", "")),
            ("اثر:", item.get("impact", "")),
            ("درمان:", item.get("recommendation", ""))
        ]
        for label, txt in details:
            story.append(Paragraph(fix(f"{label} {txt}"), styles['FaBody']))
        story.append(Spacer(1, 3*mm))

    # سلب مسئولیت
    story.append(PageBreak())
    story.append(Paragraph(fix("سلب مسئولیت"), styles['FaHeading']))
    story.append(Paragraph(fix("این گزارش صرفاً جنبه آموزشی دارد و جایگزین تشخیص بالینی نیست."), styles['FaBody']))
    
    doc.build(story, onFirstPage=draw_header_footer, onLaterPages=draw_header_footer)
    return output_path

if __name__ == "__main__":
    from questions import YSQ_S3_QUESTIONS
    from scoring import calculate_scores, get_summary
    import random
    ans = {q["id"]: random.randint(1, 6) for q in YSQ_S3_QUESTIONS}
    res = calculate_scores(ans)
    summ = get_summary(res)
    print(f"✅ PDF Created: {generate_pdf(res, summ)}")
