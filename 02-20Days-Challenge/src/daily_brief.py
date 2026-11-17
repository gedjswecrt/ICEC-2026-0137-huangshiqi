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
import campus_news

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(BASE, "data")
OUT = os.path.join(BASE, "output")
LOGS = os.path.join(BASE, "process_logs")
os.makedirs(OUT, exist_ok=True)
os.makedirs(LOGS, exist_ok=True)

VERSION = "v0.4"
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
              "patchy rain possible": "可能有雨", "patchy rain nearby": "局部零星小雨",
              "light showers": "零星阵雨", "patchy light rain": "局部小雨",
              "light rain shower": "零星小雨", "moderate or heavy rain shower": "阵雨",
              "thundery showers possible": "可能有雷阵雨", "patchy light drizzle": "局部毛毛雨",
              "partly cloudy night": "夜间多云", "clear night": "夜间晴"}
# 兜底规则：查不到的英文描述按关键词粗译，避免英文原句直接出现在早报上
WEATHER_FALLBACK = [("rain", "有雨"), ("drizzle", "毛毛雨"), ("snow", "有雪"),
                    ("thunder", "雷雨"), ("shower", "阵雨"), ("cloud", "多云"),
                    ("fog", "有雾"), ("mist", "薄雾"), ("sunny", "晴"), ("clear", "晴")]


def weather_cn(desc_en):
    """三段式翻译：精确匹配 → 关键词兜底 → 原文（并标记未译，便于日志统计覆盖盲区）"""
    key = desc_en.strip().lower()
    if key in WEATHER_CN:
        return WEATHER_CN[key], False
    for kw, cn in WEATHER_FALLBACK:
        if kw in key:
            return cn, False
    return desc_en, True


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
        desc_cn, untranslated = weather_cn(desc_en)
        desc = (f"{desc_cn}，"
                f"{cur['temp_C']}°C，湿度{cur['humidity']}%，"
                f"风速{cur['windspeedKmph']}km/h")
        if untranslated:
            # 记录翻译盲区，供后续补全映射表（不视为运行错误）
            desc += f"（原文: {desc_en}）"
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

    # 4. 校园资讯/生活贴士（按日期轮换，同一天固定、每天不同；响应用户反馈 U01/U02）
    t0 = time.perf_counter()
    tips_today = []
    try:
        tips_all = [t for t in load_csv(os.path.join(DATA, "tips.csv"))
                    if (t.get("内容") or "").strip()]
        if tips_all:
            offset = today.timetuple().tm_yday  # 一年中的第几天
            tips_today = [tips_all[(offset + i) % len(tips_all)] for i in range(min(3, len(tips_all)))]
        step("读取资讯", True, f"池子{len(tips_all)}条 / 今日取{len(tips_today)}条",
             int((time.perf_counter() - t0) * 1000))
    except Exception as e:
        step("读取资讯", False, str(e))
        log["errors"].append(f"tips: {e}")

    # 5. 学校官网通知（v0.4 新增，响应用户需求：官网信息自动爬取）
    try:
        notices, cost = campus_news.fetch_notices(limit=5)
        log["api_calls"] += 1
        step("官网通知", True, f"抓到{len(notices)}条，最新 {notices[0]['date']}", cost)
    except Exception as e:
        notices = []
        step("官网通知", False, f"抓取失败，早报降级生成：{e}")
        log["errors"].append(f"notice: {e}")

    # 6. 生成 HTML
    t0 = time.perf_counter()
    date_str = today.strftime("%Y-%m-%d")
    out_path = os.path.join(OUT, f"早报_{date_str}.html")

    def rows(cs, mark_status=False):
        if not cs:
            return "<p>今天没有课，好好休息或抓紧 DDL 🙂</p>"
        now = datetime.now().time()
        out = []
        for c in cs:
            status = ""
            if mark_status:  # v0.4：给今天的课加"进行中/已结束/未开始"标记（U03 反馈）
                try:
                    st = datetime.strptime(c["开始"], "%H:%M").time()
                    et = datetime.strptime(c["结束"], "%H:%M").time()
                    if now < st:
                        status = '<span class="tag st-todo">未开始</span>'
                    elif now <= et:
                        status = '<span class="tag st-now">进行中</span>'
                    else:
                        status = '<span class="tag st-done">已结束</span>'
                except ValueError:
                    status = ""
            out.append(f"<tr><td>{c['开始']}-{c['结束']}</td>"
                       f"<td>{c['课程']}{status}</td><td>{c['地点']}</td></tr>")
        return "".join(out)

    # v0.4：DDL 文案歧义修复 + 紧急高亮（U03 反馈：还剩0天看不懂、重点不突出）
    def ddl_item(d):
        n = d["剩余天数"]
        if n == 0:
            word = "今天截止！"
        elif n == 1:
            word = "明天截止"
        else:
            word = f"还剩 {n} 天"
        cls = ' class="ddl-urgent"' if n <= 3 else ""
        return (f'<li{cls}>【{d["重要度"]}】{d["事项"]} —— '
                f'<b>{word}</b>（{d["截止日期"]}）</li>')

    ddl_html = "".join(ddl_item(d) for d in near_ddl) or "<li>近 7 天没有 DDL，放松～</li>"

    notice_html = ("".join(
        f'<li><span class="ndate">{n_["date"]}</span>'
        f'<a href="{n_["url"]}" target="_blank">{n_["title"]}</a></li>'
        for n_ in notices)
        or "<li>今日未获取到（官网暂时无法访问，不影响其余板块）</li>")

    tips_html = ("".join(
        f"<li>【{t.get('类型', '')}】{t['内容']}</li>" for t in tips_today)
        or "<li>今日贴士待补充（data/tips.csv）</li>")

    html = f"""<!DOCTYPE html><html lang="zh"><head><meta charset="utf-8">
<title>校园早报 {date_str}</title><style>
body{{font-family:'Microsoft YaHei';max-width:640px;margin:24px auto;padding:0 16px;color:#222}}
h1{{color:#1a5fb4;border-bottom:3px solid #1a5fb4;padding-bottom:8px}}
.card{{background:#f6f8fa;border-radius:10px;padding:16px 20px;margin:14px 0}}
.card h2{{margin:0 0 10px;font-size:17px;color:#1a5fb4}}
table{{border-collapse:collapse;width:100%}} td{{border-bottom:1px solid #ddd;padding:7px 6px}}
.badge{{display:inline-block;background:#1a5fb4;color:#fff;border-radius:6px;padding:2px 10px;font-size:13px}}
ul{{padding-left:20px;margin:6px 0}} li{{margin:5px 0;line-height:1.5}}
.ddl-urgent{{color:#c0392b;font-weight:bold}}
.ddl-urgent b{{background:#fdecea;padding:1px 6px;border-radius:4px}}
.tag{{display:inline-block;border-radius:4px;padding:1px 8px;font-size:12px;margin-left:8px;vertical-align:middle}}
.st-now{{background:#e67e22;color:#fff}} .st-done{{background:#e0e0e0;color:#888}} .st-todo{{background:#eaf2fb;color:#1a5fb4}}
.notice li{{margin:7px 0}} .ndate{{color:#999;font-size:12px;margin-right:8px}}
.notice a{{color:#1a5fb4;text-decoration:none}}
footer{{color:#999;font-size:12px;text-align:center}}
</style></head><body>
<h1>校园早报 <span class="badge">{date_str} {WEEK_CN[week_idx]}</span></h1>
<div class="card"><h2>🌤 今日天气（{config.CITY_NAME}）</h2><p>{weather}</p></div>
<div class="card"><h2>📚 今日课程</h2><table>{rows(courses, mark_status=True)}</table></div>
<div class="card"><h2>⏰ 临近截止（{config.DDL_DAYS}天内）</h2><ul>{ddl_html}</ul></div>
<div class="card"><h2>🏫 学校官网通知</h2><ul class="notice">{notice_html}</ul></div>
<div class="card"><h2>💡 生活贴士</h2><ul>{tips_html}</ul></div>
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
