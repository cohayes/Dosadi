---
title: Environment_Dynamics
doc_id: D-WORLD-0001
version: 1.0.0
status: stable
owners: [cohayes]
depends_on: 
includes:
  D-WORLD-0004  # Worldgen
last_updated: 2025-11-11
---
# **Dosadi Environment Dynamics v1**

---

## **1. Purpose**

The Environment System defines the physical and ecological conditions that shape all survival and governance behavior on Dosadi.  
It provides the *external reality* through which suits, bodies, and factions interact — a closed, resource-scarce world designed to test adaptation and loyalty.

**Core Principle:**  
> “The world itself is an enforcer. Scarcity is the only law older than the king.”

---

## **2. Planetary Overview**

Dosadi is a near-dead world engineered to contain life only within a single urban-valley system called **the City of Wards**.  
There is no rainfall, no surface wind, and the atmosphere is artificially desiccated.  
Every drop of water originates from **The Well** — a massive geothermal reclamation structure at the valley floor.

### **Environmental Constants**

| Variable | Typical Range | Description |
|-----------|----------------|-------------|
| **Temperature** | 25°C (night) → 65°C (day) | Extreme diurnal shifts caused by thin atmosphere. |
| **Humidity** | 0.1% – 2.0% | Always critically low; unprotected exposure fatal in minutes. |
| **Air Pressure** | 0.6 – 0.8 atm | Thin, hot air strains respiration. |
| **Solar Intensity** | 2× Earth norm | High UV exposure; affects suit degradation. |
| **Radiation Background** | Elevated but stable | Geothermal venting and decayed shielding. |
| **Dust/Particulate Density** | Moderate | Electrostatic dust adhesion affects optics and suits. |

These values fluctuate per tick and are locally modified by infrastructure quality, ward altitude, and the operational state of environmental systems.

---

## **3. Ward Design and Atmospheric Architecture**

The City consists of **36 Wards** organized around The Well in a concentric valley.

### **Hybrid Containment Model**

- **Inner Wards (1–6):**  
  Fully sealed microclimates; total atmospheric control. High air quality, stable temperature, near-perfect water reclamation.  
  These include **The Well (Ward 1)** and the King’s administrative domains.

- **Middle Wards (7–20):**  
  Semi-sealed with adjustable atmospheric hoods and controlled ventilation corridors.  
  Provide partial exchange for trade and transport; risk moderate contamination and heat fluctuations.

- **Outer Wards (21–36):**  
  Open-topped with massive perimeter walls and limited climate shielding.  
  Designed for population control: easy to monitor, difficult to escape, constantly stressed by temperature and dryness.  
  Infrastructure here leaks moisture and heat; survival depends heavily on suit quality.

### **Valley Geometry**

- The **Well** lies at the basin center — lowest gravitational and thermal point.  
- **Steam vents and geothermal conduits** radiate outward, powering reclamation and limited agriculture.  
- Altitude increases slightly per ring, creating gradient pressures that drive minor air circulation between wards.

This topography naturally channels water flow, power lines, and political hierarchy.

---

## **4. Environmental Subsystems**

| Subsystem | Function | Controlled By | Failure Consequence |
|------------|-----------|----------------|---------------------|
| **Thermal Regulators** | Maintain ward temperature balance via geothermal exchangers. | Local guild engineers. | Heatstroke, infrastructure warping. |
| **Dehumidifiers / Condensers** | Capture ambient moisture and human respiration. | Reclaimer Guild, licensed to each lord. | Rapid dehydration and social panic. |
| **Air Scrubbers** | Maintain breathable atmosphere, remove toxins. | Tech guilds. | Hallucinations, hypoxia, narcotic buildup. |
| **Shielding / Dome Fields** | Protect from UV, radiation, and dust intrusion. | Elite wards only. | Suit degradation, surface blisters. |
| **Lighting Arrays** | Control circadian rhythm and photosynthetic balance. | Administrative Clerks + Power Guilds. | Disorientation, crop collapse. |
| **Waste Reclaimers** | Convert biomass and greywater into nutrients + clean water. | Reclaimer Guild (state-protected). | Famine loops, disease spread. |

These subsystems are subject to maintenance contracts and corruption; negligence translates directly into environmental degradation.

---

## **5. Environmental Stressors and Suit Interaction**

### **Primary Stressors**

| Stress Type | Description | Suit Countermeasure |
|--------------|--------------|----------------------|
| **Heat / Radiation** | Burns, dehydration, fatigue. | Cooling mesh, reflective plating. |
| **Dry Air / Low Pressure** | Respiratory loss, water boil-off. | Pressure regulation, humidity capture. |
| **Dust & Chemical Corrosion** | Damages optics, seals, lungs. | Filtration units, suit self-clean cycles. |
| **Toxic Vapors / Industrial Gases** | Produced by malfunctioning machinery. | Charcoal or biofilter cartridges. |
| **Low Visibility** | Affects navigation and perception. | Active optics, HUD enhancement. |

### **Suit Feedback Loop**

- Environmental stress increases **suit decay rate**.  
- Suit integrity affects **body exposure and fatigue**.  
- Body fatigue reduces **maintenance capacity**, further lowering environmental control — a self-reinforcing entropy loop.  
- High-tech wards minimize this feedback; low-tech ones suffer cascading breakdowns.

---

## **6. Environmental Events**

Events simulate macroscopic change across wards and drive narrative progression:

| Event Type | Description | Typical Outcome |
|-------------|--------------|------------------|
| **Heat Surge** | Vent malfunction or solar flare raises local temperature by >10°C. | Increased mortality, labor slowdown. |
| **Condensation Failure** | Dehumidifiers stop; water rations halve. | Panic, unrest, increase in black-market prices. |
| **Dust Ingress** | Storm infiltration via open corridors. | Reduced visibility, rumor spread (“poison dust”). |
| **Reclaimer Contamination** | Biofilter corruption causes sickness. | Mass paranoia, legitimacy drop. |
| **Power Brownout** | Insufficient geothermal output. | Loss of lighting, heat spikes, faction blame cascade. |
| **Localized Flooding** | Barrel rupture or over-reclaim event. | Temporary abundance, political scramble. |

Events are probabilistic functions of maintenance quality, corruption, and temporal cycles.

---

## **7. Environmental–Social Feedback**

Environmental degradation acts as a **universal pressure amplifier**:
- Rising temperature → higher suit costs → reduced labor output → economic contraction → legitimacy loss.
- Moisture scarcity → increases value of Reclaimer Guild → guild corruption increases → lords lose control.

Conversely, rare environmental stability supports:
- Lower mortality.
- Improved morale.
- Decreased rumor volatility.

Environmental “weather” therefore doubles as a **social mood system**.

---

## **8. Integration Points**

| Connected System | Interaction |
|------------------|-------------|
| **Suit–Body System** | Directly determines exposure, fatigue, hydration loss. |
| **Agent Physiology** | Converts temperature and humidity into health penalties. |
| **Economic System** | Affects cost of water, rations, and maintenance goods. |
| **Governance & Legitimacy** | Environmental stability boosts legitimacy; disasters erode it. |
| **Rumor Ecology** | Failures generate high-impact rumor cascades (“The air is poison”). |
| **Temporal Simulation** | Updates all environmental variables per tick; manages event decay. |

---

## **9. Core Variables**

| Variable | Description | Range / Units |
|-----------|--------------|----------------|
| **Temperature** | Ambient air temperature | −20°C – 80°C |
| **Humidity** | Ambient relative humidity | 0 – 5% |
| **RadiationLevel** | Background radiation intensity | 0 – 10 arbitrary units |
| **AirQuality** | Proportion of breathable oxygen | 0 – 1 |
| **WaterLossRate** | Fractional daily water leakage from ward systems | 0.0001 – 0.05 |
| **MaintenanceIndex** | Overall infrastructure integrity | 0 – 1 |
| **EnvironmentalStress** | Composite hazard score combining the above | 0 – 100 |

These variables feed into agent-level calculations of fatigue, health decay, and social unrest probability.

---

## **10. Future Hooks**

- **Dynamic Climate Drift:** Long-term environmental entropy changing baseline temperature/humidity.  
- **Ward Micro-Ecosystems:** Enable flora or bio-reactor niches that recycle waste.  
- **Atmospheric Trade Routes:** Smugglers exploiting pressure gradients for covert movement.  
- **Environmental AI Agents:** Autonomous repair drones maintaining systems for lords or guilds.  
- **Toxic Narrative Layer:** Rumors about environmental decay altering perceived reality (“The air itself is dying”).  
- **Geo-political Terraforming:** King’s large-scale interventions shifting climate to assert control.

---

### **End of Environment Dynamics v1**
