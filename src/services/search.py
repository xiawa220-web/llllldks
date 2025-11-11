import os
import asyncio
import urllib.parse
import requests
from bs4 import BeautifulSoup
import feedparser


async def search_web(query: str, max_results: int = 12):
    """聚合多源搜索，尽量返回至少max_results条结果。"""
    meta = {"attempted_sources": [], "chosen_source": None, "errors": []}
    pool = []
    seen = set()
    qmod = f"{query} -推广 -广告 -下载 -APP -优惠券 -试驾 -促销 -降价"

    def _add(items, source):
        meta["attempted_sources"].append(source)
        if items and meta["chosen_source"] is None:
            meta["chosen_source"] = source
        for it in items or []:
            href = it.get("url") or it.get("href")
            if not href or href in seen:
                continue
            seen.add(href)
            pool.append({"title": it.get("title") or it.get("source") or "(无标题)",
                        "href": href,
                        "body": it.get("snippet", "")})

    # News源
    try:
        _add(_baidu_news_query(qmod, max_results*2), "baidu_news")
    except Exception as e:
        meta["errors"].append(f"baidu_news:{e}")
    try:
        _add(_sogou_news_query(qmod, max_results*2), "sogou_news")
    except Exception as e:
        meta["errors"].append(f"sogou_news:{e}")

    # SearxNG多候选
    searx_url = os.getenv("SEARXNG_URL")
    candidates = [searx_url] if searx_url else []
    candidates += ["https://searx.tiekoetter.com", "https://search.bus-hit.me", "https://searx.be"]
    for cand in candidates:
        try:
            _add(_searxng_query(cand, qmod, max_results), f"searxng:{cand}")
        except Exception as e:
            meta["errors"].append(f"searxng:{e}")

    # 通用网页
    try:
        _add(_baidu_html_query(qmod, max_results), "baidu_html")
    except Exception as e:
        meta["errors"].append(f"baidu:{e}")
    try:
        _add(_bing_html_query(qmod, max_results), "bing_html")
    except Exception as e:
        meta["errors"].append(f"bing:{e}")

    # 社交公开页
    try:
        _add(_bing_site_query(qmod, "weibo.com", max_results), "bing_site_weibo")
    except Exception as e:
        meta["errors"].append(f"bing_site_weibo:{e}")
    try:
        _add(_bing_site_query(qmod, "mp.weixin.qq.com", max_results), "bing_site_weixin")
    except Exception as e:
        meta["errors"].append(f"bing_site_weixin:{e}")

    formatted = pool[:max_results]
    meta["items_count"] = len(formatted)
    return formatted, meta


def _searxng_query(base_url: str, query: str, max_results: int):
    url = base_url.rstrip('/') + '/search'
    params = {
        'q': query,
        'format': 'json',
        'language': 'zh-CN',
        'safesearch': 1,
        'categories': 'general'
    }
    r = requests.get(url, params=params, timeout=12, headers={"User-Agent": "Mozilla/5.0", "Accept-Language": "zh-CN,zh;q=0.9"})
    r.raise_for_status()
    data = r.json()
    results = []
    for res in data.get('results', [])[:max_results]:
        results.append({"title": res.get("title"), "url": res.get("url"), "snippet": res.get("content")})
    return results


def _bing_html_query(query: str, max_results: int):
    q = urllib.parse.quote(query)
    url = f"https://www.bing.com/search?q={q}&ensearch=1&setlang=zh-cn"
    r = requests.get(url, timeout=12, headers={"User-Agent": "Mozilla/5.0", "Accept-Language": "zh-CN,zh;q=0.9"})
    r.raise_for_status()
    soup = BeautifulSoup(r.text, 'html5lib')
    results = []
    for li in soup.select('li.b_algo, li.b_algo:hover, .b_algo'):
        a = li.select_one('h2 a')
        if not a:
            continue
        title = a.get_text(strip=True)
        href = a.get('href')
        snippet_el = li.select_one('.b_caption p')
        snippet = snippet_el.get_text(strip=True) if snippet_el else ''
        results.append({"title": title, "url": href, "snippet": snippet})
        if len(results) >= max_results:
            break
    return results


def _bing_site_query(query: str, site: str, max_results: int):
    # 使用Bing的site过滤，抓取社交平台公开页
    q = urllib.parse.quote(f"site:{site} {query}")
    url = f"https://www.bing.com/search?q={q}&ensearch=1&setlang=zh-cn"
    r = requests.get(url, timeout=12, headers={"User-Agent": "Mozilla/5.0", "Accept-Language": "zh-CN,zh;q=0.9"})
    r.raise_for_status()
    soup = BeautifulSoup(r.text, 'html5lib')
    results = []
    for li in soup.select('li.b_algo, li.b_algo:hover, .b_algo'):
        a = li.select_one('h2 a')
        if not a:
            continue
        title = a.get_text(strip=True)
        href = a.get('href')
        snippet_el = li.select_one('.b_caption p')
        snippet = snippet_el.get_text(strip=True) if snippet_el else ''
        results.append({"title": title, "url": href, "snippet": snippet})
        if len(results) >= max_results:
            break
    return results


def _baidu_html_query(query: str, max_results: int):
    q = urllib.parse.quote(query)
    url = f"https://www.baidu.com/s?wd={q}"
    r = requests.get(url, timeout=12, headers={"User-Agent": "Mozilla/5.0", "Accept-Language": "zh-CN,zh;q=0.9"})
    r.raise_for_status()
    soup = BeautifulSoup(r.text, 'lxml')
    results = []
    for div in soup.select('div.result, div.c-container, div#content_left .result-op'):
        a = div.select_one('h3.t a, h3>a')
        if not a:
            continue
        title = a.get_text(strip=True)
        href = a.get('href')
        snippet_el = div.select_one('.c-abstract')
        snippet = snippet_el.get_text(strip=True) if snippet_el else ''
        results.append({"title": title, "url": href, "snippet": snippet})
        if len(results) >= max_results:
            break
    return results


def _google_news_rss(query: str, max_results: int):
    # 中文新闻RSS
    rss_url = f"https://news.google.com/rss/search?q={urllib.parse.quote(query)}&hl=zh-CN&gl=CN&ceid=CN:zh-Hans"
    feed = feedparser.parse(rss_url)
    results = []
    for entry in feed.entries[:max_results]:
        results.append({"title": entry.get('title'), "url": entry.get('link'), "snippet": entry.get('summary', '')})
    return results


def _baidu_news_query(query: str, max_results: int):
    q = urllib.parse.quote(query)
    url = f"https://news.baidu.com/ns?word={q}&tn=news&from=news&cl=2&rn={max_results}&ct=1"
    r = requests.get(url, timeout=12, headers={"User-Agent": "Mozilla/5.0", "Accept-Language": "zh-CN,zh;q=0.9"})
    r.raise_for_status()
    soup = BeautifulSoup(r.text, 'html5lib')
    results = []
    # 常见结构：div.result > h3 > a
    for div in soup.select('div.result'):
        a = div.select_one('h3 a')
        if not a:
            continue
        title = a.get_text(strip=True)
        href = a.get('href')
        snippet_el = div.select_one('.c-summary, .c-abstract, p')
        snippet = snippet_el.get_text(strip=True) if snippet_el else ''
        if href and title:
            results.append({"title": title, "url": href, "snippet": snippet})
        if len(results) >= max_results:
            break
    # 兜底：页面结构变更时，遍历新闻标题链接
    if not results:
        for a in soup.select('a'):
            href = a.get('href')
            title = a.get_text(strip=True)
            if href and title and len(title) >= 6 and ('news' in href or href.startswith('http')):
                results.append({"title": title, "url": href, "snippet": ''})
            if len(results) >= max_results:
                break
    return results


def _sogou_news_query(query: str, max_results: int):
    q = urllib.parse.quote(query)
    url = f"https://news.sogou.com/news?query={q}&type=2&page=1&num={max_results}"
    r = requests.get(url, timeout=12, headers={"User-Agent": "Mozilla/5.0", "Accept-Language": "zh-CN,zh;q=0.9"})
    r.raise_for_status()
    soup = BeautifulSoup(r.text, 'html5lib')
    results = []
    # 常见结构：a.news_tit
    for a in soup.select('a.news_tit'):
        title = a.get_text(strip=True)
        href = a.get('href')
        if href and title:
            results.append({"title": title, "url": href, "snippet": ''})
        if len(results) >= max_results:
            break
    # 兜底：h3>a
    if len(results) < max_results:
        for h in soup.select('h3 a'):
            title = h.get_text(strip=True)
            href = h.get('href')
            if href and title:
                results.append({"title": title, "url": href, "snippet": ''})
            if len(results) >= max_results:
                break
    return results


def _wikipedia_api_query(query: str, max_results: int):
    api = "https://zh.wikipedia.org/w/api.php"
    params = {
        "action": "query",
        "list": "search",
        "srsearch": query,
        "format": "json"
    }
    r = requests.get(api, params=params, timeout=12, headers={"User-Agent": "Mozilla/5.0"})
    r.raise_for_status()
    data = r.json()
    results = []
    for s in data.get("query", {}).get("search", [])[:max_results]:
        title = s.get("title")
        url = "https://zh.wikipedia.org/wiki/" + urllib.parse.quote(title)
        results.append({"title": title, "url": url, "snippet": s.get("snippet", "")})
    return results