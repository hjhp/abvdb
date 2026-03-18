-- 2026-03-18
-- Wine Owners Hub uses "Wine Product ID" which is unique per LWIN16; yet ABV is unique to LWIN11.
-- Since I need to run ABV information updates regularly on Wine Owners Hub for work, I decided to reuse that data for ABVDB as well — but due to the voting system I implemented on ABVDB, uploading data by LWIN16 is incorrect, because if my version of Hub has more bottle formats for a certain wine, that would give the impression of some LWIN11–ABV pair having more votes.
-- So we simply need to select unique LWIN11.

.headers ON
.import hub.csv hub --csv

.mode csv
.once hub_to_abvdb_output.csv
SELECT DISTINCT
LWIN11,
ABV
FROM hub
WHERE 
"ABV verified" = 'true'
AND NULLIF(LWIN11, '') IS NOT NULL
ORDER BY LWIN11
;
