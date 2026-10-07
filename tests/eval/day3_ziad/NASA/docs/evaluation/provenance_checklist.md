# 📋 Data Provenance & Evaluation Checklist

## 1. Data Governance & Separation
- **Gold Data Isolation**: تم فصل مجموعة البيانات المعيارية (`rag_gold.jsonl`) تماماً عن مخرجات التشغيل وسجلات التجارب التاريخية (`experiment_history.json`).
- **Real-World Domain Sources**: تم استبدال الحالات الوهمية أو المتكررة بحالات حقيقية مستمدة من تقارير الفحص والأنظمة الهندسية المعتمدة.

## 2. Evaluation Standards & Thresholds
- **Automated Metric Computation**: حساب المقاييس إحصائياً وبرمجياً عبر `scikit-learn` ومنع كتابتها يدوياً.
- **Strict Exit Codes**: أي حالة اختبار تفشل في اجتياز عتبة الجودة المعتمدة (`Threshold`) تتسبب في إيقاف التشغيل بـ `Exit Code != 0` لضمان عدم تمرير أي أخطاء للإنتاج.

## 3. Compliance & Traceability
- كافة السجلات مرتبطة بمعرفات تدقيق (`Audit Logs`) وتتبع بصري ونصي دقيق.