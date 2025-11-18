---
title: Identity_Licensing_and_Permits
doc_id: D-AGENT-0107
version: 1.0.0
status: draft
owners: [cohayes]
last_updated: 2025-11-13
parent: D-AGENT-0001
---
# **Identity, Licensing & Permits v1 (IDs, Skill Licenses, Travel Passes, Inspections, Revocations)**

“Position: Tier-2+; not required for minimal civic simulation. Implement after D-AGENT-0001–0003 are live in code and tested.”

**Version:** v1 — 2025‑11‑13  
**Purpose.** Define the identity model and the legal instruments that gate who may work, carry, build, heal, transport, and traverse across wards. Standardizes IDs, skill licenses, shop/guild permits, weapon/tool carry classes, travel/curfew passes, inspection workflows, and revocation/appeal—so Security, Logistics, Clinics, Fabrication, Credits & FX, and Law all speak the same language.

Integrates with **Telemetry & Audit v1** (keys, boards, tokens), **Law & Contract Systems v1** (arbiters, decrees), **Logistics Corridors & Safehouses v1**, **Escort & Security v1**, **Production & Fabrication v1**, **Clinics v1.1**, **Agent Decision v1**, **Rumor v1.1**, and the **Tick Loop**.

> Timebase: license validity **in days**; inspections **per encounter**; boards publish **hourly**; appeals resolved **within days** unless escalated.

“This is an identity and licensing interface doc; it is physically stored under 01_agents but logically belongs to the Identity/Info-Security layer and is shared with Law, Logistics, Clinics, etc.”

---
## 0) Identity Model

- **Core Identity Objects**
  - **AgentID** (person): `{agent_id, legal_name?, caste_hint?, ward_affinity, birth_hash?, biometrics?, owner_key, created_ts}`
  - **FactionID** (guild/militia/civic): `{faction_id, class: GUILD|MILITIA|CIVIC|ISSUER|CLINIC|WORKSHOP, officers[], office_keys[], charter_ref}`
  - **OfficeID** (king/duke/lord/arbiter): `{office_id, tier, jurisdiction, office_key, succession_link?}`
- **Wallet Bindings**: IDs bind to crypto keys (see Telemetry & Audit); rotate & revoke via decrees.
- **Privacy Grades**: PUBLIC (name/id), SEALED (biometrics), SECRET (aliases, witness protection). Arbiters can unseal per order.

---
## 1) Instruments & Classes

**1A. Skill Licenses (person‑bound)**  
- **Structure**: `{agent_id, skill, level: 1..5, issuer:faction_id|office_id, valid_from..to, scope, sigs}`  
- **Examples**: MedTech, Seal‑Fabricator, Escort‑Leader, Armorer, Reactor‑Tech, Auditor‑Clerk.  
- **Use**: gate clinic roles, fabrication stations, escort leadership, audit positions.

**1B. Shop/Guild Permits (organization‑bound)**  
- **Structure**: `{faction_id, permit: WORKSHOP|CLINIC|DEPOT|MONEY_SERVICE|RECLAIMER, tier, capacity, compliance_grade, inspections, valid_from..to, sigs}`  
- **Use**: allows legal operation; ties to capacity limits, hygiene requirements, and reporting cadence.

**1C. Carry Licenses (person/faction)**  
- **Classes**: `TOOL`, `LIGHT_WEAPON`, `ARMORED_WEAPON`, `HEAVY_WEAPON`, `POWER_ARMOR`  
- **Scope**: ward, route, event; **ROE flags** (INNER prohibitions).  
- **Checks**: background (rumor risk), training (skill license), faction sponsorship.

**1D. Travel/Transit Passes**  
- **Pass**: `{holder, lanes: [INNER|MIDDLE|OUTER|SMUGGLER?], time_window, cargo_class_allowed, checkpoint_rules, sigs}`  
- **Special**: **Curfew Pass**, **Medical Evac**, **Cascade Priority** (for barrels & meds), **Diplomatic**.

**1E. Tokenized Instruments**  
- All above can be mirrored as **signed tokens** for portable proof; revocable on boards (see Telemetry & Audit).

---
## 2) Life‑Cycle: Issue → Inspect → Renew/Upgrade → Suspend → Revoke → Appeal

- **Issue**: requires identity verification, sponsor, training proof, and fees (in issuer credits at FX mid).  
- **Inspect**: checkpoints and patrols verify token signatures, scope, and expiry; out‑of‑scope ⇒ warning/fine/confiscation/arrest per tier.  
- **Renew/Upgrade**: based on hours logged (telemetry), QA outcomes, exam, or Arbiter waiver.  
- **Suspend**: temporary block due to incident (hygiene fail, misuse, rumor‑confirmed misconduct).  
- **Revoke**: decree posts to boards; instruments become invalid.  
- **Appeal**: case opened; Arbiter reviews evidence bundles and can reinstate, convert to probation, or escalate.

---
## 3) Inspection & Enforcement

- **Encounter Script** (checkpoint, patrol, clinic desk, workshop audit):  
  1) Query and scan presented tokens (ID + relevant licenses).  
  2) Validate signatures, expiry, and scope; check revocation boards.  
  3) If mismatch: **ladder** of outcomes by lane tier & severity (warn → fine → confiscate → detain).  
  4) Record encounter as `LEDGER` + optional `VIDEO`; emit rumor hooks for high‑profile cases.

- **Confiscation Rules**: off‑scope heavy weapons seized on INNER/MIDDLE; tools usually allowed with record.  
- **Impersonation/Forgery**: flagged to Telemetry detectors; triggers `AuditOpened` and potential receivership for complicit shops.

---
## 4) Progression, Points & Reliability

- **Skill Progression**: hours worked + pass rates yield **Merit Points**; thresholds unlock license upgrades.  
- **Reliability Index**: punctuality, contract completion, clean inspections; used by employers and permit issuers.  
- **Probation**: reduced scope or time‑bound permits with extra inspections; successful period converts to full license.

---
## 5) Interop with Systems

- **Logistics**: travel passes & carry licenses required for escorts; safehouses check permits for class A/B bays.  
- **Fabrication**: shop permits gate station operation; skill licenses gate recipe grades (S/A require higher levels).  
- **Clinics**: clinic tier permits + medtech licenses; emergency waivers during mass casualty.  
- **Credits & FX**: fees, fines, and bonds payable in issuer credits with FX conversion; suspension can freeze money services permit.  
- **Law & Contracts**: contracts reference license IDs; breach due to suspended/revoked license handled via Arbiter.

---
## 6) Black‑Market & Forgery (Optional)

- **Forged IDs/Permits**: exist; have imperfect keys; higher detection risk on INNER lanes and Arbiter audits.  
- **Risk**: if caught, penalties increase (fines, jail, revocation) and rumor stigma spreads.  
- **Counter‑Measures**: rotating device keys, board‑anchored revocation feeds, random deep checks, seal‑tree proofs for shop outputs.

---
## 7) Policy Knobs (defaults)

```yaml
id_licensing_permits:
  license_terms_days:
    skill: 365
    workshop: 365
    clinic: 365
    carry: 180
    travel: 30
  renewal_requirements:
    hours_logged: { lvl2: 200, lvl3: 600, lvl4: 1500, lvl5: 4000 }
    exam_pass_rate_min: 0.80
  inspection:
    inner_deep_check_p: 0.20
    middle_sample_check_p: 0.10
    outer_spot_check_p: 0.04
  penalties:
    warn_fine_confiscate_escalation: true
    heavy_weapon_inner_ban: true
  appeal_sla_days: 5
  probation_window_days: 30
  forged_detection_multiplier_inner: 2.0
```

---
## 8) Event & Function Surface (for Codex)

**Functions**  
- `issue_id(agent|faction|office, fields)` → returns ID + key bindings.  
- `issue_license(agent_id, kind, scope, level)` → signed token; posts to boards.  
- `issue_permit(faction_id|agent_id, permit_kind, scope)` → travel/carry/shop/clinic/depot.  
- `inspect(holder_id, context)` → validates instruments; returns result & penalty if any.  
- `renew_or_upgrade(token_id, evidence)` → updates validity & level.  
- `suspend(token_id, reason, days)` / `revoke(token_id, reason)` → posts decree.  
- `appeal(token_id, case_data)` → opens Arbiter case with timers.
  
**Events**  
- `IDIssued`, `LicenseIssued`, `PermitIssued`, `InspectionLogged`, `PenaltyAssessed`, `Suspended`, `Revoked`, `AppealOpened`, `AppealResolved`.

---
## 9) Pseudocode (Indicative)

```python
def inspect(holder, context):
    instruments = fetch_tokens(holder)
    results = [verify(t, context) for t in instruments]
    violations = [r for r in results if not r.ok]
    penalty = ladder(violations, lane_tier=context.lane_tier)
    log_encounter(holder, context, results, penalty)
    emit("InspectionLogged", {"holder": holder, "penalty": penalty})
    return {"ok": not violations, "penalty": penalty}

def renew_or_upgrade(token, evidence):
    if meet_requirements(token, evidence):
        token.valid_to += policy.license_terms_days[token.kind]
        token.level = maybe_upgrade(token, evidence)
        anchor_to_board(token)
        emit("LicenseIssued", {"token": token.id, "level": token.level})
        return token
    else:
        return {"error": "requirements_not_met"}
```

---
## 10) Dashboards & Explainability

- **Licensing Board**: counts by class/level, pass/fail rates, revocations, probation pool.  
- **Inspection Heatmap**: violation rates by lane/ward; forged detection stats.  
- **Permit Matrix**: which factions/agents have travel/carry/shop/clinic permits; expiries & scope coverage.  
- **Appeals Tracker**: SLA timers, outcomes, reinstatements vs escalations.

---
## 11) Test Checklist (Day‑0+)

- INNER checks catch forged permits at higher rates; OUTER spot checks miss some.  
- Escort convoys with proper travel/carry licenses pass inspections and get lower delay.  
- Shops without permits cannot legally operate stations; attempts trigger penalties and rumor hits.  
- Probation successfully reinstates compliant holders; repeated violations lead to revocation per ladder.

---
### End of Identity, Licensing & Permits v1
