"""Transition connections connecting Outdoor campus nodes with Indoor building entrance nodes."""

CAMPUS_TRANSITIONS = [
    {
        "id": "TRANSITION_FET_RAMP_OUTDOOR_INDOOR",
        "outdoor_node_id": "FET_ACCESSIBLE_ENTRANCE_RAMP",
        "indoor_node_id": "INDOOR_FET_G_RAMP_ENTRY",
        "distance_m": 2.0,
        "estimated_time_sec": 2.0,
        "is_step_free": True,
        "has_stairs": False,
        "has_ramp": False,
        "notes": "Seamless automatic sliding threshold transition from outdoor ramp to indoor Ground Floor lobby."
    },
    {
        "id": "TRANSITION_FET_MAIN_OUTDOOR_INDOOR",
        "outdoor_node_id": "FET_MAIN_ENTRANCE_STEPPED",
        "indoor_node_id": "INDOOR_FET_G_MAIN_ENTRY",
        "distance_m": 2.0,
        "estimated_time_sec": 3.0,
        "is_step_free": False,
        "has_stairs": True,
        "has_ramp": False,
        "notes": "Front stepped threshold transition."
    }
]
