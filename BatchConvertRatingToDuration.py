import os
import requests
import re
import time

# --- 核心路径逻辑改进 ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MOVIES_DIR = os.path.join(BASE_DIR, "movies_details") 

OMDB_KEY = "d79c78b4"
TMDB_KEY = "642c02f606f93ef3b7f179994752f663"

def get_duration(name):
    # (保持之前的逻辑不变...)
    clean_name = name.split('(')[0].split('/')[0].strip()
    try:
        r = requests.get(f"http://www.omdbapi.com/?apikey={OMDB_KEY}&t={clean_name}", timeout=5)
        data = r.json()
        if data.get("Response") == "True":
            nums = re.findall(r'\d+', data.get("Runtime", ""))
            if nums: return nums[0]
        
        r = requests.get(f"https://api.themoviedb.org/3/search/movie?api_key={TMDB_KEY}&query={clean_name}", timeout=5)
        res = r.json().get("results")
        if res:
            m_id = res[0]['id']
            r_detail = requests.get(f"https://api.themoviedb.org/3/movie/{m_id}?api_key={TMDB_KEY}", timeout=5)
            rt = r_detail.json().get("runtime")
            if rt: return str(rt)
    except: pass
    return "待查"

def process_file(file_path):
    print(f"\n📂 正在处理文件: {os.path.basename(file_path)}")
    new_lines = []
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        
    for line in lines:
        processed_line = line
        if "|" in line and "---" not in line:
            parts = [p.strip() for p in line.split("|")]
            if "豆瓣评分" in line:
                processed_line = line.replace("豆瓣评分", "时长(分钟)")
            elif len(parts) >= 5 and parts[1] != "名称":
                movie_name = parts[1]
                print(f"  🔍 正在获取 [{movie_name}] 的时长...", end="\r")
                duration = get_duration(movie_name)
                parts[3] = duration
                processed_line = "| " + " | ".join(parts[1:-1]) + " |\n"
                time.sleep(0.2)
        new_lines.append(processed_line)

    with open(file_path, 'w', encoding='utf-8') as f:
        f.writelines(new_lines)

def main():
    # 调试信息
    print(f"脚本位置: {BASE_DIR}")
    print(f"目标文件夹: {MOVIES_DIR}")

    if not os.path.exists(MOVIES_DIR):
        # 尝试自动修正：如果用户写错了文件夹名，列出当前目录下所有文件夹提醒用户
        dirs = [d for d in os.listdir(BASE_DIR) if os.path.isdir(os.path.join(BASE_DIR, d))]
        print(f"❌ 找不到 'movies_details'。当前目录下存在的文件夹有: {dirs}")
        return
    
    files = [f for f in os.listdir(MOVIES_DIR) if f.endswith(".md")]
    if not files:
        print("Empty folder: No .md files found.")
        return

    for f_name in files:
        process_file(os.path.join(MOVIES_DIR, f_name))
    print("\n\n✨ 任务完成！")

if __name__ == "__main__":
    main()