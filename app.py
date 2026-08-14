"""
بک‌اند Flask برای آزمون طرحواره یانگ
اتصال فرانت‌اند به منطق نمره‌گذاری
"""

from flask import Flask, render_template, jsonify, request, send_file
from questions import get_questions, SCHEMAS
from scoring import calculate_scores, get_sorted_results, get_chart_data, get_summary, generate_interpretation
import json
import io
import os
from dotenv import load_dotenv

load_dotenv()
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

app = Flask(__name__)


@app.route("/")
def index():
    return render_template("index.html")

@app.route("/user-info")
def user_info():
    return render_template("user_info.html")

@app.route("/quiz")
def quiz():
    return render_template("quiz.html")

@app.route("/results")
def results():
    return render_template("results.html")


from ysq_l3 import YSQ_L3_QUESTIONS

@app.route("/api/questions", methods=["GET"])
def api_questions():
    test_type = request.args.get('type', 'ysq_s3')
    if test_type == 'ysq_l3':
        questions = YSQ_L3_QUESTIONS
    else:
        questions = get_questions(version="S3")
    safe_questions = [{"id": q["id"], "text": q["text"]} for q in questions]
    return jsonify(safe_questions)


@app.route("/api/results", methods=["POST"])
def api_results():
    data = request.get_json()
    answers = data.get('answers', {})
    test_type = data.get('test_type', 'ysq_s3')
    if not answers:
        return jsonify({"error": "پاسخی دریافت نشد"}), 400
    int_answers = {int(k): v for k, v in answers.items()}
    results = calculate_scores(int_answers, test_type=test_type)
    summary = get_summary(results)
    chart_data = get_chart_data(results)
    sorted_results = get_sorted_results(results, sort_by="severity")
    return jsonify({
        "results": results,
        "summary": summary,
        "chart_data": chart_data,
        "sorted_results": sorted_results,
        "test_type": test_type
    })


@app.route("/api/report", methods=["POST"])
def api_report():
    answers = request.get_json()
    int_answers = {int(k): v for k, v in answers.items()}
    results = calculate_scores(int_answers)
    interpretation = generate_interpretation(results)
    return jsonify({"report": interpretation})


# ============================================================
# توابع کمکی
# ============================================================

async def send_telegram_message(message_text):
    """ارسال پیام به تلگرام"""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("⚠️ تنظیمات تلگرام ناقص است")
        return
    try:
        import telegram
        bot = telegram.Bot(token=TELEGRAM_BOT_TOKEN)
        await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message_text)
        print("✅ پیام تلگرام ارسال شد")
    except Exception as e:
        print(f"❌ خطا در ارسال تلگرام: {e}")


def save_to_google_sheet(user_info, summary, test_type, pdf_path=None):
    """ذخیره نتایج + لینک PDF در گوگل شیت"""
    try:
        import gspread
        from google.oauth2.service_account import Credentials
        
        # غیرفعال کردن پروکسی
        os.environ.pop("HTTPS_PROXY", None)
        os.environ.pop("HTTP_PROXY", None)
        
        credentials_file = os.getenv("GOOGLE_CREDENTIALS_FILE", "google_credentials.json")
        sheet_id = os.getenv("GOOGLE_SHEET_ID")
        
        if not sheet_id:
            print("⚠️ GOOGLE_SHEET_ID تنظیم نشده")
            return
        
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive.file"
        ]
        creds = Credentials.from_service_account_file(credentials_file, scopes=scopes)
        
                # آپلود PDF به گوگل درایو
        drive_link = ""
        if pdf_path and os.path.exists(pdf_path):
            try:
                from googleapiclient.discovery import build
                from googleapiclient.http import MediaFileUpload
                
                print(f"📁 شروع آپلود به Drive...")
                print(f"📄 مسیر فایل: {pdf_path}")
                print(f"📂 Folder ID: {os.getenv('GOOGLE_DRIVE_FOLDER_ID', 'None')}")
                
                drive_service = build("drive", "v3", credentials=creds)
                folder_id = os.getenv("GOOGLE_DRIVE_FOLDER_ID")
                file_metadata = {
                    "name": f"schema_{user_info.get('phone', 'unknown')}_{test_type}.pdf",
                    "parents": [folder_id] if folder_id else []
                }
                media = MediaFileUpload(pdf_path, mimetype="application/pdf")
                uploaded = drive_service.files().create(
                    body=file_metadata, media_body=media, fields="id"
                ).execute()
                
                file_id = uploaded.get("id")
                drive_service.permissions().create(
                    fileId=file_id,
                    body={"type": "anyone", "role": "reader"},
                    fields="id"
                ).execute()
                
                drive_link = f"https://drive.google.com/file/d/{file_id}/view"
                print(f"✅ PDF آپلود شد: {drive_link}")
            except Exception as e:
                print(f"❌ خطا در آپلود Drive: {e}")
                import traceback
                traceback.print_exc()
        else:
            print(f"⚠️ فایل PDF یافت نشد: {pdf_path}")
        
        # ذخیره در گوگل شیت
        client = gspread.authorize(creds)
        sheet = client.open_by_key(sheet_id).sheet1
        
        if sheet.row_count == 0 or not sheet.row_values(1):
            headers = ["تاریخ", "نام", "موبایل", "شهر", "سن", "جنسیت", "نوع آزمون",
                       "میانگین کل", "شدید", "متوسط", "خفیف", "غیرفعال", "ایمیل", "لینک PDF"]
            sheet.append_row(headers)
        
        from datetime import datetime
        row = [
            datetime.now().strftime("%Y-%m-%d %H:%M"),
            user_info.get("fullname", ""),
            user_info.get("phone", ""),
            user_info.get("city", ""),
            user_info.get("age", ""),
            user_info.get("gender", ""), 
            "L3" if test_type == "ysq_l3" else "S3",
            summary.get("overall_average", 0),
            summary.get("severe_count", 0),
            summary.get("moderate_count", 0),
            summary.get("mild_count", 0),
            summary.get("inactive_count", 0),
            user_info.get("email", ""),
            drive_link
        ]
        
        sheet.append_row(row)
        print("✅ داده‌ها در گوگل شیت ذخیره شد")
        
    except Exception as e:
        print(f"❌ خطا در ذخیره گوگل شیت: {e}")


# ============================================================
# دانلود PDF
# ============================================================
from report_generator import generate_pdf

@app.route("/api/download-pdf", methods=["POST"])
def download_pdf():
    data = request.get_json()
    results = data.get('results', {})
    summary = data.get('summary', {})
    test_type = data.get('test_type', 'ysq_s3')
    user_info = data.get('user_info', {})
    if not results:
        return jsonify({"error": "نتیجه‌ای یافت نشد"}), 400

    # ۱. ساخت PDF
    pdf_path = generate_pdf(results, summary, test_type=test_type)
    print(f"📄 pdf_path = {pdf_path}")
    # ۲. ارسال به تلگرام
    try:
        msg = f"🧠 نتیجه آزمون طرحواره یانگ\n"
        msg += f"━━━━━━━━━━━━━━\n"
        msg += f"👤 نام: {user_info.get('fullname', '—')}\n"
        msg += f"📱 موبایل: {user_info.get('phone', '—')}\n"
        msg += f"🏙️ شهر: {user_info.get('city', '—')}\n"
        msg += f"🎂 سن: {user_info.get('age', '—')}\n"
        msg += f"👫 جنسیت: {user_info.get('gender', '—')}\n"
        msg += f"📋 نوع: {'جامع (L3)' if test_type == 'ysq_l3' else 'کوتاه (S3)'}\n"
        msg += f"━━━━━━━━━━━━━━\n"
        msg += f"📊 میانگین: {summary.get('overall_average', '—')}\n"
        msg += f"🔴 شدید: {summary.get('severe_count', 0)}\n"
        msg += f"🟠 متوسط: {summary.get('moderate_count', 0)}\n"
        msg += f"🟡 خفیف: {summary.get('mild_count', 0)}\n"
        msg += f"🟢 غیرفعال: {summary.get('inactive_count', 0)}"
        import asyncio
        asyncio.run(send_telegram_message(msg))
    except Exception as e:
        print(f"⚠️ خطا در ارسال تلگرام: {e}")

    
    # ۳. ذخیره در گوگل شیت + آپلود PDF به Drive
    save_to_google_sheet(user_info, summary, test_type, pdf_path=pdf_path)

    # ۴. تحویل PDF به کاربر
    return send_file(pdf_path, as_attachment=True, download_name="schema_report.pdf")


# ============================================================
# اجرای سرور
# ============================================================
if __name__ == "__main__":
    print("\n" + "=" * 50)
    print("  🧠 آزمون طرحواره یانگ - سرور فعال شد")
    print("  🌐 http://localhost:5000")
    print("=" * 50 + "\n")
    app.run(debug=True, port=5000)
