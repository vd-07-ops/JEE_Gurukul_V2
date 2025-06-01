import json
import random
import time
import os
import numpy as np
import pandas as pd
import pickle
import re
import traceback
from sentence_transformers import SentenceTransformer
import faiss
from ollama import Client
from tqdm import tqdm
import concurrent.futures
import torch

# === Config ===
EMBEDDINGS_FILE = "data/question_embeddings.npy"
FAISS_INDEX_PKL = "data/faiss_index.pkl"
OUTPUT_CSV = "final_generated_jee_questions.csv"
FAILED_CSV = "failed_generations.csv"
MODEL_NAME = "mistral:7b-instruct-v0.3-q4_0"
MAX_RETRIES = 2
TARGET_TOTAL = 10  # For testing; increase as needed
CHAIN_OF_THOUGHT_SUFFIX = "Your solution must explain each step clearly like a teacher."
BATCH_SIZE = 5
MAX_WORKERS = 5

print("Checking GPU availability via torch:")
print(f"CUDA available? {torch.cuda.is_available()}, devices: {torch.cuda.device_count()}")

# === Load data ===
print("Loading datasets...")
with open("data/original_questions.json", "r", encoding="utf-8") as f:
    dataset = json.load(f)
with open("data/dist_topic.json", "r", encoding="utf-8") as f:
    topic_distribution = json.load(f)
print(f"Loaded {len(dataset)} questions and {len(topic_distribution)} topics.")

questions = [item["question"] for item in dataset]

# === Embeddings and FAISS ===
def load_or_compute_embeddings():
    os.makedirs("data", exist_ok=True)
    if os.path.exists(EMBEDDINGS_FILE) and os.path.exists(FAISS_INDEX_PKL):
        print("Loading cached embeddings and FAISS index...")
        with open(FAISS_INDEX_PKL, "rb") as f:
            data = pickle.load(f)
            embeddings = data["embeddings"]
            index = data["index"]
        return embeddings, index
    else:
        print("Computing embeddings and building FAISS index...")
        embedder_local = SentenceTransformer("all-MiniLM-L6-v2", device='cuda' if torch.cuda.is_available() else 'cpu')
        embeddings_local = embedder_local.encode(questions, convert_to_numpy=True, show_progress_bar=True)
        dim = embeddings_local.shape[1]
        index_local = faiss.IndexFlatL2(dim)
        index_local.add(embeddings_local)
        np.save(EMBEDDINGS_FILE, embeddings_local)
        with open(FAISS_INDEX_PKL, "wb") as f:
            pickle.dump({"embeddings": embeddings_local, "index": index_local}, f)
        return embeddings_local, index_local

embeddings, index = load_or_compute_embeddings()

# Reuse embedder globally
embedder = SentenceTransformer("all-MiniLM-L6-v2", device='cuda' if torch.cuda.is_available() else 'cpu')
client = Client()
print(f"FAISS index ready with {index.ntotal} entries.")

def retrieve_examples(query, k=1):
    q_emb = embedder.encode([query], convert_to_numpy=True)
    dists, idxs = index.search(q_emb, k)
    return [dataset[i] for i in idxs[0]]

def build_batch_prompt(subject, topic, difficulty, num_questions=BATCH_SIZE):
    examples = retrieve_examples(f"{subject} {topic} {difficulty}", k=1)
    prompt = "Example JEE question with full solution:\n"
    for ex in examples:
        prompt += f"QUESTION: {ex['question']}\n"
        if ex.get("options"):
            prompt += f"OPTIONS: {ex['options']}\n"
        if ex.get("gold"):
            prompt += f"ANSWER: {ex['gold']}\n"
        prompt += "SOLUTION: Step-by-step reasoning...\n---\n"

    prompt += (
        f"\nNow generate {num_questions} NEW distinct JEE-style questions for:\n"
        f"Subject: {subject}\nTopic: {topic}\nDifficulty: {difficulty}\n\n"
        "Format each question block as:\n"
        "QUESTION: ...\nTYPE: MCQ or NUMERIC\nOPTIONS: ... [for MCQ]\nANSWER: ...\nSOLUTION: detailed explanation\n---\n"
        "Do NOT add extra commentary. Separate each question with ---\n"
        f"{CHAIN_OF_THOUGHT_SUFFIX}"
    )
    return prompt

# Parsing functions unchanged (copy from your original, trimmed here for brevity)
# ...

def parse_response(response_text):
    # Your robust parse_response code here (unchanged)
    components = {'question': None, 'type': None, 'options': "", 'answer': None, 'solution': None}
    try:
        q_match = re.search(r'QUESTION:\s*(.+?)(?=\n\s*(TYPE|OPTIONS|ANSWER|SOLUTION|$))', response_text, re.DOTALL | re.IGNORECASE)
        if q_match:
            components['question'] = q_match.group(1).strip()

        t_match = re.search(r'TYPE:\s*(\w+)', response_text, re.IGNORECASE)
        if t_match:
            qtype = t_match.group(1).upper()
            components['type'] = 'MCQ' if 'MCQ' in qtype or 'MULTIPLE' in qtype else 'NUMERIC'

        if components['type'] == 'MCQ':
            opt_match = re.search(r'OPTIONS:\s*(.+?)(?=\n\s*(ANSWER|SOLUTION|$))', response_text, re.DOTALL | re.IGNORECASE)
            if opt_match:
                options_text = opt_match.group(1).strip()
                options = []
                for letter in ['A', 'B', 'C', 'D']:
                    pattern = r'\(?'+letter+r'[\)\s\.\-:]+([^\(\)\n]+)'
                    match = re.search(pattern, options_text, re.IGNORECASE)
                    if match:
                        options.append(match.group(1).strip())
                if len(options) >= 4:
                    components['options'] = " | ".join(options[:4])
                else:
                    components['type'] = 'NUMERIC'

        ans_match = re.search(r'ANSWER:\s*([A-D0-9\.\-]+)', response_text, re.IGNORECASE)
        if ans_match:
            components['answer'] = ans_match.group(1).strip()

        sol_match = re.search(r'SOLUTION:\s*(.+)', response_text, re.DOTALL | re.IGNORECASE)
        if sol_match:
            components['solution'] = sol_match.group(1).strip()
    except Exception as e:
        print(f"Parsing error: {str(e)}")

    if not components['question'] or len(components['question']) < 15:
        return None
    if not components['answer']:
        return None
    return {
        'question': components['question'],
        'type': components['type'],
        'options': components['options'],
        'correct_answer': components['answer'],
        'solution': components['solution'] or "Solution not provided"
    }

def parse_multiple_questions(response_text):
    blocks = re.split(r'\n---+\n', response_text.strip())
    questions = []
    for block in blocks:
        parsed = parse_response(block)
        if parsed:
            questions.append(parsed)
    return questions

def generate_batch(subject, topic, difficulty):
    prompt = build_batch_prompt(subject, topic, difficulty)
    for attempt in range(MAX_RETRIES):
        try:
            start_time = time.time()
            response = client.chat(
                model=MODEL_NAME,
                messages=[{"role": "user", "content": prompt}],
                options={'temperature': 0.7, 'num_ctx': 2048}  # No 'num_gpu' param here
            )
            duration = time.time() - start_time
            print(f"API call for batch ({subject}/{topic}/{difficulty}) took {duration:.2f}s")
            content = response.get('message', {}).get('content', '')
            if content:
                return parse_multiple_questions(content)
        except Exception as e:
            print(f"Batch generation error (attempt {attempt+1}): {e}")
            time.sleep(1)
    return []

# Prepare distribution
difficulty_levels = ["easy", "medium", "hard"]
subject_topic_counts = {}
total_count = 0
for subject, topics in topic_distribution.items():
    for topic, weight in topics.items():
        count = max(1, int((weight / 5000) * TARGET_TOTAL))
        subject_topic_counts[(subject, topic)] = count
        total_count += count

print(f"Will generate approx {total_count} questions total.")

# Main task with proper metadata passing
def task(subject, topic, difficulty, count):
    generated = []
    batches = (count + BATCH_SIZE - 1) // BATCH_SIZE
    for _ in range(batches):
        batch_questions = generate_batch(subject, topic, difficulty)
        for q in batch_questions:
            q['subject'] = subject
            q['topic'] = topic
            q['difficulty'] = difficulty
        generated.extend(batch_questions)
        if len(generated) >= count:
            break
    return generated[:count]

successful_questions = []
failed_tasks = []

print("Starting concurrent question generation...")

with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
    futures = []
    for (subject, topic), count in subject_topic_counts.items():
        difficulty = random.choice(difficulty_levels)
        futures.append((subject, topic, difficulty, executor.submit(task, subject, topic, difficulty, count)))

    for subject, topic, difficulty, future in tqdm(futures):
        try:
            res = future.result()
            if res:
                successful_questions.extend(res)
            else:
                failed_tasks.append(f"Empty batch result for {subject}-{topic}-{difficulty}")
        except Exception as e:
            failed_tasks.append(f"Exception for {subject}-{topic}-{difficulty}: {e}")

print(f"Generated {len(successful_questions)} questions total.")

# Save results
if successful_questions:
    df = pd.DataFrame(successful_questions)
    df.insert(0, 'id', [f"Q{i+1:05d}" for i in range(len(df))])
    df.to_csv(OUTPUT_CSV, index=False)

if failed_tasks:
    pd.DataFrame({"error": failed_tasks}).to_csv(FAILED_CSV, index=False)

print("\n" + "="*50)
print(f"SUCCESS: {len(successful_questions)}")
print(f"FAILED tasks: {len(failed_tasks)}")

if successful_questions:
    print("\n=== DISTRIBUTION ===")
    print("Question Types:")
    print(df['type'].value_counts())
    print("\nDifficulty Levels:")
    print(df['difficulty'].value_counts())
    print("\nSubjects:")
    print(df['subject'].value_counts())

print(f"\nResults saved to {OUTPUT_CSV}")
