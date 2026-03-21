import traceback
import sys
try:
    from ai.parser import extract_text
    from ai.extractor import extract_jd_skills, extract_resume_skills
    from ai.embedder import anchor_to_onet
    from ai.gap_analyzer import compute_gap_vector, generate_adaptive_pathway
    from ai.models import AnalysisResult
    print('SUCCESS')
except Exception as e:
    traceback.print_exc()
