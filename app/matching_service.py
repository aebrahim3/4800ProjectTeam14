from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(
    title="Matching Service API",
    description="Converts profile JSON to a vector for career matching",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

def profile_to_vector(profile: dict) -> list[float]:
    """
    Converts the complete profile JSON into a  vector
    for pgvector similarity search.

    Total: 56 dimensions (40 activity + 16 personality)
    Missing values default to 1.
    """

    vector = []

    activity_fields = [
        "estimating_quantifiable_characteristics_score",
        "getting_information_score",
        "identifying_objects_actions_and_events_score",
        "inspecting_equipment_structures_or_material_score",
        "monitoring_processes_materials_or_surroundings_score",
        "controlling_machines_and_processes_score",
        "developing_technical_instructions_score",
        "clerical_activities_score",
        "electronic_maintenance_score",
        "handling_and_moving_objects_score",
        "interacting_with_computers_score",
        "managing_resources_score",
        "mechanical_maintenance_score",
        "operating_vehicles_mechanized_devices_or_equipment_score",
        "performing_general_physical_activities_score",
        "processing_information_score",
        "analyzing_data_or_information_score",
        "developing_objectives_and_strategies_score",
        "evaluating_info_to_determine_compliance_with_standards_score",
        "judging_quality_score",
        "making_decisions_score",
        "planning_and_organizing_score",
        "scheduling_work_and_activities_score",
        "thinking_creatively_score",
        "using_new_relevant_knowledge_score",
        "assisting_and_caring_for_others_score",
        "coaching_and_developing_others_score",
        "communicating_with_persons_outside_organization_score",
        "communicating_with_coworkers_score",
        "coordinating_work_and_activities_of_others_score",
        "establishing_and_maintaining_interpersonal_relationships_score",
        "interpreting_meaning_of_information_for_others_score",
        "performing_for_or_working_directly_with_public_score",
        "providing_consultation_and_advice_score",
        "resolving_conflicts_and_negotiating_with_others_score",
        "selling_or_influencing_others_score",
        "staffing_score",
        "supervising_subordinates_score",
        "team_building_score",
        "training_and_teaching_score",
    ]

    personality_fields = [
        "achievement_effort_score",
        "adaptability_flexibility_score",
        "stress_tolerance_score",
        "initiative_score",
        "analytical_thinking_score",
        "attention_to_detail_score",
        "innovation_score",
        "concern_for_others_score",
        "collaboration_score",
        "service_orientation_score",
        "integrity_score",
        "social_orientation_score",
        "independence_score",
        "accountability_score",
        "competitive_drive_score",
        "charisma_score",
    ]

    # Activity Scores
    activity_scores = profile.get("activity_scores", {}) or {}
    for field in activity_fields:
        raw = activity_scores.get(field) or 1
        vector.append(float(raw))

    # Personality Scores
    personality_scores = profile.get("personality_scores", {}) or {}
    for field in personality_fields:
        raw = personality_scores.get(field) or 1
        vector.append(float(raw))

    return vector


# this class is used to validate the incoming JSON request body for the /vectorize endpoint
class ProfileRequest(BaseModel):
    profile: dict

# This endpoint receives a profile JSON, converts it to a vector, and returns the vector
@app.post("/vectorize")
def vectorize(request: ProfileRequest):
    vector = profile_to_vector(request.profile)
    return {"vector": vector}

@app.get("/health")
def health():
    return {"status": "ok"}
