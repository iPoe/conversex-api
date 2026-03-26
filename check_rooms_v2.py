from core.database import supabase
import json

res = supabase.table("rooms").select("*").limit(1).execute()
if res.data:
    print("Rooms columns:", json.dumps(list(res.data[0].keys()), indent=2))
else:
    print("No rooms found")
