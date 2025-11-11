import re
import asyncio
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse


AD_KEYWORDS = [
    "推广", "广告", "下载APP", "扫码加群", "优惠券", "秒杀", "团购", "返利", "导购", "赞助",
    "商务合作", "加微信", "扫码", "点击购买", "独家优惠", "开屏广告", "投放", "拉新",
    "促销", "降价", "试驾", "下订", "到店", "预约", "报价", "一口价", "优惠", "活动", "立减",
    "javascript:void", "立即购买", "点击领取", "福利", "红包"
]

# 域名优先/黑名单：优先保留国内主流媒体，剔除百科/素材站等非新闻源
WHITELIST_DOMAINS = {
    # 新闻与深度媒体
    "thepaper.cn", "jiemian.com", "yicai.com", "21jingji.com", "nbd.com.cn", # 澎湃、界面、第一财经、21世纪、每日经济新闻
    "sina.com.cn", "news.sina.com.cn", "163.com", "news.163.com", "sohu.com", "news.sohu.com",
    # 央媒与权威
    "people.com.cn", "xinhuanet.com", "cctv.com", "cnr.cn", "chinanews.com.cn", "china.com.cn",
    # 地方主流（可扩充）
    "ifeng.com", "news.ifeng.com"
}

BLACKLIST_DOMAINS = {
    "wikipedia.org", "upload.wikimedia.org", "commons.wikimedia.org",
    "baike.baidu.com"
}


def is_chinese_ratio_ok(text: str, min_ratio: float = 0.6):
    if not text:
        return False
    total = len(text)
    zh = len(re.findall(r"[\u4e00-\u9fff]", text))
    return (zh / max(total, 1)) >= min_ratio


def ad_keyword_score(text: str) -> int:
    if not text:
        return 0
    score = 0
    for kw in AD_KEYWORDS:
        if kw in text:
            score += 1
    return score


def normalize_url(url: str) -> str:
    try:
        parsed = urlparse(url)
        return f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
    except Exception:
        return url


def domain_of(url: str) -> str:
    try:
        return urlparse(url).netloc.replace("www.", "")
    except Exception:
        return ""


def clean_text(text: str) -> str:
    # 移除Markdown图片/链接/裸URL/多余空白
    if not text:
        return ""
    t = re.sub(r"!\[[^\]]*\]\([^\)]*\)", "", text)  # 图片
    t = re.sub(r"\[[^\]]*\]\([^\)]*\)", "", t)      # 链接
    t = re.sub(r"https?://\S+", "", t)                 # 裸URL
    t = re.sub(r"\s+", " ", t).strip()
    return t


def is_spammy(text: str) -> bool:
    """检测模板/营销噪声，例如异常符号重复、JS伪链接等"""
    if not text:
        return False
    # 过多的|或*等符号
    if len(re.findall(r"[\|]{10,}", text)) > 0 or len(re.findall(r"\*{10,}", text)) > 0:
        return True
    # 含JS伪链接或大量价格数字
    if "javascript:void" in text.lower():
        return True
    if len(re.findall(r"\d{2,}\.?\d*万|￥\d+", text)) > 10:
        return True
    return False


async def extract_text(url: str) -> str:
    def _worker(u: str) -> str:
        try:
            # 先尝试 r.jina.ai 可读接口（免费，无需Key），提升复杂页面抽取质量
            reader_url = f"https://r.jina.ai/{u}"
            rr = requests.get(reader_url, timeout=8, headers={"User-Agent": "Mozilla/5.0"})
            # 强制按UTF-8解码，避免乱码
            rr.encoding = rr.encoding or 'utf-8'
            text_rr = rr.text
            if rr.status_code == 200 and text_rr and len(text_rr) > 300:
                return clean_text(text_rr)

            # 回退为直接抓取HTML并解析
            r = requests.get(u, timeout=8, headers={"User-Agent": "Mozilla/5.0"})
            if r.status_code != 200:
                return ""
            # 使用apparent_encoding或UTF-8，避免中文乱码
            enc = getattr(r, 'apparent_encoding', None) or 'utf-8'
            r.encoding = enc
            rtext = r.text
            if not rtext:
                return ""
            soup = BeautifulSoup(rtext, 'html5lib')
            for tag in soup(['script', 'style', 'noscript']):
                tag.decompose()
            candidates = []
            for sel in ['article', 'main', 'div#content', 'div.post', 'div.content', 'section']:
                el = soup.select_one(sel)
                if el:
                    txt = el.get_text(separator='\n', strip=True)
                    if txt and len(txt) > 300:
                        candidates.append(txt)
            text = max(candidates, key=len) if candidates else soup.get_text(separator='\n', strip=True)
            return clean_text(text) or ""
        except Exception:
            return ""
    return await asyncio.to_thread(_worker, url)


async def extract_and_filter_texts(results: list[dict], min_len: int = 150, max_docs: int = 20):
    # 规范化URL去重
    seen = set()
    uniq = []
    for r in results:
        u = normalize_url(r.get("href") or r.get("url") or "")
        if not u or u in seen:
            continue
        seen.add(u)
        title = r.get("title") or "(无标题)"
        dom = domain_of(u)
        # 黑名单剔除
        if any(bad in dom for bad in BLACKLIST_DOMAINS):
            continue
        snippet = r.get("body") or ""
        uniq.append({"title": title, "url": u, "domain": dom, "snippet": snippet})

    # 白名单优先排序
    uniq.sort(key=lambda it: (0 if any(it['domain'].endswith(d) for d in WHITELIST_DOMAINS) else 1, it['domain']))

    # 并发抽取
    tasks = [extract_text(it["url"]) for it in uniq[:20]]
    contents = await asyncio.gather(*tasks)

    # 过滤与评分
    docs = []
    stats = {
        "attempted": len(contents),
        "kept": 0,
        "filtered": {
            "empty": 0,
            "too_short": 0,
            "low_chinese_ratio": 0,
            "ad_keywords": 0
        },
        "thresholds": {"min_len": min_len, "min_ch_ratio": 0.5}
    }
    for it, content in zip(uniq, contents):
        if not content:
            # 回退使用snippet
            content = (it.get("snippet") or "").strip()
            if not content:
                stats["filtered"]["empty"] += 1
                continue
        content = content.strip()
        # 如果过短，尝试拼接snippet增强
        if len(content) < min_len and it.get("snippet"):
            content = (content + "\n" + it["snippet"]).strip()
        # 允许较短文本进入，但记录统计；仅在中文比例极低时过滤
        if len(content) < min_len:
            stats["filtered"]["too_short"] += 1
        # 更宽松：域名白名单进一步降低中文比例要求
        min_ratio = 0.1 if any(it['domain'].endswith(d) for d in WHITELIST_DOMAINS) else 0.15
        if not is_chinese_ratio_ok(content, min_ratio):
            stats["filtered"]["low_chinese_ratio"] += 1
            if len(content) < 120:
                continue
        if ad_keyword_score(content) >= 1 or is_spammy(content):
            stats["filtered"]["ad_keywords"] += 1
            continue
        score = len(content)
        if any(it['domain'].endswith(d) for d in WHITELIST_DOMAINS):
            score += 100  # 白名单来源加权
        docs.append({"title": it["title"], "url": it["url"], "domain": it.get("domain", ""), "content": content, "score": score})

    # 选取前max_docs
    docs.sort(key=lambda d: d["score"], reverse=True)
    kept_docs = docs[:max_docs]
    stats["kept"] = len(kept_docs)
    return kept_docs, stats