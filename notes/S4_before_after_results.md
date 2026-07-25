
## Q1 - Failure rate by facility type and year

**D (raw)**
```
ARCHDIOCESE | 2021 | 1 | 1.0
ART GALLERY | 2016 | 1 | 1.0
BANQUET HALL/CATERING | 2017 | 2 | 1.0
BAR | 2017 | 2 | 1.0
CAFE | 2012 | 1 | 1.0
CATERED EVENTS | 2011 | 2 | 1.0
CHURCH/AFTER SCHOOL PROGRAM | 2011 | 1 | 1.0
COFFEE VENDING MACHINE | 2010 | 4 | 1.0
DAY CARE 1023 | 2015 | 1 | 1.0
DAYCARE 2-6, UNDER 6 | 2012 | 2 | 1.0
DISTRIBUTOR | 2016 | 1 | 1.0
DOLLAR STORE | 2015 | 1 | 1.0
EVENT SPACE | 2017 | 2 | 1.0
FARMER'S MARKET | 2010 | 1 | 1.0
Food Pantry | 2019 | 2 | 1.0
... (2344 rows total)
```

Total (facility_type, year) groups on D: 2344
**D' (clean)**
```
Archdiocese | 2021 | 1 | 1.0
Art Gallery W/wine And Beer | 2016 | 1 | 1.0
Bar | 2017 | 2 | 1.0
Catered Events | 2011 | 2 | 1.0
Distribution Center | 2016 | 1 | 1.0
Event Center | 2017 | 2 | 1.0
Farmer's Market | 2010 | 1 | 1.0
Golf Course | 2014 | 1 | 1.0
Hair Salon | 2019 | 1 | 1.0
Hooka Lounge | 2010 | 3 | 1.0
Hot Dog Station | 2021 | 1 | 1.0
Illegal Vendor | 2012 | 2 | 1.0
Illegal Vendor | 2013 | 1 | 1.0
Internet Cafe | 2018 | 1 | 1.0
Milk Tea | 2019 | 1 | 1.0
... (1183 rows total)
```

Total (facility_type, year) groups on D': 1183

'Restaurant' fail rate on D (exact-spelling only): 0.217 over 173984 inspections
'Restaurant' fail rate on D' (canonicalized): 0.217 over 174244 inspections

## Q2 - Most common violations among failed inspections

**D (raw) - degenerate: grouping on the whole unparsed Violations blob**
```
9. WATER SOURCE: SAFE, HOT & COLD UNDER CITY PRESSURE - Comm | 3
39. CONTAMINATION PREVENTED DURING FOOD PREPARATION, STORAGE | 3
38. VENTILATION: ROOMS AND EQUIPMENT VENTED AS REQUIRED: PLU | 3
38. INSECTS, RODENTS, & ANIMALS NOT PRESENT - Comments: OBSE | 3
18. NO EVIDENCE OF RODENT OR INSECT OUTER OPENINGS PROTECTED | 3
18. NO EVIDENCE OF RODENT OR INSECT OUTER OPENINGS PROTECTED | 3
18. NO EVIDENCE OF RODENT OR INSECT OUTER OPENINGS PROTECTED | 3
11. ADEQUATE NUMBER, CONVENIENT, ACCESSIBLE, DESIGNED, AND M | 3
10. ADEQUATE HANDWASHING SINKS PROPERLY SUPPLIED AND ACCESSI | 3
9. WATER SOURCE: SAFE, HOT & COLD UNDER CITY PRESSURE - Comm | 2
... (54155 rows total)
```

54240 failed inspections with a non-blank Violations field produce 54155 distinct blobs (99.8% unique) - grouping on the raw text answers 'which exact inspections repeat', not 'which violations are common'.
**D' (clean)**
```
55-POST2018 | PHYSICAL FACILITIES INSTALLED, MAINTAINED & CLEAN | 24805
34-PRE2018 | FLOORS: CONSTRUCTED PER CODE, CLEANED, GOOD REPAIR, COVING INSTALLED, DUST-LESS CLEANING METHODS USED | 19371
35-PRE2018 | WALLS, CEILINGS, ATTACHED EQUIPMENT CONSTRUCTED PER CODE: GOOD REPAIR, SURFACES CLEAN AND DUST-LESS CLEANING METHODS | 18257
33-PRE2018 | FOOD AND NON-FOOD CONTACT EQUIPMENT UTENSILS CLEAN, FREE OF ABRASIVE DETERGENTS | 16445
18-PRE2018 | NO EVIDENCE OF RODENT OR INSECT OUTER OPENINGS PROTECTED/RODENT PROOFED, A WRITTEN LOG SHALL BE MAINTAINED AVAILABLE TO THE INSPECTORS | 16432
38-PRE2018 | VENTILATION: ROOMS AND EQUIPMENT VENTED AS REQUIRED: PLUMBING: INSTALLED AND MAINTAINED | 15529
32-PRE2018 | FOOD AND NON-FOOD CONTACT SURFACES PROPERLY DESIGNED, CONSTRUCTED AND MAINTAINED | 15019
38-POST2018 | INSECTS, RODENTS, & ANIMALS NOT PRESENT | 14079
10-POST2018 | ADEQUATE HANDWASHING SINKS PROPERLY SUPPLIED AND ACCESSIBLE | 13123
47-POST2018 | FOOD & NON-FOOD CONTACT SURFACES CLEANABLE, PROPERLY DESIGNED, CONSTRUCTED & USED | 11068
41-PRE2018 | PREMISES MAINTAINED FREE OF LITTER, UNNECESSARY ARTICLES, CLEANING  EQUIPMENT PROPERLY STORED | 10667
49-POST2018 | NON-FOOD/FOOD CONTACT SURFACES CLEAN | 9283
51-POST2018 | PLUMBING INSTALLED; PROPER BACKFLOW DEVICES | 8394
36-PRE2018 | LIGHTING: REQUIRED MINIMUM FOOT-CANDLES OF LIGHT PROVIDED, FIXTURES SHIELDED | 7736
56-POST2018 | ADEQUATE VENTILATION & LIGHTING; DESIGNATED AREAS USED | 7284
... (109 rows total)
```

## IC1 - License # must identify a real establishment (Problem 3)

D:  787 inspections with an unusable License # (unjoinable to any establishment)
D': 60 inspections still unjoinable after recovery attempt
IC violations reduced by 727 (92.4%)
**D' fix_status breakdown**
```
ambiguous | 60
ok | 298082
recovered_name_addr | 89
unresolved | 638
```

## IC2 - Facility Type must be consistent per establishment (Problem 1)

D:  387 license numbers with inconsistent Facility Type across their own inspection history
D': 0 (establishment enforces one facility_type per license_no by construction)

## IC3 - Distinct value counts (Problems 1 & 2)

Facility Type: D = 521 distinct values, D' = 231 distinct canonical values
City: D = 90 distinct values, D' = 69 distinct canonical values

## IC4 - Results must be a real pass/fail outcome (for U1's fail-rate calc)

D: 41882 of 298869 rows (14.01%) have a Results value that isn't a real outcome and must be excluded, or they silently distort any naive fail-rate calculation:
Business Not Located | 93
No Entry | 12953
Not Ready | 4110
Out of Business | 24726

D': all 41882 handled via outcome_bucket = 'no_outcome' (see results_bucketed.csv) - U1 queries filter on outcome_bucket IN ('pass','fail').