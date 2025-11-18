---
title: Agent_Core_Schema_v0
doc_id: D-AGENT-0001
version: 0.1.0
status: draft
owners: [cohayes]
last_updated: 2025-11-18
depends_on:
  - D-WORLD-0003  # Ward_Branch_Hierarchies
  - D-ECON-0001  # Ward_Resource_and_Water_Economy
  - D-CIV-0000    # Civic_Microdynamics_Index
  - D-CIV-0001    # Civic_Microdynamics_Soup_Kitchens_and_Bunkhouses
  - D-CIV-0002    # Civic_Microdynamics_Clinics_and_Triage_Halls
  - D-CIV-0006    # Civic_Microdynamics_Entertainment_and_Vice_Halls
  - D-INFO-0002   # Espionage_Branch
  - D-INFO-0003   # Information_Flows_and_Report_Credibility
---

# Agent Core Schema v0

> This document defines the **minimal agent representation** for early Dosadi simulations:
> - Focused on civic microdynamics (soup kitchens, bunkhouses, clinics, vice halls).
> - Simple enough for immediate implementation.
> - Structured for upgrade into richer tiers (skills, advanced learning, detailed social graphs).

This is **Agent Tier 1** with some Tier 2 hooks:

- Tier 1: background population, simple heuristics, light memory.
- Tier 2/3 fields are hinted but not fully modeled here.

---

## 1. Design Goals

Agent v0 should:

- Be **cheap to simulate in bulk**.
- Still feel like:
  - A body trying to survive.
  - With drives and loyalties.
  - Making noisy, local decisions based on partial information.

Core pillars:

1. **Skills as point-buy** (stubbed here, expandable later).
2. **Loyalty as long-term self-interest** (drives over time under factions).
3. **Perception as vision-cone-ish / local** (no global knowledge).
4. **Elements of learning** (preferences and beliefs update via experience).

---

## 2. Top-Level Schema Overview

High-level shape (conceptual JSON):

```json
{
  "agent_id": "A_W21_001234",
  "name_label": "optional_debug_name",
  "tier": 1,

  "body": { },
  "suit": { },
  "inventory": { },

  "drives": { },
  "stress": 0.3,

  "traits": { },
  "skills": { },

  "social": { },
  "beliefs": { },
  "memory": { },

  "state": { }
}
```

Sections below define each sub-object.

---

## 3. Body & Survival State

Minimum needed for civic loops, clinics, and body reclamation.

```json
"body": {
  "health": 0.85,
  "injury_level": 0.1,
  "disease_load": 0.0,

  "hydration": 0.5,
  "nutrition": 0.6,
  "sleep_debt": 0.2,

  "temperature_stress": 0.0,
  "fatigue": 0.3,

  "alive": true,
  "death_cause": null
}
```

Notes:

- `SURVIVAL` drive is largely a function of:
  - low hydration, low nutrition, high injury, high disease_load, high sleep_debt.

---

## 4. Suit & Gear Envelope

Enough to matter for movement, work, and risk.

```json
"suit": {
  "suit_type": "mid",
  "suit_integrity": 0.8,
  "water_recovery_rate": 0.4,
  "protection_env": 0.5,
  "protection_physical": 0.2
},
"inventory": {
  "credits_wcr": 12.5,
  "credits_kcr": 0.0,
  "ration_chits": 3,
  "water_liters": 1.2,

  "id_token": "W21_RES_0087",
  "weapon_tag": null,
  "tool_tag": "tool_basic_maint",

  "key_items": []
}
```

Notes:

- For early civic sims, we can treat weapon/tool tags symbolically (affecting risk outcomes).
- Suit values affect:
  - Which jobs they can take.
  - How dangerous certain zones are.

---

## 5. Drives & Stress

Core drive stack + stress as a modifier.

```json
"drives": {
  "SURVIVAL": { "value": 0.4, "weight": 1.0 },
  "SAFETY":   { "value": 0.2, "weight": 0.9 },
  "BELONG":   { "value": 0.6, "weight": 0.8 },
  "STATUS":   { "value": 0.3, "weight": 1.1 },
  "CONTROL":  { "value": 0.3, "weight": 1.0 },
  "NOVELTY":  { "value": 0.5, "weight": 1.0 },
  "MORAL":    { "value": 0.1, "weight": 0.9 }
},
"stress": 0.3
```

- `value` ∈ [0, 1]: unmet need (0 = satisfied, 1 = desperate).
- `weight`: personality/temperament; how strongly that drive influences choices.

**Urgency at decision time** (conceptual):

```text
urgency(D) = drives[D].value * drives[D].weight * f(stress)
```

where `f(stress)` is a simple function like `1 + stress`.

---

## 6. Traits & Skills (Point-Buy Stubs)

### 6.1 Traits (Personality)

Light scalar biases we can use in heuristics:

```json
"traits": {
  "risk_tolerance": 0.5,
  "conformity": 0.6,
  "aggression": 0.4,
  "empathy": 0.5,
  "curiosity": 0.6
}
```

These combine with drives to tilt decisions:
- High risk_tolerance + high NOVELTY → more vice, more espionage opportunities.
- High conformity + high SAFETY → preference for “legitimized” facilities/factions.

### 6.2 Skills (Point-Buy)

Minimal early set, expandable:

```json
"skills": {
  "labor_general": 1,
  "maintenance": 0,
  "scavenging": 1,
  "combat_melee": 0,
  "combat_ranged": 0,
  "negotiation": 0,
  "espionage_ops": 0,
  "medical_basic": 0,
  "admin_clerical": 0
}
```

- Integers as point-buy/proficiency (0 = untrained).
- v0 use:
  - Affect job eligibility and outcomes (e.g., work efficiency, fight odds, informant value).

---

## 7. Social & Faction Identity

### 7.1 Identity & Roles

```json
"social": {
  "home_ward": "W21",

  "caste_band": "low",
  "job_role": "day_laborer",

  "primary_faction": "guild_scrap",
  "secondary_faction": null,

  "loyalty": {
    "lord_W21": 0.4,
    "guild_scrap": 0.7,
    "gang_low": 0.1
  },

  "reputation": {
    "lawful": 0.3,
    "reliable": 0.6,
    "violent": 0.2,
    "traitor": 0.0
  }
}
```

Notes:

- Loyalty values are *outputs* of long-run drive satisfaction under each faction, not arbitrary morals.
- Reputation can be partly local (by ward/faction) in later tiers; v0 can keep one set.

---

## 8. Beliefs & Memory (Lightweight)

### 8.1 Beliefs about Facilities / Systems

Very simple early structure:

```json
"beliefs": {
  "facility_attitudes": {
    "W21_KITCHEN_01": {
      "safety": 0.6,
      "fairness": 0.4,
      "queue_length": 0.7
    },
    "W21_VICE_DRINK_01": {
      "safety": 0.3,
      "fun": 0.8,
      "price": 0.5
    }
  },
  "faction_attitudes": {
    "lord_W21": {
      "justice": 0.4,
      "strength": 0.7
    },
    "gang_low": {
      "trustworthy": 0.3,
      "dangerous": 0.8
    }
  }
}
```

These values:

- Start from ward defaults.
- Drift as the agent experiences queues, raids, court decisions, vice nights.

### 8.2 Memory (Episodic Shards)

Keep a small ring buffer of salient events:

```json
"memory": {
  "recent_events": [
    {
      "type": "KITCHEN_VISIT",
      "facility_id": "W21_KITCHEN_01",
      "tick": 128300,
      "outcome": "FED",
      "queue_time": 0.8,
      "felt_fair": false
    },
    {
      "type": "VICE_VISIT",
      "facility_id": "W21_VICE_DRINK_01",
      "tick": 128500,
      "outcome": "RELIEF",
      "incident": "BAR_FIGHT_NEARBY"
    }
  ],
  "last_slept_at": "W21_BUNK_03",
  "last_slept_tick": 128200
}
```

These memories feed:

- Drive updates (stress relief or increase).
- Belief updates (facility_attitudes adjustments).

---

## 9. Operational State (What They’re Doing Now)

Current location, activity, and simple flags.

```json
"state": {
  "location_id": "W21_STREET_05",
  "current_action": "MOVE_TO_FACILITY",
  "current_target_facility": "W21_KITCHEN_01",

  "on_duty": false,
  "arrested": false,
  "incapacitated": false,

  "tick_last_decision": 128290
}
```

This block tells the sim loop how to interpret and move the agent each step.

---

## 10. Minimal Example Agent v0

Putting it together for a **low-caste day laborer** in Ward 21:

```json
{
  "agent_id": "A_W21_000137",
  "name_label": "W21_daylabor_137",
  "tier": 1,

  "body": {
    "health": 0.7,
    "injury_level": 0.1,
    "disease_load": 0.0,
    "hydration": 0.4,
    "nutrition": 0.5,
    "sleep_debt": 0.3,
    "temperature_stress": 0.1,
    "fatigue": 0.4,
    "alive": true,
    "death_cause": null
  },

  "suit": {
    "suit_type": "scrap",
    "suit_integrity": 0.5,
    "water_recovery_rate": 0.2,
    "protection_env": 0.2,
    "protection_physical": 0.1
  },
  "inventory": {
    "credits_wcr": 4.0,
    "credits_kcr": 0.0,
    "ration_chits": 1,
    "water_liters": 0.5,
    "id_token": "W21_RES_3127",
    "weapon_tag": null,
    "tool_tag": null,
    "key_items": []
  },

  "drives": {
    "SURVIVAL": { "value": 0.6, "weight": 1.0 },
    "SAFETY":   { "value": 0.3, "weight": 0.9 },
    "BELONG":   { "value": 0.5, "weight": 0.8 },
    "STATUS":   { "value": 0.2, "weight": 1.1 },
    "CONTROL":  { "value": 0.3, "weight": 1.0 },
    "NOVELTY":  { "value": 0.4, "weight": 1.0 },
    "MORAL":    { "value": 0.1, "weight": 0.9 }
  },
  "stress": 0.4,

  "traits": {
    "risk_tolerance": 0.4,
    "conformity": 0.6,
    "aggression": 0.3,
    "empathy": 0.5,
    "curiosity": 0.5
  },

  "skills": {
    "labor_general": 1,
    "maintenance": 0,
    "scavenging": 1,
    "combat_melee": 0,
    "combat_ranged": 0,
    "negotiation": 0,
    "espionage_ops": 0,
    "medical_basic": 0,
    "admin_clerical": 0
  },

  "social": {
    "home_ward": "W21",
    "caste_band": "low",
    "job_role": "day_laborer",
    "primary_faction": "guild_scrap",
    "secondary_faction": null,
    "loyalty": {
      "lord_W21": 0.3,
      "guild_scrap": 0.6
    },
    "reputation": {
      "lawful": 0.5,
      "reliable": 0.6,
      "violent": 0.2,
      "traitor": 0.0
    }
  },

  "beliefs": {
    "facility_attitudes": {
      "W21_KITCHEN_01": { "safety": 0.6, "fairness": 0.4, "queue_length": 0.7 },
      "W21_VICE_DRINK_01": { "safety": 0.4, "fun": 0.7, "price": 0.4 }
    },
    "faction_attitudes": {
      "lord_W21": { "justice": 0.4, "strength": 0.7 },
      "guild_scrap": { "justice": 0.5, "strength": 0.5 }
    }
  },

  "memory": {
    "recent_events": [],
    "last_slept_at": "W21_BUNK_02",
    "last_slept_tick": 128200
  },

  "state": {
    "location_id": "W21_STREET_03",
    "current_action": "IDLE",
    "current_target_facility": null,
    "on_duty": false,
    "arrested": false,
    "incapacitated": false,
    "tick_last_decision": 128290
  }
}
```

---
