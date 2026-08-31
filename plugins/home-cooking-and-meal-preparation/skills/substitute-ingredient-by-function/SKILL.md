---
name: substitute-ingredient-by-function
description: Replace a missing cooking ingredient by identifying its function and adjusting quantity, liquid, acid, sweetness, thickening, binding, leavening, texture, or flavour expectations. Trigger on Chinese requests such as “缺这个食材能用什么替代、用多少” and equivalent English requests. Do not improvise substitutions for medical allergies, canning, fermentation, infant food, or other safety-critical formulas.
---

# Substitute an ingredient by function

Choose a replacement that behaves acceptably in this dish, not a list of ingredients with similar names. The user decides and cooks the change.

## Get the decision context

Ask for the dish/recipe, missing ingredient and amount, cooking method, available alternatives, desired result, and allergy or safety constraints. If the ingredient performs several roles, identify each.

## Classify the function

Determine whether the ingredient mainly provides:

- bulk/structure or binding;
- moisture;
- fat/emulsification;
- acid/alkalinity or leavening reaction;
- thickening;
- sweetness/browning;
- salt/umami/aroma/heat;
- colour or garnish.

Then rank only alternatives available to the user.

## Propose and adjust

For each viable option state:

1. why it matches the required function;
2. starting amount and any connected liquid, acid, fat, sugar, or cooking-time adjustment;
3. expected texture, flavour, colour, volume, or browning difference;
4. a small observable checkpoint before committing the whole batch;
5. how to recover if the mixture becomes too wet, dry, thin, thick, salty, bland, or intense.

Prefer a small test portion when failure is costly. Do not hide uncertainty behind exact-looking ratios.

## Stop boundaries

Do not improvise substitutions in tested canning/preservation formulas, fermentation controls, infant feeding, or allergy avoidance. A known food allergy requires label and cross-contact controls; symptoms require stopping food consumption and medical/emergency help. Never suggest that cooking makes an allergen safe.

Completion means the user has one chosen substitute, adjusted amount, expected difference, checkpoint, and fallback—not that the dish was completed.

Source: [Colorado State University Extension ingredient substitutions](https://extension.colostate.edu/resource/ingredient-substitutions/). Safety boundary: [FDA food allergies](https://www.fda.gov/food/nutrition-food-labeling-and-critical-foods/food-allergies).
