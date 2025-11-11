---
title: Dosadi_Global_Schemas
doc_id: D-RUNTIME-0004
version: 1.0.0
status: stable
owners: [cohayes]
last_updated: 2025-11-11
parent: D-RUNTIME-0001
---
# **Global State & Entity Schemas v1**

Machine‑readable structures for Codex codegen. Types given as JSON‑ish with comments.

---

## 1) IDs
```json
{
  "ID": "string",             // globally unique
  "AgentID": "ID",
  "FactionID": "ID",
  "WardID": "ID",
  "ContractID": "ID",
  "RumorID": "ID",
  "EventID": "ID",
  "CaseID": "ID"
}
```

---

## 2) WorldState
```json
{
  "tick": 0,
  "t_min": 0,
  "t_day": 0,
  "wards": ["WardID", "..."],
  "factions": ["FactionID", "..."],
  "agents": ["AgentID", "..."],
  "events_outbox": ["EventID", "..."],
  "config": { "tick_seconds": 0.6 }
}
```

---

## 3) WardState
```json
{
  "id": "WardID",
  "name": "string",
  "ring": 1,                    // 1..6 inner; 7..20 middle; 21..36 outer
  "sealed_mode": "INNER|MIDDLE|OUTER",
  "env": {
    "temp": 35.0,
    "hum": 1.0,
    "o2": 0.21,
    "rad": 1.0,
    "w_loss": 0.001,
    "S": 10.0
  },
  "infra": {
    "M": 0.8,
    "subsystems": {
      "thermal": "OK|WARN|FAIL",
      "condensers": "OK|WARN|FAIL",
      "scrubbers": "OK|WARN|FAIL",
      "shielding": "OK|WARN|FAIL",
      "lighting": "OK|WARN|FAIL",
      "reclaimers": "OK|WARN|FAIL"
    }
  },
  "stocks": { "water_L": 0.0, "biomass_kg": 0.0, "credits": {} },
  "governor_faction": "FactionID",
  "newsfeed": ["RumorID", "..."]
}
```

---

## 4) FactionState
```json
{
  "id": "FactionID",
  "name": "string",
  "archetype": "FEUDAL|GUILD|MILITARY|CIVIC|CULT|CLERK|RECLAIMER|SMUGGLER",
  "home_ward": "WardID",
  "members": ["AgentID", "..."],
  "assets": { "credits": {}, "water_L": 0.0, "materials": {}, "suits": {} },
  "metrics": {
    "gov": { "L": 0.6, "C": 0.2 },
    "econ": { "R": 0.5, "X": {} },
    "law": { "RR": 0.7, "RI": 0.1, "E": 600, "AC": 0.7 }
  },
  "reputation": { "by_audience": { "FactionID": -0.2 } },
  "contracts_active": ["ContractID", "..."],
  "rumor_bank": { "verified": ["RumorID"], "unverified": ["RumorID"] },
  "roles": { "lawyers": ["AgentID"], "stewards": ["AgentID"], "captains": ["AgentID"] }
}
```

---

## 5) AgentState
```json
{
  "id": "AgentID",
  "name": "string",
  "faction": "FactionID",
  "ward": "WardID",
  "body": {
    "H": 100.0, "W": 3.0, "N": 2500.0, "Sta": 80.0, "ME": 80.0,
    "Blad": 0.2, "Bow": 0.1, "chronic": []
  },
  "suit": {
    "model": "string",
    "caste": "ELITE|HIGH|MID|LOW|SCAV",
    "I": 0.9, "Seal": 0.9, "Comf": 0.6,
    "Def": { "blunt": 0.3, "slash": 0.4, "pierce": 0.5 },
    "ratings": { "heat": 0.8, "chem": 0.6, "rad": 0.5 }
  },
  "affinities": {
    "STR": 0.0, "DEX": 0.0, "CON": 0.0, "INT": 0.0, "WILL": 0.0, "CHA": 0.0
  },
  "inventory": {
    "worn": ["ItemID"], "owned": ["ItemID"], "access": ["FacilityID"], "credits": {}
  },
  "social": {
    "rep": { "by_faction": { "FactionID": 0.0 } },
    "loyalty": { "to_faction": { "FactionID": 0.0 } },
    "relationships": { "AgentID": 0.1 },
    "caste": { "profession": "string", "ward": "WardID" }
  },
  "memory": {
    "events": ["RumorID"],
    "beliefs": { "RumorID": { "Cred": 0.5, "B": 0.4, "Sal": 0.3 } },
    "memes": { "key": 0.1 }
  },
  "drives": { "weights": { "Survival": 0.6, "Hoard": 0.2, "Advancement": 0.2 } },
  "techniques": ["Barter","Observe","Labor"]
}
```

---

## 6) Contract
```json
{
  "id": "ContractID",
  "parties": ["AgentOrFactionID","..."],
  "type": "MANDATE|TRADE|SERVICE|ALLIANCE|TRUCE|LOYALTY_OATH|LICENSE|SURETY",
  "obligations": [{ "what": "string", "qty": 0.0, "quality": "spec", "loc": "WardID", "due": 0 }],
  "consideration": [{ "asset": "WATER|CREDITS|PROTECTION|STATUS|ACCESS", "amt": 0.0 }],
  "conditions": { "start": 0, "end": 0, "contingencies": [] },
  "jurisdiction": "ROYAL|FEUDAL|GUILD|CIVIC|CULT|MIXED",
  "record_medium": "WITNESSED|TOKENIZED|HYBRID",
  "witnesses": ["AgentID"],
  "penalties": {
    "restorative": { "make_whole": true, "surcharge": 0.0, "service_hours": 0 },
    "retributive": { "fine": 0.0, "seizure": true, "imprison": false, "execution": false, "outlawry": false }
  },
  "reputation_impacts": { "on_fulfill": 0.05, "on_breach": -0.2, "on_renegotiate": -0.02 },
  "audit_hooks": { "clerks": ["AgentID"], "interval": 6000, "channels": ["WardID"] },
  "token": { "present": false, "escrow_proxy": null },
  "status": "PENDING|ACTIVE|FULFILLED|LATE|DISPUTED|BREACHED|SETTLED|CLOSED",
  "timestamps": { "created": 0, "activated": 0, "last_audit": 0, "closed": 0 }
}
```

---

## 7) Rumor
```json
{
  "id": "RumorID",
  "topic": "PERSON|FACTION|PLACE|THING|CONTRACT|EVENT",
  "subject_id": "ID",
  "content": "string",
  "source": { "type": "WITNESS|HEARSAY|PROPAGANDA", "by": "AgentID|FactionID|null" },
  "cred": 0.5,
  "salience": 0.3,
  "belief_updates": [{ "agent": "AgentID", "delta": 0.1 }],
  "visibility": { "firsthand": true, "radius": 2 },
  "timestamps": { "created": 0, "last_propagated": 0 }
}
```

---

## 8) Event (Bus Message)
```json
{
  "id": "EventID",
  "type": "BarrelCascadeIssued|ContractActivated|RumorEmitted|HeatSurge|SuccessionResolved|EnforcementExecuted|PowerBrownout|CondensationFailure|DustIngress",
  "ward": "WardID|null",
  "actors": ["AgentID|FactionID"],
  "payload": {},
  "emitter": "System|FactionID|AgentID",
  "tick": 0,
  "ttl": 300
}
```

---

## 9) ArbiterCase (Dispute)
```json
{
  "id": "CaseID",
  "contract": "ContractID",
  "arbiter_tier": "JUNIOR|CIRCUIT|HIGH",
  "parties": ["AgentOrFactionID"],
  "evidence": ["RumorID","DocumentID"],
  "proceedings": [{ "tick": 0, "action": "HEARING|INSPECTION|MEDIATION" }],
  "outcome": "RESTORATIVE|RETRIBUTIVE|NONE",
  "orders": { "make_whole": {}, "penalties": {}, "monitoring": { "interval": 6000 } }
}
```

---

## 10) InventoryItem & Facilities (Minimal)
```json
{
  "Item": {
    "id": "ItemID",
    "kind": "TOOL|WEAPON|RATIONS|MATERIAL|TOKEN",
    "props": { "durability": 1.0, "effects": {} }
  },
  "Facility": {
    "id": "FacilityID",
    "kind": "RECLAIMER|KITCHEN|WORKSHOP|CLINIC|SAFEHOUSE",
    "ward": "WardID",
    "access_rules": { "factions": ["FactionID"], "fee": 0.0 }
  }
}
```
