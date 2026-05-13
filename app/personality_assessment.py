"""
Personality assessment logic for evaluating user profiles.

-------------------------------------------------------

FastAPI service that:
1. Returns the personality assessment questions (GET /questions)
2. Accepts user responses and returns scored JSON (POST /assess)

Traits mapped to OaSIS Personal Attributes (1-5 scale):
- Achievement/Effort
- Adaptability/Flexibility
- Stress Tolerance
- Initiative
- Analytical Thinking
- Attention to Detail
- Innovation
- Concern for Others
- Collaboration
- Service Orientation
- Integrity
- Social Orientation
- Independence
- Accountability
- Competitive Drive
- Charisma

Run with:
uvicorn personality_assessment:app --reload --port 8003
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(
    title="Personality Assessment API",
    description="API for assessing personality traits based on user responses.",
    version="1.0.0"
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
     # Achievement / Effort
    {
        "id": 1,
        "trait": "achievement_effort",
        "text": "I set high goals for myself and work hard to achieve them.",
        "direction": "positive",
    },
    {
        "id": 2,
        "trait": "achievement_effort",
        "text": "I persist through challenges rather than giving up when things get difficult.",
        "direction": "positive",
    },
    {
        "id": 3,
        "trait": "achievement_effort",
        "text": "I often settle for doing just enough to get by.",
        "direction": "negative",
    },
 
    # Adaptability / Flexibility
    {
        "id": 4,
        "trait": "adaptability_flexibility",
        "text": "I adjust easily when plans change unexpectedly.",
        "direction": "positive",
    },
    {
        "id": 5,
        "trait": "adaptability_flexibility",
        "text": "I am comfortable working in environments where things change frequently.",
        "direction": "positive",
    },
    {
        "id": 6,
        "trait": "adaptability_flexibility",
        "text": "I find it difficult to change my approach once I have decided on a plan.",
        "direction": "negative",
    },
 
    # Stress Tolerance
    {
        "id": 7,
        "trait": "stress_tolerance",
        "text": "I remain calm and focused when working under pressure or tight deadlines.",
        "direction": "positive",
    },
    {
        "id": 8,
        "trait": "stress_tolerance",
        "text": "I recover quickly after facing setbacks or stressful situations.",
        "direction": "positive",
    },
    {
        "id": 9,
        "trait": "stress_tolerance",
        "text": "Stressful situations make it hard for me to think clearly.",
        "direction": "negative",
    },
 
    # Initiative
    {
        "id": 10,
        "trait": "initiative",
        "text": "I often take action without being asked when I see something that needs to be done.",
        "direction": "positive",
    },
    {
        "id": 11,
        "trait": "initiative",
        "text": "I look for opportunities to improve things even when no one asks me to.",
        "direction": "positive",
    },
    {
        "id": 12,
        "trait": "initiative",
        "text": "I prefer to wait for instructions before starting a new task.",
        "direction": "negative",
    },
 
    # Analytical Thinking
    {
        "id": 13,
        "trait": "analytical_thinking",
        "text": "I enjoy breaking down complex problems into smaller parts to find a solution.",
        "direction": "positive",
    },
    {
        "id": 14,
        "trait": "analytical_thinking",
        "text": "I use logic and evidence to evaluate information before making decisions.",
        "direction": "positive",
    },
    {
        "id": 15,
        "trait": "analytical_thinking",
        "text": "I tend to go with my gut feeling rather than analyzing a situation thoroughly.",
        "direction": "negative",
    },
 
    # Attention to Detail
    {
        "id": 16,
        "trait": "attention_to_detail",
        "text": "I carefully check my work to make sure it is accurate and error-free.",
        "direction": "positive",
    },
    {
        "id": 17,
        "trait": "attention_to_detail",
        "text": "I notice small details that others often overlook.",
        "direction": "positive",
    },
    {
        "id": 18,
        "trait": "attention_to_detail",
        "text": "I sometimes submit work without thoroughly reviewing it.",
        "direction": "negative",
    },
 
    # Innovation
    {
        "id": 19,
        "trait": "innovation",
        "text": "I enjoy coming up with new and creative ideas to solve problems.",
        "direction": "positive",
    },
    {
        "id": 20,
        "trait": "innovation",
        "text": "I often think of unconventional approaches that others have not considered.",
        "direction": "positive",
    },
    {
        "id": 21,
        "trait": "innovation",
        "text": "I prefer proven methods over trying something new and unproven.",
        "direction": "negative",
    },
 
    # Concern for Others
    {
        "id": 22,
        "trait": "concern_for_others",
        "text": "I am genuinely interested in the wellbeing of the people around me.",
        "direction": "positive",
    },
    {
        "id": 23,
        "trait": "concern_for_others",
        "text": "I notice when others are struggling and offer help without being asked.",
        "direction": "positive",
    },
 
    # Collaboration
    {
        "id": 24,
        "trait": "collaboration",
        "text": "I work effectively with others to achieve shared goals.",
        "direction": "positive",
    },
    {
        "id": 25,
        "trait": "collaboration",
        "text": "I actively contribute to group discussions and make sure everyone's voice is heard.",
        "direction": "positive",
    },
    {
        "id": 26,
        "trait": "collaboration",
        "text": "I find it easier to work alone than in a team.",
        "direction": "negative",
    },
 
    # Service Orientation
    {
        "id": 27,
        "trait": "service_orientation",
        "text": "I find satisfaction in helping others accomplish their goals.",
        "direction": "positive",
    },
    {
        "id": 28,
        "trait": "service_orientation",
        "text": "I go out of my way to make sure others have what they need.",
        "direction": "positive",
    },
 
    # Integrity
    {
        "id": 29,
        "trait": "integrity",
        "text": "I am honest even when it is not in my best interest.",
        "direction": "positive",
    },
    {
        "id": 30,
        "trait": "integrity",
        "text": "I follow through on my commitments even when it is inconvenient.",
        "direction": "positive",
    },
    {
        "id": 31,
        "trait": "integrity",
        "text": "I have bent the rules when I thought no one would notice.",
        "direction": "negative",
    },
 
    # Social Orientation
    {
        "id": 32,
        "trait": "social_orientation",
        "text": "I enjoy working in environments where I interact with many different people.",
        "direction": "positive",
    },
    {
        "id": 33,
        "trait": "social_orientation",
        "text": "I find energy in social interactions and connecting with new people.",
        "direction": "positive",
    },
 
    # Independence
    {
        "id": 34,
        "trait": "independence",
        "text": "I prefer to figure things out on my own rather than asking for help.",
        "direction": "positive",
    },
    {
        "id": 35,
        "trait": "independence",
        "text": "I am comfortable making decisions without needing approval from others.",
        "direction": "positive",
    },
 
    # Accountability
    {
        "id": 36,
        "trait": "accountability",
        "text": "I take responsibility for my mistakes rather than blaming others.",
        "direction": "positive",
    },
    {
        "id": 37,
        "trait": "accountability",
        "text": "I follow through on my responsibilities even when no one is watching.",
        "direction": "positive",
    },
    {
        "id": 38,
        "trait": "accountability",
        "text": "I tend to make excuses when things do not go as planned.",
        "direction": "negative",
    },
 
    # Competitive Drive
    {
        "id": 39,
        "trait": "competitive_drive",
        "text": "I am motivated by competing with others and being the best at what I do.",
        "direction": "positive",
    },
    {
        "id": 40,
        "trait": "competitive_drive",
        "text": "I push myself harder when I know others are performing at a high level.",
        "direction": "positive",
    },
 
    # Charisma
    {
        "id": 41,
        "trait": "charisma",
        "text": "I am able to inspire and motivate others through my words and actions.",
        "direction": "positive",
    },
    {
        "id": 42,
        "trait": "charisma",
        "text": "People naturally look to me for direction in group situations.",
        "direction": "positive",
    },
]

# Map trait names to their JSON fields
TRAIT_FIELD_MAP = {
    "achievement_effort": "achievement_effort_score",
    "adaptability_flexibility": "adaptability_flexibility_score",
    "stress_tolerance": "stress_tolerance_score",
    "initiative": "initiative_score",
    "analytical_thinking": "analytical_thinking_score",
    "attention_to_detail": "attention_to_detail_score",
    "innovation": "innovation_score",
    "concern_for_others": "concern_for_others_score",
    "collaboration": "collaboration_score",
    "service_orientation": "service_orientation_score",
    "integrity": "integrity_score",
    "social_orientation": "social_orientation_score",
    "independence": "independence_score",
    "accountability": "accountability_score",
    "competitive_drive": "competitive_drive_score",
    "charisma": "charisma_score"
}

# =============================
# Request Model
# =============================
class AssessmentResponse(BaseModel):
    """
    Student submits:
    - profile: the full JSON from resume extraction (with TBD personality scores)
    - responses: a dict of question_id -> likert score (1-5)
 
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

    if 



