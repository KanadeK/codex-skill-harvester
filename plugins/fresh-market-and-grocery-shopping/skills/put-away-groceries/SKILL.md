---
name: put-away-groceries
description: Decide where newly purchased food belongs and what should be used first from labels, perishability, opened state, planned meals, and available refrigerator/freezer/pantry space. Trigger on Chinese requests such as “买菜回来怎么收、先吃什么” and equivalent English requests. Do not decide that questionable food is safe from smell alone.
---

# Put away groceries

Guide the user through storage and use priority. Never claim items were stored, labelled, frozen, or discarded until the user confirms the action.

## Gather the minimum inventory

Ask for the purchased items, package/open state, use-by or best-before/storage instructions, time since purchase, intended meals, and available cold/dry storage. Ask current refrigerator/freezer temperature only when it matters.

## Sort and prioritize

1. Identify anything needing immediate attention: leaking/damaged packaging, unknown warm time, expired use-by date, or insufficient cold storage.
2. Assign destinations:
   - prompt refrigeration for cooked/perishable food;
   - freezer only when the label/food and future use support it;
   - cool, clean, dry storage for suitable shelf-stable items;
   - separate household chemicals from food.
3. Prevent cross-contamination: covered/sealed containers; raw meat, poultry, and seafood below ready-to-eat/cooked food.
4. Label opened, divided, cooked, or frozen items with identity and date when useful. Avoid overcrowding that blocks cold-air circulation.
5. Build an eat-first order from use-by safety dates, opened state, perishability, existing older stock, and planned meals. “Best before” concerns quality; it does not override package storage instructions or signs of spoilage.
6. Use FIFO where appropriate, but do not keep unsafe food merely to avoid waste.

For an active put-away session, give one location/action at a time and wait for confirmation.

## Completion and recovery

Return a compact table: item, destination, container/separation, label/date, use-first priority, and unresolved concern. Check that all perishables are cold, raw food cannot drip onto ready-to-eat food, and the user knows which items need early use.

If cold-chain time, package condition, or safety date is uncertain, do not rely on appearance or smell; use conservative local food-safety guidance or discard. Medical illness questions are out of scope.

Source: [Hong Kong CFS food-waste, date-label, storage, and leftovers guidance](https://www.cfs.gov.hk/english/consumer_zone/other_foodsafety/reduce_foodwaste.html).
