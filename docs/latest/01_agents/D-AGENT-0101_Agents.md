---
title: Agents
doc_id: D-AGENT-0101
version: 1.0.0
status: stable
owners: [cohayes]
depends_on: [D-RUNTIME-0001]
includes:
  - D-AGENT-0002  # Agent Action API
  - D-AGENT-0003  # Agent Decision
  - D-AGENT-0004  # Perception and Memory
  - D-AGENT-0005  # Task Selection and Utility
  - D-AGENT-0006  # Scoring and Update Equations
last_updated: 2025-11-11
---

# Dosadi Agents v1

## 1. Overview
This document defines the structure, behavior, and lifecycle of intelligent agents within the Dosadi simulation. Agents are autonomous, resource-dependent organisms that perceive, act, and adapt within the planetary system. They exist at the intersection of physical, psychological, social, and environmental dynamics.

---

## 2. Agent State Model

### 2.1 The Body
Core physiological state variables:

| Variable | Description |
|-----------|--------------|
| **Health** | Represents structural and biological integrity. |
| **Nutrition** | Measures caloric reserves. |
| **Hydration** | Measures available body water. |
| **Stamina** | Reflects physical energy. |
| **Energy** | Reflects cognitive and emotional vitality. |
| **Bladder/Bowel Capacity** | Tracks excretory pressure. |
| **Size (BodyMass)** | Determines baseline metabolic and thermal parameters. |

### 2.1.1 Thermal Model
Humans function optimally between 18–24°C ambient. Outside this range, physiological costs increase.

HeatStressIndex = (EnvTemp - 22) × (1 - SuitThermalResistance) / BodyThermoregulationEfficiency

ColdStressIndex = (22 - EnvTemp) × (1 - SuitThermalResistance) / BodyThermoregulationEfficiency

### 2.1.2 Nutrition and Hydration
CaloricDemand = BaseRate × (1 + 0.5 × ActivityLevel)

WaterDemand = 35ml × BodyMass × (1 + 0.3 × HeatStressIndex)

Deficits impact Health, Stamina, and cognition.

### 2.1.3 Rest and Recovery
RestRequirement = f(ActivityHistory)
Insufficient rest reduces Stamina and Energy recovery.

### 2.1.4 Cognitive Load
Agents possess a daily MentalProcessingBudget (MPB). Overuse leads to Burnout and errors.

---

### 2.2 The Suit
The suit is a prosthetic body-extension. Key parameters:

| Variable | Description |
|-----------|--------------|
| **SuitCaste** | Defines model lineage and profession. |
| **SuitIntegrity (0–1)** | Structural durability. |
| **SuitSeal (0–1)** | Air/moisture containment. |
| **SuitThermalResistance (0–1)** | Protection from heat/cold. |
| **SuitEnvironment** | Resistances to heat, cold, electric, chemical, radiation. |
| **SuitDefense** | Bludgeon/slash/pierce protection. |
| **SuitFit** | Match to wearer size; affects fatigue and comfort. |

Suit attributes modify sensory states: Exposure, Fear, Comfort.

---

### 2.3 Affinities
Base capabilities influencing all drives:

| Attribute | Description |
|------------|-------------|
| Strength | Physical power. |
| Dexterity | Agility and precision. |
| Constitution | Endurance and resistance. |
| Intelligence | Analytical skill and innovation. |
| Willpower | Persistence under stress. |
| Charisma | Social influence. |

Affinities train slowly through use; environment and suits can modify them.

---

### 2.4 Drives
Drives are avenues of investment guiding all agent behavior.

#### Physiological
Apathy, Survival, Grow  
#### Material
Hoard, Maintenance, Innovation  
#### Social – Reputation
Dominance, Subservience, Vengeance, Reputation Preservation, Legacy  
#### Social – Relationships
Conciliation, Paranoia, Destruction  
#### Environmental
Reclamation, Order, Curiosity, Transcendence

Agents allocate investment weights dynamically between drives.

---

### 2.5 Inventory
Categorized by ownership and access:
- **Worn:** suits, armor.
- **Owned:** personal tools, weapons, ration packs.
- **Accessed:** shared guild or faction storage.
- **Purchasable:** available goods in marketplaces.

---

### 2.6 Social Model
Tracks affiliations, promises, and reputations.

| Variable | Description |
|-----------|--------------|
| **FactionAffiliations** | Membership and loyalty values. |
| **Relationships[]** | Trust, hostility, or neutrality toward others. |
| **Rumors[]** | Verified/unverified information with decay timers. |
| **Caste** | Profession and ward of residence. |
| **Promises[]** | Obligations and contracts. |
| **Reputation[]** | Historical record of reliability and achievement. |

---

### 2.7 Perception & Value Model
Perceived value of any entity = firsthand experiences + verified rumors + unverified rumors.  
Cognitive biases weight these inputs.

Biases:
- Authority
- Negativity
- Confirmation
- Novelty

Each archetype has unique bias weighting.

---

## 3. Extended Behavioral Interfaces

### 3.1 Environment Coupling
Environmental inputs directly affect physiology and emotion:

| Variable | Effect |
|-----------|---------|
| **Air Quality** | Low quality reduces Constitution, Energy recovery. |
| **Noise Density** | Increases Stress, reduces Rest efficiency. |
| **Light Exposure** | Affects circadian rhythm, Hope, Apathy. |
| **Radiation** | Causes chronic injury; increases Despair. |

---

### 3.2 Emotional Kernel
Three scalar states mediate behavior:

| State | Raised by | Lowers by |
|--------|------------|-----------|
| **Stress** | Pain, Fear, Noise, Threat | Safety, Rest |
| **Hope** | Drive success, Comfort | Failure, Fatigue |
| **Despair** | Long deprivation, Isolation | Community, Recovery |

Drive reallocation uses:  
NewWeight = OldWeight × (1 + Hope - Stress - Despair)

---

### 3.3 Rumor Ecology
Rumors propagate if payoff > risk. Mutation chance grows with Burnout and social distance.  
Decay occurs exponentially unless reinforced. High Conciliation wards have dense rumor webs; high Paranoia wards have sparse ones.

---

## 4. Suit–Body–Environment Feedback Loop
Physiological processes:
- Heat/cold stress modulated by suit insulation.
- Nutrition and hydration drain from activity, stress, and environment.
- Rest efficiency depends on safety, noise, and comfort.
- Cognitive load adjusts by fatigue and stress.

Feedback between comfort, fear, and exposure defines ongoing homeostasis.

---

## 5. Decision Hierarchy
Three layers govern decisions:

1. **Instinct:** automatic survival actions.  
2. **Strategic:** drive-based planning.  
3. **Reflective:** periodic reallocation of drive investments.

Conflict resolution: priority = DriveWeight × Hope × (1 - Stress).  
Tie → choose least-recently successful drive.

---

## 6. Lifecycle and Succession

| Stage | Description |
|--------|-------------|
| **Birth / Origin** | Natural, cloned, or synthetic creation; sets initial biases. |
| **Aging** | Gradual decay of stamina and repair efficiency. |
| **Death / Termination** | Triggers Reclamation: conversion to water and biomass. |
| **Succession** | Knowledge fragments and rumor inheritance to offspring, apprentices, or scavengers. |

Death and reclamation link economy and ecology.

---

## 7. Archetypes

| Archetype | Caste | Drives | Bias | Techniques | Preferred Environment |
|------------|--------|--------|------|-------------|------------------------|
| Reclaimer | Mid-Low | Reclamation, Order | Negativity | Labor, Barter | Industrial zones |
| Mystic | Mid-Low | Transcendence, Conciliation | Authority | Commune, Influence | Enclosed areas |
| Militia | Mid | Survival, Dominance | Confirmation | Secure, Violence | Guard posts |
| Technician | Mid-High | Maintenance, Innovation | Novelty | Labor, Innovate | Clean zones |
| Noble Clerk | High | Order, Legacy | Authority | Influence, Investigate | Administrative hubs |

---

## 8. Inter-Agent Influence
Nearby agents modify local drive weights dynamically. Proximity to Dominant agents raises Fear; proximity to Hopeful agents raises Integration and Grow.

---

## 9. Key Metrics
- Environmental Exposure Index  
- Emotional Stability Index  
- Rumor Entropy  
- Bias Coherence

---

## 10. Future Hooks
- **Memory Decay Curve:** fading recall of old data.  
- **Personality Archetypes:** initial drive weighting templates.  
- **Learning Rate Differentiation:** individual differences in adaptation.

---

### End of Dosadi Agents v1
