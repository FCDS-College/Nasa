"""Print the generated table section of docs/data/DATA_DICTIONARY.md (§4) from the ORM metadata.

    python docs/tools/render_data_dictionary_tables.py > /tmp/tables.md

Paste the output over §4 after any migration (E2-3 rule: docs ship with schema changes).
"""
import os, sys
os.environ["FLAME_API_AUTH_ENABLED"]="false"
ROOT = __import__("pathlib").Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / "apps" / "api")]
from flame_api.models import Base
from sqlalchemy.dialects import postgresql
out=[]
for t in Base.metadata.sorted_tables:
    out.append(f"### `{t.name}`\n")
    out.append("| Column | Type (PostgreSQL) | Null | Key / default |\n|---|---|---|---|")
    for c in t.columns:
        typ=c.type.compile(dialect=postgresql.dialect())
        key=[]
        if c.primary_key: key.append("PK")
        for fk in c.foreign_keys: key.append(f"FK → `{fk.target_fullname}`" + (f" ON DELETE {fk.ondelete}" if fk.ondelete else ""))
        if c.server_default is not None: key.append(f"server default `{c.server_default.arg}`")
        elif c.default is not None and not callable(getattr(c.default,'arg',None)): key.append(f"default `{c.default.arg}`")
        out.append(f"| `{c.name}` | {typ} | {'yes' if c.nullable else 'no'} | {', '.join(key)} |")
    idx=[f"`{i.name}` ({', '.join(c.name for c in i.columns)}{', unique' if i.unique else ''})" for i in t.indexes]
    uq=[f"`{u.name}` ({', '.join(c.name for c in u.columns)})" for u in t.constraints if u.__class__.__name__=='UniqueConstraint']
    if idx: out.append(f"\nIndexes: {'; '.join(sorted(idx))}.")
    if uq: out.append(f"Unique: {'; '.join(uq)}.")
    out.append("")
print("\n".join(out))
