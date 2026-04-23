from .connector import load_from_upload, load_sample
from .quality import compute_quality_score, score_label
from .dashboard import auto_dashboard, detect_column_types
from .ai_narrator import generate_narrative, answer_natural_query
from .report_generator import generate_pdf_report
from .risk_detector import (
    run_risk_analysis,
    get_tercero_summary,
    get_analysis_stats,
    RISK_DICTIONARY_RAW,
    RISK_COLORS,
    ALERT_SCORES,
)
