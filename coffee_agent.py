#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
coffee_agent.py
跨境咖啡品牌 AI 情报 Agent
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
情报来源：① Google News RSS  ② SerpAPI/DuckDuckGo 搜索  ③ 官网/Instagram 页面抓取
触发方式：直接运行 or cron 定时
输出：
  · reports/YYYY-MM-DD.md      —— 每日情报 + 空气感文案
  · reports/weekly_YYYY-Www.md —— 周报汇总（每周一自动生成）
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
依赖（均为标准库，零额外安装）：
  urllib, json, os, datetime, re, time, xml.etree, html, concurrent.futures
"""

import json, os, re, time, datetime, html, hashlib, logging
import urllib.request, urllib.error, urllib.parse
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

# ══════════════════════════════════════════════════════════
#  配置区  ── 只需改这里
# ══════════════════════════════════════════════════════════
COMPETITORS_FILE = "competitors.json"
REPORTS_DIR      = Path("reports")
CACHE_FILE       = Path(".agent_cache.json")   # 去重缓存，避免重复抓同一条新闻

GEMINI_KEY   = os.environ.get("GEMINI_API_KEY", "")
GEMINI_URL   = ("https://generativelanguage.googleapis.com"
                "/v1beta/models/{model}:generateContent?key={key}")
GEMINI_MODEL = "gemini-2.0-flash"

# 每品牌最多处理几条新闻（避免 API 费用失控）
MAX_NEWS_PER_BRAND = 2
# 并发抓取线程数
FETCH_WORKERS = 6
# HTTP 超时（秒）
HTTP_TIMEOUT = 12
# 本次只处理哪些类别（留空 = 全部）
TARGET_CATEGORIES: list[str] = []
# 本次只处理哪些品牌名（留空 = 全部）
TARGET_BRANDS: list[str] = []

# ══════════════════════════════════════════════════════════

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("coffee_agent")

# ── vibe → 中文氛围描述 ─────────────────────────────────
VIBE_MAP = {
    "daily_comfort":          "亲切温暖、融入日常、平凡中的小确幸",
    "seasonal_experience":    "季节限定、仪式感、粉红色的期待",
    "privacy_retro":          "复古静谧、老派自在、被沙发包裹的午后",
    "business_balance":       "职场从容、专注一杯、都市人的喘息",
    "bakery_fusion":          "面包香与咖啡香的交叠、温热、手作感",
    "traditional_flannel":    "法兰绒手冲、老派讲究、沉默的职人美学",
    "hand_drip_pancake":      "手冲的专注、松饼的柔软、周末的奢侈",
    "classic_kissaten":       "纯喫茶老铺、时间静止、昭和余香",
    "day_night_hybrid":       "白天咖啡夜晚酒、城市的双面人格",
    "urban_refresh":          "都市解压、玻璃窗外的人流、短暂出走",
    "efficiency_speed":       "高效即美德、浓缩即生命、无废话的清醒",
    "premium_italian":        "意式浓郁、皮革座椅、稍微体面一点",
    "bottomless_coffee":      "无限续杯的慷慨、甜圈圈与时光打转",
    "convenience_value":      "便利即诗意、百元哲学、随手的温暖",
    "health_decaf":           "无咖啡因的温柔、关照身体的小决定",
    "minimalism":             "留白即丰盛、单一产地、克制是最高美学",
    "global_design":          "建筑感构图、全球视野、美是可以喝的",
    "omakase_lab":            "主厨发办式选豆、信任、未知的惊喜",
    "light_roast_top":        "顶级浅焙、果酸如诗、懂的人才懂",
    "lifestyle_vintage":      "北欧复古、黑胶唱片、生活方式本身",
    "community_sustainable":  "可持续的温度、社群连结、对土地负责",
    "neo_japanese_specialty": "日式精品、职人精神、现代与传统的对话",
    "self_serve_innovation":  "自助革新、科技温度、新型相遇",
    "wood_classic":           "木质经典、澳洲阳光、踏实的手艺",
    "industrial_roastery":    "工业烘焙美学、铁与香气、硬朗中的细腻",
    "street_culture":         "街头灵魂、反叛与精致并存",
    "california_sun":         "加州阳光、冲浪后的一杯、轻盈自由",
    "osaka_personality":      "大阪个性、不拘一格、亲切又有锋芒",
    "nara_balance":           "奈良静谧、鹿与咖啡、平衡的生活哲学",
    "experimental_brewing":   "实验精神、每一杯都是假设与验证",
    "latte_art_pioneer":      "拿铁艺术先驱、美在杯口绽放",
    "street_stand":           "街头站吧、城市动脉、移动的生命力",
    "single_origin_purist":   "单一产地纯粹主义、风土即灵魂",
    "organic_earth":          "有机土地、自然呼吸、根系的哲学",
    "origin_focused":         "产地溯源、透明即诚意、每一口有来处",
    "art_gallery_non_alc":    "无酒精艺廊、感官的另一种旅行",
    "luxury_moroccan":        "摩洛哥奢华、金器与香料、异域的贵气",
    "champion_italian":       "冠军意式、竞技台背后的执念",
    "warm_community":         "仓前温暖社群、街角的归属感",
    "taiwanese_fusion":       "台湾融合东京、跨海而来的味觉记忆",
    "healing_space":          "疗愈空间、放下手机、让身体先休息",
    "quirky_retro":           "怪趣复古、美人鱼尾巴与旧时光",
    "3d_latte_art":           "3D拿铁艺术、惊叹先于饮用",
    "middle_east_spice":      "中东香料、肉桂与豆蔻的异乡温度",
    "vertical_cafe":          "垂直空间咖啡馆、建筑就是体验",
    "minimalist_stand":       "极简站台、去掉所有多余的才剩下本质",
    "transparent_craft":      "透明手艺、让你看见每一步的诚实",
    "nakameguro_stroll":      "中目黑散步道、樱花河岸、随走随停",
    "vinyl_culture":          "黑胶文化、老唱片与浓缩、慢慢听完这杯",
    "data_driven_2026":       "数据驱动2026、精准即未来的温柔",
}


# ══════════════════════════════════════════════════════════
#  工具函数
# ══════════════════════════════════════════════════════════

def _http_get(url: str, timeout: int = HTTP_TIMEOUT) -> str:
    """简单 GET，返回文本；失败返回空字符串"""
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            )},
        )
        with urllib.request.urlopen(req, timeout=timeout) as r:
            charset = r.headers.get_content_charset() or "utf-8"
            return r.read().decode(charset, errors="replace")
    except Exception as e:
        log.debug(f"GET 失败 {url}: {e}")
        return ""


def _strip_html(raw: str, max_chars: int = 800) -> str:
    """去除 HTML 标签，截断到 max_chars"""
    text = re.sub(r"<[^>]+>", " ", raw)
    text = html.unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:max_chars]


def _news_id(title: str, brand: str) -> str:
    return hashlib.md5(f"{brand}:{title}".encode()).hexdigest()[:12]


# ══════════════════════════════════════════════════════════
#  缓存（去重）
# ══════════════════════════════════════════════════════════

def load_cache() -> set[str]:
    if CACHE_FILE.exists():
        try:
            return set(json.loads(CACHE_FILE.read_text()))
        except Exception:
            pass
    return set()


def save_cache(seen: set[str]):
    # 只保留最近 2000 条
    recent = list(seen)[-2000:]
    CACHE_FILE.write_text(json.dumps(recent, ensure_ascii=False))


# ══════════════════════════════════════════════════════════
#  情报来源 1：Google News RSS
# ══════════════════════════════════════════════════════════

def fetch_google_news_rss(brand_name: str, jp_name: str) -> list[dict]:
    """
    用 Google News RSS 搜索品牌动态。
    每个品牌发两次查询：英文名 + 日文名。
    """
    results = []
    queries = [brand_name, jp_name]

    for q in queries:
        encoded = urllib.parse.quote(f"{q} コーヒー 新商品 OR ニュース OR キャンペーン")
        url = f"https://news.google.com/rss/search?q={encoded}&hl=ja&gl=JP&ceid=JP:ja"
        raw = _http_get(url)
        if not raw:
            continue
        try:
            root = ET.fromstring(raw)
            items = root.findall(".//item")[:5]
            for item in items:
                title = item.findtext("title", "").strip()
                link  = item.findtext("link", "").strip()
                pub   = item.findtext("pubDate", "").strip()
                desc  = _strip_html(item.findtext("description", ""), 400)
                if title:
                    results.append({
                        "source": "google_news_rss",
                        "title":  title,
                        "link":   link,
                        "date":   pub,
                        "snippet": desc,
                    })
        except ET.ParseError as e:
            log.debug(f"RSS 解析失败 {q}: {e}")
        time.sleep(0.3)

    return results


# ══════════════════════════════════════════════════════════
#  情报来源 2：DuckDuckGo HTML 搜索（无需 API Key）
# ══════════════════════════════════════════════════════════

def fetch_duckduckgo(brand_name: str, jp_name: str) -> list[dict]:
    """
    DuckDuckGo HTML 搜索，抓取摘要文本。
    不需要任何 API Key。
    """
    results = []
    query = f"{jp_name} {brand_name} 新商品 OR キャンペーン OR コラボ site:prtimes.jp OR site:coffee.jp OR site:fashionsnap.com"
    encoded = urllib.parse.quote(query)
    url = f"https://html.duckduckgo.com/html/?q={encoded}"

    raw = _http_get(url)
    if not raw:
        return results

    # 提取搜索结果摘要
    snippets = re.findall(
        r'<a class="result__snippet"[^>]*>(.*?)</a>',
        raw, re.DOTALL
    )
    titles = re.findall(
        r'<a class="result__a"[^>]*>(.*?)</a>',
        raw, re.DOTALL
    )
    links = re.findall(
        r'<a class="result__a" href="([^"]+)"',
        raw
    )

    for i, snippet in enumerate(snippets[:4]):
        title = _strip_html(titles[i]) if i < len(titles) else ""
        link  = links[i] if i < len(links) else ""
        results.append({
            "source":  "duckduckgo",
            "title":   title,
            "link":    link,
            "date":    "",
            "snippet": _strip_html(snippet, 400),
        })

    return results


# ══════════════════════════════════════════════════════════
#  情报来源 3：官网 / PR TIMES 页面抓取
# ══════════════════════════════════════════════════════════

# PR TIMES 是日本最主要的新闻稿平台，绝大多数咖啡品牌都会在这里发稿
PRTIMES_SEARCH = "https://prtimes.jp/main/html/searchrlp/key/{query}"

def fetch_prtimes(brand_name: str, jp_name: str) -> list[dict]:
    results = []
    for q in [jp_name, brand_name]:
        encoded = urllib.parse.quote(q)
        url = PRTIMES_SEARCH.format(query=encoded)
        raw = _http_get(url)
        if not raw:
            continue

        # 抓取新闻稿标题
        titles_raw = re.findall(
            r'<h2 class="list-article__title"[^>]*>(.*?)</h2>',
            raw, re.DOTALL
        )
        dates_raw = re.findall(
            r'<time[^>]*datetime="([^"]+)"',
            raw
        )
        links_raw = re.findall(
            r'href="(/main/html/rd/p/[^"]+)"',
            raw
        )

        for i, t in enumerate(titles_raw[:3]):
            title = _strip_html(t)
            date  = dates_raw[i] if i < len(dates_raw) else ""
            link  = "https://prtimes.jp" + links_raw[i] if i < len(links_raw) else ""
            if title:
                results.append({
                    "source":  "prtimes",
                    "title":   title,
                    "link":    link,
                    "date":    date,
                    "snippet": "",
                })
        time.sleep(0.4)

    return results


# ══════════════════════════════════════════════════════════
#  汇总抓取（三路并行）
# ══════════════════════════════════════════════════════════

def gather_intel(brand: dict, seen: set[str]) -> list[dict]:
    """并行调三路情报源，去重后返回新鲜动态列表"""
    name    = brand["name"]
    jp_name = brand["jp_name"]

    with ThreadPoolExecutor(max_workers=3) as ex:
        futures = {
            ex.submit(fetch_google_news_rss, name, jp_name): "rss",
            ex.submit(fetch_duckduckgo,      name, jp_name): "ddg",
            ex.submit(fetch_prtimes,         name, jp_name): "prt",
        }
        raw_items: list[dict] = []
        for f in as_completed(futures):
            try:
                raw_items.extend(f.result())
            except Exception as e:
                log.warning(f"情报源异常 ({futures[f]}): {e}")

    # 去重 + 过滤已处理
    fresh = []
    for item in raw_items:
        nid = _news_id(item["title"], name)
        if nid not in seen and item["title"].strip():
            seen.add(nid)
            item["_id"] = nid
            fresh.append(item)

    # 按日期粗排（有日期的排前面），截取 MAX_NEWS_PER_BRAND 条
    fresh.sort(key=lambda x: x.get("date", ""), reverse=True)
    return fresh[:MAX_NEWS_PER_BRAND]


# ══════════════════════════════════════════════════════════
#  Gemini 调用
# ══════════════════════════════════════════════════════════

def _gemini_request(prompt: str, temperature: float = 0.85) -> str:
    if not GEMINI_KEY:
        raise EnvironmentError(
            "未找到 GEMINI_API_KEY\n"
            "请执行：export GEMINI_API_KEY='AIzaSy...'"
        )
    url     = GEMINI_URL.format(model=GEMINI_MODEL, key=GEMINI_KEY)
    payload = json.dumps({
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {
            "maxOutputTokens": 1200,
            "temperature":     temperature,
        },
    }).encode()
    req = urllib.request.Request(
        url, data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            res = json.loads(r.read())
            return res["candidates"][0]["content"]["parts"][0]["text"].strip()
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"Gemini {e.code}: {e.read().decode()}") from e
    except (KeyError, IndexError) as e:
        raise RuntimeError(f"响应解析失败: {e}") from e


def distill_news(brand: dict, items: list[dict]) -> str:
    """Step 1 — 让 Gemini 从抓取的原始片段中提炼出一句真正有价值的动态"""
    snippets = "\n".join(
        f"[{i+1}] {it['title']} | {it['snippet'][:200]}"
        for i, it in enumerate(items)
    )
    prompt = f"""你是一名咖啡行业分析师。
以下是关于品牌「{brand['name']}（{brand['jp_name']}）」的最新信息片段：

{snippets}

请判断：
1. 哪条信息最具品牌动态价值（新品/活动/联名/门店/理念更新）？
2. 用一句话（30字以内）提炼出最核心的动态。

只输出那一句中文动态描述，不要编号、不要解释。
如果所有信息都是旧新闻或与品牌无关，输出：【无有效动态】"""
    return _gemini_request(prompt, temperature=0.3)


def generate_copy(brand: dict, news_summary: str) -> str:
    """Step 2 — 生成松浦弥太郎风格的空气感文案"""
    vibe_desc = VIBE_MAP.get(brand.get("vibe", ""), brand.get("vibe", ""))
    prompt = f"""你是一位精通松浦弥太郎散文风格的中日双语文案师。
请为以下竞品动态，创作一段极致「空气感」的 Instagram 文案。

品牌：{brand['name']}（{brand['jp_name']}）
品牌氛围标签：{vibe_desc}
今日动态：{news_summary}

【文案要求】
- 先写日文，再写中文，两段之间空一行
- 日文：3～4 行俳句式短句，每句独立成行，捕捉感官细节与情绪留白
- 中文：与日文对应，但不是直译——用自己的话重述那种感受
- 风格：松浦弥太郎式——留白、克制、用最少的词触碰最深的共鸣
- 禁止：品牌名硬植入、感叹号、emoji、空洞营销词汇
- 结尾附 2～4 个小写英文标签，如 #slow_morning #tokyo_air

只输出文案本身，不要任何解释或前言。"""
    return _gemini_request(prompt, temperature=0.88)


# ══════════════════════════════════════════════════════════
#  输出写入
# ══════════════════════════════════════════════════════════

def write_daily_report(entries: list[dict], today: str):
    """写入 reports/YYYY-MM-DD.md"""
    REPORTS_DIR.mkdir(exist_ok=True)
    path = REPORTS_DIR / f"{today}.md"

    lines = [
        f"# ☕ 竞品情报日报 · {today}\n",
        f"> 共处理 **{len(entries)}** 条竞品动态  \n",
        f"> 生成时间：{datetime.datetime.now().strftime('%H:%M:%S')}\n\n",
        "---\n",
    ]

    for e in entries:
        b = e["brand"]
        lines += [
            f"\n## {b['name']}（{b['jp_name']}）\n",
            f"**类别：** {b.get('category', '')}  \n",
            f"**氛围：** `{b.get('vibe', '')}`  \n",
            f"**情报摘要：** {e['summary']}  \n",
            f"**来源：** {', '.join(set(i['source'] for i in e['items']))}  \n\n",
        ]
        # 原始情报条目（折叠展示）
        lines.append("<details><summary>原始情报片段</summary>\n\n")
        for it in e["items"]:
            link_md = f"[链接]({it['link']})" if it.get("link") else ""
            lines.append(
                f"- **{it['title']}** {link_md}  \n"
                f"  {it.get('snippet','')[:150]}\n\n"
            )
        lines.append("</details>\n\n")
        lines += [
            "### ✨ 空气感文案\n\n",
            e["copy"] + "\n\n",
            "---\n",
        ]

    path.write_text("".join(lines), encoding="utf-8")
    log.info(f"📄 日报已写入：{path}")
    return path


def write_weekly_report(today_str: str):
    """
    每周一自动汇总上一周所有日报，生成 reports/weekly_YYYY-Www.md
    """
    today = datetime.date.fromisoformat(today_str)
    if today.weekday() != 0:   # 只在周一执行
        return

    # 收集过去 7 天的日报
    REPORTS_DIR.mkdir(exist_ok=True)
    week_label = today.strftime("%Y-W%W")
    week_path  = REPORTS_DIR / f"weekly_{week_label}.md"

    collected = []
    for i in range(1, 8):
        day = today - datetime.timedelta(days=i)
        p   = REPORTS_DIR / f"{day.isoformat()}.md"
        if p.exists():
            collected.append((day.isoformat(), p.read_text(encoding="utf-8")))

    if not collected:
        log.info("没有找到上周日报，跳过周报生成")
        return

    # 让 Gemini 生成执行摘要
    all_summaries = "\n\n".join(
        f"=== {d} ===\n{txt[:3000]}" for d, txt in collected
    )
    prompt = f"""你是一名跨境咖啡品牌战略分析师。
以下是本周（{week_label}）每日竞品情报日报的汇总内容：

{all_summaries[:8000]}

请生成一份「竞品周报」，包含：
1. **本周关键动态摘要**（3～5条 bullet，每条不超过50字）
2. **值得警惕的竞品动作**（哪个品牌在发力，为什么值得关注）
3. **可借鉴的灵感方向**（对我方跨境品牌的启示，2～3点）
4. **下周值得持续跟踪的品牌**（列出2～3个，附理由）

用简洁专业的中文输出，Markdown 格式。"""

    try:
        exec_summary = _gemini_request(prompt, temperature=0.4)
    except Exception as e:
        exec_summary = f"（周报 AI 摘要生成失败：{e}）"

    header = (
        f"# 📊 竞品周报 · {week_label}\n\n"
        f"> 汇总日期：{today_str}  \n"
        f"> 覆盖日报：{', '.join(d for d, _ in collected)}\n\n"
        "---\n\n"
        "## 🧠 AI 执行摘要\n\n"
        + exec_summary
        + "\n\n---\n\n## 📋 本周日报归档\n\n"
    )
    archive = "\n\n".join(
        f"### {d}\n\n{txt}" for d, txt in collected
    )

    week_path.write_text(header + archive, encoding="utf-8")
    log.info(f"📊 周报已生成：{week_path}")


# ══════════════════════════════════════════════════════════
#  品牌加载
# ══════════════════════════════════════════════════════════

def load_brands() -> list[dict]:
    with open(COMPETITORS_FILE, encoding="utf-8") as f:
        data = json.load(f)
    brands = []
    for cat in data.get("coffee_competitors", []):
        cat_name = cat.get("category", "")
        if TARGET_CATEGORIES and cat_name not in TARGET_CATEGORIES:
            continue
        for b in cat.get("brands", []):
            b = dict(b)
            b["category"] = cat_name
            if TARGET_BRANDS and b["name"] not in TARGET_BRANDS:
                continue
            brands.append(b)
    return brands


# ══════════════════════════════════════════════════════════
#  主流程
# ══════════════════════════════════════════════════════════

def run():
    today = datetime.date.today().isoformat()
    log.info("=" * 56)
    log.info(f"  ☕  咖啡竞品 AI 情报 Agent  ·  {today}")
    log.info("=" * 56)

    if not GEMINI_KEY:
        log.error("未设置 GEMINI_API_KEY，请先 export GEMINI_API_KEY='...'")
        return

    brands = load_brands()
    log.info(f"已加载 {len(brands)} 个品牌")

    seen       = load_cache()
    entries    = []
    skipped    = 0

    # ── 并发抓取情报 ───────────────────────────────────────
    def process_brand(brand: dict) -> dict | None:
        name = brand["name"]
        log.info(f"  🔍 抓取情报：{name}（{brand['jp_name']}）")
        items = gather_intel(brand, seen)

        if not items:
            log.info(f"     → 无新动态，跳过")
            return None

        log.info(f"     → 获得 {len(items)} 条新情报，提炼中...")
        try:
            summary = distill_news(brand, items)
        except Exception as e:
            log.warning(f"     → 提炼失败: {e}")
            return None

        if "【无有效动态】" in summary:
            log.info(f"     → Gemini 判断无有效动态，跳过")
            return None

        log.info(f"     → 动态：{summary}")
        log.info(f"     → 生成文案中...")
        try:
            copy = generate_copy(brand, summary)
        except Exception as e:
            log.warning(f"     → 文案生成失败: {e}")
            copy = "（文案生成失败）"

        time.sleep(1)  # 避免触发 Gemini 速率限制
        return {"brand": brand, "items": items, "summary": summary, "copy": copy}

    # 串行处理（避免 Gemini 并发限速；抓取阶段已并发）
    for brand in brands:
        result = process_brand(brand)
        if result:
            entries.append(result)
        else:
            skipped += 1

    # ── 保存缓存 ────────────────────────────────────────────
    save_cache(seen)

    # ── 写入日报 ────────────────────────────────────────────
    log.info(f"\n处理完成：{len(entries)} 条有效动态，{skipped} 个品牌跳过")

    if entries:
        daily_path = write_daily_report(entries, today)

        # 终端预览
        print("\n" + "─" * 56)
        print(f"  今日共生成 {len(entries)} 条空气感文案\n")
        for e in entries[:3]:   # 终端只预览前3条
            b = e["brand"]
            print(f"  ▸ {b['name']}（{b['jp_name']}）")
            print(f"    {e['summary']}")
            print()
        if len(entries) > 3:
            print(f"  … 及另外 {len(entries)-3} 条，详见日报")
        print(f"\n  📄 完整日报：{daily_path}")
        print("─" * 56 + "\n")
    else:
        log.info("今日无新动态，未生成日报")

    # ── 周报（每周一自动）──────────────────────────────────
    write_weekly_report(today)


if __name__ == "__main__":
    run()
