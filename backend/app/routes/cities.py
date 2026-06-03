from fastapi import APIRouter

router = APIRouter(prefix="/api/cities", tags=["cities"])

HOT_CITIES = [
    {"name": "北京", "code": "beijing"},
    {"name": "上海", "code": "shanghai"},
    {"name": "广州", "code": "guangzhou"},
    {"name": "深圳", "code": "shenzhen"},
    {"name": "杭州", "code": "hangzhou"},
    {"name": "成都", "code": "chengdu"},
    {"name": "武汉", "code": "wuhan"},
    {"name": "南京", "code": "nanjing"},
    {"name": "苏州", "code": "suzhou"},
    {"name": "西安", "code": "xian"},
]


@router.get("")
async def list_cities():
    return {"cities": HOT_CITIES}
