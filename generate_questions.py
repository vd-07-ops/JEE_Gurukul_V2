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
TARGET_TOTAL = 50
CHAIN_OF_THOUGHT_SUFFIX = "Your solution must explain each step clearly like a teacher."
BATCH_SIZE = 1
MAX_WORKERS = 2
USE_GPU = True

print("Checking GPU availability via torch:")
print(f"CUDA available? {torch.cuda.is_available()}, devices: {torch.cuda.device_count()}")
print(f"Using GPU: {USE_GPU}")
if USE_GPU and torch.cuda.is_available():
    print(f"Using GPU device: {torch.cuda.get_device_name(0)}")

# === Load data ===
os.makedirs("data", exist_ok=True)
with open("data/original_questions.json", "r", encoding="utf-8") as f:
    dataset = json.load(f)
with open("data/dist_topic.json", "r", encoding="utf-8") as f:
    topic_distribution = json.load(f)
print(f"Loaded {len(dataset)} questions and {len(topic_distribution)} topics.")

questions = [item["question"] for item in dataset]

# === Embeddings and FAISS ===
def load_or_compute_embeddings():
    if os.path.exists(EMBEDDINGS_FILE) and os.path.exists(FAISS_INDEX_PKL):
        print("Loading cached embeddings and FAISS index...")
        try:
            with open(FAISS_INDEX_PKL, "rb") as f:
                data = pickle.load(f)
                embeddings = data["embeddings"]
                index = data["index"]
            return embeddings, index
        except Exception as e:
            print(f"Error loading cached embeddings: {e}")
            print("Will recompute embeddings...")
    
    print("Computing embeddings and building FAISS index...")
    device = 'cuda' if USE_GPU and torch.cuda.is_available() else 'cpu'
    print(f"Using device: {device}")
    
    embedder_local = SentenceTransformer("all-MiniLM-L6-v2", device=device)
    embeddings_local = embedder_local.encode(questions, convert_to_numpy=True, show_progress_bar=True)
    dim = embeddings_local.shape[1]
    index_local = faiss.IndexFlatL2(dim)
    
    if USE_GPU and torch.cuda.is_available():
        try:
            res = faiss.StandardGpuResources()
            index_local = faiss.index_cpu_to_gpu(res, 0, index_local)
        except Exception as e:
            print(f"GPU FAISS initialization failed: {e}")
            print("Falling back to CPU FAISS...")
    
    index_local.add(embeddings_local)
    np.save(EMBEDDINGS_FILE, embeddings_local)
    with open(FAISS_INDEX_PKL, "wb") as f:
        pickle.dump({"embeddings": embeddings_local, "index": faiss.index_gpu_to_cpu(index_local) if USE_GPU else index_local}, f)
    return embeddings_local, index_local

embeddings, index = load_or_compute_embeddings()
embedder = SentenceTransformer("all-MiniLM-L6-v2", device='cuda' if torch.cuda.is_available() else 'cpu')
client = Client()
print(f"FAISS index ready with {index.ntotal} entries.")

def retrieve_examples(query, k=1):
    q_emb = embedder.encode([query], convert_to_numpy=True)
    dists, idxs = index.search(q_emb, k)
    return [dataset[i] for i in idxs[0]]

def build_batch_prompt(subject, topic, difficulty, num_questions=BATCH_SIZE):
    examples = retrieve_examples(f"{subject} {topic} {difficulty}", k=1)
    prompt = "Generate JEE question:\n\n"
    for ex in examples:
        prompt += f"QUESTION: {ex['question']}\n"
        if ex.get("options"):
            prompt += f"OPTIONS: {ex['options']}\n"
        if ex.get("gold"):
            prompt += f"ANSWER: {ex['gold']}\n"
        prompt += "SOLUTION: Step-by-step solution\n---\n"

    prompt += (
        f"\nGenerate {num_questions} NEW JEE question for:\n"
        f"Subject: {subject}\nTopic: {topic}\nDifficulty: {difficulty}\n\n"
        "Rules:\n"
        "1. For MCQ: TYPE: MCQ, 4 options (A-D), answer A/B/C/D\n"
        "2. For NUMERIC: TYPE: NUMERIC, no options, numeric answer\n\n"
        "Format:\n"
        "QUESTION: [text]\n"
        "TYPE: [MCQ/NUMERIC]\n"
        "OPTIONS: [A) opt1 | B) opt2 | C) opt3 | D) opt4] (MCQ only)\n"
        "ANSWER: [A/B/C/D or number]\n"
        "SOLUTION: [steps]\n---\n"
    )
    return prompt

def parse_response(response_text):
    components = {'question': None, 'type': None, 'options': "", 'answer': None, 'solution': None}
    try:
        # Quick validation of required sections
        if not all(x in response_text for x in ['QUESTION:', 'TYPE:', 'ANSWER:']):
            return None

        # Extract question
        q_match = re.search(r'QUESTION:\s*(.+?)(?=\n\s*(TYPE|OPTIONS|ANSWER|SOLUTION|$))', response_text, re.DOTALL | re.IGNORECASE)
        if not q_match:
            return None
        components['question'] = q_match.group(1).strip()

        # Extract type
        t_match = re.search(r'TYPE:\s*(\w+)', response_text, re.IGNORECASE)
        if not t_match:
            return None
        qtype = t_match.group(1).upper()
        if qtype not in ['MCQ', 'NUMERIC']:
            return None
        components['type'] = qtype

        # Handle options for MCQ
        if components['type'] == 'MCQ':
            opt_match = re.search(r'OPTIONS:\s*(.+?)(?=\n\s*(ANSWER|SOLUTION|$))', response_text, re.DOTALL | re.IGNORECASE)
            if not opt_match:
                return None
            options = re.findall(r'[A-D][\)\.\-:\s]+([^\n]+)', opt_match.group(1))
            if len(options) != 4:
                return None
            components['options'] = " | ".join(opt.strip() for opt in options)

        # Extract answer
        ans_match = re.search(r'ANSWER:\s*([A-D0-9\.\-]+)', response_text, re.IGNORECASE)
        if not ans_match:
            return None
        answer = ans_match.group(1).strip()
        
        # Validate answer format
        if components['type'] == 'MCQ':
            if answer not in ['A', 'B', 'C', 'D']:
                return None
        else:
            try:
                float(answer)
            except ValueError:
                return None
        components['answer'] = answer

        # Extract solution
        sol_match = re.search(r'SOLUTION:\s*(.+)', response_text, re.DOTALL | re.IGNORECASE)
        if sol_match:
            components['solution'] = sol_match.group(1).strip()
        else:
            components['solution'] = "Solution not provided"

        return {
            'question': components['question'],
            'type': components['type'],
            'options': components['options'],
            'correct_answer': components['answer'],
            'solution': components['solution']
        }
    except Exception:
        return None

def parse_multiple_questions(response_text):
    blocks = re.split(r'\n---+\n', response_text.strip())
    parsed_questions = []
    for block in blocks:
        if block.strip():
            question = parse_response(block)
            if question:
                parsed_questions.append(question)
    return parsed_questions

def generate_batch(subject, topic, difficulty):
    prompt = build_batch_prompt(subject, topic, difficulty)
    for attempt in range(MAX_RETRIES):
        try:
            start_time = time.time()
            print(f"\nGenerating for {subject}/{topic}/{difficulty} (attempt {attempt + 1}/{MAX_RETRIES})")
            response = client.chat(
                model=MODEL_NAME,
                messages=[{"role": "user", "content": prompt}],
                options={'temperature': 0.5, 'num_ctx': 2048}
            )
            content = response.get('message', {}).get('content', '')
            if content:
                print(f"✓ Generated in {time.time()-start_time:.2f}s")
                questions = parse_multiple_questions(content)
                if questions:
                    print(f"✓ Parsed {len(questions)} questions")
                    return questions
            time.sleep(1)
        except Exception as e:
            print(f"✗ Attempt {attempt+1} failed: {e}")
            time.sleep(1)
    return []

# === Distribution Logic ===
total_weight = sum(
    weight for subject_topics in topic_distribution.values() for weight in subject_topics.values()
)
subject_topic_counts = {}
total_assigned = 0

for subject, topics in topic_distribution.items():
    for topic, weight in topics.items():
        count = max(1, round((weight / total_weight) * TARGET_TOTAL))
        subject_topic_counts[(subject, topic)] = count
        total_assigned += count

print(f"Will generate approx {total_assigned} questions total.")

def task(subject, topic, difficulty, count):
    generated = []
    batches = (count + BATCH_SIZE - 1) // BATCH_SIZE
    print(f"\nStarting task for {subject}/{topic}/{difficulty}")
    print(f"Need to generate {count} questions in {batches} batches")
    
    for batch_num in range(batches):
        print(f"\nProcessing batch {batch_num + 1}/{batches}")
        batch_questions = generate_batch(subject, topic, difficulty)
        if batch_questions:
            for q in batch_questions:
                q['subject'] = subject
                q['topic'] = topic
                q['difficulty'] = difficulty
            generated.extend(batch_questions)
            print(f"Progress: {len(generated)}/{count} questions generated")
            if len(generated) >= count:
                break
        else:
            print("Warning: No questions generated in this batch")
    return generated[:count]

successful_questions = []
failed_tasks = []

print("Starting concurrent question generation...")
with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
    futures = []
    for (subject, topic), count in subject_topic_counts.items():
        difficulty = random.choice(["easy", "medium", "hard", "very hard"])
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

# === Save Results ===
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