from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
db=ROOT/'data'/'campusbuddy.db'
if db.exists(): db.unlink()
print('Removed development database. It will be recreated on next server start.')
