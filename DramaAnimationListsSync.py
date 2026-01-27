'''
1. This is a python code file, cycle reading all the list names in file "AanimationDramaLists.txt" in current code same folder.
inside the move list could be like fellowing
'
电影 movie name A
movie name B
movie name C
'
while one name was been read, moving to the updating process from 2 - 7. until finished updating, move back to here, read the next 
movie inside the files. after reading and updated all the movie lists. delete the movie name that updating successfully. 
keep the movie that updating failed. if all success, clear this file, but do not delete.

2. acknowledge this function is for updating infomation to the movies list, always do no change the original file content, 
only add content list to the existing list.
3. automatically detect the current code file path, the processing folder is named drama_animations,traversal the folder
list all the file names with line break, the file name having prefix like 00/01/02 and so on. 
4. remind me to select the target file which need to be updated. I can simply use two number to represent file, like 03 
to represent '03 帮派犯罪.md' this file.
5. if selection is '00', means add only single name, the file in '00' is like the fellowing.
'
|Movie A|Movie B|Movie C|Movie D|Movie E|
|-----|-----|----|----|----|
|长安的荔枝|危险关系|穆赫兰道|大逃杀|高山下的花环|
|第六感|死神来了|小岛惊魂|逃出绝命岛|
'
just add the new movie name to the markdown list.
6. if the selection is not '00', but others 02/03 or so on, is is not recognized, remember to select again
then the updating file content is like the fellowing.
'
| 名称  | 年份  | 豆瓣评分 | 简介  |
| --- | --- | --- | --- |
| 勇闯夺命岛 The Rock | 1996 | 8.6 | 海豹突击队带前FBI专家从恶棍将军手中夺回被化学武器威胁的监狱岛，动作紧张，迈克尔·贝早期经典 |
| 第九区 District 9 | 2009 | 8.4 | 南非外星难民被隔离，揭示人性与种族冲突的科幻寓言 |
'
means via the new movie generate a new line add to the bottom. 
7. Regarding fill the move list, already had the movie name, through any API at least try 3 diferent API if not found.
search 年份, 豆瓣评分, 简介, if the 豆瓣评分 is not exist,  also can use IMDB rate, about 简介, 
please summarize all the content in 60 chinese 汉字

OMDB_KEY = "d79c78b4"
TMDB_KEY = "642c02f606f93ef3b7f179994752f663"

'''

### Adjusting and improving
'''
1. Bug one, after updating a movie name, you should let me select again, to decide which to update next.
2. Bug two, there are no summary info for all there movies, please summarize it. through wiki or any other platform you prefer
3. For summary chinese is the first priority, english is the second, if using english, in 40 words.
4. Bug three, excepct '00',for others, while generate a new line, always keep the cursor from the line beginning, 
if not, move to the next line.
5. for '00'
'
|Movie A|Movie B|Movie C|Movie D|Movie E|
|-----|-----|----|----|----|
'
there are five items, if the five items is full, then move the cursor to the next line.
6.这是电视剧和动漫的生成数据的列表，但是似乎OMDB这个平台已经不适用，请更换其他平台
give me the whole code fixed.
'''

import os
import requests
import time
import re

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LIST_FILE = os.path.join(BASE_DIR, "AanimationDramaLists.txt")
MOVIES_DIR = os.path.join(BASE_DIR, "drama_animations")

HEADERS = {"User-Agent": "Mozilla/5.0"}

TMDB_KEY = "642c02f606f93ef3b7f179994752f663"


# ---------------- Movie List ----------------

def load_movies():
    if not os.path.exists(LIST_FILE):
        return []
    with open(LIST_FILE, "r", encoding="utf-8") as f:
        return [m.strip() for m in f if m.strip()]


def save_movies(left):
    with open(LIST_FILE, "w", encoding="utf-8") as f:
        for m in left:
            f.write(m + "\n")


# ---------------- Folder ----------------

def scan_files():
    files = sorted(os.listdir(MOVIES_DIR))
    print("\n📂 Lists:\n")
    for f in files:
        print(f)
    return files


def select_file(files):
    while True:
        prefix = input("\nSelect prefix (00/01/02...): ").strip()
        for f in files:
            if f.startswith(prefix):
                return os.path.join(MOVIES_DIR, f), prefix
        print("❌ Invalid — try again.")


# ---------------- Wikipedia ----------------

def wiki_cn(title):
    try:
        r = requests.get(
            f"https://zh.wikipedia.org/api/rest_v1/page/summary/{title}",
            headers=HEADERS, timeout=10
        )
        if r.status_code == 200:
            return r.json().get("extract")
    except:
        pass
    return None


def wiki_en(title):
    try:
        r = requests.get(
            f"https://en.wikipedia.org/api/rest_v1/page/summary/{title}",
            headers=HEADERS, timeout=10
        )
        if r.status_code == 200:
            return r.json().get("extract")
    except:
        pass
    return None


# ---------------- TMDB (movies + animation) ----------------

def tmdb_movie(name):
    try:
        r = requests.get(
            f"https://api.themoviedb.org/3/search/multi?api_key={TMDB_KEY}&query={name}",
            timeout=10
        )
        j = r.json()
        if j["results"]:
            return j["results"][0]
    except:
        pass
    return None


# ---------------- TVMaze (drama/anime king) ----------------

def tvmaze(name):
    try:
        r = requests.get(
            f"https://api.tvmaze.com/search/shows?q={name}",
            timeout=10
        )
        j = r.json()
        if j:
            show = j[0]["show"]
            return {
                "year": show.get("premiered", "")[:4],
                "rate": show.get("rating", {}).get("average"),
                "intro": re.sub("<.*?>", "", show.get("summary", ""))
            }
    except:
        pass
    return None


# ---------------- Summary ----------------

def chinese_summary(text):
    return "".join(re.findall(r"[\u4e00-\u9fa5]", text))[:60]


def english_summary(text):
    words = re.findall(r"[A-Za-z']+", text)
    return " ".join(words[:40])


def summarize(text):
    if not text:
        return ""
    if re.search("[\u4e00-\u9fa5]", text):
        return chinese_summary(text)
    return english_summary(text)


# ---------------- Movie Info Core ----------------

def get_movie_info(name):
    intro = wiki_cn(name)

    tv = tvmaze(name)

    tmdb = tmdb_movie(name)

    year = ""
    rate = ""

    if tv:
        year = tv["year"]
        rate = tv["rate"]
        if not intro:
            intro = tv["intro"]

    if tmdb:
        year = year or tmdb.get("release_date", "")[:4] or tmdb.get("first_air_date", "")[:4]
        rate = rate or tmdb.get("vote_average")
        if not intro:
            intro = tmdb.get("overview")

    if not intro:
        intro = wiki_en(name)

    intro = summarize(intro)

    if not (intro or year or rate):
        return None

    return year, rate, intro


# ---------------- Cursor Fix ----------------

def ensure_newline_end(f):
    f.seek(0, os.SEEK_END)
    if f.tell() == 0:
        return
    f.seek(f.tell() - 1)
    if f.read(1) != "\n":
        f.write("\n")


# ---------------- 00 Table (5 columns wrap) ----------------

def append_simple(file_path, movie):
    with open(file_path, "r+", encoding="utf-8") as f:
        lines = f.read().splitlines()

        if len(lines) < 3:
            lines.append("")

        last = lines[-1]
        if not last.startswith("|"):
            last = ""

        items = [i for i in last.split("|") if i]

        if len(items) >= 5:
            lines.append(f"|{movie}|")
        else:
            if last:
                lines[-1] = last + f"{movie}|"
            else:
                lines[-1] = f"|{movie}|"

        f.seek(0)
        f.write("\n".join(lines) + "\n")
        f.truncate()


# ---------------- Normal Table ----------------

def append_table(file_path, movie, year, rate, intro):
    with open(file_path, "a+", encoding="utf-8") as f:
        ensure_newline_end(f)
        f.write(f"| {movie} | {year} | {rate} | {intro} |\n")


# ---------------- One Movie ----------------

def process_movie(movie):
    files = scan_files()
    target, mode = select_file(files)

    info = get_movie_info(movie)

    if not info:
        print(f"❌ No data: {movie}")
        return False

    year, rate, intro = info

    if mode == "00":
        append_simple(target, movie)
    else:
        append_table(target, movie, year, rate, intro)

    print(f"✅ Updated: {movie}")
    return True


# ---------------- Main Loop ----------------

def main():
    movies = load_movies()
    if not movies:
        print("List empty.")
        return

    failed = []

    for movie in movies:
        print(f"\n🎬 {movie}")
        ok = process_movie(movie)
        if not ok:
            failed.append(movie)
        time.sleep(1)

    save_movies(failed)

    if not failed:
        print("\n🎉 All updated — list cleared.")
    else:
        print("\n⚠ Failed movies kept.")


if __name__ == "__main__":
    main()
