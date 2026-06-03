from .boss import BossZhipinScraper
from .liepin import LiepinScraper
from .zhaopin import ZhaopinScraper
from .guopin import GuopinScraper

SCRAPER_REGISTRY = {
    "boss": BossZhipinScraper,
    "liepin": LiepinScraper,
    "zhaopin": ZhaopinScraper,
    "guopin": GuopinScraper,
}
