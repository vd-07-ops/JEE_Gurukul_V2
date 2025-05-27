# 🧠 JEE Gurukul

**JEE Gurukul** is an AI-powered, multi-agent system designed to revolutionize JEE preparation. It features intelligent agents that ingest, understand, simplify, and generate questions based on past JEE papers, while profiling students and adapting content to their learning needs.

---

## 🚀 Project Vision

We aim to build an **adaptive learning platform** where each student gets a personalized journey, driven by LLMs and agent collaboration. This prototype is being developed during a hackathon and will evolve into a full-scale edtech startup.

---

## 🧩 Agents Overview

| Agent | Name | Role |
|-------|------|------|
| 1 | Knowledge Extractor | Ingests past papers (PDF/CSV), classifies by subject & topic |
| 2 | Topic Mapper | Maps question topics to trusted sources (NCERT, Wikipedia) |
| 3 | Simplification Extractor | Finds alternate, simpler solving methods |
| 4 | Question Generator | Generates Easy/Medium/Hard questions |
| 5 | Student Profiler | Profiles user skill levels |
| 6 | Adaptive Curator | Adjusts difficulty dynamically |
| 7 | Feedback Evaluator | Analyzes user feedback and learning gain |
| 8 | Reward Engine | Gamifies the experience with points & badges |

---

## 🏗️ Tech Stack

- **Python 3.10+**
- **LangChain** / **LLM APIs** (OpenAI, Claude, Gemini, Mistral)
- **PyMuPDF / pdfminer / pytesseract** for PDF & image question parsing
- **Haystack / Weaviate / FAISS** for semantic search
- **FastAPI** for APIs
- **PostgreSQL** or **SQLite** for user & progress data
- **GitHub Actions** (CI/CD)

---

## 🛠️ Setup Instructions

```bash
git clone https://github.com/<your-username>/JEE_Gurukul.git
cd JEE_Gurukul
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
