"""Synchronize movie Markdown tables with IMDb ratings and original titles.

Normal use remains interactive for adding entries from NewUpdatingMoviesLists.txt.
Use ``python SyncMoviesInfotoFIles.py --sync-all`` to update every existing movie
entry below movies_details in one pass.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import html
import os
import re
import time
from typing import Any, Dict, Iterable, List, Optional, Tuple

import requests


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LIST_FILE = os.path.join(BASE_DIR, "NewUpdatingMoviesLists.txt")
MOVIES_DIR = os.path.join(BASE_DIR, "movies_details")

HEADERS = {"User-Agent": "FreeDark-Movie-Sync/2.0"}
OMDB_KEY = "d79c78b4"
TMDB_KEY = "642c02f606f93ef3b7f179994752f663"
REQUEST_TIMEOUT = 15

session = requests.Session()
session.headers.update(HEADERS)


# These entries correct titles whose current year or Chinese name makes a
# generic API search select a different film.
MOVIE_OVERRIDES: Dict[str, Dict[str, str]] = {
    "1987：黎明到来的那一天": {
        "imdb_id": "tt6493286",
        "display": "1987：黎明到来的那一天",
        "year": "2018",
        "english": "1987: When the Day Comes",
    },
    "黎明到来的那一天": {
        "imdb_id": "tt6493286",
        "display": "1987：黎明到来的那一天",
        "year": "2018",
        "english": "1987: When the Day Comes",
    },
    "碟中谍8最终清算": {
        "imdb_id": "tt9603208",
        "display": "碟中谍8：最终清算",
        "year": "2025",
    },
    "魔兽": {"imdb_id": "tt0803096", "display": "魔兽", "year": "2016"},
    "麻将": {"imdb_id": "tt0116962", "display": "麻将", "year": "1996"},
    "剃头匠": {
        "imdb_id": "tt1160619",
        "display": "剃头匠",
        "year": "纪录片",
        "english": "The Old Barber",
    },
    "我们的父辈": {
        "imdb_id": "tt1883092",
        "display": "我们的父辈",
        "year": "2013",
        "english": "Unsere Mütter, unsere Väter / Generation War",
    },
    "婚姻生活": {
        "imdb_id": "tt12682218",
        "display": "婚姻生活",
        "year": "2021",
    },
    "教父": {"imdb_id": "tt0071562", "display": "教父2", "year": "1974"},
    "金刚": {"imdb_id": "tt13000980", "display": "金刚川", "year": "2020"},
    "大河恋": {
        "imdb_id": "tt0105265",
        "display": "大河恋",
        "year": "1992",
    },
    "血钻": {"imdb_id": "tt0450259", "display": "血钻", "year": "2006"},
    "星际穿越": {
        "imdb_id": "tt0816692",
        "display": "星际穿越",
        "year": "2014",
    },
    "马语者": {
        "imdb_id": "tt0119314",
        "display": "马语者",
        "year": "1998",
    },
    "荒岛余生": {
        "imdb_id": "tt0162222",
        "display": "荒岛余生",
        "year": "2000",
    },
    "角斗士": {"imdb_id": "tt0172495", "display": "角斗士", "year": "2000"},
    "勇敢的心": {
        "imdb_id": "tt0112573",
        "display": "勇敢的心",
        "year": "1995",
    },
    "心灵点滴": {
        "imdb_id": "tt2948372",
        "display": "心灵奇旅",
        "year": "2020",
    },
    "The Journey": {
        "imdb_id": "tt0105744",
        "display": "旅途",
        "year": "1992",
    },
    "红鳉鱼": {
        "imdb_id": "tt4396044",
        "display": "红鳉鱼",
        "year": "2015",
    },
    "海街": {
        "imdb_id": "tt3756788",
        "display": "海街日记",
        "year": "2015",
        "english": "Our Little Sister",
    },
    "黄昏双镖客": {
        "imdb_id": "tt0064116",
        "display": "黄昏双镖客",
        "year": "1968",
    },
    "指环王三部曲": {
        "display": "指环王三部曲加长版",
        "year": "2001-2003",
        "rating": "8.9 / 8.8 / 9.0",
        "english": "The Lord of the Rings Trilogy: Extended Editions",
    },
    "1900": {
        "imdb_id": "tt0074084",
        "display": "1900（上 & 下）",
        "year": "1976",
        "english": "Novecento",
    },
}


# 00 record.md is a watchlist without year/rating columns.  Keep its aliases
# explicit because a title without a year is too ambiguous for an API search.
RECORD_ALIASES: Dict[str, str] = {
    "长安的荔枝": "长安的荔枝 (The Lychee Road)",
    "危险关系": "危险关系 (Dangerous Liaisons)",
    "穆赫兰道": "穆赫兰道 (Mulholland Drive)",
    "大逃杀": "大逃杀 (Battle Royale)",
    "高山下的花环": "高山下的花环 (Wreaths at the Foot of the Mountain)",
    "第六感": "第六感 (The Sixth Sense)",
    "死神来了": "死神来了 (Final Destination)",
    "小岛惊魂": "小岛惊魂 (The Others)",
    "逃出绝命岛": "逃出绝命岛 (Awaken)",
    "惊魂记": "惊魂记 (Psycho)",
    "孤岛惊魂": "孤岛惊魂 (Mysterious Island)",
    "黑暗侵袭": "黑暗侵袭 (The Descent)",
    "恐怖游轮": "恐怖游轮 (Triangle)",
    "鬼水怪谈": "鬼水怪谈 (Dark Water)",
    "咒怨": "咒怨 (Ju-On: The Grudge)",
    "雏菊": "雏菊 (Daisies / Sedmikrásky)",
    "致命诱惑": "致命诱惑 (Fatal Attraction)",
    "尖峰时刻": "尖峰时刻 (Rush Hour)",
    "华尔街之狼": "华尔街之狼 (The Wolf of Wall Street)",
    "东京塔": "东京塔 (Tokyo Tower)",
    "逃出克隆岛": "逃出克隆岛 (The Island)",
    "摩托日记": "摩托日记 (The Motorcycle Diaries)",
    "乘船而去": "乘船而去 (Gone with the Boat)",
    "云图": "云图 (Cloud Atlas)",
    "国际市场": "国际市场 (Ode to My Father)",
    "2001天空漫游": "2001：太空漫游 (2001: A Space Odyssey)",
    "天空漫游": "2001：太空漫游 (2001: A Space Odyssey)",
    "太空漫游": "2001：太空漫游 (2001: A Space Odyssey)",
    "全金属外壳": "全金属外壳 (Full Metal Jacket)",
    "巴比伦": "巴比伦 (Babylon)",
    "戏台": "戏台 (The Stage)",
    "钢的琴": "钢的琴 (The Piano in a Factory)",
    "祝你好运里奥·格兰德": "祝你好运里奥·格兰德 (Good Luck to You, Leo Grande)",
    "了不起的盖茨比": "了不起的盖茨比 (The Great Gatsby)",
    "壮志凌云：独行侠": "壮志凌云：独行侠 (Top Gun: Maverick)",
    "拉贝日记": "拉贝日记 (John Rabe)",
    "这里的黎明静悄悄": "这里的黎明静悄悄 (The Dawns Here Are Quiet)",
    "前目的地": "前目的地 (Predestination)",
    "费城故事": "费城故事 (Philadelphia)",
    "生化危机": "生化危机 (Resident Evil)",
    "落凡尘": "落凡尘 (Into the Mortal World)",
    "F1狂飙飞车": "F1狂飙飞车 (F1: The Movie)",
    "狂飙飞车": "F1狂飙飞车 (F1: The Movie)",
    "那山那人那狗": "那山那人那狗 (Postmen in the Mountains)",
    "阿拉伯的劳伦斯": "阿拉伯的劳伦斯 (Lawrence of Arabia)",
    "木乃伊": "木乃伊 (The Mummy)",
    "三岛由纪夫传": "三岛由纪夫传 (Mishima: A Life in Four Chapters)",
    "极限审判": "极限审判 (Mercy)",
    "雷霆特工队": "雷霆特工队 (Thunderbolts*)",
    "拯救大兵瑞恩": "拯救大兵瑞恩 (Saving Private Ryan)",
    "鼹鼠：朝鲜卧底": "鼹鼠：朝鲜卧底 (The Mole: Undercover in North Korea)",
    "哪吒": "哪吒 (Ne Zha)",
    "终结者": "终结者 (The Terminator)",
    "最后的决斗": "最后的决斗 (The Last Duel)",
    "黑夜传说": "黑夜传说 (Underworld)",
    "坠落的审判": "坠落的审判 (Anatomy of a Fall)",
    "后天": "后天 (The Day After Tomorrow)",
    "真实谎言": "真实谎言 (True Lies)",
    "危机13小时": "危机13小时 (13 Hours: The Secret Soldiers of Benghazi)",
    "金矿": "金矿 (Gold)",
    "彗星来的那一夜": "彗星来的那一夜 (Coherence)",
    "恐怖分子": "恐怖分子 (The Terrorizers)",
    "世界上最糟糕的人": "世界上最糟糕的人 (The Worst Person in the World)",
    "伊尼舍林的报丧女妖": "伊尼舍林的报丧女妖 (The Banshees of Inisherin)",
    "黑洞频率": "黑洞频率 (Frequency)",
    "重庆森林": "重庆森林 (Chungking Express)",
    "默杀": "默杀 (A Place Called Silence)",
    "走走停停": "走走停停 (Gold or Shit)",
    "浪客剑心": "浪客剑心 (Rurouni Kenshin)",
}


def request_json(url: str, **params: Any) -> Dict[str, Any]:
    """Return a JSON object, converting network/API failures into an empty one."""
    try:
        response = session.get(url, params=params, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        data = response.json()
        return data if isinstance(data, dict) else {}
    except (requests.RequestException, ValueError):
        return {}


def omdb_by_id(imdb_id: str) -> Dict[str, Any]:
    if not imdb_id:
        return {}
    data = request_json(
        "https://www.omdbapi.com/", apikey=OMDB_KEY, i=imdb_id, plot="short"
    )
    return data if data.get("Response") == "True" else {}


def omdb_by_title(title: str, year: str = "") -> Dict[str, Any]:
    if not title:
        return {}
    params: Dict[str, Any] = {"apikey": OMDB_KEY, "t": title, "plot": "short"}
    if re.fullmatch(r"\d{4}", year):
        params["y"] = year
    data = request_json("https://www.omdbapi.com/", **params)
    return data if data.get("Response") == "True" else {}


def tmdb_search(query: str, language: str) -> List[Dict[str, Any]]:
    if not query:
        return []
    data = request_json(
        "https://api.themoviedb.org/3/search/movie",
        api_key=TMDB_KEY,
        query=query,
        language=language,
        include_adult="false",
    )
    results = data.get("results", [])
    return results if isinstance(results, list) else []


def tmdb_details(movie_id: Any) -> Dict[str, Any]:
    if not movie_id:
        return {}
    return request_json(
        f"https://api.themoviedb.org/3/movie/{movie_id}",
        api_key=TMDB_KEY,
        append_to_response="external_ids",
        language="en-US",
    )


def year_from_text(value: str) -> str:
    match = re.search(r"(?<!\d)(\d{4})(?!\d)", value or "")
    return match.group(1) if match else ""


def normalize_title(value: str) -> str:
    value = html.unescape(value or "").lower()
    return re.sub(r"[^a-z0-9\u4e00-\u9fff\u3040-\u30ff\uac00-\ud7af]+", "", value)


def title_queries(title: str) -> List[str]:
    """Produce useful search terms from a cell containing several aliases."""
    title = re.sub(r"\s+", " ", title).strip()
    queries = [title]
    for inside in re.findall(r"[（(]([^（）()]*)[）)]", title):
        for item in re.split(r"\s*/\s*|\s+or\s+", inside, flags=re.I):
            item = item.strip().rstrip("?")
            if item:
                queries.append(item)
    without_notes = re.sub(
        r"[（(][^（）()]*[）)]|加长版|上下部|上\s*[&＆]\s*下|\s*[–-]\s*\d{4}$",
        "",
        title,
    ).strip()
    if without_notes:
        queries.append(without_notes)
    return list(dict.fromkeys(queries))


def override_for(title: str) -> Optional[Dict[str, str]]:
    for key, value in MOVIE_OVERRIDES.items():
        if key in title or normalize_title(title) == normalize_title(key):
            return value
    return None


def candidate_score(candidate: Dict[str, Any], title: str, year_hint: str) -> float:
    candidate_title = " ".join(
        str(candidate.get(key, ""))
        for key in ("title", "original_title")
    )
    wanted = normalize_title(title)
    actual = normalize_title(candidate_title)
    score = float(candidate.get("popularity") or 0)
    wanted_year = year_from_text(year_hint)
    candidate_year = year_from_text(str(candidate.get("release_date", "")))
    if wanted_year and wanted_year == candidate_year:
        score += 1000
    if wanted and (wanted in actual or actual in wanted):
        score += 250
    for query in title_queries(title):
        normalized_query = normalize_title(query)
        if normalized_query and normalized_query in {
            normalize_title(str(candidate.get("title", ""))),
            normalize_title(str(candidate.get("original_title", ""))),
        }:
            score += 500
    score += min(float(candidate.get("vote_count") or 0) / 10000, 20)
    return score


def resolve_tmdb(title: str, year_hint: str) -> Dict[str, Any]:
    candidates: Dict[Any, Dict[str, Any]] = {}
    queries = title_queries(title)
    # Most rows already contain an alias.  Only try shorter fallback queries
    # when the complete title does not produce a result.
    for query in queries[:1]:
        for language in ("zh-CN", "en-US"):
            for result in tmdb_search(query, language):
                if result.get("id"):
                    candidates[result["id"]] = result
    if not candidates:
        for query in queries[1:]:
            for language in ("zh-CN", "en-US"):
                for result in tmdb_search(query, language):
                    if result.get("id"):
                        candidates[result["id"]] = result
    if not candidates:
        return {}
    return max(
        candidates.values(), key=lambda item: candidate_score(item, title, year_hint)
    )


def get_movie_info(title: str, year_hint: str = "") -> Optional[Dict[str, str]]:
    """Resolve one title and return authoritative IMDb metadata."""
    fixed = override_for(title)
    if fixed and fixed.get("rating"):
        display = add_alias(fixed["display"], fixed.get("english", ""))
        return {
            "display": display,
            "year": fixed.get("year", year_hint),
            "rating": fixed["rating"],
            "english": fixed.get("english", ""),
            "original": "",
            "localized": fixed["display"],
            "intro": "",
        }

    omdb: Dict[str, Any] = {}
    tmdb: Dict[str, Any] = {}
    if fixed and fixed.get("imdb_id"):
        omdb = omdb_by_id(fixed["imdb_id"])
    else:
        tmdb = resolve_tmdb(title, year_hint)
        tmdb_detail = tmdb_details(tmdb.get("id"))
        imdb_id = (tmdb_detail.get("external_ids") or {}).get("imdb_id", "")
        if imdb_id:
            omdb = omdb_by_id(imdb_id)
        if not omdb:
            for query in title_queries(title):
                omdb = omdb_by_title(query, year_hint)
                if omdb:
                    break

    rating = str(omdb.get("imdbRating", "")).strip()
    if not rating or rating == "N/A":
        return None

    omdb_title = str(omdb.get("Title", "")).strip()
    localized = str(tmdb.get("title", "")).strip()
    original = str(tmdb.get("original_title", "")).strip()
    if fixed:
        display = add_alias(fixed["display"], fixed.get("english", "") or omdb_title)
    else:
        display = make_display_name(title, localized, original, omdb_title)

    year = (fixed or {}).get("year") or year_hint or str(omdb.get("Year", ""))
    intro = str(omdb.get("Plot", "")).strip()
    return {
        "display": display,
        "year": year,
        "rating": rating,
        "english": omdb_title,
        "original": original,
        "localized": localized,
        "intro": intro,
        "imdb_id": str(omdb.get("imdbID", "")),
    }


def extract_local_title(title: str) -> str:
    """Get the Chinese/Japanese/Korean part already present in a title cell."""
    title = re.sub(r"\s+", " ", title).strip()
    title = re.sub(r"\s*[（(][^（）()]*[）)]", "", title)
    title = re.sub(r"\s*[–-]\s*\d{4}$", "", title).strip()
    matches = re.findall(
        r"[\u4e00-\u9fff\u3040-\u30ff\uac00-\ud7af][\u4e00-\u9fff\u3040-\u30ff\uac00-\ud7af0-9：:、，。！？·\-]*",
        title,
    )
    if matches:
        return max(matches, key=len).strip()
    return title


def choose_foreign_title(localized: str, original: str, english: str) -> str:
    """Prefer an English title for Chinese films and original language otherwise."""
    localized = localized.strip()
    original = original.strip()
    english = english.strip()
    has_cjk_original = bool(
        re.search(r"[\u4e00-\u9fff\u3040-\u30ff\uac00-\ud7af]", original)
    )
    if has_cjk_original:
        return english or localized or original
    return original or english or localized


def add_alias(local_title: str, foreign_title: str) -> str:
    local_title = local_title.strip()
    foreign_title = foreign_title.strip()
    if not foreign_title or normalize_title(local_title) == normalize_title(foreign_title):
        return local_title
    return f"{local_title} ({foreign_title})"


def make_display_name(
    current: str, localized: str, original: str, english: str
) -> str:
    local = extract_local_title(current)
    if not re.search(r"[\u4e00-\u9fff\u3040-\u30ff\uac00-\ud7af]", local):
        local = localized or local
    foreign = choose_foreign_title(localized, original, english)
    if not foreign or normalize_title(foreign) == normalize_title(local):
        return current.strip()
    return f"{local} ({foreign})"


def summarize(text: str) -> str:
    if not text:
        return ""
    if re.search(r"[\u4e00-\u9fff]", text):
        return "".join(re.findall(r"[\u4e00-\u9fff]", text))[:60]
    return " ".join(re.findall(r"[A-Za-z']+", text)[:40])


def split_row(line: str) -> List[str]:
    return [part.strip() for part in line.strip().strip("|").split("|")]


def render_row(cells: Iterable[str]) -> str:
    safe = [str(cell).replace("|", r"\|").strip() for cell in cells]
    return "| " + " | ".join(safe) + " |\n"


def is_separator(cells: List[str]) -> bool:
    return bool(cells) and all(re.fullmatch(r"[-: ]+", cell or "") for cell in cells)


def record_alias_for(title: str) -> Optional[str]:
    for key, alias in RECORD_ALIASES.items():
        if key in title or normalize_title(title) == normalize_title(key):
            return alias
    return None


def batch_movie_info(rows: List[Tuple[str, str]]) -> List[Optional[Dict[str, str]]]:
    """Resolve rows concurrently while keeping their original order."""
    with ThreadPoolExecutor(max_workers=8) as executor:
        return list(executor.map(lambda row: get_movie_info(*row), rows))


def sync_record_file(file_path: str) -> Tuple[int, List[str]]:
    """Add an English/original-language alias to each cell in 00 record.md."""
    with open(file_path, encoding="utf-8") as stream:
        lines = stream.read().splitlines()
    changed = 0
    failures: List[str] = []
    output: List[str] = []
    for line_number, line in enumerate(lines, 1):
        cells = split_row(line) if line.lstrip().startswith("|") else []
        if not cells or line_number <= 2 or is_separator(cells):
            output.append(line + "\n")
            continue
        new_cells: List[str] = []
        for cell in cells:
            display = record_alias_for(cell)
            if display is None:
                display = cell
                failures.append(cell)
            new_cells.append(display)
            changed += display != cell
        output.append("|" + "|".join(new_cells) + "|\n")
    with open(file_path, "w", encoding="utf-8") as stream:
        stream.writelines(output)
    return changed, failures


def sync_movie_table(file_path: str) -> Tuple[int, List[str]]:
    """Replace the old rating/runtime column with the current IMDb rating."""
    with open(file_path, encoding="utf-8") as stream:
        lines = stream.read().splitlines()
    changed = 0
    failures: List[str] = []
    output: List[str] = []
    movie_rows: List[Tuple[str, str, str]] = []
    row_positions: List[int] = []
    header_seen = False
    for line in lines:
        cells = split_row(line) if line.lstrip().startswith("|") else []
        if not cells:
            output.append(line + "\n")
            continue
        if is_separator(cells):
            output.append(render_row(["---"] * 4))
            continue
        if cells[0] == "名称":
            output.append(render_row(["名称", "年份", "IMDb评分", "简介"]))
            header_seen = True
            continue
        if len(cells) < 4 or not header_seen:
            output.append(line + "\n")
            continue
        title, year, _old_rating, intro = cells[:4]
        row_positions.append(len(output))
        movie_rows.append((title, year, intro))
        output.append("")
    infos = batch_movie_info([(title, year) for title, year, _ in movie_rows])
    for position, (title, year, intro), info in zip(row_positions, movie_rows, infos):
        if not info:
            output[position] = render_row([title, year, "待查", intro])
            failures.append(title)
            continue
        # Replace the placeholder inserted above; this keeps file order while
        # allowing all API requests to run concurrently.
        output[position] = render_row([info["display"], info["year"], info["rating"], intro])
        changed += 1
    with open(file_path, "w", encoding="utf-8") as stream:
        stream.writelines(output)
    return changed, failures


def sync_all() -> int:
    if not os.path.isdir(MOVIES_DIR):
        print(f"找不到目录: {MOVIES_DIR}")
        return 1
    total_changed = 0
    failures: List[Tuple[str, str]] = []
    for name in sorted(os.listdir(MOVIES_DIR)):
        if not name.endswith(".md"):
            continue
        path = os.path.join(MOVIES_DIR, name)
        print(f"正在同步: {name}")
        if name.startswith("00"):
            changed, missing = sync_record_file(path)
        else:
            changed, missing = sync_movie_table(path)
        total_changed += changed
        failures.extend((name, title) for title in missing)
        print(f"  已更新 {changed} 项" + (f"，失败 {len(missing)} 项" if missing else ""))
        time.sleep(0.1)
    print(f"同步完成，共更新 {total_changed} 项。")
    if failures:
        print("以下条目没有可用 IMDb 评分，请人工确认:")
        for filename, title in failures:
            print(f"  {filename}: {title}")
        return 2
    return 0


def load_movies() -> List[str]:
    if not os.path.exists(LIST_FILE):
        return []
    with open(LIST_FILE, encoding="utf-8") as stream:
        return [line.strip() for line in stream if line.strip()]


def save_movies(movies: Iterable[str]) -> None:
    with open(LIST_FILE, "w", encoding="utf-8") as stream:
        for movie in movies:
            stream.write(movie + "\n")


def append_record(file_path: str, movie: str) -> None:
    with open(file_path, encoding="utf-8") as stream:
        lines = stream.read().splitlines()
    info = get_movie_info(movie)
    display = info["display"] if info else movie
    if info is None:
        print(f"无法找到 IMDb 信息，保留原名: {movie}")
    if not lines:
        lines = ["|Movie A|Movie B|Movie C|Movie D|Movie E|", "|-----|-----|----|----|----|"]
    if len(lines) < 2:
        lines.append("|-----|-----|----|----|----|")
    last_cells = split_row(lines[-1]) if lines[-1].startswith("|") else []
    if len(last_cells) >= 5:
        lines.append(f"|{display}|")
    else:
        lines[-1] = "|" + "|".join(last_cells + [display]) + "|"
    with open(file_path, "w", encoding="utf-8") as stream:
        stream.write("\n".join(lines) + "\n")


def append_table(file_path: str, info: Dict[str, str]) -> None:
    with open(file_path, encoding="utf-8") as stream:
        lines = stream.read().splitlines()
    if not lines:
        lines = ["| 名称 | 年份 | IMDb评分 | 简介 |", "| --- | --- | --- | --- |"]
    intro = summarize(info.get("intro", ""))
    lines.append(render_row([info["display"], info["year"], info["rating"], intro]).rstrip("\n"))
    with open(file_path, "w", encoding="utf-8") as stream:
        stream.write("\n".join(lines) + "\n")


def process_movie(movie: str) -> bool:
    files = sorted(name for name in os.listdir(MOVIES_DIR) if name.endswith(".md"))
    print("\n电影列表:")
    for name in files:
        print(name)
    prefix = input("\n选择目标编号 (00/01/02...): ").strip()
    target_name = next((name for name in files if name.startswith(prefix)), "")
    if not target_name:
        print("编号无效")
        return False
    target = os.path.join(MOVIES_DIR, target_name)
    if prefix == "00":
        append_record(target, movie)
        return True
    info = get_movie_info(movie)
    if not info:
        print(f"没有找到 {movie} 的 IMDb 评分")
        return False
    append_table(target, info)
    print(f"已添加: {info['display']} ({info['rating']})")
    return True


def interactive_main() -> int:
    movies = load_movies()
    failed: List[str] = []
    for movie in movies:
        if not process_movie(movie):
            failed.append(movie)
        time.sleep(0.2)
    save_movies(failed)
    return 0 if not failed else 2


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync movie lists with IMDb metadata")
    parser.add_argument(
        "--sync-all",
        action="store_true",
        help="update every existing movie row and add aliases in 00 record.md",
    )
    args = parser.parse_args()
    return sync_all() if args.sync_all else interactive_main()


if __name__ == "__main__":
    raise SystemExit(main())
