from __future__ import annotations
"""
Personality assessment logic for evaluating user profiles.

-------------------------------------------------------

FastAPI service that:
1. Returns the personality assessment questions (GET /questions)
2. Accepts user responses and returns scored JSON (POST /assess)

Traits mapped to OaSIS Personal Attributes (1-5 scale):
- Active Learning
- Adaptability
- Analytical Thinking
- Attention to Detail
- Creativity 
- Concern for Others
- Collaboration
- Independence
- Innovativeness
- Leadership
- Social Orientation
- Service Orientation
- Stress Tolerance


Run with:
uvicorn personality_assessment:app --reload --port 8003
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="Personality Assessment API",
    description="API for assessing personality traits based on user responses.",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

LIKERT_SCALE = {
    1: "Strongly Disagree",
    2: "Disagree",
    3: "Neutral",
    4: "Agree",
    5: "Strongly Agree"
}

# ============================
# Assessment Questions
# Each question maps to a trait and has a direction:
# "positive" = higher trait score
# "negative" = lower trait score
# ============================
QUESTIONS = [
    # Active Learning
    {
        "id": 1,
        "trait": "active_learning",
        "text": "I actively seek out new information to improve my skills and knowledge.",
        "direction": "positive",
    },
    {
        "id": 2,
        "trait": "active_learning",
        "text": "I look for opportunities to learn from new experiences and challenges.",
        "direction": "positive",
    },
    {
        "id": 3,
        "trait": "active_learning",
        "text": "I prefer to stick with what I already know rather than learning new things.",
        "direction": "negative",
    },

    # Adaptability
    {
        "id": 4,
        "trait": "adaptability",
        "text": "I adjust easily when plans change unexpectedly.",
        "direction": "positive",
    },
    {
        "id": 5,
        "trait": "adaptability",
        "text": "I am comfortable working in environments where things change frequently.",
        "direction": "positive",
    },
    {
        "id": 6,
        "trait": "adaptability",
        "text": "I find it difficult to change my approach once I have decided on a plan.",
        "direction": "negative",
    },

    # Analytical Thinking
    {
        "id": 7,
        "trait": "analytical_thinking",
        "text": "I enjoy breaking down complex problems into smaller parts to find a solution.",
        "direction": "positive",
    },
    {
        "id": 8,
        "trait": "analytical_thinking",
        "text": "I use logic and evidence to evaluate information before making decisions.",
        "direction": "positive",
    },
    {
        "id": 9,
        "trait": "analytical_thinking",
        "text": "I tend to go with my gut feeling rather than analyzing a situation thoroughly.",
        "direction": "negative",
    },

    # Attention to Detail
    {
        "id": 10,
        "trait": "attention_to_detail",
        "text": "I carefully check my work to make sure it is accurate and error-free.",
        "direction": "positive",
    },
    {
        "id": 11,
        "trait": "attention_to_detail",
        "text": "I notice small details that others often overlook.",
        "direction": "positive",
    },
    {
        "id": 12,
        "trait": "attention_to_detail",
        "text": "I sometimes submit work without thoroughly reviewing it.",
        "direction": "negative",
    },

    # Creativity
    {
        "id": 13,
        "trait": "creativity",
        "text": "I enjoy coming up with new and creative ideas to solve problems.",
        "direction": "positive",
    },
    {
        "id": 14,
        "trait": "creativity",
        "text": "I often think of unconventional approaches that others have not considered.",
        "direction": "positive",
    },
    {
        "id": 15,
        "trait": "creativity",
        "text": "I prefer proven methods over trying something new and unproven.",
        "direction": "negative",
    },

    # Concern for Others
    {
        "id": 16,
        "trait": "concern_for_others",
        "text": "I am genuinely interested in the wellbeing of the people around me.",
        "direction": "positive",
    },
    {
        "id": 17,
        "trait": "concern_for_others",
        "text": "I notice when others are struggling and offer help without being asked.",
        "direction": "positive",
    },
    {
        "id": 18,
        "trait": "concern_for_others",
        "text": "I tend to focus on my own tasks without paying much attention to how others are doing.",
        "direction": "negative",
    },

    # Collaboration
    {
        "id": 19,
        "trait": "collaboration",
        "text": "I work effectively with others to achieve shared goals.",
        "direction": "positive",
    },
    {
        "id": 20,
        "trait": "collaboration",
        "text": "I actively contribute to group discussions and make sure everyone's voice is heard.",
        "direction": "positive",
    },
    {
        "id": 21,
        "trait": "collaboration",
        "text": "I find it easier to work alone than in a team.",
        "direction": "negative",
    },

    # Independence
    {
        "id": 22,
        "trait": "independence",
        "text": "I prefer to figure things out on my own rather than asking for help.",
        "direction": "positive",
    },
    {
        "id": 23,
        "trait": "independence",
        "text": "I am comfortable making decisions without needing approval from others.",
        "direction": "positive",
    },
    {
        "id": 24,
        "trait": "independence",
        "text": "I rely heavily on others to guide me when faced with new situations.",
        "direction": "negative",
    },

    # Innovativeness
    {
        "id": 25,
        "trait": "innovativeness",
        "text": "I enjoy experimenting with new approaches even when the outcome is uncertain.",
        "direction": "positive",
    },
    {
        "id": 26,
        "trait": "innovativeness",
        "text": "I look for ways to improve existing processes rather than accepting the status quo.",
        "direction": "positive",
    },
    {
        "id": 27,
        "trait": "innovativeness",
        "text": "I am satisfied with how things are done and rarely see a need to change them.",
        "direction": "negative",
    },

    # Leadership
    {
        "id": 28,
        "trait": "leadership",
        "text": "I am able to inspire and motivate others through my words and actions.",
        "direction": "positive",
    },
    {
        "id": 29,
        "trait": "leadership",
        "text": "People naturally look to me for direction in group situations.",
        "direction": "positive",
    },
    {
        "id": 30,
        "trait": "leadership",
        "text": "I prefer to follow rather than take charge in group settings.",
        "direction": "negative",
    },

    # Social Orientation
    {
        "id": 31,
        "trait": "social_orientation",
        "text": "I enjoy working in environments where I interact with many different people.",
        "direction": "positive",
    },
    {
        "id": 32,
        "trait": "social_orientation",
        "text": "I find energy in social interactions and connecting with new people.",
        "direction": "positive",
    },
    {
        "id": 33,
        "trait": "social_orientation",
        "text": "I find social interactions draining and prefer working alone.",
        "direction": "negative",
    },

    # Service Orientation
    {
        "id": 34,
        "trait": "service_orientation",
        "text": "I find satisfaction in helping others accomplish their goals.",
        "direction": "positive",
    },
    {
        "id": 35,
        "trait": "service_orientation",
        "text": "I go out of my way to make sure others have what they need.",
        "direction": "positive",
    },
    {
        "id": 36,
        "trait": "service_orientation",
        "text": "I prefer tasks that benefit myself over tasks that involve helping others.",
        "direction": "negative",
    },

    # Stress Tolerance
    {
        "id": 37,
        "trait": "stress_tolerance",
        "text": "I remain calm and focused when working under pressure or tight deadlines.",
        "direction": "positive",
    },
    {
        "id": 38,
        "trait": "stress_tolerance",
        "text": "I recover quickly after facing setbacks or stressful situations.",
        "direction": "positive",
    },
    {
        "id": 39,
        "trait": "stress_tolerance",
        "text": "Stressful situations make it hard for me to think clearly.",
        "direction": "negative",
    },
]

# Map trait names to their OaSIS-aligned JSON fields
TRAIT_FIELD_MAP = {
    "active_learning": "active_learning_score",
    "adaptability": "adaptability_score",
    "analytical_thinking": "analytical_thinking_score",
    "attention_to_detail": "attention_to_detail_score",
    "creativity": "creativity_score",
    "concern_for_others": "concern_for_others_score",
    "collaboration": "collaboration_score",
    "independence": "independence_score",
    "innovativeness": "innovativeness_score",
    "leadership": "leadership_score",
    "social_orientation": "social_orientation_score",
    "service_orientation": "service_orientation_score",
    "stress_tolerance": "stress_tolerance_score",
}

# =============================
# Request Model
# =============================
class AssessmentResponse(BaseModel):
    """
    Student submits:
    - profile: the full JSON from resume extraction (with TBD personality scores)
    - responses: a dict of question_id -> likert score (1-5)
    - Outside this file, we will specify what values profile and responses
    store. Profile stores the full JSON output from resume extraction, and responses 
    stores a dict of question_id -> likert score (1-5). 
 
    Example:
    {
        "profile": { "full_name": "John", "personality_scores": {"achievement_effort_score": "TBD", ...} },
        "responses": { "1": 4, "2": 5, "3": 2, ... }
    }
    """
    profile: dict
    responses: dict[int, int]

#=============================
# Scoring Logic
#=============================
def score_responses(responses: dict[int, int]) -> dict[str, float | None]:
    """
    Converts raw Likert responses into trait scores on a 1-5 scale.
 
    For each trait:
    1. Collect all question scores for that trait
    2. Reverse-score negative questions (6 - score)
    3. Average the scores
    4. Round to 2 decimal places
 
    Returns a dict matching the OaSIS personality_scores JSON structure.
    """

    # Step 1: Group responses by trait
    trait_scores: dict[str, list[float]] = {trait: [] for trait in TRAIT_FIELD_MAP}

    for question in QUESTIONS:
        q_id = question["id"]
        trait = question["trait"]
        direction = question["direction"]

        if q_id in responses:
            score = responses[q_id]
            if direction == "negative":
                score = 6 - score  # Reverse score for negative questions
            trait_scores[trait].append(score)

        else:
            continue

    # Step 2: Average scores for each trait
    result = {}
    for trait, key in TRAIT_FIELD_MAP.items():
        scores = trait_scores[trait]
        if scores:
            avg_score = round(sum(scores) / len(scores), 2)
            result[key] = avg_score
        else:
            result[key] = None  # No responses for this trait

    return result

# ============================
# API Endpoints
# ============================
@app.get("/questions")
def get_questions():
    """
    Returns the list of assessment questions.
    """
    return {"questions": 
            [
     {
        "id": question["id"],
        "text": question["text"]
     } for question in QUESTIONS
     ]}

@app.post("/assess")
def assess(assessment: AssessmentResponse):
    """
    Accepts the resume extraction profile JSON and student Likert responses.
    Scores the responses and replaces TBD personality scores in the profile.
 
    Input:
    {
        "profile": { ...full resume JSON with TBD personality scores... },
        "responses": { "1": 4, "2": 5, "3": 2, ... }
    }
 
    Output:
        Complete profile JSON with personality_scores filled in.
    """
    try:
        scores = score_responses(assessment.responses)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    # Take the profile from resume extraction
    # and replace TBD personality scores with real scored values

    profile = assessment.profile
    profile["personality_scores"] = scores

    return profile


# ============================
# Health Check Endpoint
# ============================
@app.get("/health")
def health_check():
    """
    Simple endpoint to check if the service is running.
    """
    return {"status": "ok"}






