# -*- coding: utf-8 -*-
"""
每日校园早报生成器 v0.1
========================
每天自动运行一次：
  1. 读取课程表 schedule.csv，筛出今天/明天的课
  2. 读取 DDL 列表 ddl.csv，筛出临近事项
  3. 调用 Open-Meteo 免费天气 API 拿今日天气
  4. 生成 output/早报_YYYY-MM-DD.html
  5. 把本次运行的完整遥测日志写入 process_logs/（JSONL）

运行：python src/daily_brief.py
"""
import csv
import json
import os
import sys
import time
import urllib.request
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(BASE, "data")
OUT = os.path.join(BASE, "output")
LOGS = os.path.join(BASE, "process_logs")
os.makedirs(OUT, exist_ok=True)
os.makedirs(LOGS, exist_ok=True)

VERSION = "v0.2"
WEEK_CN = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]


def load_csv(path):
    """兼容编码：优先 UTF-8(BOM)，失败则回退 GBK（用户用记事本编辑常存 ANSI）"""
    try:
        with open(path, encoding="utf-8-sig") as f:
            return list(csv.DictReader(f))
    except UnicodeDecodeError:
        with open(path, encoding="gbk") as f:
            return list(csv.DictReader(f))


WEATHER_CN = {"sunny": "晴", "clear": "晴", "partly cloudy": "多云", "cloudy": "多云",
              "overcast": "阴", "mist": "薄雾", "fog": "雾", "haze": "霾", "smoke": "霾",
              "light drizzle": "毛毛雨", "light rain": "小雨", "moderate rain": "中雨",
              "heavy rain": "大雨", "light snow": "小雪", "thundery outbreaks": "雷雨",
              "patchy rain possible": "可能有雨", "light showers": "零星阵雨"}


def fetch_weather():
    """
    获取当前天气，返回 (描述, 耗时ms, 数据源)。
    主源 wttr.in（国内可达），备源 open-meteo（校园网下曾超时，保留作冗余）。
    """
    errors = []
    # 主源：wttr.in
    t0 = time.perf_counter()
    try:
        url = f"https://wttr.in/{config.CITY_NAME}?format=j1"
        with urllib.request.urlopen(url, timeout=20) as r:
            raw = json.loads(r.read().decode("utf-8"))
        cost_ms = int((time.perf_counter() - t0) * 1000)
        cur = raw["current_condition"][0]
        desc_en = cur["weatherDesc"][0]["value"].strip()
        desc = (f"{WEATHER_CN.get(desc_en.lower(), desc_en)}，"
                f"{cur['temp_C']}°C，湿度{cur['humidity']}%，"
                f"风速{cur['windspeedKmph']}km/h")
        return desc, cost_ms, "wttr.in"
    except Exception as e:
        errors.append(f"wttr.in: {e}")
    # 备源：open-meteo
    t0 = time.perf_counter()
    try:
        url = (f"https://api.open-meteo.com/v1/forecast"
               f"?latitude={config.LAT}&longitude={config.LON}"
               f"&current=temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m"
               f"&timezone=Asia%2FShanghai")
        with urllib.request.urlopen(url, timeout=15) as r:
            raw = json.loads(r.read().decode("utf-8"))
        cost_ms = int((time.perf_counter() - t0) * 1000)
        cur = raw["current"]
        codes = {0: "晴", 1: "多云", 2: "多云", 3: "阴", 45: "雾", 48: "雾",
                 51: "毛毛雨", 61: "小雨", 63: "中雨", 65: "大雨", 71: "小雪",
                 80: "阵雨", 95: "雷雨"}
        desc = (f"{codes.get(cur['weather_code'], '天气码' + str(cur['weather_code']))}，"
                f"{cur['temperature_2m']}°C，湿度{cur['relative_humidity_2m']}%，"
                f"风速{cur['wind_speed_10m']}km/h")
        return desc, cost_ms, "open-meteo"
    except Exception as e:
        errors.append(f"open-meteo: {e}")
    raise RuntimeError("; ".join(errors))


def main():
    run_id = datetime.now().strftime("%Y%m%d-%H%M%S")
    log = {"run_id": run_id, "version": VERSION,
           "start": datetime.now().isoformat(timespec="seconds"),
           "steps": [], "api_calls": 0, "errors": []}

    def step(name, ok=True, detail="", cost_ms=0):
        log["steps"].append({"step": name, "ok": ok, "detail": detail, "cost_ms": cost_ms})
        print(("✅" if ok else "❌"), name, detail)

    today = datetime.now()
    week_idx = today.weekday()          # 0=周一
    tomorrow_idx = (week_idx + 1) % 7

    # 1. 今天的课
    t0 = time.perf_counter()
    try:
        courses = [c for c in load_csv(os.path.join(DATA, "schedule.csv"))
                   if c["星期"] == WEEK_CN[week_idx]]
        tomorrow = [c for c in load_csv(os.path.join(DATA, "schedule.csv"))
                    if c["星期"] == WEEK_CN[tomorrow_idx]]
        step("读取课程表", True, f"今天{len(courses)}节 / 明天{len(tomorrow)}节",
             int((time.perf_counter() - t0) * 1000))
    except Exception as e:
        courses, tomorrow = [], []
        step("读取课程表", False, str(e))
        log["errors"].append(f"schedule: {e}")

    # 2. 临近 DDL
    t0 = time.perf_counter()
    near_ddl = []
    try:
        for d in load_csv(os.path.join(DATA, "ddl.csv")):
            delta = (datetime.strptime(d["截止日期"], "%Y-%m-%d") - today).days
            if 0 <= delta <= config.DDL_DAYS:
                near_ddl.append({**d, "剩余天数": delta})
        near_ddl.sort(key=lambda x: x["剩余天数"])
        step("读取DDL", True, f"{len(near_ddl)}项临近",
             int((time.perf_counter() - t0) * 1000))
    except Exception as e:
        step("读取DDL", False, str(e))
        log["errors"].append(f"ddl: {e}")

    # 3. 天气 API
    try:
        weather, cost, source = fetch_weather()
        log["api_calls"] += 1
        step("天气API", True, f"{weather}（数据源 {source}）", cost)
    except Exception as e:
        weather, cost = "API 获取失败（不影响早报生成）", 0
        step("天气API", False, str(e), cost)
        log["errors"].append(f"weather: {e}")

    # 4. 生成 HTML
    t0 = time.perf_counter()
    date_str = today.strftime("%Y-%m-%d")
    out_path = os.path.join(OUT, f"早报_{date_str}.html")

    def rows(cs):
        if not cs:
            return "<p>今天没有课，好好休息或抓紧 DDL 🙂</p>"
        return "".join(
            f"<tr><td>{c['开始']}-{c['结束']}</td><td>{c['课程']}</td><td>{c['地点']}</td></tr>"
            for c in cs)

    ddl_html = ("".join(
        f"<li>【{d['重要度']}】{d['事项']} —— 还剩 <b>{d['剩余天数']}</b> 天（{d['截止日期']}）</li>"
        for d in near_ddl) or "<li>近 7 天没有 DDL，放松～</li>")

    html = f"""<!DOCTYPE html><html lang="zh"><head><meta charset="utf-8">
<title>校园早报 {date_str}</title><style>
body{{font-family:'Microsoft YaHei';max-width:640px;margin:24px auto;padding:0 16px;color:#222}}
h1{{color:#1a5fb4;border-bottom:3px solid #1a5fb4;padding-bottom:8px}}
.card{{background:#f6f8fa;border-radius:10px;padding:16px 20px;margin:14px 0}}
.card h2{{margin:0 0 10px;font-size:17px;color:#1a5fb4}}
table{{border-collapse:collapse;width:100%}} td{{border-bottom:1px solid #ddd;padding:7px 6px}}
.badge{{display:inline-block;background:#1a5fb4;color:#fff;border-radius:6px;padding:2px 10px;font-size:13px}}
footer{{color:#999;font-size:12px;text-align:center}}
</style></head><body>
<h1>校园早报 <span class="badge">{date_str} {WEEK_CN[week_idx]}</span></h1>
<div class="card"><h2>🌤 今日天气（{config.CITY_NAME}）</h2><p>{weather}</p></div>
<div class="card"><h2>📚 今日课程</h2><table>{rows(courses)}</table></div>
<div class="card"><h2>⏰ 临近截止（{config.DDL_DAYS}天内）</h2><ul>{ddl_html}</ul></div>
<div class="card"><h2>📖 明天预告</h2><table>{rows(tomorrow)}</table></div>
<footer>生成时间 {datetime.now().strftime('%H:%M:%S')} · 早报机器人 {VERSION}</footer>
</body></html>"""
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    step("生成早报HTML", True, out_path, int((time.perf_counter() - t0) * 1000))

    # 5. 写遥测日志（JSONL 追加）
    log["end"] = datetime.now().isoformat(timespec="seconds")
    log["total_cost_ms"] = sum(s["cost_ms"] for s in log["steps"])
    log["success"] = len(log["errors"]) == 0
    log_file = os.path.join(LOGS, f"telemetry_{today.strftime('%Y%m%d')}.jsonl")
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(log, ensure_ascii=False) + "\n")
    print("\n📄 日志已写入:", log_file)
    print("📰 早报已生成:", out_path)
    return 0 if log["success"] else 1


if __name__ == "__main__":
    sys.exit(main())
