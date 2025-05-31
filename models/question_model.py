from pydantic import BaseModel, Field
from typing import List, Optional, Literal

class QuestionOption(BaseModel):
    text: str
    is_correct: bool = False

class Question(BaseModel):
    id: Optional[str] = None # Will be generated (e.g., UUID)
    question_text: str
    question_type: Literal["MCQ", "NVQ"]
    options: Optional[List[QuestionOption]] = None # Only for MCQ
    correct_answer: str # For NVQ, it's the numerical value; for MCQ, the text of the correct option
    solution: str
    topic: str
    subtopic: Optional[str] = None
    difficulty: Literal["Easy", "Medium", "Hard", "Very Hard"]
    source_id: Optional[str] = None # Original source ID if from dataset
    is_generated: bool = False
    generated_at: Optional[str] = None # ISO format datetime
    user_feedback_difficulty: Optional[float] = None # Average user feedback
    embedding: Optional[List[float]] = None # Store embedding after generation

class QuizQuestion(BaseModel):
    id: str
    question_text: str
    question_type: Literal["MCQ", "NVQ"]
    options: Optional[List[QuestionOption]] = None # Options for MCQ
    topic: str
    difficulty: Literal["Easy", "Medium", "Hard", "Very Hard"]

class QuizSubmission(BaseModel):
    user_id: str
    quiz_id: str
    answers: dict[str, str] # {question_id: user_answer}
    difficulty_feedback: dict[str, Literal["Easy", "Medium", "Hard"]] # {question_id: user_rated_difficulty}

class UserProfile(BaseModel):
    user_id: str
    preparation_stage: Literal["Beginner", "Intermediate", "Advanced", "Expert", "Legend"] = "Beginner"
    total_quizzes_completed: int = 0
    average_score: float = 0.0
    topic_proficiency: dict[str, float] = Field(default_factory=dict) # {topic: proficiency_score (0-1)}
    last_quiz_date: Optional[str] = None
