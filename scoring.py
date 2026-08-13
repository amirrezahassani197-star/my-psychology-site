"""
منطق نمره‌گذاری و تفسیر نتایج آزمون طرحواره یانگ (YSQ)
نمره‌گذاری بر اساس میانگین سوالات هر طرحواره
Cutoff ها بر اساس Young et al. (2003)
"""

from questions import SCHEMAS, YSQ_S3_QUESTIONS, get_schema_level
from ysq_l3 import YSQ_L3_QUESTIONS


def calculate_scores(answers: dict, test_type="ysq_s3") -> dict:
    """
    محاسبه نمرات تمام طرحواره‌ها
    
    Args:
        answers: دیکشنری {question_id: score} 
        test_type: نوع آزمون ("ysq_s3" یا "ysq_l3")
    
    Returns:
        دیکشنری ساختاریافته نتایج
    """
    # انتخاب بانک سوالات بر اساس نوع آزمون
    if test_type == "ysq_l3":
        current_questions = YSQ_L3_QUESTIONS
    else:
        current_questions = YSQ_S3_QUESTIONS

    # گروه‌بندی سوالات بر اساس طرحواره
    schema_questions = {}
    for q in current_questions:
        schema = q["schema"]
        if schema not in schema_questions:
            schema_questions[schema] = []
        schema_questions[schema].append(q["id"])
    
    results = {}
    
    for schema_code, question_ids in schema_questions.items():
        # جمع‌آوری نمرات سوالات این طرحواره
        scores = []
        for qid in question_ids:
            if qid in answers:
                scores.append(answers[qid])
        
        if not scores:
            continue
        
        # محاسبه میانگین
        avg_score = round(sum(scores) / len(scores), 2)
        
        # تعیین سطح بالینی
        level = get_schema_level(avg_score)
        
        # اطلاعات کامل طرحواره
        schema_info = SCHEMAS.get(schema_code, {})
        
        results[schema_code] = {
            "code": schema_code,
            "name": schema_info.get("name", schema_code),
            "category": schema_info.get("category", ""),
            "score": avg_score,
            "level": level["label"],
            "color": level["color"],
            "description": schema_info.get("description", ""),
            "childhood_origin": schema_info.get("childhood_origin", ""),
            "impact": schema_info.get("impact", ""),
            "recommendation": schema_info.get("recommendation", ""),
            "question_count": len(scores),
            "raw_scores": scores
        }
    
    return results


def get_sorted_results(results: dict, sort_by="severity") -> list:
    """
    مرتب‌سازی نتایج
    
    Args:
        results: خروجی تابع calculate_scores
        sort_by: "severity" (شدید به خفیف) یا "alphabetical" یا "category"
    
    Returns:
        لیست مرتب‌شده نتایج
    """
    items = list(results.values())
    
    if sort_by == "severity":
        # مرتب‌سازی نزولی بر اساس نمره (شدید اول)
        items.sort(key=lambda x: x["score"], reverse=True)
    elif sort_by == "alphabetical":
        items.sort(key=lambda x: x["name"])
    elif sort_by == "category":
        category_order = [
            "بریدگی و طرد",
            "خودگردانی و عملکرد مختل",
            "محدودیت‌های مختل",
            "دیگرجهت‌مندی",
            "بیش‌جبران‌گری"
        ]
        items.sort(key=lambda x: (
            category_order.index(x["category"]) if x["category"] in category_order else 99,
            -x["score"]
        ))
    
    return items


def get_chart_data(results: dict) -> dict:
    """
    آماده‌سازی داده برای نمودار Chart.js
    
    Returns:
        دیکشنری سازگار با Chart.js bar/radar chart
    """
    sorted_items = get_sorted_results(results, sort_by="severity")
    
    return {
        "labels": [item["name"] for item in sorted_items],
        "datasets": [{
            "label": "نمره طرحواره",
            "data": [item["score"] for item in sorted_items],
            "backgroundColor": [item["color"] for item in sorted_items],
            "borderColor": [item["color"] for item in sorted_items],
            "borderWidth": 1
        }],
        "options": {
            "indexAxis": "y",
            "scales": {
                "x": {"min": 0, "max": 6, "title": {"display": True, "text": "نمره (۱ تا ۶)"}}
            },
            "plugins": {
                "legend": {"display": False},
                "annotation": {
                    "annotations": {
                        "cutoff_mild": {"type": "line", "xMin": 2, "xMax": 2, "borderColor": "#f59e0b", "borderDash": [5, 5]},
                        "cutoff_severe": {"type": "line", "xMin": 4, "xMax": 4, "borderColor": "#ef4444", "borderDash": [5, 5]}
                    }
                }
            }
        }
    }


def get_summary(results: dict) -> dict:
    """
    خلاصه آماری نتایج
    
    Returns:
        دیکشنری شامل آمار کلی
    """
    items = list(results.values())
    total = len(items)
    
    severe = [i for i in items if i["score"] >= 4.0]
    moderate = [i for i in items if 3.0 <= i["score"] < 4.0]
    mild = [i for i in items if 2.0 <= i["score"] < 3.0]
    inactive = [i for i in items if i["score"] < 2.0]
    
    overall_avg = round(sum(i["score"] for i in items) / total, 2) if total > 0 else 0
    
    return {
        "total_schemas": total,
        "overall_average": overall_avg,
        "severe_count": len(severe),
        "moderate_count": len(moderate),
        "mild_count": len(mild),
        "inactive_count": len(inactive),
        "severe_schemas": [i["name"] for i in severe],
        "moderate_schemas": [i["name"] for i in moderate],
        "top_3": [i["name"] for i in get_sorted_results(results)[:3]],
        "needs_attention": len(severe) + len(moderate) > 0
    }


def generate_interpretation(results: dict) -> str:
    """
    تولید تفسیر متنی فارسی نتایج
    
    Returns:
        متن تفسیر کامل
    """
    summary = get_summary(results)
    sorted_items = get_sorted_results(results, sort_by="severity")
    
    lines = []
    lines.append("=" * 60)
    lines.append("       گزارش تفسیری آزمون طرحواره یانگ (YSQ-S3)")
    lines.append("=" * 60)
    lines.append("")
    lines.append(f"📊 میانگین کلی: {summary['overall_average']} از ۶")
    lines.append(f"🔴 طرحواره‌های شدید: {summary['severe_count']} مورد")
    lines.append(f"🟠 طرحواره‌های متوسط: {summary['moderate_count']} مورد")
    lines.append(f"🟡 طرحواره‌های خفیف: {summary['mild_count']} مورد")
    lines.append(f"🟢 طرحواره‌های غیرفعال: {summary['inactive_count']} مورد")
    lines.append("")
    
    if summary["severe_count"] > 0:
        lines.append("⚠️ طرحواره‌هایی که نیاز به توجه ویژه دارند:")
        for name in summary["severe_schemas"]:
            lines.append(f"   • {name}")
        lines.append("")
    
    lines.append("-" * 60)
    lines.append("📋 تحلیل تفصیلی هر طرحواره:")
    lines.append("-" * 60)
    
    for item in sorted_items:
        emoji = "🔴" if item["score"] >= 4 else "🟠" if item["score"] >= 3 else "🟡" if item["score"] >= 2 else "🟢"
        lines.append("")
        lines.append(f"{emoji} {item['name']} ({item['code']})")
        lines.append(f"   دسته: {item['category']}")
        lines.append(f"   نمره: {item['score']} — {item['level']}")
        lines.append(f"   توضیح: {item['description']}")
        lines.append(f"   ریشه کودکی: {item['childhood_origin']}")
        lines.append(f"   تأثیرات: {item['impact']}")
        lines.append(f"   پیشنهاد: {item['recommendation']}")
        lines.append("")
    
    lines.append("=" * 60)
    lines.append("⚕️ سلب مسئولیت:")
    lines.append("این گزارش صرفاً جنبه غربالگری و آموزشی دارد و جایگزین")
    lines.append("تشخیص بالینی توسط روانشناس دارای پروانه نیست.")
    lines.append("در صورت داشتن نمرات بالا، مراجعه به متخصص توصیه می‌شود.")
    lines.append("=" * 60)
    
    return "\n".join(lines)


# ============================================================
# تست سریع
# ============================================================
if __name__ == "__main__":
    # نمونه پاسخ‌های تصادفی برای تست
    import random
    test_answers = {q["id"]: random.randint(1, 6) for q in YSQ_S3_QUESTIONS}
    
    results = calculate_scores(test_answers)
    summary = get_summary(results)
    
    print(f"✅ نمره‌گذاری {len(results)} طرحواره انجام شد")
    print(f"📊 میانگین کلی: {summary['overall_average']}")
    print(f"🔴 شدید: {summary['severe_count']} | 🟠 متوسط: {summary['moderate_count']} | 🟡 خفیف: {summary['mild_count']} | 🟢 غیرفعال: {summary['inactive_count']}")
    print(f"🏆 بالاترین نمرات: {', '.join(summary['top_3'])}")
    print()
    print(generate_interpretation(results))