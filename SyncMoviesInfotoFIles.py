import os
import requests
import time
import re

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LIST_FILE = os.path.join(BASE_DIR, "NewUpdatingMoviesLists.txt")
MOVIES_DIR = os.path.join(BASE_DIR, "movies_details")

HEADERS = {"User-Agent": "Mozilla/5.0"}
OMDB_KEY = "d79c78b4"
TMDB_KEY = "642c02f606f93ef3b7f179994752f663"

# ---------------- API Fetching (Updated for Duration) ----------------

def get_duration_from_api(api_data):
    """从API返回的数据中提取分钟数"""
    # OMDB 返回 "142 min"
    # TMDB 返回 142 (int)
    runtime = api_data.get("Runtime") or api_data.get("runtime")
    if not runtime: return ""
    
    nums = re.findall(r'\d+', str(runtime))
    return nums[0] if nums else ""

def omdb(name):
    try:
        r = requests.get(f"http://www.omdbapi.com/?apikey={OMDB_KEY}&t={name}", timeout=10)
        j = r.json()
        return j if j.get("Response") == "True" else None
    except: return None

def tmdb(name):
    try:
        # 先搜索ID
        r = requests.get(f"https://api.themoviedb.org/3/search/movie?api_key={TMDB_KEY}&query={name}", timeout=10)
        results = r.json().get("results")
        if results:
            movie_id = results[0]['id']
            # 再获取详情（详情里才有时长）
            r_detail = requests.get(f"https://api.themoviedb.org/3/movie/{movie_id}?api_key={TMDB_KEY}", timeout=10)
            return r_detail.json()
    except: return None

def get_movie_info(name):
    intro = wiki_cn(name) or wiki_en(name)
    api = omdb(name) or tmdb(name)

    year = ""
    duration = "" # 替换之前的 rate

    if api:
        year = api.get("Year") or api.get("release_date", "")[:4]
        duration = get_duration_from_api(api)
        if not intro:
            intro = api.get("Plot") or api.get("overview")

    intro = summarize(intro)
    if not (intro or year or duration): return None
    return year, duration, intro

# ---------------- Rest of the functions (Keep logic but change variable names) ----------------

def wiki_cn(title):
    try:
        r = requests.get(f"https://zh.wikipedia.org/api/rest_v1/page/summary/{title}", headers=HEADERS, timeout=10)
        if r.status_code == 200: return r.json().get("extract")
    except: pass
    return None

def wiki_en(title):
    try:
        r = requests.get(f"https://en.wikipedia.org/api/rest_v1/page/summary/{title}", headers=HEADERS, timeout=10)
        if r.status_code == 200: return r.json().get("extract")
    except: pass
    return None

def summarize(text):
    if not text: return ""
    if re.search("[\u4e00-\u9fa5]", text):
        return "".join(re.findall(r"[\u4e00-\u9fa5]", text))[:60]
    words = re.findall(r"[A-Za-z']+", text)
    return " ".join(words[:40])

def append_table(file_path, movie, year, duration, intro):
    with open(file_path, "a+", encoding="utf-8") as f:
        ensure_newline_end(f)
        # 注意这里格式保持一致
        f.write(f"| {movie} | {year} | {duration} | {intro} |\n")

def ensure_newline_end(f):
    f.seek(0, os.SEEK_END)
    if f.tell() > 0:
        f.seek(f.tell() - 1)
        if f.read(1) != "\n": f.write("\n")

# ----- 原封不动搬过来的 00 特殊处理逻辑 (5 columns wrap) -----
def append_simple(file_path, movie):
    with open(file_path, "r+", encoding="utf-8") as f:
        lines = f.read().splitlines()

        if len(lines) < 3:
            lines.append("")

        last_row = lines[-1]

        if not last_row.startswith("|"):
            last_row = ""

        items = [i for i in last_row.split("|") if i]

        if len(items) >= 5:
            lines.append(f"|{movie}|")
        else:
            if last_row == "":
                lines[-1] = f"|{movie}|"
            else:
                lines[-1] = last_row + f"{movie}|"

        f.seek(0)
        f.write("\n".join(lines) + "\n")
        f.truncate()

def process_movie(movie):
    print(f"\n🎬 Current Movie: {movie}")
    
    files = sorted(os.listdir(MOVIES_DIR))
    for f in files: print(f)
    prefix = input("\nSelect prefix (00/01/02...): ").strip()
    target = next((os.path.join(MOVIES_DIR, f) for f in files if f.startswith(prefix)), None)
    
    if not target: return False
    
    # 🌟 搬过来的 00 判断逻辑：如果是00，不需要请求网络API，直接单电影名追加并返回
    if prefix == "00":
        append_simple(target, movie)
        print(f"✅ Updated: {movie}")
        return True
        
    info = get_movie_info(movie)
    if not info: return False
    
    year, duration, intro = info
    append_table(target, movie, year, duration, intro)
    print(f"✅ Updated: {movie} ({duration} min)")
    return True

def main():
    if not os.path.exists(LIST_FILE): return
    with open(LIST_FILE, "r", encoding="utf-8") as f:
        movies = [m.strip() for m in f if m.strip()]
    
    failed = []
    for movie in movies:
        if not process_movie(movie): failed.append(movie)
        time.sleep(1)
    
    with open(LIST_FILE, "w", encoding="utf-8") as f:
        for m in failed: f.write(m + "\n")

if __name__ == "__main__":
    main()