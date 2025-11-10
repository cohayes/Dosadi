
from __future__ import annotations
from dosadi.api import DosadiSim
from dosadi.core import WorldState

def main():
    sim = DosadiSim(WorldState(seed=7719))
    sim.generate_world(cfg={"policy":{"tax_rate":0.10}}, seed=7719)
    # Minimal walk-through; replace with full playbook steps during implementation.
    sim.plan_cascade(day=0)
    sim.start_delivery("plan_0")
    sim.complete_delivery("plan_0", loss_frac=0.05)
    sim.update_daily_reference("W21", "water")
    sim.minute_quote_update("W21", "water", "civic_kiosk_1")
    sim.post_job({"job_id": "j_1", "ward": "W21", "kind": "MAINT_REPAIR"})
    sim.minute_labor_tick("W21")
    sim.queue_task({"task_id":"t_1","facility":"fac_res_W21","component":"seal_A","kind":"REPAIR"})
    sim.start_maintenance("t_1")
    sim.complete_maintenance("t_1")
    sim.minute_kitchen_tick("kit_W21")
    v = sim.clinic_intake("agent_1","cl_W21")["data"]["visit_id"]
    sim.minute_clinic_tick("cl_W21")
    sim.discharge(v, "RECOVERED")
    sim.open_case("kitchen_W21","carrier_1","late_delivery")
    sim.recalc_legitimacy("W21")
    print("Day-0 skeleton ran. (This is a stub; wire real logic next.)")

if __name__ == "__main__":
    main()
