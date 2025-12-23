from fastapi import APIRouter, HTTPException, Query

from utils.locations import LOCATION_DATA, get_countries, get_cities, get_districts

router = APIRouter(prefix="/locations", tags=["locations"])


@router.get("/countries", response_model=list[str], summary="Список доступных стран")
async def list_countries() -> list[str]:
    return get_countries()


@router.get("/cities", response_model=list[str], summary="Список городов по стране")
async def list_cities(country: str = Query(..., description="Страна")) -> list[str]:
    cities = get_cities(country)
    if not cities:
        raise HTTPException(status_code=404, detail="Страна не найдена")
    return cities


@router.get("/districts", response_model=list[str], summary="Список районов по городу")
async def list_districts(
    country: str = Query(..., description="Страна"),
    city: str = Query(..., description="Город"),
) -> list[str]:
    districts = get_districts(country, city)
    if not districts:
        raise HTTPException(status_code=404, detail="Город не найден")
    return districts


@router.get("", response_model=dict, summary="Полное дерево локаций")
async def get_location_tree() -> dict:
    return LOCATION_DATA
