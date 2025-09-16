from dataclasses import dataclass
from typing import Optional
import os
import aiohttp

@dataclass
class ValidationResponse:
    beatmapIds: list[int]
    beatmapsetId: int
    complianceStatus: str
    complianceStatusString: str
    complianceFailureReason: Optional[str] = None
    complianceFailureReasonString: Optional[str] = None
    notes: Optional[str] = None
    cover: Optional[str] = None
    artist: Optional[str] = None
    title: Optional[str] = None
    ownerId: Optional[int] = None
    ownerUsername: Optional[str] = None
    status: str = ""

@dataclass
class ApiResponse:
    results: list[ValidationResponse]
    failures: list[int]

# API response:
# - Types: https://github.com/hburn7/omc-api/blob/6ca27c3ac58f0ece8616eacf37ff4c1a7e7b7a32/src/lib/dataTypes.ts#L33
# - Response: https://github.com/hburn7/omc-api/blob/master/index.ts#L57
async def validate(beatmap_ids: list[int]) -> Optional[ApiResponse]:
    secret = os.getenv("API_SECRET")
    if not secret:
        return None
    
    endpoint = f"{os.getenv('API_URL')}/validate"

    async with aiohttp.ClientSession() as session:
        async with session.post(endpoint, json=beatmap_ids, headers={
            'X-Api-Key': secret
        }) as response:
            if response.status != 200:
                data = await response.json()
                print(f'Failed to validate beatmaps due to non-200 status code: {data}')
                return None

            data = await response.json()
            all_results = [ValidationResponse(**result) for result in data.get('results', [])]
            all_failures = data.get('failures', [])

            return ApiResponse(
                results=all_results,
                failures=all_failures
            )