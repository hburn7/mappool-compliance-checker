from dataclasses import dataclass
from typing import Optional
import json
import os
import requests

@dataclass
class ValidationResponse:
    beatmap_ids: list[int]
    beatmapset_id: int
    compliance_status: str
    compliance_status_string: str
    compliance_failure_reason: Optional[str] = None
    compliance_failure_reason_string: Optional[str] = None
    notes: Optional[str] = None
    cover: Optional[str] = None
    artist: Optional[str] = None
    title: Optional[str] = None
    owner_id: Optional[int] = None
    owner_username: Optional[str] = None
    status: str = ""

@dataclass
class ApiResponse:
    results: list[ValidationResponse]
    failures: list[int]

# API response:
# - Types: https://github.com/hburn7/omc-api/blob/6ca27c3ac58f0ece8616eacf37ff4c1a7e7b7a32/src/lib/dataTypes.ts#L33
# - Response: https://github.com/hburn7/omc-api/blob/master/index.ts#L57
def validate(beatmap_ids: list[int]) -> Optional[ApiResponse]:
    secret = os.getenv("API_SECRET")
    endpoint = f"{os.getenv('API_URL')}/validate"

    response = requests.post(endpoint, json=beatmap_ids, headers={
        'X-Api-Key': secret
    })

    if response.status_code != 200:
        print(f'Failed to validate beatmaps due to non-200 status code: {response.json()}')
        return None

    data = response.json()
    all_results = [ValidationResponse(**result) for result in data.get('results', [])]
    all_failures = data.get('failures', [])

    return ApiResponse(
        results=all_results,
        failures=all_failures
    )