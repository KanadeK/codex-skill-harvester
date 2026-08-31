---
name: plan-fresh-market-trip
description: Plan a bounded fresh-market or grocery trip from household size, meals, budget, existing food, storage, travel time, and preferences. Use for Chinese requests such as “帮我列买菜清单、控制预算和份量” or equivalent English requests. Do not use for nutrition treatment, price prediction, or automatic purchasing.
---

# Plan a fresh-market trip

Turn the user's real household constraints into a shopping plan they can carry out. Never say food was bought or inspected unless the user reports doing it.

## Start with only missing critical conditions

Ask at most the few questions needed now:

- how many people, meals, and days;
- budget or a hard spending ceiling;
- dislikes, ordinary dietary preferences, allergies, or ingredients that must be excluded;
- useful food already at home and refrigerator/freezer space;
- travel time, cooling bag availability, and whether this is a fresh market, supermarket, or both.

If the user is already at the market, ask only the next decision needed. Reply in the user's language.

## Build the plan

1. Choose the meal scope before listing ingredients. Prefer a small coherent plan over unrelated “healthy” items.
2. Use existing perishables first. Subtract usable stock from the list and flag uncertain dates or storage.
3. Estimate quantities from the user's customary portions, planned meals, and storage. Label estimates; do not present one region's units or serving customs as universal.
4. Group the list by the user's actual market layout when known. Otherwise use a flexible order: shelf-stable/non-food items, produce and eggs, then raw meat/seafood and chilled/frozen food last.
5. Separate raw animal products from ready-to-eat food and chemicals in baskets and bags. Add a cold-pack plan when transport may be long.
6. Give substitutions by meal function, budget, storage life, and local availability. Do not invent current prices, seasonality, bargaining rules, or stall customs.

For live mode, give the current action and one completion check, then wait. Give the whole list only when requested.

## Output contract

Include:

- list with purpose and approximate quantity;
- optional spending allocation, clearly marked as a plan rather than a price forecast;
- route/order and cold-chain/separation actions;
- shortage and price-change substitutions;
- a final check that the list fits meals, budget, transport, and storage.

## Safety boundaries

Prefer licensed, hygienic sellers and intact packages/dates. Appearance can reject an item but cannot guarantee safety. Stop and ask for safer local guidance when the request involves medical diets, an active allergic reaction, unknown-source high-risk food, or advice that conflicts with an official label or local authority.

Sources: [Hong Kong CFS purchase guidance](https://www.cfs.gov.hk/tc_chi/consumer_zone/safefood_all/five_keys_apply_purchase.html) and [CFS food-waste guidance](https://www.cfs.gov.hk/english/consumer_zone/other_foodsafety/reduce_foodwaste.html).
