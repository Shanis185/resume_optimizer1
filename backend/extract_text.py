import sys
import fitz  # PyMuPDF
import json
import re
from transformers import pipeline
from sklearn.feature_extraction.text import TfidfVectorizer

# Initialize AI models with proper settings
nlp_feedback = pipeline(
    "text-generation", 
    model="facebook/blenderbot-400M-distill",
    device="cpu",  # Explicitly set to CPU
    truncation=True  # Enable truncation
)

nlp_comparison = pipeline(
    "text2text-generation", 
    model="google/flan-t5-small",  # Using smaller model to save memory
    device="cpu",
    truncation=True
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
    """Extract text from PDF"""
    try:
        with fitz.open(file_path) as doc:
            return " ".join(page.get_text() for page in doc)
    except Exception as e:
        print(f"Error extracting text: {str(e)}", file=sys.stderr)
        return ""

def analyze_resume(file_path, jd_text=None):
    """Main analysis function"""
    text = extract_text(file_path).lower()
    if not text:
        return {"error": "Failed to extract text from PDF"}
    
    # Extract keywords
    sections = {
        section: [kw for kw in keywords if re.search(r'\b' + re.escape(kw) + r'\b', text)]
        for section, keywords in KEYWORD_DICT.items()
    }
    
    # Calculate ATS score
    total_possible = sum(len(keywords) for keywords in KEYWORD_DICT.values())
    found = sum(len(keywords) for keywords in sections.values())
    ats_score = min(100, int((found / max(1, total_possible)) * 80 + 20))  # Avoid division by zero
    
    # Generate AI feedback with proper token handling
    feedback_prompt = f"Analyze this resume and suggest 3 improvements:\n{text[:2000]}"
    try:
        ai_feedback = nlp_feedback(
            feedback_prompt,
            max_new_tokens=150,
            truncation=True,
            do_sample=True,
            temperature=0.7
        )[0]['generated_text']
        ai_feedback = ai_feedback.split("Suggestions:")[-1].strip()
    except Exception as e:
        print(f"Error generating feedback: {str(e)}", file=sys.stderr)
        ai_feedback = "Could not generate feedback"
    
    result = {
        "sections": sections,
        "ats_score": ats_score,
        "ai_feedback": ai_feedback
    }
    
    # Add comparison if JD provided
    if jd_text:
        jd_text = jd_text.lower()
        jd_keywords = {
            section: [kw for kw in keywords if re.search(r'\b' + re.escape(kw) + r'\b', jd_text)]
            for section, keywords in KEYWORD_DICT.items()
        }
        
        match_score = sum(
            1 for section in KEYWORD_DICT
            for kw in jd_keywords[section]
            if kw in text
        ) / max(1, sum(len(kws) for kws in jd_keywords.values())) * 100
        
        try:
            comparison_prompt = f"Compare resume with job description:\nJD: {jd_text[:1000]}\nResume: {text[:1000]}\nKey matches and gaps:"
            comparison_summary = nlp_comparison(
                comparison_prompt,
                max_length=400,
                truncation=True
            )[0]['generated_text']
        except Exception as e:
            print(f"Error generating comparison: {str(e)}", file=sys.stderr)
            comparison_summary = "Could not generate comparison"
        
        result.update({
            "match_score": round(match_score, 2),
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