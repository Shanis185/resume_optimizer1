import sys
import fitz  # PyMuPDF
import json
import re
from transformers import pipeline
from sklearn.feature_extraction.text import TfidfVectorizer

# Initialize AI models with safe settings
nlp_feedback = pipeline(
    "text-generation", 
    model="facebook/blenderbot-400M-distill",
    device="cpu"
)

nlp_comparison = pipeline(
    "text2text-generation", 
    model="google/flan-t5-small",
    device="cpu"
)

KEYWORD_DICT = {
    "Skills": [
        "python", "java", "javascript", "typescript", "c++", "c#", "go", "rust",
        "kotlin", "swift", "php", "ruby", "scala", "r",
        "html", "css", "react", "angular", "vue", "node.js", "django", "flask",
        "spring", "laravel", "express", "graphql", "rest api",
        "machine learning", "deep learning", "tensorflow", "pytorch", "keras",
        "numpy", "pandas", "scikit-learn", "opencv", "nltk", "spark", "hadoop",
        "sql", "mysql", "postgresql", "mongodb", "redis", "oracle", "sqlite",
        "aws", "azure", "google cloud", "docker", "kubernetes", "terraform",
        "ansible", "jenkins", "ci/cd", "github actions",
        "communication", "teamwork", "leadership", "problem solving",
        "critical thinking", "time management"
    ],
    "Experience": [
        "developed", "designed", "implemented", "engineered", "built", "created",
        "managed", "led", "supervised", "mentored", "coordinated", "directed",
        "optimized", "improved", "enhanced", "refactored", "debugged", "fixed",
        "collaborated", "partnered", "liaised", "presented", "demonstrated",
        "increased", "decreased", "reduced", "saved", "achieved", "delivered",
        "researched", "analyzed", "evaluated", "tested", "documented"
    ],
    "Education": [
        "bachelor", "master", "phd", "degree", "diploma", "certificate",
        "university", "college", "institute", "school",
        "computer science", "engineering", "information technology",
        "mathematics", "physics", "statistics",
        "gpa", "honors", "dean's list", "scholarship"
    ],
    "Tools": [
        "vscode", "intellij", "pycharm", "eclipse", "xcode", "android studio",
        "git", "github", "gitlab", "bitbucket", "svn",
        "jira", "trello", "asana", "clickup", "confluence",
        "selenium", "jest", "mocha", "junit", "postman", "swagger",
        "linux", "windows", "macos", "unix",
        "docker", "kubernetes", "jenkins", "ansible", "terraform"
    ],
    "Projects": [
        "project", "portfolio", "application", "website", "mobile app",
        "web app", "api", "microservices", "database", "algorithm",
        "machine learning model", "data analysis", "data visualization",
        "automation", "script", "plugin", "extension", "library"
    ],
    "Certifications": [
        "certified", "certification", "aws certified", "microsoft certified",
        "google certified", "oracle certified", "cisco certified",
        "comptia", "pmp", "scrum master", "agile", "six sigma",
        "coursera", "udemy", "edx", "linkedin learning"
    ]
}

def extract_text(file_path):
    try:
        with fitz.open(file_path) as doc:
            return " ".join(page.get_text() for page in doc)
    except Exception as e:
        print(f"Error extracting text: {str(e)}", file=sys.stderr)
        return ""

def analyze_resume(file_path, jd_text=None):
    text = extract_text(file_path).lower()
    if not text:
        return {"error": "Failed to extract text from PDF"}
    
    sections = {
        section: [kw for kw in keywords if re.search(r'\b' + re.escape(kw) + r'\b', text)]
        for section, keywords in KEYWORD_DICT.items()
    }

    total_possible = sum(len(keywords) for keywords in KEYWORD_DICT.values())
    found = sum(len(keywords) for keywords in sections.values())
    ats_score = min(100, int((found / max(1, total_possible)) * 80 + 20))

    # AI Feedback generation (safe)
    feedback_prompt = f"Analyze this resume and suggest 3 improvements:\n{text[:2000]}"
    try:
        ai_raw = nlp_feedback(
            feedback_prompt,
            max_new_tokens=150,
            truncation=True,
            do_sample=True,
            temperature=0.7
        )
        ai_feedback = ai_raw[0].get("generated_text", "").split("Suggestions:")[-1].strip()
        if not ai_feedback:
            ai_feedback = ai_raw[0].get("generated_text", "").strip()
    except Exception as e:
        print(f"Error generating feedback: {str(e)}", file=sys.stderr)
        ai_feedback = "⚠️ Could not generate AI feedback due to input size or model limitations."

    result = {
        "sections": sections,
        "ats_score": ats_score,
        "ai_feedback": ai_feedback
    }

    if jd_text:
        jd_text = jd_text.lower()
        jd_keywords = {
            section: [kw for kw in keywords if re.search(r'\b' + re.escape(kw) + r'\b', jd_text)]
            for section, keywords in KEYWORD_DICT.items()
        }

        matched = sum(
            1 for section in KEYWORD_DICT
            for kw in jd_keywords[section]
            if kw in text
        )
        total_jd_keywords = sum(len(kws) for kws in jd_keywords.values())
        match_score = (matched / max(1, total_jd_keywords)) * 100

        if match_score >= 75:
            summary_sentence = "✅ This resume is a strong fit for the job description."
        elif match_score >= 40:
            summary_sentence = "🟡 This resume moderately matches the job description."
        else:
            summary_sentence = "🔴 This resume does not effectively match the job description."

        try:
            comparison_prompt = f"Compare resume with job description:\nJD: {jd_text[:1000]}\nResume: {text[:1000]}\nKey matches and gaps:"
            comparison_output = nlp_comparison(
                comparison_prompt,
                max_length=400,
                truncation=True
            )
            comparison_summary = comparison_output[0].get("generated_text", "").strip()
        except Exception as e:
            print(f"Error generating comparison: {str(e)}", file=sys.stderr)
            comparison_summary = "⚠️ Could not generate AI comparison summary."

        result.update({
            "match_score": round(match_score, 2),
            "summary_sentence": summary_sentence,
            "missing_keywords": {
                section: [kw for kw in jd_keywords[section] if kw not in text]
                for section in KEYWORD_DICT
            },
            "comparison_summary": comparison_summary
        })

    return result

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(json.dumps({"error": "File path required"}, indent=2))
        sys.exit(1)

    jd_text = sys.argv[2] if len(sys.argv) > 2 else None
    try:
        result = analyze_resume(sys.argv[1], jd_text)
        print(json.dumps(result, indent=2))
    except Exception as e:
        print(json.dumps({"error": f"Processing failed: {str(e)}"}, indent=2))
        sys.exit(1)
