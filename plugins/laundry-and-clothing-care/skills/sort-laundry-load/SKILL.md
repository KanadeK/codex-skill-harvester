---
name: sort-laundry-load
description: Read garment care labels and separate clothing into compatible loads by wash permission, temperature ceiling, cycle strength, bleach/drying limits, colour, fabric, soil, and stain risk. Trigger on Chinese requests such as “帮我看标签、深浅色和面料分几桶洗” and equivalent English requests. Do not guess unreadable labels or machine controls.
---

# Sort a laundry load

Help the user decide what can safely be washed together. The user reads, photographs, handles, and sorts the items; do not claim the load has been prepared.

## Ask only for decisive information

Request readable label symbols/text, colour, fabric, visible stains/soil, known colour bleeding, and available drying method. If a symbol or garment construction is unclear, ask for a clearer image or label transcription rather than guessing.

## Interpret and separate

1. Decode the label groups: washing, bleaching, drying, ironing, and professional cleaning. A crossed-out process is prohibited; temperature and line/dot modifiers are ceilings or treatment limits.
2. Remove items that forbid home washing or require professional care.
3. Separate incompatible constraints before optimizing load count:
   - likely colour bleeders, new darks, and whites/lights;
   - wool/delicates versus sturdy cottons;
   - heavily soiled or contaminated items versus ordinary clothing;
   - items with incompatible maximum temperature, agitation/spin, bleach, or drying limits;
   - waterproof items when the exact machine manual requires a separate cycle/load.
4. Within each group, use the most restrictive compatible label. A weaker/cooler treatment may be chosen when it still meets the cleaning need.
5. Treat stains before washing only with the garment and product labels. Never mix bleach with ammonia, acids, or other cleaners, and never improvise chemical combinations.

For a live sorting session, ask about one item or one decision at a time. In planning mode, provide a full load table.

## Output and completion

Return: load name, included items, controlling label limit, excluded items/reason, stain pre-check, and drying boundary. Finish only when every item has one destination: a compatible load, hand wash, professional care, or hold for more information.

If an item is valuable, damaged, unlabeled, structurally delicate, or chemically contaminated, stop before washing and seek manufacturer or professional-cleaner advice.

Sources: [Government of Canada care symbols](https://ised-isde.canada.ca/site/office-consumer-affairs/en/product-safety-recalls-and-labelling/guide-apparel-and-textile-care-symbols) and [CDC bleach safety](https://www.cdc.gov/hygiene/about/cleaning-and-disinfecting-with-bleach.html).
