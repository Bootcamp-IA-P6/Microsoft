import json
import sys

data = json.load(sys.stdin)
block = (data.get("data") or [{}])[0]
arrivals = block.get("Arrive", [])
print("stop:", block.get("StopName") or block.get("stopName"))
print("total arrivals:", len(arrivals))
for a in arrivals[:8]:
    eta = a.get("estimateArrive")
    dist = a.get("DistanceBus")
    print(f"  line {a.get('line')} -> {a.get('destination')}: {eta}s, {dist}m")
