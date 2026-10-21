# دليل المعمارية الشامل والمخططات التوضيحية لمشروع Flame in Freefall
## Comprehensive Architecture Guide & System Diagrams

---

## 1. نبذة عامة وأهداف المشروع (Project Mission & Overview)

مشروع **Flame in Freefall** هو منصة ذكاء علمي وتحليلي مبنية وفق نهج **"الأدلة أولاً" (Evidence-First Scientific Intelligence Platform)**، تم تطويرها خصيصاً لمسابقة **NASA Space Apps Challenge**.

### 1.1 المشكلة العلمية (Scientific Context)
في بيئة الأرض (1G)، يتحكم الحمل الحراري الطبيعي (Buoyancy / Natural Convection) في شكل اللهب وسلوكه؛ حيث يصعد الهواء الساخن للأعلى مما يمنح اللهب شكله المخروطي المستدق المميز ويسحب الأكسجين باستمرار لقاعدة اللهب.  
أما في الفضاء والجاذبية الصغرى (**Microgravity - 0G/μG**)، يختفي الحمل الحراري الطبيعي تماماً، ويصبح انتقال الحرارة والغازات محكوماً بـ **الانتشار الجزيئي (Molecular Diffusion)**، مما يجعل اللهب يتخذ شكلاً كروياً (Spherical Flame)، ويحترق بدرجات حرارة وسرعات مختلفة وظواهر إخماد فريدة (Cool Flames & Radiative Extinction).

### 1.2 الركائز الأساسية للمشروع (Core Architectural Principles)
1. **الدليل فوق الادعاء (Evidence Over Claims):** لا يتم قبول أي حقيقة أو استنتاج علمي دون ربطه بسجل تجريبي موثق.
2. **سلسلة المصداقية الإلزامية (Mandatory Provenance Chain):** كل استعلام، قياس بالرؤية الحاسوبية، أو استنتاج ذكي يجب أن يتتبع مساره بدقة حتى الملف المصدر الأصلي المشفر بـ `sha256`.
3. **الحفاظ على عدم اليقين (Preserve Uncertainty):** إذا كانت البيانات غير كافية أو متضاربة، يتم إظهار التضارب صراحة للمستخدم بدلاً من افتراض إجابة وهمية (No Hallucinations).
4. **التعاقد أولاً (Contract-First Architecture):** الاعتماد على مواصفات صارمة واضحة (OpenAPI 3.1 & JSON Schemas) قبل كتابة الكود.

---

## 2. المعمارية العامة للنظام (End-to-End System Architecture)

يوضح المخطط التالي بنية المنظومة الموزعة بجميع طبقاتها: من بيانات ناسا الخام وصولاً لواجهة المستخدم ومنظومة الذكاء الاصطناعي الخارجي (AURA AI).

```mermaid
flowchart TB
    subgraph NASA_Sources["🌐 مصادر بيانات ناسا الفضائية (NASA Data Sources)"]
        PSI_API["NASA PSI API & S3<br/>(Physical Sciences Informatics)"]
        NTRS["NASA Technical Reports (PDFs)<br/>NTRS Research Papers"]
        EXP_TABLES["جداول القياسات التجريبية<br/>(CSV / ISA-Tab)"]
        RAW_MEDIA["مقاطع الفيديو والصور الفضائية<br/>(BASS-II / FLEX / SAFFIRE / SPICE)"]
        PSI_API --> RAW_MEDIA
        PSI_API --> EXP_TABLES
    end

    subgraph Data_Ingestion["📥 طبقة استيراد البيانات وتتبع المصداقية (Ingestion & Provenance)"]
        INGEST_SCRIPT["psi_download.py<br/>(تنزيل البيانات المعيارية)"]
        PROV_SCRIPT["record_provenance.py<br/>(حساب sha256 وسجل التدقيق)"]
        REGISTRY["source_registry.csv<br/>(سجل المصادر والرخص CC0)"]
        FILES_META["files.jsonl<br/>(بيانات وصفية للملفات والمصداقية)"]
        
        RAW_MEDIA --> INGEST_SCRIPT
        EXP_TABLES --> INGEST_SCRIPT
        NTRS --> PROV_SCRIPT
        INGEST_SCRIPT --> PROV_SCRIPT
        REGISTRY --> PROV_SCRIPT
        PROV_SCRIPT --> FILES_META
    end

    subgraph Storage_Tier["💾 طبقة التخزين وإدارة الحالة (Persistence & Storage)"]
        POSTGRES[("🐘 PostgreSQL 16 + pgvector<br/>- جداول المصادر والملفات<br/>- الوثائق والمقاطع (Chunks)<br/>- التجارب والظروف الفيزيائية<br/>- نتائج التحليلات وسجلات الأدلة")]
        MINIO[("🪣 MinIO Object Storage (S3-Compatible)<br/>- الصور الأصلية (Original Frames)<br/>- الصور المعالجة (Preprocessed)<br/>- أقنعة التجزئة (Binary Masks)<br/>- الرسوم المتراكبة (Overlay Visualizations)")]
        REDIS[("⚡ Redis 7 (In-Memory Data Store)<br/>- طابور المهام (RQ Job Queue)<br/>- التخزين المؤقت للاستجابات (CAG Cache)")]
    end

    FILES_META -->|flame_api.seed & ingest| POSTGRES

    subgraph Backend_Tier["⚙️ خوادم المعالجة والواجهة الخلفية (Backend & Compute)"]
        FASTAPI["🚀 FastAPI Core Service (apps/api)<br/>- إدارة واجهات OpenAPI 3.1 REST<br/>- المصادقة والتحقق (Token Auth)<br/>- البحث الدلالي والهجين<br/>- استقبال واسترجاع تحليلات الصور"]
        WORKER["👷 Background Worker (RQ Worker)<br/>- معالجة غير متزامنة لمهام الصور<br/>- تشغيل خوارزميات OpenCV<br/>- كتابة المخرجات في MinIO و Postgres"]
    end

    subgraph CV_Engine["👁️ محرك الرؤية الحاسوبية (Computer Vision Engine - cv/flame_cv.py)"]
        CV_VAL["فحص صحة الصورة وأبعادها<br/>(Image Intake & Dimensions)"]
        CV_PRE["معالجة مسبقة وتعديل التوجيه<br/>(Letterbox & EXIF Transpose)"]
        CV_SEG["تجزئة اللهب واستخلاص الحدود<br/>(Otsu Threshold & Contours)"]
        CV_FEAT["استخراج الخصائص الهندسية والفيزيائية<br/>(Height, Width, Area, Centroid, Calibration)"]
        
        CV_VAL --> CV_PRE --> CV_SEG --> CV_FEAT
    end

    subgraph AI_RAG_Engine["🧠 محرك الذكاء الاصطناعي التوليدي والبحث الدلالي (RAG & Grounding)"]
        QUERY_REWRITE["تحليل وإعادة صياغة الاستعلام<br/>(Query Analysis & Rewriting)"]
        HYBRID_RET["بحث هجين (Hybrid Retrieval)<br/>Semantic (Vectors) + Lexical (BM25)"]
        RERANKER["إعادة الترتيب الدقيق<br/>(Cross-Encoder Reranking)"]
        CTX_BUILDER["بناء وتصفية السياق<br/>(Context Builder & Token Budget)"]
        LLM_GEN["توليد الإجابات الموثقة<br/>(Grounded LLM Generation)"]
        CITE_VAL["التحقق الصارم من الاقتباسات والمصادر<br/>(Citation & Provenance Validation)"]

        QUERY_REWRITE --> HYBRID_RET --> RERANKER --> CTX_BUILDER --> LLM_GEN --> CITE_VAL
    end

    subgraph External_AI["🌐 تكامل الاستدلال المتقدم (AURA AI Integration)"]
        AURA_API["AURA Scientific Reasoning Service<br/>- تصنيف الادعاءات: Inferred / Hypothesized<br/>- استدلال أوتوماتيكي ومقارنة النتائج"]
    end

    subgraph Frontend_App["🖥️ لوحة التحكم التفاعلية (Web Dashboard - Next.js 15)"]
        UI_DASH["لوحة المؤشرات والعدّادات (Dashboard Overview)"]
        UI_SEARCH["محرك البحث الدلالي الموحد (Unified Scientific Search)"]
        UI_STUDIO["استوديو تحليل صور اللهب (Flame Analysis Studio)"]
        UI_EVIDENCE["مستكشف الأدلة وسلسلة المصداقية (Evidence & Lineage Viewer)"]
        UI_EXP["مستعرض التجارب والظروف (Experiments Explorer)"]
        UI_STATUS["مراقبة حالة النظام والخدمات (System Health & Services)"]
    end

    FASTAPI -->|Read/Write Records| POSTGRES
    FASTAPI -->|Fetch & Put Media| MINIO
    FASTAPI -->|Enqueue Jobs & Cache| REDIS

    REDIS -->|Dequeue Job| WORKER
    WORKER --> CV_Engine
    CV_Engine -->|Save Artifacts| MINIO
    CV_Engine -->|Update Status & Metrics| POSTGRES
    WORKER -.->|Optional Interpretation| AURA_API

    FASTAPI --> AI_RAG_Engine
    AI_RAG_Engine -->|Vector Search| POSTGRES

    Frontend_App <-->|REST API JSON + Multipart| FASTAPI
```

---

## 3. تجارب ناسا المعتمدة وخط أنابيب المصداقية (NASA Datasets & Provenance)

النظام مبني على أربع تجارب احتراق رئيسية من منصة ناسا للمعلوماتية الفيزيائية (**NASA Physical Sciences Informatics - PSI**) بالإضافة لتجربة مرجعية:

| المعرّف (Source ID) | اسم التجربة | المنصة الفضائية / البيئة | نوع الاحتراق والمواد | التفاصيل والملفات المتاحة |
|---|---|---|---|---|
| **FF-PSI-25** | **BASS-II** (Burning and Suppression of Solids) | محطة الفضاء الدولية (ISS MSG) | احتراق وانتشار اللهب في المواد الصلبة (Solid fuel) وإطفاؤها | 25 ملفاً، 17 فيديو احتراق، قياسات سرعة تدفق الهواء وسرعة تراجع الوقود |
| **FF-PSI-69** | **FLEX** (Flame Extinguishment Experiment) | محطة الفضاء الدولية (ISS CIR) | احتراق وإطفاء قطرات الوقود السائل (Liquid droplets) | 19 ملفاً، 274 اختبار قطرات نفاثة، درجات حرارة، أقطار القطرات وزمن الاحتراق |
| **FF-PSI-98** | **SAFFIRE-I** (Spacecraft Fire Safety) | مركبة الشحن الفضائية غير المأهولة (Cygnus) | احتراق الأقمشة على نطاق واسع في بيئة المركبة الفضائية | 9 ملفات، 1,556 إطار تصويري لتدفق الغازات واحتراق نسيج القطن والألياف |
| **FF-PSI-107** | **SPICE** (Smoke Point In Co-flow) | محطة الفضاء الدولية (ISS MSG) | دراسة نقاط تصاعد الدخان في التدفق المشترك للهب الغازي الصفائحي | 73 ملفاً بعد فك الضغط، قياسات تدفق الغاز وتركيزات السخام |
| **FF-PSI-DSI** | **DECLIC-DSI** (Directional Solidification) | محطة الفضاء الدولية (ISS) | مرجع مقارن للفيزياء الحركية غير الاحتراقية | مجموعة بيانات مرجعية لفحص اتساق بنية البيانات |

### 3.1 خط أنابيب استيراد البيانات وتتبع المصداقية (Provenance Pipeline)

```mermaid
sequenceDiagram
    autonumber
    participant NASA as 🌐 NASA PSI / NTRS
    participant Ingestion as 📥 Ingestion Script (psi_download.py)
    participant Provenance as 🛡️ Provenance Tracker (record_provenance.py)
    participant Registry as 📋 source_registry.csv & files.jsonl
    participant DB as 🐘 PostgreSQL (flame_api.seed & ingest)
    participant S3 as 🪣 MinIO Storage

    NASA->>Ingestion: تنزيل الملفات الأصلية (CSVs, Docs, Raw Images)
    Ingestion->>Provenance: تمرير الملفات مع معرف المصدر (e.g. FF-PSI-25)
    Provenance->>Provenance: حساب بصمة التشفير sha256 لكل ملف
    Provenance->>Registry: تسجيل بيانات الملف (Path, Size, sha256, URL, Retrived_At)
    Registry-->>DB: إنشاء سجلات SourceRecord و FileRecord
    Registry-->>DB: تفكيك الجداول التجريبية إلى ExperimentRecord و Condition
    Registry-->>DB: استخراج نصوص الوثائق إلى DocumentRecord و DocumentChunk
    Ingestion->>S3: تخزين عينات الصور والوسائط المرجعية
```

---

## 4. مسار معالجة الرؤية الحاسوبية (Computer Vision Pipeline)

يعد ملف [`cv/flame_cv.py`](file:///media/belal/Data/Belal-work/Belal-NASA-project/Nasa/apps/web_nasa/Nasa/cv/flame_cv.py) النواة الرياضية والبصرية لتحليل صور اللهب. يتم تنفيذ التحليل بشكل غير متزامن بالكامل (Asynchronous) لضمان سرعة استجابة واجهة المستخدم.

### 4.1 تفاصيل تدفق التحليل (Analysis Flowchart)

```mermaid
flowchart TD
    A["مستخدم يرفع صورة اللهب<br/>(POST /api/analyses)<br/>مع معاملات المعايرة: scale_px_per_mm"] --> B{"التحقق من صحة الطلب<br/>(Format, Size, Exif)"}
    
    B -->|صورة غير صالحة| ERR["إرجاع خطأ فوري 422 أو 415 أو 413<br/>مع تفاصيل سبب الرفض"]
    B -->|صورة صالحة| C["حفظ الصورة الأصلية في MinIO<br/>(analyses/{id}/original.png)"]
    
    C --> D["إنشاء سجل التحليل في Postgres بحالة 'queued'<br/>وتوليد ULID فريد للمعاملة"]
    D --> E["إرجاع استجابة سريعة للمتصفح 202 Accepted<br/>تحتوي معرف التحليل ومكان الاستعلام"]
    
    D --> F["إرسال معرف التحليل لطابور مهام Redis<br/>(Redis Queue: flame-analysis)"]
    
    subgraph Worker_Execution["معالجة غير متزامنة في الخلفية (Worker Process)"]
        F --> G["التقاط المهمة وتحديث الحالة إلى 'processing'"]
        G --> H["تحميل بايتات الصورة الأصلية من MinIO"]
        H --> I["تعديل الاتجاه الهندسي (EXIF Transpose)<br/>وضبط الحجم الموحد (Letterboxing)"]
        
        I --> J["تطبيق خوارزمية التجزئة الثنائية (Otsu Thresholding)<br/>واستخراج كونتور اللهب (Contour Detection)"]
        
        J --> K["حساب الخصائص الهندسية والفيزيائية:<br/>- الارتفاع والعرض بالبكسل والملمتر<br/>- مساحة اللهب ونقطة المركز (Centroid)<br/>- النسبة الباعية (Aspect Ratio) والدائرية<br/>- مؤشر الثقة وفحص جودة الإضاءة"]
        
        K --> L["توليد وحفظ المرفقات في MinIO:<br/>1. Preprocessed Frame<br/>2. Binary Segmentation Mask<br/>3. Visual Overlay (Bounding Box & Contours)"]
        
        L --> M{"هل طُلِب استدلال AURA؟<br/>(request_interpretation)"}
        M -->|نعم| N["إرسال القياسات لـ AURA AI Service<br/>واستلام استنتاجات مدعومة بأدلة"]
        M -->|لا| O["تخطي الاستدلال الخارجي"]
        
        N --> P["تسجيل القياسات كأدلة (EvidenceRecord)<br/>وتحديث سجل التحليل إلى 'completed'"]
        O --> P
    end
    
    P --> Q["المتصفح يطلب دورياً GET /api/analyses/{id}<br/>ويستعرض النتائج والمرفقات فور اكتمالها"]
```

### 4.2 المتغيرات الفيزيائية المستخرجة من صورة اللهب:
1. **ارتفاع اللهب (Flame Height):** المسافة الرأسية من قاعدة اللهب حتى أقصى نقطة عمودية (بالبكسل وبالملمتر عند توفر المعايرة).
2. **عرض اللهب (Flame Width):** أقصى اتساع أفقي لمنطقة الاحتراق.
3. **مساحة السطح المسقطة (Projected Area):** عدد البكسلات المضيئة الممثلة لجسم اللهب، مع تحويلها إلى $mm^2$.
4. **مركز الكتلة الضوئية (Centroid $C_x, C_y$):** نقطة المركز الهندسي المحسوبة عبر العزوم الرياضية للمساحة (Image Moments).
5. **معامل الاستدارة (Circularity / Sphericity):** قياس مدى اقتراب اللهب من الشكل الكروي التام (وهي السمة الفيزيائية الأبرز في الجاذبية الصغرى 0G نتيجة غياب تيارات الحمل).
6. **مؤشرات الجودة والثقة (Quality & Confidence Flags):** فحص التشبع اللوني (Clipping)، انخفاض التباين (Low Contrast)، وعدم دقة المقياس لتجنب الحسابات الخاطئة.

---

## 5. معمارية الذكاء الاصطناعي والاسترجاع المعزز بالأدلة (RAG & Scientific Grounding)

تضمن هذه الطبقة أن أي إجابة استفسارية أو معلومة يقدمها النظام مستندة إلى أوراق ناسا البحثية أو جداول القياسات التجريبية دون أي اجتهاد غير موثق.

```mermaid
flowchart LR
    subgraph Input_Stage["1. مرحلة الاستعلام"]
        UQ["سؤال الباحث العلمي<br/>(User Question)"] --> QA["تحليل وتوسيع المصطلحات العلمية<br/>(Scientific Query Expansion)"]
    end

    subgraph Retrieval_Stage["2. مرحلة الاسترجاع الهجين"]
        QA -->|Embedding Model| VEC_SEARCH["بحث متجهي دلالي (Semantic)<br/>PostgreSQL pgvector (Cosine Similarity)"]
        QA -->|Exact & Stemmed Terms| LEX_SEARCH["بحث نصي معجمي (Lexical/BM25)<br/>PostgreSQL Full-Text Search"]
        FILTERS["مرشحات البيانات الوصفية (Metadata Filters):<br/>- معرّف التجربة (Experiment ID)<br/>- نوع الوقود (Fuel / Material)<br/>- نظام الجاذبية (Microgravity 0G / 1G)"] -.-> VEC_SEARCH
        FILTERS -.-> LEX_SEARCH
    end

    subgraph Ranking_Stage["3. الترتيب وبناء السياق"]
        VEC_SEARCH --> HYBRID_FUSION["دمج النتائج (Hybrid Fusion)<br/>RRF: Reciprocal Rank Fusion"]
        LEX_SEARCH --> HYBRID_FUSION
        HYBRID_FUSION --> RERANK["إعادة الترتيب المتقدم<br/>Cross-Encoder Reranker"]
        RERANK --> CTX["بناء السياق (Context Builder):<br/>- إزالة التكرار<br/>- التقيد بحدود الـ Tokens<br/>- الحفاظ على التضارب إن وُجد"]
    end

    subgraph Generation_Stage["4. التوليد والتحقق"]
        CTX --> LLM["نموذج اللغة الكبير (Grounded LLM)"]
        PROMPT["System Prompt:<br/>'اعتمد حصراً على الأدلة المرفقة،<br/>واذكر معرف الاقتباس لكل حقيقة،<br/>واعلن عجز الأدلة صراحة إذا لم تتوفر'"] --> LLM
        LLM --> CITE_CHECK{"فحص صحة الاقتباسات<br/>(Citation Verification)"}
        CITE_CHECK -->|جميع الاقتباسات موثقة| FINAL_ANS["إجابة علمية نهائية موثوقة<br/>مع روابط المصادر والملفات الأصلية"]
        CITE_CHECK -->|ادعاء غير موثق| FALLBACK["تصنيف الحقيقة كـ Unsupported<br/>أو التنبيه بعدم كفاية الدليل"]
    end
```

### 5.1 سلسلة التحقق من المصداقية (Lineage & Provenance Chain)
تسير دورة حياة الحقيقة العلمية وفق التسلسل الصارم التالي:
$$\text{Answer Claim} \longrightarrow \text{Citation} \longrightarrow \text{Document Chunk} \longrightarrow \text{Document} \longrightarrow \text{File Record (sha256)} \longrightarrow \text{NASA Source}$$

---

## 6. مخطط الكيانات والعلاقات لقاعدة البيانات (Database ERD Diagram)

تم تصميم قاعدة البيانات في PostgreSQL لتربط بين الوثائق النصية، الملفات الرقمية، القياسات التجريبية، ونتائج تحليل الرؤية الحاسوبية بدقة متناهية:

```mermaid
erDiagram
    SOURCE ||--o{ FILE_RECORD : "يمتلك ملفات أصلية"
    SOURCE ||--o{ DOCUMENT : "يحتوي وثائق بحثية"
    SOURCE ||--o{ EXPERIMENT : "يحتوي تجارب طيران"
    SOURCE ||--o{ EVIDENCE : "يُنسب إليه الدليل"

    FILE_RECORD ||--o{ DOCUMENT : "يُشتق منه وثيقة"
    FILE_RECORD ||--o{ EXPERIMENT : "جدول القياسات المرجعي"
    FILE_RECORD ||--o{ EVIDENCE : "ملف الدليل المادي"
    FILE_RECORD ||--o{ FILE_RECORD : "ملف مشتق من أصل"

    DOCUMENT ||--|{ DOCUMENT_CHUNK : "يُجزأ إلى مقاطع نصية"
    DOCUMENT ||--o{ EVIDENCE : "مرجع للدليل"

    EXPERIMENT ||--|{ EXPERIMENT_CONDITION : "يحتوي ظروف فيزيائية"
    EXPERIMENT ||--o{ ANALYSIS_RECORD : "تُجرى عليه تحليلات صور"
    EXPERIMENT ||--o{ EVIDENCE : "مرجع للتجربة"

    ANALYSIS_RECORD ||--o{ EVIDENCE : "ينتج قياسات تُسجل كأدلة"

    SOURCE {
        string source_id PK "معرف المصدر e.g. FF-PSI-25"
        text title "عنوان الدراسة أو التجربة"
        text short_name "الاسم المختصر e.g. BASS-II"
        text repository "المستودع e.g. NASA PSI"
        text license "الترخيص e.g. CC0-1.0"
        string domain "المجال e.g. combustion"
    }

    FILE_RECORD {
        string file_id PK "معرف الملف الفريد"
        string source_id FK "المصدر التابع له"
        string sha256 "البصمة التشفيرية للملف"
        text original_filename "اسم الملف الأصلي"
        text media_type "النوع e.g. image/png, text/csv"
        bigint size_bytes "حجم الملف بالبايت"
        datetime retrieved_at "تاريخ التنزيل"
        boolean is_original "هل هو الملف الخام الأصلي"
    }

    DOCUMENT {
        string document_id PK "معرف الوثيقة (ULID)"
        string source_id FK "معرف المصدر"
        string file_id FK "معرف الملف الأصلي"
        text title "عنوان الورقة أو التقرير"
        string document_type "نوع المستند (paper, report)"
        integer page_count "عدد الصفحات"
        string text_layer "حالة الطبقة النصية"
        datetime ingested_at "تاريخ الفهرسة"
    }

    DOCUMENT_CHUNK {
        string chunk_id PK "معرف المقطع"
        string document_id FK "معرف الوثيقة"
        string evidence_id "معرف الدليل المرتبط"
        integer page "رقم الصفحة"
        text section "القسم أو العنوان الفرعي"
        text text "النص المستخرج"
    }

    EXPERIMENT {
        string experiment_id PK "معرف التجربة (ULID)"
        string source_id FK "معرف المصدر"
        text test_id "رقم الاختبار في سجلات ناسا"
        text investigation "اسم المشروع الاستقصائي"
        string gravity_regime "نظام الجاذبية e.g. microgravity"
        text fuel_or_material "المادة أو الوقود المستخدم"
        string table_file_id FK "ملف الجدول التجريبي"
    }

    EXPERIMENT_CONDITION {
        string condition_id PK "معرف المتغير الفيزيائي"
        string experiment_id FK "معرف التجربة التابع لها"
        text variable "اسم المتغير (Oxygen, Pressure, Velocity)"
        float value_numeric "القيمة الرقمية"
        text unit_original "الوحدة في سجل ناسا"
        float value_si "القيمة المعيارية الدولية"
        text unit_si "الوحدة الدولية المعيارية"
        string evidence_id "معرف الدليل المرتبط"
    }

    EVIDENCE {
        string evidence_id PK "معرف الدليل (ULID)"
        string source_id FK "معرف المصدر"
        string file_id FK "معرف الملف"
        string document_id FK "معرف الوثيقة إن وُجد"
        string experiment_id FK "معرف التجربة إن وُجد"
        string analysis_id "معرف التحليل البصري إن وُجد"
        string kind "نوع الدليل (chunk, condition, measurement)"
        string origin "أصل الدليل"
        text excerpt "المقتبس أو البيان العلمي"
        jsonb locator "موقع الدليل في الملف (Page/Row)"
    }

    ANALYSIS_RECORD {
        string analysis_id PK "معرف التحليل (ULID)"
        string status "الحالة: queued, processing, completed, failed"
        string experiment_id FK "التجربة المرتبطة"
        string image_sha256 "بصمة الصورة المرفوعة"
        string pipeline_version "إصدار خوارزمية التحليل"
        jsonb payload "القياسات الفيزيائية المستخرجة"
        jsonb artifacts "روابط المرفقات (Mask, Overlay, Original)"
        datetime created_at "تاريخ الإنشاء"
    }
```

---

## 7. مواصفات واجهة برمجة التطبيقات (API Endpoints Catalogue)

تتوافق الواجهة البرمجية في `apps/api` تماماً مع العقد المعياري الموثق في [`docs/api/openapi.json`](file:///media/belal/Data/Belal-work/Belal-NASA-project/Nasa/apps/web_nasa/Nasa/docs/api/openapi.json):

```mermaid
classDiagram
    class SystemAPI {
        +GET /api/health : فحص جاهزية وتكامل الخدمات (DB, MinIO, Redis, AURA)
        +GET /api/dashboard/counts : إحصائيات الوثائق والتجارب والتحليلات
    }

    class ResearchAPI {
        +GET /api/search : بحث موحد متعدد المعايير في الوثائق والتجارب
        +GET /api/documents/{id} : تفاصيل وثيقة معينة وسجل مصداقيتها
        +GET /api/experiments/{id} : استعراض تجربة وظروفها الفيزيائية
    }

    class EvidenceAPI {
        +GET /api/evidence/{id} : استرجاع سجل الدليل وسلسلة المصداقية الكاملة
    }

    class AnalysisAPI {
        +POST /api/analyses : رفع صورة لهب لبدء التحليل البصري (202 Accepted)
        +GET /api/analyses : استعراض سجل كافة التحليلات السابقة والترشيح
        +GET /api/analyses/{id} : استعلام تفصيلي عن حالة التحليل ونتائجه
        +GET /api/analyses/{id}/artifacts/{kind} : تحميل مرفق بصري (original, mask, overlay)
    }
```

### 7.1 جدول ملخص الـ Endpoints:

| المسار (Endpoint) | الطريقة (Method) | الدور الوظيفي | كود الاستجابة الناجحة |
|---|---|---|---|
| `/api/health` | `GET` | فحص صحة المكونات التابعة (PostgreSQL, pgvector, MinIO, Redis, AURA) | `200 OK` أو `503` |
| `/api/dashboard/counts` | `GET` | تزويد بطاقات لوحة التحكم بعدد الوثائق والتجارب والتحليلات الجارية | `200 OK` |
| `/api/search` | `GET` | بحث علمي دلالي ومعجمي مع فلاتر (نوع المستند، التجربة، المجال) | `200 OK` |
| `/api/documents/{id}` | `GET` | جلب تفاصيل وثيقة علمية مع المقاطع وسجل التنزيل الموثق | `200 OK` / `404` |
| `/api/experiments/{id}`| `GET` | جلب تفاصيل تجربة ناسا وظروف الضغط والأكسجين وسرعة التدفق | `200 OK` / `404` |
| `/api/evidence/{id}` | `GET` | محطة قراءة الدليل العلمي ورسم خط الرجوع للمصدر | `200 OK` / `404` |
| `/api/analyses` | `POST` | استلام صورة اللهب عبر `multipart/form-data` وحجز مهمة في الطابور | `202 Accepted` |
| `/api/analyses` | `GET` | استعراض سجل التحليلات مع التصفية والتقليب (Pagination) | `200 OK` |
| `/api/analyses/{id}` | `GET` | جلب القياسات المستخرجة ومعدل الثقة والروابط (Polling Endpoint) | `200 OK` |
| `/api/analyses/{id}/artifacts/{kind}` | `GET` | استعراض البايتات المباشرة للمرفقات (`original`, `preprocessed`, `mask`, `overlay`) | `200 OK` (PNG/JPEG) |

---

## 8. بنية واجهة المستخدم التفاعلية (Frontend Application Architecture)

تم بناء الواجهة الأمامية باستخدام **Next.js 15 (App Router)**، مع دعم كامل للغة TypeScript وتصميم مظلم فاخر (Aesthetic Modern Dark Theme) مستوحى من واجهات مراكز أبحاث الفضاء.

```mermaid
graph TD
    subgraph App_Layout["إطار العمل العام (app/layout.tsx)"]
        NAV["شريط التنقل الجانبي والعلوي (Sidebar & Header)"]
        STATUS_BADGE["مؤشر حالة الاتصال بالخادم الحي (Live Health Pulse)"]
    end

    subgraph Pages["صفحات المنصة (Pages & Views)"]
        PAGE_HOME["/ (Dashboard Overview)<br/>- بطاقات الإحصائيات السريعة<br/>- ملخص حالة مهام التحليل الجارية<br/>- نظرة عامة على تجارب ناسا"]
        
        PAGE_SEARCH["/search (Unified Explorer)<br/>- شريط بحث ذكي هجين<br/>- مرشحات تفاعلية للجاذبية والمواد<br/>- بطاقات نتائج مع مقتطفات الأدلة"]
        
        PAGE_ANALYSIS["/analysis (Flame CV Studio)<br/>- منطقة سحب وإفلات لصور اللهب<br/>- إعدادات المعايرة الفيزيائية (px/mm)<br/>- عارض تفاعلي متقدم يقارن الصورة بالقناع<br/>- جدول بالقياسات الهندسية ومؤشرات الثقة"]
        
        PAGE_HISTORY["/history (Analysis Archive)<br/>- أرشيف لكافة التحليلات السابقة<br/>- إمكانية الفلترة بالوقت ونوع التجربة"]
        
        PAGE_EXP["/experiments (NASA Experiments)<br/>- استعراض تجارب BASS-II, FLEX, SAFFIRE, SPICE<br/>- جداول الظروف المعيارية والنتائج"]
        
        PAGE_EVIDENCE["/evidence (Evidence Lineage)<br/>- عارض سلسلة المصداقية التفاعلية<br/>- إظهار شجرة الارتباط حتى الـ sha256 الأصلي"]
        
        PAGE_STATUS["/status (System Diagnostics)<br/>- شاشة مراقبة حية لزمن استجابة الخدمات<br/>- حالة Postgres, MinIO, Redis, AURA"]
    end

    NAV --> PAGE_HOME
    NAV --> PAGE_SEARCH
    NAV --> PAGE_ANALYSIS
    NAV --> PAGE_HISTORY
    NAV --> PAGE_EXP
    NAV --> PAGE_EVIDENCE
    NAV --> PAGE_STATUS
```

---

## 9. خريطة النشر والبنية التحتية (Infrastructure & Deployment Topology)

تعمل المنظومة محلياً وفي بيئة الإنتاج باستخدام **Docker Compose** عبر حاويات متناسقة تضمن الأمان وعزل العمليات:

```mermaid
flowchart TB
    subgraph Docker_Compose["بيئة التشغيل الموحدة (Docker Compose Environment)"]
        subgraph Databases["حاويات قواعد البيانات والتخزين"]
            PG_CONT["postgres (pgvector/pgvector:pg16)<br/>Port: 5432<br/>حفظ البيانات المهيكلة والمتجهات"]
            REDIS_CONT["redis (redis:7-alpine)<br/>Port: 6379<br/>إدارة طوابير المهام والكاش"]
            MINIO_CONT["minio (minio:RELEASE.2025)<br/>Ports: 9000 (S3 API), 9001 (Console)<br/>تخزين الصور والأقنعة"]
            MINIO_INIT["minio-init (minio/mc)<br/>تهيئة Bucket: flame-artifacts"]
            MINIO_CONT --> MINIO_INIT
        end

        subgraph Application_Containers["حاويات التطبيق والخدمات"]
            API_CONT["api (FastAPI Container)<br/>Port: 8000<br/>- تنفيذ ترحيلات Alembic<br/>- فحص المصادقة بالتوكنات<br/>- تقديم واجهات REST"]
            WORKER_CONT["worker (Python RQ Worker Container)<br/>- معالجة صور اللهب باستخدام OpenCV<br/>- استخراج القياسات الفيزيائية"]
            WEB_CONT["web (Next.js Dashboard)<br/>Port: 3000<br/>واجهة المستخدم التفاعلية"]
        end

        PG_CONT -->|Healthcheck Healthy| API_CONT
        REDIS_CONT -->|Healthcheck Healthy| API_CONT
        MINIO_INIT -->|Bucket Created| API_CONT
        
        API_CONT -->|Depends on API Ready| WORKER_CONT
        REDIS_CONT -->|Job Queue Channel| WORKER_CONT
        MINIO_CONT <-->|Artifacts Read/Write| WORKER_CONT
        PG_CONT <-->|Records Read/Write| WORKER_CONT
        
        API_CONT <-->|Rewrite /api/* requests| WEB_CONT
    end

    CLIENT["🌐 المتصفح / الباحث العلمي"] <-->|Port 3000 / Port 8000| Docker_Compose
```

---

## 10. ملخص شامل للتقنيات المستخدمة (Technology Stack Summary)

| الطبقة (Layer) | التقنيات المستخدمة (Technologies) | الوظيفة في المشروع |
|---|---|---|
| **الواجهة الأمامية (Frontend)** | Next.js 15, React 19, TypeScript, Tailwind CSS, Lucide Icons | لوحة تحكم علمية تفاعلية سريعة ومظلمة |
| **الواجهة الخلفية (Backend API)** | FastAPI, Python 3.12, Uvicorn, Pydantic, Alembic | خادم عالي الأداء يوفر واجهات OpenAPI 3.1 تعاقدية |
| **قواعد البيانات (Databases)** | PostgreSQL 16, pgvector Extension, SQLAlchemy ORM | تخزين مهيكل للبيانات التجريبية والبحث الدلالي بالمتجهات |
| **التخزين السحابي للوسائط (Object Storage)** | MinIO (AWS S3-compatible SDK: Boto3) | تخزين الصور الأصلية والأقنعة المتراكبة والصور المعالجة |
| **طوابير المهام والكاش (Queues & Cache)** | Redis 7, Python-RQ (Redis Queue) | معالجة خلفية غير متزامنة لصور اللهب وعزل أعباء العمل |
| **الرؤية الحاسوبية (Computer Vision)** | OpenCV (cv2), Pillow (PIL), NumPy | تجزئة اللهب، استخراج الخصائص الهندسية، قياس التردد والدائرية |
| **الذكاء الاصطناعي (AI / RAG / Grounding)** | RAG Pipeline, Hybrid RRF, Cross-Encoder, Grounded LLM | إجابات علمية مقيدة بالأدلة مع ربطها بالمصادر الأصلية |
| **التكامل الخارجي (External AI Integration)** | AURA AI Platform | استدلال متقدم وتصنيف موثوقية الاستنتاجات العلمية |
| **الحاويات والنشر (DevOps & Infrastructure)** | Docker, Docker Compose, Railway | بيئة تشغيل موحدة قابلة للنشر الفوري والمحاكاة المحلية |

---

> 📌 **خلاصة:** هذا الملف يمثل المرجع الشامل لكافة أجزاء المنظومة (من المصدر الفضائي في ناسا حتى بكسل الواجهة في لوحة التحكم)، وهو وثيقة حية تعكس المعمارية المنفذة فعلياً في المستودع.
