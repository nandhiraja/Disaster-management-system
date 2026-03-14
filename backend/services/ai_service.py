import os
import json
import logging
from typing import List, Dict, Any, Tuple
from groq import Groq
from dotenv import load_dotenv

# Configure logger
logger = logging.getLogger(__name__)

# Try to get the Groq API key from environment
load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
client = None
if GROQ_API_KEY:
    try:
        client = Groq(api_key=GROQ_API_KEY)
    except Exception as e:
        logger.error(f"Failed to initialize Groq client: {e}")

MODEL_NAME = "llama-3.3-70b-versatile"

def parse_sos_message(message: str) -> dict:
    """
    Uses Groq LLM to convert a messy SOS string into structured JSON.
    """
    if not client:
        logger.warning("Groq client not initialized. Falling back to basic parsing.")
        return _fallback_parse(message)

    prompt = f"""You are an expert AI emergency response parser. 
Extract key information from the following distress message and return ONLY valid JSON.
Extract these fields:
- emergency_type: one of 'medical', 'flood', 'trapped', 'elderly', 'shelter', 'fire', 'other'
- people_count: integer (estimate if not explicit, default 1)
- is_medical: boolean
- is_elderly: boolean
- urgency: one of 'low', 'medium', 'high', 'critical'

Message: "{message}"

Return ONLY JSON. Do not include markdown code block syntax. Example:
{{"emergency_type": "flood", "people_count": 2, "is_medical": true, "is_elderly": false, "urgency": "critical"}}
"""
    try:
        completion = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            max_tokens=200,
            response_format={"type": "json_object"}
        )
        content = completion.choices[0].message.content
        return json.loads(content)
    except Exception as e:
        logger.error(f"Error parsing SOS with Groq: {e}")
        return _fallback_parse(message)

def _fallback_parse(message: str) -> dict:
    """Fallback naive parsing if AI fails."""
    m_lower = message.lower()
    return {
        "emergency_type": "medical" if "sick" in m_lower or "hurt" in m_lower else "flood",
        "people_count": 1,
        "is_medical": "sick" in m_lower or "medic" in m_lower,
        "is_elderly": "old" in m_lower or "grand" in m_lower or "elder" in m_lower,
        "urgency": "critical" if "help" in m_lower else "medium"
    }

def _build_context(sos_data: dict, responders: List[dict]) -> tuple:
    """
    Context Builder: Cleans and prepares data for rules and scoring.
    """
    cleaned_sos = {
        "id": sos_data.get("sos_id"),
        "type": sos_data.get("emergency_type"),
        "people": sos_data.get("people_count"),
        "triage_level": sos_data.get("triage_level"),
        "location": f'{sos_data.get("lat")},{sos_data.get("lon")}'
    }
    
    cleaned_responders = []
    for r in responders:
        # Distance is assumed to be provided via nearby query (Haversine)
        # We ensure standard keys exist
        cleaned_responders.append({
            "id": r.get("id"),
            "name": r.get("name"),
            "type": r.get("type"),
            "tier": r.get("tier"),
            "trust_score": r.get("trust_score", 50),
            "distance_km": r.get("distance_km", 99.0),
            "skills": json.loads(r.get("skills", "[]")) if isinstance(r.get("skills"), str) else r.get("skills", []),
            "equipment": json.loads(r.get("equipment", "[]")) if isinstance(r.get("equipment"), str) else r.get("equipment", []),
        })
        
    return cleaned_sos, cleaned_responders

def _rule_filter(sos: dict, responders: List[dict]) -> List[dict]:
    """
    Rule Filter: Removes responders that violate hard constraints.
    """
    filtered = []
    for r in responders:
        # Example Rule 1: Medical emergencies strongly prefer medical/ambulance teams or those with first_aid skill
        is_medical_sos = sos.get("type") == "medical"
        has_medical_skill = "first_aid" in r.get("skills", []) or r.get("type") in ["medical", "ambulance"]
        
        # We might not rigidly exclude non-medical if they are the ONLY ones, but for strict filtering we can penalize or remove
        # For prototype, let's keep it simple: Filter out non-boats for deep floods (if we had water depth)
        
        # Example Rule 2: If sos type is 'fire', we need 'fire' type responders ideally. But let's just use it to boost scoring instead of hard exclusion unless strict.
        
        # We will lightly filter: if distance > 50km, remove (already handled by radius in SQL usually, but just in case)
        if r.get("distance_km", 0) > 50:
            continue
            
        filtered.append(r)
    return filtered

def _scoring_engine(sos: dict, responders: List[dict]) -> List[dict]:
    """
    Heuristic Base Score model.
    """
    scored = []
    sos_type = sos.get("type")
    
    for r in responders:
        score = 0.0
        
        # 1. Equipment & Type Match (30%)
        # Simple string matching heuristic
        equip_match = 0
        if sos_type == "flood" and ("boat" in r.get("equipment", []) or r.get("type") == "boat"):
            equip_match = 1.0
        elif sos_type == "medical" and ("ambulance" in r.get("equipment", []) or r.get("type") == "medical"):
            equip_match = 1.0
        elif sos_type == "fire" and ("truck" in r.get("equipment", []) or r.get("type") == "fire"):
            equip_match = 1.0
        score += 0.30 * equip_match
        
        # 2. Skill Match (25%)
        # E.g. elder/medical needs first aid
        skill_match = 0
        if sos_type == "medical" and "first_aid" in r.get("skills", []):
            skill_match = 1.0
        elif sos_type == "flood" and "flood_rescue" in r.get("skills", []):
            skill_match = 1.0
        elif len(r.get("skills", [])) > 0: # General utility
            skill_match = 0.5
        score += 0.25 * skill_match
        
        # 3. Trust level (20%)
        trust = r.get("trust_score", 50) / 100.0
        score += 0.20 * trust
        
        # 4. Distance Score (15%) - Inverse linearly up to 20km
        dist = r.get("distance_km", 20.0)
        dist_score = max(0.0, 1.0 - (dist / 20.0))
        score += 0.15 * dist_score
        
        # 5. Availability (10%) - Assume all passed are available, but might add tier bonus
        tier_bonus = 1.0 if r.get("tier") in ["government", "certified_volunteer"] else 0.5
        score += 0.10 * tier_bonus
        
        r["ai_score"] = round(score, 3)
        scored.append(r)
        
    # Sort descending
    scored.sort(key=lambda x: x["ai_score"], reverse=True)
    return scored

def _generate_llm_explanation(sos: dict, top_responders: List[dict]) -> dict:
    """
    Pass the top scored responders to Groq to generate a human-readable reasoning JSON.
    """
    if not client:
        # Fallback explanation if no Groq
        recommendations = []
        for index, r in enumerate(top_responders[:3]):
            rec = {
                "team_id": r["id"],
                "name": r["name"],
                "score": r["ai_score"],
                "distance": r["distance_km"],
                "reason": f"Heuristic score {r['ai_score']}. Closest match based on type {r['type']} and distance."
            }
            recommendations.append(rec)
            
        return {
            "sos_id": sos.get("id"),
            "recommended_plan": recommendations[:2],
            "alternative_options": recommendations[2:]
        }

    # Use LLM for explanation
    prompt_context = {
        "sos_details": sos,
        "available_top_responders": top_responders[:4] # Only send top 4 to save context window
    }
    
    prompt = f"""You are the AI reasoning module for an Emergency Dispatch System.
Based on the heuristic scores, evaluate the top responders for this SOS request and explain WHY they are the best fit.

Input Context:
{json.dumps(prompt_context, indent=2)}

CRITICAL INSTRUCTIONS:
1. You MUST ONLY select responders that exist in the `available_top_responders` list above. 
2. Use the EXACT `id` provided for that responder inside the `team_id` field.
3. DO NOT hallucinate, invent, or create any new responders. If there are no responders, return empty arrays.

Task:
1. Pick the top 1 or 2 from the provided list as the 'recommended_plan'. Explain the rationale concisely (e.g. "Required for flood evacuation" or "Medical support required").
2. Put the next 1 or 2 from the provided list as 'alternative_options' and explain why they are backups (e.g. "Quick arrival but lacks equipment" or "Further away").

Return ONLY valid JSON in this exact structure:
{{
  "recommended_plan": [
    {{
      "team_id": "EXACT_ID_FROM_CONTEXT",
      "reason": "Clear explanation here"
    }}
  ],
  "alternative_options": [
    {{
      "team_id": "EXACT_ID_FROM_CONTEXT",
      "reason": "Clear explanation here"
    }}
  ]
}}
"""
    try:
        print("\n\n" + "="*50)
        print("🤖 [AI DEBUG] GROQ PROMPT: Sending the following context to Groq LLM:")
        print(json.dumps(prompt_context, indent=2))
        print("="*50 + "\n")
        
        completion = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            max_tokens=300,
            response_format={"type": "json_object"}
        )
        content = completion.choices[0].message.content
        
        print("\n" + "="*50)
        print("🤖 [AI DEBUG] GROQ RESPONSE: Received the following JSON from Groq:")
        print(content)
        print("="*50 + "\n\n")
        
        explained_data = json.loads(content)
        
        # Merge LLM reasoning back with original scores and names for the frontend
        merged_rec = []
        merged_alt = []
        
        # helper
        def merge_list(llm_list, dest_list):
            for item in llm_list:
                for r in top_responders:
                    if str(r.get("id")) == str(item.get("team_id")):
                        dest_list.append({
                            "team_id": r["id"],
                            "name": r["name"],
                            "type": r["type"],
                            "score": r["ai_score"],
                            "distance_km": r["distance_km"],
                            "reason": item.get("reason", "Highly recommended by scoring engine")
                        })
                        break
        
        merge_list(explained_data.get("recommended_plan", []), merged_rec)
        merge_list(explained_data.get("alternative_options", []), merged_alt)
        
        return {
            "sos_id": sos.get("id"),
            "recommended_plan": merged_rec,
            "alternative_options": merged_alt
        }
    except Exception as e:
        logger.error(f"Error generating reasoning with Groq: {e}")
        # Fallback explanation if Groq fails
        recommendations = []
        for index, r in enumerate(top_responders[:3]):
            rec = {
                "team_id": r["id"],
                "name": r["name"],
                "score": r["ai_score"],
                "distance_km": r.get("distance_km", 0),
                "reason": f"Fallback: Heuristic score {r['ai_score']}."
            }
            recommendations.append(rec)
            
        return {
            "sos_id": sos.get("id"),
            "recommended_plan": recommendations[:2],
            "alternative_options": recommendations[2:]
        }

def generate_hybrid_recommendation(sos_data: dict, raw_responders: List[dict]) -> dict:
    """
    Main entry point for AI Dispatch Recommendation.
    Orchestrates the Context Builder -> Rule Filter -> Scoring Engine -> LLM Explanation.
    """
    # 1. Context Builder
    sos, responders = _build_context(sos_data, raw_responders)
    
    # 2. Rule Filter
    filtered_responders = _rule_filter(sos, responders)
    if not filtered_responders:
        return {
            "sos_id": sos.get("id"),
            "recommended_plan": [],
            "alternative_options": [],
            "note": "No valid responders found after rule filtering."
        }
        
    # 3. Scoring Engine
    scored_responders = _scoring_engine(sos, filtered_responders)
    
    # 4. LLM Explanation / Reasoning
    final_output = _generate_llm_explanation(sos, scored_responders)
    
    # Attach all parsed and scored responders so the frontend can display them too
    final_output["all_available_responders"] = scored_responders
    
    return final_output
