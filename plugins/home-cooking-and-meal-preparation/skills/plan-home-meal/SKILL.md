---
name: plan-home-meal
description: Plan and sequence one home meal from people, time, existing ingredients, equipment, ordinary preferences, and food-safety constraints. Trigger on Chinese requests such as “按现有食材帮我安排一顿饭和备菜顺序” and equivalent English requests. Do not prescribe medical diets, promise nutrition treatment, or mechanically generate a cookbook.
---

# Plan a home meal

Turn current household constraints into a meal the user can actually cook. The user shops, cuts, cooks, tastes, and serves; do not claim those actions happened.

## Ask only what changes the meal

Gather people/portions, available time, useful ingredients and their use priority, equipment/burners, cooking confidence, ordinary dislikes/preferences, and any known allergen that must be avoided. If the request is about disease treatment or a therapeutic diet, stop and refer to an appropriate clinician.

## Scope the meal

1. Choose a small coherent meal rather than many unrelated dishes. Use existing perishables and opened items first when safe.
2. Confirm that the equipment, attention, and time support the plan. Avoid simultaneous high-attention tasks for an inexperienced cook.
3. Estimate portions from the household's normal amounts and desired leftovers; label estimates and allow adjustment.
4. List only missing ingredients. Offer functional substitutions for availability or ordinary preference, but do not silently substitute known allergens.

## Build the timeline

Work backward from serving time:

- storage/thawing and food-safety prerequisites;
- longest unattended cooking first;
- shared washing/cutting/marinating while safe;
- raw-food work separated from ready-to-eat food;
- high-attention stove, knife, hot-oil, and final-seasoning steps when the user can watch them;
- doneness checks, rest/hold, serving, then leftover cooling.

For live mode, give one current action with quantity/time or observable completion, then wait. For plan mode, provide the complete timeline. For recovery mode, identify the current state before changing heat, liquid, seasoning, or timing.

## Output and safety

Return meal scope, portions, missing list, prep order, parallelizable steps, doneness checks, serve-time checkpoint, and leftover plan. Explain locality/equipment assumptions.

Stop for active fire, uncontrolled hot oil, gas smell, appliance fault, serious cut/burn, or allergic symptoms. Turn off heat only when safe, evacuate for escaping flames or gas, and contact local emergency/professional help. Do not give gas/electrical repair or medical treatment.

Sources: [CFS Chinese food planning and waste reduction](https://www.cfs.gov.hk/tc_chi/consumer_zone/other_foodsafety/reduce_foodwaste.html), [CFS cooking safety](https://www.cfs.gov.hk/tc_chi/consumer_zone/safefood_all/five_keys_apply_cook.html), and [USFA cooking fire safety](https://www.usfa.fema.gov/prevention/home-fires/prevent-fires/cooking/).
