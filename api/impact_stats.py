"""Impact numbers for the README, from the real CDSCO alerts in data/kincare.db.

    python impact_stats.py

Medicine groups are matched on the generic (salt) name in the alert's product name, so the counts are a lower
bound: an alert that names only a brand is not counted.
"""
import collections
import re
import sqlite3

from db import DB_PATH
c=sqlite3.connect(DB_PATH)
rows=c.execute('select category,product_name,alert_month from alerts').fetchall()
print('total',len(rows), collections.Counter(r[0] for r in rows))
months=sorted({r[2] for r in rows if r[2]}); print('months',months[0],months[-1],len(months))
last12=[r for r in rows if r[2] and r[2]>='2025-11']; print('last12 (2025-11..)',len(last12), 'months', len({r[2] for r in last12}))
latest=months[-1]; print('latest',latest, sum(r[2]==latest for r in rows))
groups={'blood pressure / heart':r'amlodipin|telmisartan|losartan|olmesartan|atenolol|metoprolol|ramipril|cilnidipin|nebivolol|bisoprolol|clopidogrel|aspirin|telma',
'diabetes':r'metformin|glimepirid|gliclazid|sitagliptin|vildagliptin|teneligliptin|insulin|dapagliflozin|empagliflozin|voglibose|pioglitazone',
'cholesterol':r'atorvastatin|rosuvastatin',
'pain / fever':r'paracetamol|diclofenac|aceclofenac|ibuprofen|nimesulide|tramadol|dolo',
'calcium / vitamin D':r'calcium|cholecalciferol|vitamin d'}
anyhit=0
for r in rows:
    if any(re.search(p,r[1] or '',re.I) for p in groups.values()): anyhit+=1
for g,p in groups.items(): print(g, sum(bool(re.search(p,r[1] or '',re.I)) for r in rows))
print('any elder group',anyhit, round(100*anyhit/len(rows),1))
