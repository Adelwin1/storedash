import json
import ssl
import certifi
import urllib.parse
import urllib.request

from fastapi import (
    APIRouter,
    HTTPException,
    Query,
)


router = APIRouter(
    prefix="/locations",
    tags=["locations"],
)


NOMINATIM_URL = (
    "https://nominatim.openstreetmap.org/search"
)


@router.get("/search")
def search_location(
    q: str = Query(
        ...,
        min_length=3,
    ),
):
    query = q.strip()

    # Bias StoreDash searches toward Ghana
    # unless the operator explicitly included Ghana.
    if "ghana" not in query.lower():
        query = f"{query}, Ghana"

    params = urllib.parse.urlencode(
        {
            "q": query,
            "format": "jsonv2",
            "limit": 5,
            "countrycodes": "gh",
            "addressdetails": 1,
        }
    )

    request = urllib.request.Request(
        f"{NOMINATIM_URL}?{params}",
        headers={
            "User-Agent":
                "StoreDash-MVP/1.0 "
                "(internal logistics application)",
        },
    )

    try:
        ssl_context = ssl.create_default_context(
            cafile=certifi.where()
        )

        with urllib.request.urlopen(
            request,
            timeout=10,
            context=ssl_context,
        ) as response:
            data = json.loads(
                response.read().decode(
                    "utf-8"
                )
            )

    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=(
                "Location search service "
                "is temporarily unavailable."
            ),
        ) from exc

    return [
        {
            "display_name":
                item.get(
                    "display_name"
                ),

            "latitude":
                float(
                    item["lat"]
                ),

            "longitude":
                float(
                    item["lon"]
                ),

            "type":
                item.get(
                    "type"
                ),
        }

        for item in data
    ]
