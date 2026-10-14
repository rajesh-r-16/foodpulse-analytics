from bson import ObjectId
from datetime import datetime, timezone

def serialize(doc):
    if doc is None:
        return None
    out = dict(doc)
    if "_id" in out:
        out["id"] = str(out.pop("_id"))
    for key, value in list(out.items()):
        if isinstance(value, ObjectId):
            out[key] = str(value)
        elif isinstance(value, datetime):
            out[key] = value.isoformat()
    return out

def now_utc():
    return datetime.now(timezone.utc)
