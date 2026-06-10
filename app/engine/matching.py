def _get(obj, key, default=None):
    """Helper to support both dicts and objects for flexible matching."""
    if isinstance(obj, dict):
        val = obj.get(key, default)
    else:
        val = getattr(obj, key, default)
    return default if val is None else val


def recommend_hostels(resident, hostels, config) -> list[dict]:
    """
    Stage 1: Hard Filtering on gender, smoking, drinking, veg_only, age bands, and budget.
    Stage 2: Soft Ranking using PriceFit, LocationFit, and AmenityFit indices.
    Downstream: Premium and verification boosts.
    """
    results = []
    
    r_gender = _get(resident, 'gender')
    r_smoking = _get(resident, 'smoking')
    r_drinking = _get(resident, 'drinking')
    r_veg = _get(resident, 'vegetarian')
    r_age = _get(resident, 'age')
    r_bmax = _get(resident, 'budget_max', float('inf'))
    r_bmin = _get(resident, 'budget_min', 0.0)
    r_loc = str(_get(resident, 'location', '')).lower()
    r_amenities = set(_get(resident, 'amenities', []))
    
    min_allowed_budget = r_bmin - config.BUDGET_SLACK
    
    for hostel in hostels:
        # 1. Hard Filtering
        h_gender_policy = _get(hostel, 'gender_policy')
        if h_gender_policy and h_gender_policy != 'any' and h_gender_policy != r_gender:
            continue
            
        if not _get(hostel, 'smoking_allowed', True) and r_smoking:
            continue
            
        if not _get(hostel, 'drinking_allowed', True) and r_drinking:
            continue
            
        if _get(hostel, 'veg_only', False) and not r_veg:
            continue
            
        if r_age is not None:
            if r_age < _get(hostel, 'age_min', 0) or r_age > _get(hostel, 'age_max', 200):
                continue
                
        rooms_raw = _get(hostel, 'rooms', [])
        # Normalize rooms to an iterable list. Some hostels may have a single room
        # represented as a dict or invalid/non-iterable types; handle gracefully.
        if isinstance(rooms_raw, dict):
            rooms = [rooms_raw]
        elif isinstance(rooms_raw, (list, tuple, set)):
            rooms = list(rooms_raw)
        else:
            rooms = []

        valid_rooms = [
            r for r in rooms
            if min_allowed_budget <= _get(r, 'price', 0.0) <= r_bmax
        ]
        
        if not valid_rooms:
            continue
            
        # 2. Soft Ranking
        best_price = min(_get(r, 'price', 0.0) for r in valid_rooms)
        if r_bmax == float('inf'):
            price_fit = 1.0
        elif r_bmax > min_allowed_budget:
            price_fit = 1.0 - ((best_price - min_allowed_budget) / (r_bmax - min_allowed_budget))
        else:
            price_fit = 1.0
            
        h_loc = str(_get(hostel, 'location', '')).lower()
        location_fit = 1.0 if (r_loc and r_loc == h_loc) else 0.0
        
        h_amenities_raw = _get(hostel, 'amenities', [])
        h_amenities = set(h_amenities_raw if isinstance(h_amenities_raw, (list, tuple, set)) else [])
        union_amenities = r_amenities | h_amenities
        amenity_fit = (len(r_amenities & h_amenities) / len(union_amenities)) if union_amenities else 0.0
            
        base_score = (
            config.W_PRICE * price_fit +
            config.W_LOCATION * location_fit +
            config.W_AMENITY * amenity_fit
        )
        
        # 3. Downstream Modifiers
        if _get(hostel, 'tier') == 'PREMIUM':
            base_score = min(1.0, base_score * config.PREMIUM_BOOST)
            
        if _get(hostel, 'verified'):
            base_score = min(1.0, base_score + config.VERIFIED_BOOST)
            
        results.append({
            'hostel_id': _get(hostel, 'id'),
            'final_score': base_score,
            'price_fit': price_fit,
            'location_fit': location_fit,
            'amenity_fit': amenity_fit,
            'tier': _get(hostel, 'tier'),
            'verified': _get(hostel, 'verified', False)
        })
        
    return sorted(results, key=lambda x: x['final_score'], reverse=True)


def rank_candidates(resident_x, candidates, config) -> list[dict]:
    """
    Pairwise Hard Gates: filter out mismatched strict parameters and disjoint budgets.
    Soft Scoring: aggregated 0-100 score on lifestyle frequencies and social profile.
    """
    results = []
    
    rx_gender = _get(resident_x, 'gender')
    rx_smoking = _get(resident_x, 'smoking')
    rx_drinking = _get(resident_x, 'drinking')
    rx_sleep = _get(resident_x, 'sleep_schedule')
    rx_clean = _get(resident_x, 'cleanliness', 1)
    rx_bmax = _get(resident_x, 'budget_max', float('inf'))
    rx_bmin = _get(resident_x, 'budget_min', 0.0)
    rx_social = _get(resident_x, 'social_profile')
    
    def ordinal_score(cand, attr, levels=4):
        a = _get(resident_x, attr, 1)
        b = _get(cand, attr, 1)
        return 1.0 - (abs(a - b) / float(levels - 1))

    for cand in candidates:
        # Pairwise Hard Gates
        if _get(cand, 'gender') != rx_gender:
            continue
        if _get(cand, 'smoking') != rx_smoking:
            continue
        if _get(cand, 'drinking') != rx_drinking:
            continue
        if _get(cand, 'sleep_schedule') != rx_sleep:
            continue
            
        if abs(_get(cand, 'cleanliness', 1) - rx_clean) > config.CLEAN_BAND:
            continue
            
        c_bmax = _get(cand, 'budget_max', float('inf'))
        c_bmin = _get(cand, 'budget_min', 0.0)
        
        # Budget windows overlap condition
        if max(rx_bmin, c_bmin) > min(rx_bmax, c_bmax):
            continue
            
        # Soft Scoring
        social_score = 1.0 if _get(cand, 'social_profile') == rx_social else 0.0
        
        gaming_score = ordinal_score(cand, 'gaming_frequency')
        study_score = ordinal_score(cand, 'study_frequency')
        fitness_score = ordinal_score(cand, 'fitness_frequency')
        visitor_score = ordinal_score(cand, 'visitor_frequency')
        
        overall_score = (
            (social_score * 0.20) +
            (gaming_score * 0.15) +
            (study_score * 0.25) +
            (fitness_score * 0.15) +
            (visitor_score * 0.25)
        ) * 100.0
        
        results.append({
            'candidate_id': _get(cand, 'id'),
            'overall_score': overall_score,
            'breakdown': {
                'social': social_score,
                'gaming': gaming_score,
                'study': study_score,
                'fitness': fitness_score,
                'visitors': visitor_score
            }
        })
        
    return sorted(results, key=lambda x: x['overall_score'], reverse=True)