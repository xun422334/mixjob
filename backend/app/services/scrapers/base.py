import hashlib
import logging

logger = logging.getLogger(__name__)


class BaseScraper:
    source_name: str = "unknown"
    rate_limit_delay: float = 1.0
    base_url: str = ""

    def __init__(self, city: str, keyword: str):
        self.city = city
        self.keyword = keyword

    async def scrape(self) -> list[dict]:
        raise NotImplementedError

    @staticmethod
    def normalize_city(city: str) -> str:
        return city.rstrip("市")

    @staticmethod
    def build_dedup_key(title: str, company: str, city: str) -> str:
        raw = f"{title}|{company}|{city}"
        return hashlib.md5(raw.encode()).hexdigest()

    @staticmethod
    def _headers() -> dict:
        return {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/125.0.0.0 Safari/537.36"
            ),
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }

    @staticmethod
    def _clean_company(text: str) -> str:
        """Extract clean company name, removing metadata tags."""
        if not text:
            return ""
        suffixes = [
            "最佳雇主", "上市公司", "民营", "国企", "外资", "合资",
            "股份制企业", "已上市", "未融资", "A轮", "B轮", "C轮", "D轮",
            "天使轮", "不需要融资", "已融资",
        ]
        lines = [l.strip() for l in text.split("\n") if l.strip()]
        clean_lines = []
        for line in lines:
            skip = False
            for sfx in suffixes:
                if line == sfx or line.startswith(sfx):
                    skip = True
                    break
            if not skip and not line.startswith("立即沟通") and "回复" not in line:
                # Also skip lines that are just numbers (company size)
                if line.replace(",", "").replace("人", "").replace("以上", "").replace("-", "").strip().isdigit():
                    continue
                clean_lines.append(line)
        return clean_lines[0] if clean_lines else lines[0] if lines else ""

    @staticmethod
    def _clean_salary(text: str) -> str:
        """Extract just the salary part."""
        if not text:
            return ""
        text = text.strip()
        patterns = ["万", "k", "K", "元", "千"]
        has_salary_unit = any(p in text for p in patterns)
        if has_salary_unit:
            parts = text.split("\n")
            for part in parts:
                part = part.strip()
                if any(p in part for p in patterns):
                    return part
        return text

    @staticmethod
    def _extract_description(full_text: str, title: str, company: str, salary: str, posted_date: str) -> str:
        """Extract remaining job description from card text after filtering known fields."""
        if not full_text:
            return ""
        lines = [l.strip() for l in full_text.split("\n") if l.strip()]
        known = {title, company, salary, posted_date}
        remaining = [l for l in lines if l not in known and l != ""]
        # Filter out very short lines, city names, and metadata tags
        skip_keywords = ["立即沟通", "回复", "人关注", "人评论", "人浏览", "人看过",
                         "放心投", "反馈快", "今日活跃", "刚刚活跃", "在线", "急招"]
        filtered = []
        for line in remaining:
            if len(line) < 3:
                continue
            if any(kw in line for kw in skip_keywords):
                continue
            # Skip pure numbers / company size
            if line.replace(",", "").replace("人", "").replace("以上", "").replace("-", "").strip().isdigit():
                continue
            filtered.append(line)
        return "\n".join(filtered[:6])  # max 6 lines
