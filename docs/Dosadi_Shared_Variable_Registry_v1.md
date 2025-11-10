# **Shared Variable Registry v1 (SVR)**

This registry is the single source of truth for cross‑system variables.  
Each entry declares: **name · key · type · units · range · default · update rule · decay/aggregation · notes**.

---

## 0) Notation
- Ranges use inclusive bounds unless stated.
- Decay uses either exponential `x ← x * exp(-λΔt)` or linear `x ← max(0, x - kΔt)`.
- Tick = 0.6 s. 100 ticks = 1 minute.

---

## 1) Temporal Core
| Name | Key | Type | Units | Range | Default | Update | Decay/Agg | Notes |
|---|---|---|---|---|---|---|---|---|
| Simulation Tick | tick | int | ticks | ≥0 | 0 | +1 per step | — | Global monotonic counter |
| Minute Index | t_min | int | minutes | ≥0 | 0 | ⌊tick/100⌋ | — | Aggregation window |
| Day Index | t_day | int | days | ≥0 | 0 | step at 144k ticks | rollover | Barrel cascade cadence |

---

## 2) Environment & Infrastructure
| Name | Key | Type | Units | Range | Default | Update | Decay/Agg | Notes |
|---|---|---|---|---|---|---|---|---|
| Temperature | env.temp | float | °C | -20–80 | 35 | event + regulator model | — | Ward-local |
| Humidity | env.hum | float | %RH | 0–5 | 1.0 | event + condensers | — | Ward-local |
| Air Quality | env.o2 | float | fraction | 0–1 | 0.21 | scrubbers - leaks | exp λ=0.02/min | Low → hypoxia |
| Radiation Level | env.rad | float | a.u. | 0–10 | 1.0 | add events | exp λ=0.005/min | Impacts suit decay |
| Water Loss Rate | env.w_loss | float | frac/day | 1e-4–5e-2 | 1e-3 | maintenance index | — | Leakage of ward systems |
| Maintenance Index | infra.M | float | idx | 0–1 | 0.8 | tasks/neglect | exp λ=0.002/min | Governs failures |
| Environmental Stress | env.S | float | idx | 0–100 | f(vars) | composite of temp/hum/rad/o2 | — | Drives fatigue & unrest |

---

## 3) Governance & Economy
| Name | Key | Type | Units | Range | Default | Update | Decay/Agg | Notes |
|---|---|---|---|---|---|---|---|---|
| Legitimacy | gov.L | float | idx | 0–1 | 0.6 | + consistent rulings; − crises | exp λ=0.001/min to mid | Per faction ruler |
| Corruption | gov.C | float | idx | 0–1 | 0.2 | + diversion; − audits | exp to 0 with λ=0.002/min if pressure | Raises prices |
| Reliability | econ.R | float | idx | 0–1 | 0.5 | contract outcomes | EWMA α=0.2 | Per faction |
| Credit Exchange Rate | econ.X | float | water/credit | >0 | 1.0 | market clear | — | Per issuer |
| Barrel Allocation Bias | econ.B | float | idx | -1–1 | 0 | policy + politics | exp → 0 | King’s bowling bias |

---

## 4) Law & Contracts
| Name | Key | Type | Units | Range | Default | Update | Decay/Agg | Notes |
|---|---|---|---|---|---|---|---|---|
| Enforcement Latency | law.E | float | ticks | ≥0 | 600 | case ledger | EWMA α=0.3 | Lower is better |
| Restorative Ratio | law.RR | float | % | 0–1 | 0.7 | case mix | roll 24h | Ward/faction |
| Retributive Index | law.RI | float | idx | 0–1 | 0.1 | penalties | roll 24h | Signals fear law |
| Arbiter Consistency | law.AC | float | idx | 0–1 | 0.7 | case similarity | exp λ=0.001/min | Trust in bench |

---

## 5) Rumor, Perception & Memory
| Name | Key | Type | Units | Range | Default | Update | Decay/Agg | Notes |
|---|---|---|---|---|---|---|---|---|
| Rumor Credibility | rumor.Cred | float | idx | 0–1 | source rank | Bayes update | exp λ=0.03/min | Per agent rumor |
| Belief Strength | mem.B | float | idx | 0–1 | 0 | evidence | exp λ=0.02/min | Thresholds trigger actions |
| Memory Salience | mem.Sal | float | idx | 0–1 | 0.2 | event energy | exp λ=0.01/min | High → meme |
| Meme Strength | meme.M | float | idx | 0–1 | 0 | repeated high-sal events | slow decay λ=0.001/min | Faction narrative |

---

## 6) Agent Physiology
| Name | Key | Type | Units | Range | Default | Update | Decay/Agg | Notes |
|---|---|---|---|---|---|---|---|---|
| Health | body.H | float | % | 0–100 | 100 | damage/heal | — | 0 → death |
| Hydration | body.W | float | L | 0–10 | 3.0 | intake − losses | linear k by env/suit | Personalized |
| Nutrition | body.N | float | kcal | 0–8000 | 2500 | intake − burn | linear | |
| Stamina | body.Sta | float | idx | 0–100 | 80 | work/rest | exp recovery λ=0.05/min | |
| Mental Energy | body.ME | float | idx | 0–100 | 80 | focus/rest | exp recovery λ=0.04/min | |
| Bladder/Bowel | body.Blad, body.Bow | float | L | 0–2 | 0 | fill rate | emptied on facility use | Suit capture factor |

---

## 7) Suit State
| Name | Key | Type | Units | Range | Default | Update | Decay/Agg | Notes |
|---|---|---|---|---|---|---|---|---|
| Suit Integrity | suit.I | float | idx | 0–1 | 0.9 | wear/repair | exp λ by env.S | |
| Suit Seal | suit.Seal | float | idx | 0–1 | 0.9 | breaches/repair | exp λ by dust/chem | |
| Exposure Score | suit.Exp | float | idx | 0–100 | f(env,suit) | derived | — | Drives health loss |
| Comfort | suit.Comf | float | idx | 0–1 | 0.6 | fit/cleanliness | exp | Affects fatigue |
| Defense (B/S/P) | suit.Def_* | float | idx | 0–1 | model | events | — | Damage model |

---

## 8) Social & Reputation
| Name | Key | Type | Units | Range | Default | Update | Decay/Agg | Notes |
|---|---|---|---|---|---|---|---|---|
| Reputation | rep.R | float | idx | -1–1 | 0 | actions/outcomes | exp λ=0.005/min | Per audience |
| Loyalty Edge | social.L | float | idx | -1–1 | 0 | promised value − rival | exp | Tie-breaker in alignment |
| Fear Index | social.Fear | float | idx | 0–1 | 0.1 | retributive sightings | exp | Modulates obedience |

---

## 9) Contract Economics
| Name | Key | Type | Units | Range | Default | Update | Decay/Agg | Notes |
|---|---|---|---|---|---|---|---|---|
| Price Premium | econ.Prem | float | credits | ≥0 | f(C,R,E,L) | offer calc | — | Risk pricing |
| Collateral | econ.Col | float | asset | ≥0 | f(rank, token) | offer calc | — | Escrow rules |
| Tax Skim | econ.Tax | float | % | 0–0.2 | 0.1 | royal take | — | On official transfer |

---

## 10) Barrel Cascade Controls
| Name | Key | Type | Units | Range | Default | Update | Decay/Agg | Notes |
|---|---|---|---|---|---|---|---|---|
| Daily Draw | cascade.Q | float | L | ≥0 | policy | king algorithm | — | From Well |
| Target Set | cascade.T | set | wards | — | rotation | policy | — | Bowling plan |
| Specialization Score | cascade.S | float | idx | 0–1 | observed | rolling output window | slow | Aids targeting |

---

## Dependency Hints
- env.S depends on temp/hum/rad/o2 and MaintenanceIndex.
- Hydration losses depend on env.S and suit.Seal.
- Legitimacy increases with ArbiterConsistency and on-time mandates; falls with crises/biased rulings.
- Reliability rolls up contract outcomes; affects price premium and collateral.
