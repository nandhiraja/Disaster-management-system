import json
import logging
from services.ai_service import parse_sos_message, generate_hybrid_recommendation

# Mock data for testing recommendation engine
MOCK_SOS = {
    "id": "test-sos-123",
    "type": "medical",
    "people": 2,
    "triage_level": 1,
    "location": "13.08, 80.27"
}

MOCK_RESPONDERS = [
    {
        "id": "r1",
        "name": "Boat Team Alpha",
        "type": "boat",
        "tier": "government",
        "trust_score": 90,
        "distance_km": 5.0,
        "equipment": ["boat", "lifejacket"],
        "skills": ["flood_rescue"]
    },
    {
        "id": "r2",
        "name": "Medic Volunteer John",
        "type": "medical",
        "tier": "certified_volunteer",
        "trust_score": 85,
        "distance_km": 2.0,
        "equipment": ["first_aid_kit"],
        "skills": ["first_aid", "cpr"]
    },
    {
        "id": "r3",
        "name": "Ambulance Unit 7",
        "type": "ambulance",
        "tier": "government",
        "trust_score": 95,
        "distance_km": 8.0,
        "equipment": ["ambulance", "stretcher"],
        "skills": ["paramedic"]
    }
]

def run_tests():
    print("=== Testing AI SOS Parser ===")
    messy_msg = "Please help! 3 people stuck on roof, water is rushing fast! Grandma has chest pain."
    print("Input:", messy_msg)
    parsed = parse_sos_message(messy_msg)
    print("Parsed JSON:")
    print(json.dumps(parsed, indent=2))
    print("\n" + "="*40 + "\n")
    
    print("=== Testing AI Hybrid Recommendation Engine ===")
    print("SOS:", MOCK_SOS["type"], "emergency")
    print("Available Responders:", len(MOCK_RESPONDERS))
    result = generate_hybrid_recommendation(MOCK_SOS, MOCK_RESPONDERS)
    print("Recommendation Result:")
    print(json.dumps(result, indent=2))
    
if __name__ == "__main__":
    run_tests()
