# -*- coding: utf-8 -*-
"""
校园官网通知爬虫 v0.4
====================
抓取学校官网「通知公告」栏目列表页，解析出最新的通知（日期 / 标题 / 链接）。

设计要点（对应 iter3）：
  - 单一数据源：https://www.ssti.net.cn/html/tzgg/index.html（列表页一次请求即可）
  - 超时 15 秒：官网偶尔响应慢，超时立即放弃，由 daily_brief 降级处理
  - 失败不中断：本模块只抛异常，早报主程序负责"抓不到也要出报"
  - 正则解析：页面结构固定（<li><a>标题</a><span>日期</span></li>），
    不引入 BeautifulSoup 等重依赖，减少环境崩坏面
"""
import re
import time
import urllib.request

# 官网「通知公告」栏目列表页（学校官网 www.ssti.net.cn）
NOTICE_URL = "https://www.ssti.net.cn/html/tzgg/index.html"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36")

# 匹配：<li><a href="/html/tzgg/29927.html">标题</a> <span class="float_r">2026-11-16</span> </li>
ITEM_RE = re.compile(
    r'<li><a href="(/html/tzgg/\d+\.html)"[^>]*>([^<]+)</a>\s*'
    r'<span class="float_r">(\d{4}-\d{2}-\d{2})</span>')


def fetch_notices(limit=5, timeout=15):
    """抓取最新通知，返回 [{'date','title','url'}, ...]；任何网络/解析问题抛异常。"""
    t0 = time.perf_counter()
    req = urllib.request.Request(NOTICE_URL, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        html = r.read().decode("utf-8", errors="replace")
    items = []
    for m in ITEM_RE.finditer(html):
        items.append({
            "date": m.group(3),
            "title": m.group(2).strip(),
            "url": "https://www.ssti.net.cn" + m.group(1),
        })
        if len(items) >= limit:
            break
    if not items:
        raise ValueError("页面能访问但未解析出任何通知条目（页面结构可能已改版）")
    cost_ms = int((time.perf_counter() - t0) * 1000)
    return items, cost_ms
