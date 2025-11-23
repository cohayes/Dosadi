---
title: AI_Policy_Profiles
doc_id: D-RUNTIME-0105
version: 1.0.0
status: draft
owners: [cohayes]
last_updated: 2025-11-23
depends_on:
  - D-RUNTIME-0001        # Simulation_Timebase
  - D-RUNTIME-0102        # Campaign_Milestone_and_Crisis_Triggers
  - D-RUNTIME-0103        # Scenario_Framing_and_Win_Loss_Conditions
  - D-RUNTIME-0104        # Scenario_Packaging_and_Metadata
  - D-WORLD-0002          # Ward_Attribute_Schema
  - D-WORLD-0003          # Ward_Evolution_and_Specialization_Dynamics
  - D-IND-0003            # Guild_Influence_and_Bargaining_Power
  - D-ECON-0001           # Ward_Resource_and_Water_Economy
  - D-MIL-0001            # Force_Types_and_Infrastructure
  - D-MIL-0002            # Garrison_Structure_and_Deployment_Zones
  - D-MIL-0003            # Response_Cadences_and_Alert_Levels
  - D-MIL-0102            # Officer_Doctrines_and_Patronage_Networks
  - D-MIL-0103            # Command_Rotations_and_Purge_Cycles
  - D-MIL-0104            # Checkpoint_and_Patrol_Behavior_Profiles
  - D-MIL-0105            # Garrison_Morale_and_Fracture_Risk
  - D-MIL-0106            # Field_Justice_and_In-Unit_Discipline
  - D-MIL-0107            # Special_Detachments_and_Commissar_Cadres
  - D-MIL-0108            # Counterintelligence_and_Infiltration_Risk
  - D-INFO-0001           # Telemetry_and_Audit_Infrastructure
  - D-INFO-0002           # Espionage_Branch
  - D-INFO-0003           # Information_Flows_and_Report_Credibility
  - D-INFO-0006           # Rumor_Networks_and_Informal_Channels
  - D-INFO-0009           # Counterintelligence_Tradecraft_and_Signatures
  - D-INFO-0014           # Security_Dashboards_and_Threat_Surfaces
  - D-INFO-0015           # Operator_Alerts_and_Escalation_Prompts
---

# 02_runtime · AI Policy Profiles (D-RUNTIME-0105)

## 1. Purpose

This document defines a standard **AI policy profile** layer for major actors in
the Dosadi system (duke_house, Espionage Branch, MIL, guilds, cartels, bishops,
etc.).

The goal is to:

- Separate **who** an actor is (role, position, structural powers) from
  **how** they tend to behave (preferences, risk tolerance, paranoia).
- Provide a compact, data-driven way to configure:
  - responses to alerts and escalation prompts,
  - choices between crackdowns vs restraint,
  - posture decisions (CI, MIL, LAW, guild collective action).
- Allow multiple runs of the same scenario to diverge dramatically simply by
  swapping **policy profiles**, without changing the world or scenario config.

This layer is intended to guide both:

- simple scripted behavior, and
- more advanced policies / RL controllers that want an initial “personality”
  structure to align with.

---

## 2. Conceptual Overview

We distinguish:

- **RoleConfig** (D-RUNTIME-0103):
  - who the actor is in game terms:
    - `actor_type`, visibility, control levers.

- **AI policy profile** (this document):
  - how that actor:
    - evaluates trade-offs,
    - reacts to pressure,
    - chooses between available actions.

- **Decision hooks**:
  - specific points where the simulation calls into the policy profile:
    - choose CI stance,
    - accept or decline a crackdown,
    - escalate or ignore a threat,
    - trigger guild strikes or stand down.

An AI policy profile does not directly encode low-level mechanics; it provides
**weights, thresholds, and simple heuristics** that downstream code applies to
particular decision problems.

---

## 3. AI Policy Profile Schema

We define a generic `AiPolicyProfile` schema that can be specialized per role:

```yaml
AiPolicyProfile:
  id: string
  role: string                         # "duke_house", "espionage_branch", "mil_command", "guild_faction", "cartel", "bishop_guild"
  label: string
  description: string

  # Core value weights (0–1, not necessarily normalized)
  weight_survival: float               # regime/faction survival and control
  weight_legitimacy: float             # cares about perceived fairness and trust
  weight_order: float                  # cares about low unrest/violence
  weight_control: float                # favors centralized, coercive tools
  weight_economy: float                # cares about stable production and trade
  weight_secrecy: float                # cares about information control / OpSec

  # Temperament
  risk_tolerance: float                # 0–1: willingness to take actions that raise stress/repression
  paranoia: float                      # 0–1: tendency to see infiltration/plots
  patience: float                      # 0–1: willingness to delay decisive moves

  # Thresholds and biases
  crackdown_stress_threshold: float    # stress level where regime is willing to pivot to Hard Crackdown
  fragmentation_tolerance: float       # how much de facto decentralization is tolerated
  purge_tolerance: float               # comfort with frequent or large purges
  soft_power_preference: float         # preference for LAW/CI tools vs open MIL force
  negotiation_preference: float        # preference for bargaining, guild deals, settlement

  # Stance biases (normalized or relative weights)
  ci_stance_bias:
    cautious: float
    balanced: float
    aggressive: float

  mil_posture_bias:
    low_alert: float
    normal_alert: float
    high_alert: float

  law_intensity_bias:
    procedural: float
    expedited: float
    draconian: float

  # Optional role-specific extra fields (non-normative)
  extra: object
```

The engine is not required to use every field in every decision. Profiles are
**descriptive**; decision hooks select the relevant subset.

---

## 4. Decision Hooks

A policy profile is only meaningful where it touches the simulation. We define a
set of **decision hooks** that runtime code can implement.

### 4.1 CI Stance Selection (Espionage / Security roles)

Hook:

```python
def choose_ci_stance(
    profile: AiPolicyProfile,
    stress: float,
    infiltration_risk: float,
    legitimacy: float,
) -> Literal["cautious", "balanced", "aggressive"]:
    ...
```

Guidelines:

- High `paranoia` + high `weight_control`:
  - prefers `"aggressive"` at lower infiltration thresholds.
- High `weight_legitimacy` + low `risk_tolerance`:
  - prefers `"cautious"` until stress is very high.
- Moderates use `"balanced"` most of the time, tilting under extremes.

This hook is already prototyped in Quiet Season; this document formalizes the
inputs and expected outputs.

---

### 4.2 Campaign Path Decisions (Duke / Central Regime)

Hook:

```python
class DukalDecision(Enum):
    ACCEPT_CRACKDOWN = "accept_crackdown"
    ACCEPT_FRAGMENTATION = "accept_fragmentation"
    SEEK_RESTRAINT = "seek_restraint"

def decide_campaign_path(
    profile: AiPolicyProfile,
    stress: float,
    fragmentation: float,
    legitimacy: float,
) -> DukalDecision:
    ...
```

Guidelines:

- High `weight_control`, high `paranoia`:
  - favor `ACCEPT_CRACKDOWN` once stress passes
    `crackdown_stress_threshold`.
- High `weight_legitimacy`, high `patience`:
  - favor `SEEK_RESTRAINT` even at moderate/high stress.
- High `weight_economy`, high `negotiation_preference`:
  - may tolerate `ACCEPT_FRAGMENTATION` to preserve trade and avoid civil war.

This hook influences which crisis triggers (D-RUNTIME-0102) are allowed to
fire, or how their thresholds are tuned.

---

### 4.3 Alert and Escalation Handling

Hook:

```python
def handle_security_alert(
    profile: AiPolicyProfile,
    alert: SecurityAlert,
) -> Literal["ignore", "monitor", "investigate", "sting", "purge_recommendation"]:
    ...
```

and/or

```python
def handle_escalation_prompt(
    profile: AiPolicyProfile,
    prompt: EscalationPrompt,
) -> bool:  # accept or decline
    ...
```

Guidelines:

- High `risk_tolerance` + high `paranoia`:
  - more likely to escalate alerts towards `sting` or `purge_recommendation`.
- High `weight_legitimacy` and `soft_power_preference`:
  - more likely to start with `monitor` or `investigate`.
- Low `patience`:
  - more likely to accept escalation prompts quickly.

Initially, this can be coded as simple **decision tables** driven by profile
weights and alert severity.

---

### 4.4 Guild and Cartel Collective Action

Hook (guild/cartel):

```python
class CollectiveAction(Enum):
    NONE = "none"
    STRIKE = "strike"
    SLOWDOWN = "slowdown"
    SABOTAGE = "sabotage"
    ESCALATE_TO_VIOLENCE = "escalate_to_violence"

def choose_collective_action(
    profile: AiPolicyProfile,
    repression: float,
    contract_pressure: float,
    black_market_margin: float,
    security_threat: float,
) -> CollectiveAction:
    ...
```

Guidelines:

- `guild_shadow_profit`:
  - prioritizes `SLOWDOWN` and quiet `SABOTAGE` over open strikes.
- `guild_civic_defender` (if defined later):
  - may favor `STRIKE` over `SABOTAGE` to preserve legitimacy.
- `cartel_expansionist`:
  - more willing to `ESCALATE_TO_VIOLENCE` at lower thresholds.

These choices feed directly into IND and ECON dynamics (charter stress,
black-market intensity, etc.).

---

## 5. Canonical Profiles (Initial Palette)

We define a non-exhaustive set of **named profiles** for core roles. These act
as defaults for scenarios and as reference points for tuning.

### 5.1 Duke House

- `duke_paranoid_hardline`
  - Very high `weight_control`, high `paranoia`, low `weight_legitimacy`.
  - Low `fragmentation_tolerance`, low `patience`.
  - `crackdown_stress_threshold`: low to moderate.
  - CI stance bias: leans toward `"aggressive"` under moderate stress.
  - Likely to:
    - accept crackdowns early,
    - tolerate heavy repression and purges.

- `duke_pragmatic_balancer`
  - Balanced weights across `survival`, `order`, `legitimacy`, `economy`.
  - Moderate `risk_tolerance`, moderate `paranoia`, higher `patience`.
  - `crackdown_stress_threshold`: higher.
  - CI stance bias: `"balanced"` most of the time, `cautious` early, `aggressive` only at high stress.
  - Likely to:
    - seek restraint longer,
    - bargain with guilds/bishops to avoid outright collapse.

### 5.2 Espionage Branch

- `espionage_cautious_analyst`
  - High `weight_legitimacy`, `weight_order`, moderate `weight_survival`.
  - Low `risk_tolerance`, moderate `paranoia`, high `patience`.
  - Prefers:
    - `"cautious"` CI stance until stress is very high,
    - `monitor` and `investigate` actions over `sting`/`purge`.
  - Good for:
    - “slow boil” trajectories where unrest and infiltration can creep up.

- `espionage_proactive_hawk`
  - High `weight_survival`, `weight_control`, high `paranoia`.
  - Higher `risk_tolerance`, lower `patience`.
  - Prefers:
    - `"balanced"` or `"aggressive"` CI stance as soon as infiltration rises,
    - more `sting` and occasional `purge_recommendation`.
  - Good for:
    - brittle but tightly controlled states.

### 5.3 MIL Command

- `mil_professional_order`
  - High `weight_order`, moderate `weight_legitimacy`, moderate `weight_survival`.
  - Low `purge_tolerance`, moderate `risk_tolerance`.
  - MIL posture bias: `normal_alert` most of the time, `high_alert` when threat is clear.
  - Hesitant to:
    - engage in arbitrary purges or collective punishment.

- `mil_zealot_crusader`
  - High `weight_survival`, very high `weight_control`, low `weight_legitimacy`.
  - High `risk_tolerance`, moderate to high `paranoia`.
  - MIL posture bias: comfortable at `high_alert`, quick to escalate.
  - Likely to:
    - support harsh crackdowns and collaborate with CI purges.

### 5.4 Guild and Cartel

- `guild_shadow_profit`
  - High `weight_economy`, high `weight_secrecy`, moderate `negotiation_preference`.
  - Low `risk_tolerance` for open conflict.
  - Prefers:
    - `SLOWDOWN`, `SABOTAGE`, `NONE` as actions,
    - avoid `ESCALATE_TO_VIOLENCE` unless regime is already weak.

- `cartel_expansionist`
  - High `weight_survival` (for the cartel), high `weight_economy`, low `weight_legitimacy`.
  - Higher `risk_tolerance`, moderate `paranoia`.
  - More willing to:
    - `SABOTAGE`, `ESCALATE_TO_VIOLENCE` when repression grows or rivals appear.

---

## 6. Integration with Scenarios

From D-RUNTIME-0103, `RoleConfig` includes an `ai_personality_ref` (or similar).
We interpret that as a reference to an `AiPolicyProfile.id`.

Per scenario:

- Each role can specify:
  - controlled by player (`ai_or_player: "player"`) → ignore profile or use only
    as UI flavor.
  - controlled by AI (`ai_or_player: "ai"`) → use profile as primary decision
    driver at relevant hooks.

Examples:

```yaml
role_configs:
  - role_id: "espionage_cell"
    actor_type: "espionage_branch"
    visibility_profile: "espionage_view"
    control_profile: "espionage_control"
    ai_or_player: "ai"
    ai_personality_ref: "espionage_cautious_analyst"

  - role_id: "ducal_cabinet"
    actor_type: "duke_house"
    visibility_profile: "ducal_view"
    control_profile: "ducal_control"
    ai_or_player: "ai"
    ai_personality_ref: "duke_paranoid_hardline"
```

Scenarios can be designed as **“personality experiments”**:

- same world + pressures,
- different policy profiles → different arcs and outcomes.

---

## 7. Implementation Notes (Non-Normative)

Suggested code-level structure:

- `dosadi/runtime/ai_profiles.py`:
  - defines `AiPolicyProfile` dataclass and registry.
  - exposes `get_ai_profile(id: str) -> AiPolicyProfile`.

- `dosadi/runtime/ai_decision_hooks.py`:
  - implements:
    - `choose_ci_stance(...)`,
    - `decide_campaign_path(...)`,
    - `handle_security_alert(...)`,
    - `choose_collective_action(...)`.
  - uses only fields from `AiPolicyProfile` and current metrics.

- Entry points (e.g., Quiet Season CLI):
  - expose CLI flags to select AI profiles per role,
  - call decision hooks at appropriate times.

This document serves as the **design contract** for those modules.

---

## 8. Future Extensions

Possible future work:

- Extend profiles with:
  - **learning flags** (how quickly RL policies can adapt away from base
    personality).
  - **memory bias** (how long they remember betrayals or failed operations).
- Define:
  - `D-RUNTIME-0106_AI_Policy_Evaluation_and_Metrics` to analyze how different
    profiles perform across scenario packages.
- Allow:
  - emergent “drift” in policy profiles when stress or trauma is extreme
    (e.g., a pragmatic duke gradually becomes paranoid_hardline over a long
     campaign).
