"""
بک‌اند Flask برای آزمون طرحواره یانگ
اتصال فرانت‌اند به منطق نمره‌گذاری
"""

from flask import Flask, render_template, jsonify, request, send_file
from questions import get_questions, SCHEMAS
from scoring import calculate_scores, get_sorted_results, get_chart_data, get_summary, generate_interpretation
import json
import os
import io

app = Flask(__name__)


@app.route("/")
def index():
    """صفحه ورود"""
    return render_template("index.html")

@app.route("/user-info")
def user_info():
    """صفحه دریافت اطلاعات کاربر"""
    return render_template("user_info.html")
@app.route("/quiz")
def quiz():
    """صفحه سوالات"""
    return render_template("quiz.html")


@app.route("/results")
def results():
    """صفحه نتایج"""
    return render_template("results.html")


from ysq_l3 import YSQ_L3_QUESTIONS

@app.route("/api/questions", methods=["GET"])
def api_questions():
    """ارسال لیست سوالات به فرانت‌اند بر اساس نوع آزمون"""
    test_type = request.args.get('type', 'ysq_s3')
    
    if test_type == 'ysq_l3':
        questions = YSQ_L3_QUESTIONS
    else:
        questions = get_questions(version="S3")
        
    safe_questions = [{"id": q["id"], "text": q["text"]} for q in questions]
    return jsonify(safe_questions)


@app.route("/api/results", methods=["POST"])
def api_results():
    """دریافت پاسخ‌ها و بازگرداندن نتایج"""
    data = request.get_json()
    answers = data.get('answers', {})
    test_type = data.get('test_type', 'ysq_s3')

    if not answers:
        return jsonify({"error": "پاسخی دریافت نشد"}), 400

    # تبدیل کلیدهای رشته‌ای به عدد
    int_answers = {int(k): v for k, v in answers.items()}

    # نمره‌گذاری بر اساس نوع آزمون
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
    """تولید گزارش متنی کامل"""
    answers = request.get_json()
    int_answers = {int(k): v for k, v in answers.items()}
    results = calculate_scores(int_answers)
    interpretation = generate_interpretation(results)
    return jsonify({"report": interpretation})


# ============================================================
# اجرای سرور
# ============================================================
from report_generator import generate_pdf

@app.route("/api/download-pdf", methods=["POST"])
def download_pdf():
    """تولید و دانلود PDF بر اساس نتایج آماده"""
    data = request.get_json()
    
    results = data.get('results', {})
    summary = data.get('summary', {})
    test_type = data.get('test_type', 'ysq_s3') # ✅ دریافت نوع آزمون
    
    if not results:
        return jsonify({"error": "نتیجه‌ای برای ساخت PDF یافت نشد"}), 400
        
    # ✅ ارسال نوع آزمون به تولیدکننده PDF
    pdf_path = generate_pdf(results, summary, test_type=test_type)
    return send_file(pdf_path, as_attachment=True, download_name="schema_report.pdf")

if __name__ == "__main__":
    print("\n" + "=" * 50)
    print("  🧠 آزمون طرحواره یانگ - سرور فعال شد")
    print("  🌐 http://localhost:5000")
    print("=" * 50 + "\n")
    app.run(debug=True, port=5000)