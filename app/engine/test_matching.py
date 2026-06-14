import pytest
from app.engine.matching import recommend_hostels, rank_candidates


class MockConfig:
    """Mocking OperationalConfig parameters structurally."""
    W_PRICE = 0.40
    W_LOCATION = 0.40
    W_AMENITY = 0.20
    BUDGET_SLACK = 50.00
    CLEAN_BAND = 1
    PREMIUM_BOOST = 1.15
    VERIFIED_BOOST = 0.05


@pytest.fixture
def config():
    return MockConfig()


def test_smoking_resident_excluded_from_non_smoking_hostel(config):
    resident = {
        'gender': 'male',
        'smoking': True,
        'drinking': False,
        'vegetarian': False,
        'age': 25,
        'budget_max': 1000,
        'budget_min': 500,
    }
    
    hostel = {
        'name': 'Healthy Living Hostel',
        'gender_policy': 'any',
        'smoking_allowed': False,  # Key hard gate condition
        'drinking_allowed': True,
        'veg_only': False,
        'rooms': [{'price': 800}]
    }
    
    results = recommend_hostels(resident, [hostel], config)
    assert len(results) == 0, "Hostel should be excluded due to strict smoking mismatch."


def test_cleanliness_hard_gate(config):
    resident = {
        'gender': 'male',
        'smoking': False,
        'drinking': False,
        'sleep_schedule': 'early',
        'cleanliness': 3,
        'budget_max': 1000,
        'budget_min': 500,
    }
    
    # Candidate 1: Diff of 1 (Passes gate)
    cand_pass = {
        'id': 'cand_1',
        'gender': 'male',
        'smoking': False,
        'drinking': False,
        'sleep_schedule': 'early',
        'cleanliness': 4,
        'budget_max': 1000,
        'budget_min': 500,
    }
    
    # Candidate 2: Diff of 2 (Fails gate)
    cand_fail = {
        'id': 'cand_2',
        'gender': 'male',
        'smoking': False,
        'drinking': False,
        'sleep_schedule': 'early',
        'cleanliness': 1,
        'budget_max': 1000,
        'budget_min': 500,
    }
    
    results = rank_candidates(resident, [cand_pass, cand_fail], config)
    assert len(results) == 1
    assert results[0]['candidate']['id'] == 'cand_1'


def test_roommate_compatibility_score_exact(config):
    # Shared base structure passing all pairwise hard gates
    base_profile = {
        'gender': 'female', 'smoking': False, 'drinking': False,
        'sleep_schedule': 'night_owl', 'cleanliness': 4, 
        'budget_max': 1500, 'budget_min': 1000,
    }
    
    resident_a = {**base_profile, 'social_profile': 'ambivert', 'study_frequency': 4, 'fitness_frequency': 2, 'visitor_frequency': 2, 'gaming_frequency': 4}
    candidate_b = {**base_profile, 'social_profile': 'ambivert', 'study_frequency': 4, 'fitness_frequency': 2, 'visitor_frequency': 3, 'gaming_frequency': 2}
    
    results = rank_candidates(resident_a, [candidate_b], config)
    assert len(results) == 1
    
    # 0.20(1) + 0.25(1) + 0.15(1) + 0.25(2/3) + 0.15(1/3) = 0.81666... (81.666%) -> Rounded == 82.0%
    assert round(results[0]['overall_score'], 0) == 82.0, "The manual design math dictates a rounded score of exactly 82.0%"