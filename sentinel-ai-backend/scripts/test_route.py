import asyncio
import json
from app.services.route_service import get_route

async def main():
    result = await get_route("Hyderabad", "Gachibowli")
    # Print summary without flooding the terminal with all coordinates
    print(json.dumps({
        "source": result.source,
        "destination": result.destination,
        "distance_km": result.distance_km,
        "duration_min": result.duration_min,
        "is_live": result.is_live,
        "total_points": result.geometry.total_points,
        "bbox": result.geometry.bbox,
        "segment_count": len(result.segments),
        "first_segment": {
            "index": result.segments[0].segment_index,
            "distance_km": result.segments[0].distance_km,
            "duration_min": result.segments[0].duration_min,
            "start": result.segments[0].start.model_dump(),
            "end": result.segments[0].end.model_dump(),
            "coord_count": len(result.segments[0].coordinates),
        } if result.segments else None,
    }, indent=2))

asyncio.run(main())
