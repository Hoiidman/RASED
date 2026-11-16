"""UI labels EN / AR (owner: Agent B). Headers and navigation only; content stays EN for now."""

L = {
    "en": {
        "tagline": "Sees the change before it happens · Ajman economic early-warning",
        "portal": "Portal", "gov": "Government portal", "inv": "Investor portal", "nav": "Pages",
        "login_title": "Government portal sign-in", "password": "Password", "login": "Enter portal",
        "wrong_pw": "Wrong password", "logout": "Sign out",
        "demo_login": "Demo mode: no GOV_PASSWORD is set in .env, so the portal opens without one.",
        "sync_now": "Sync now",
        "p_overview": "Overview", "p_alerts": "Early warnings", "p_outlook": "Outlook", "p_actions": "Actions",
        "p_sectors": "Sectors & groups", "p_drivers": "Drivers", "p_impact": "Impact & measurement",
        "p_export": "Export & API",
        "p_opportunities": "Opportunities", "p_watchouts": "Watch-outs", "p_advisor": "My business advisor",
    },
    "ar": {
        "tagline": "يرصد التغيير قبل حدوثه · نظام الإنذار المبكر لاقتصاد عجمان",
        "portal": "البوابة", "gov": "البوابة الحكومية", "inv": "بوابة المستثمر", "nav": "الصفحات",
        "login_title": "تسجيل الدخول إلى البوابة الحكومية", "password": "كلمة المرور", "login": "دخول",
        "wrong_pw": "كلمة مرور خاطئة", "logout": "تسجيل الخروج",
        "demo_login": "وضع العرض: لم يتم تعيين كلمة مرور، اضغط للدخول.",
        "sync_now": "مزامنة الآن",
        "p_overview": "نظرة عامة", "p_alerts": "الإنذارات المبكرة", "p_outlook": "التوقعات", "p_actions": "الإجراءات",
        "p_sectors": "القطاعات والفئات", "p_drivers": "المحركات", "p_impact": "الأثر والقياس",
        "p_export": "التصدير والواجهة البرمجية",
        "p_opportunities": "الفرص", "p_watchouts": "تنبيهات", "p_advisor": "مستشار أعمالي",
    },
}

LANG = {"v": "en"}  # set by main.py on each run

TITLES_AR = {
    "overview": ("نظرة عامة", "ما الذي يتغير في اقتصاد عجمان؟"),
    "alerts": ("الإنذارات المبكرة", "ما الذي يبدو غير معتاد، وما الذي يمكن للدائرة فعله؟"),
    "outlook": ("التوقعات", "ما الذي قد يحدث لاحقاً؟"),
    "actions": ("الإجراءات", "ما الخيارات المتاحة للدائرة، وما قيمة كل خيار؟"),
    "sectors": ("القطاعات والفئات", "أي القطاعات والفئات تتحرك بشكل مختلف؟"),
    "drivers": ("المحركات", "ما الذي قد يسبب التغيير؟ فرضيات قيد المتابعة"),
    "impact": ("الأثر والقياس", "كيف تستفيد عجمان، وكيف نقيس ذلك"),
    "export": ("التصدير والواجهة البرمجية", "انقل البيانات إلى أنظمتك"),
    "opportunities": ("الفرص", "أين ينمو الطلب على الأعمال في عجمان؟"),
    "watchouts": ("تنبيهات", "ما الذي يجب أن ينتبه له صاحب العمل الجديد؟"),
    "advisor": ("مستشار أعمالي", "توقعات مخصصة لقطاعك ومنطقتك"),
}

TITLES = {  # (title, question) per page
    "overview": ("Overview", "What's changing in Ajman's economy?"),
    "alerts": ("Early warnings", "What looks unusual, and what DED can do about it"),
    "outlook": ("Outlook", "What may happen next?"),
    "actions": ("Actions", "What DED could do, and what each option is worth"),
    "sectors": ("Sectors & groups", "Which sectors and groups are moving differently?"),
    "drivers": ("Drivers", "What might be causing the change? (hypotheses being monitored)"),
    "impact": ("Impact & measurement", "How Ajman benefits, and how we measure it"),
    "export": ("Export & API", "Take the data into your own systems"),
    "opportunities": ("Opportunities", "Where is Ajman's business demand growing?"),
    "watchouts": ("Watch-outs", "What should a new business be careful about?"),
    "advisor": ("My business advisor", "A tailored outlook for your sector and area"),
}
