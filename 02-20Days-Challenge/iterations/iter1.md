# 迭代 1 ｜ v0.1 → v0.2（2026-11-15）

## 改动依据（全部来自 process_logs 真实日志，非凭空想象）

| # | 日志证据 | 问题 | 修复 |
|---|---|---|---|
| 1 | run_id `20261115-011742`：`天气API ok:false`，open-meteo SSL 握手超时 | open-meteo 在校园网/该网络环境不可达 | 改用 wttr.in 为主源，open-meteo 降级为备源（双源冗余） |
| 2 | run_id `20261115-011949`：天气描述显示英文 "Smoke" | wttr.in 返回英文天气描述未翻译 | 增加中英文映射表（Smoke→霾 等 17 项） |
| 3 | run_id `20261115-015440`（**任务计划程序自动运行时**）：`读取课程表 ok:false`，`'utf-8' codec can't decode byte 0xd0` | 用户用记事本编辑 schedule.csv 被保存为 GBK 编码，程序按 UTF-8 读取失败 | `load_csv()` 增加编码自适应：UTF-8(BOM) 失败自动回退 GBK |

## 改动内容（diff 摘要）

```
src/daily_brief.py
- VERSION = "v0.1"                      → "v0.2"
+ WEATHER_CN = {...}                    # 新增中英文天气映射
- def fetch_weather(): ... open-meteo   # 单一数据源
+ def fetch_weather(): ... wttr.in 主源 + open-meteo 备源（双源 try/except）
- def load_csv(path): open(utf-8-sig)
+ def load_csv(path): try utf-8-sig / except → gbk   # 编码自适应
```

## 验证

修复后运行（run_id `20261115-015615`）：4 个步骤全部 ok:true，success=true，课程/DDL/天气均正常。

## 特别说明

第 3 项 bug 只在"任务计划程序自动运行"时暴露（当时用户刚用记事本改了课程表），
说明自动化运行环境与手动运行存在差异——这正是"连续运行日志"的价值：
**手动测试通过 ≠ 自动化运行可靠**。
