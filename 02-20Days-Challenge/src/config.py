# -*- coding: utf-8 -*-
"""
每日校园早报 · 配置文件
修改 CITY 的经纬度可以换城市（查经纬度：https://www.latlong.net/）
"""
# 城市经纬度（深圳龙岗（Longgang），wttr.in 查询用 Shenzhen；换成你学校所在城市）
CITY_NAME = "Shenzhen"
LAT = 22.72
LON = 114.25

# 每天提醒的临近 DDL 天数窗口
DDL_DAYS = 7

# 学校官网「通知公告」栏目（v0.4 新增，由 src/campus_news.py 抓取）
CAMPUS_NOTICE_URL = "https://www.ssti.net.cn/html/tzgg/index.html"
