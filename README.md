# ICEC-2026-0137-huangshiqi

> ICEC 2026 智能·创造者创新实验班选拔考核仓库
> 流程记录：GitHub 过程留痕 + 阶段一实地测评 + 阶段二项目 + 阶段三面试

## 个人简介

- 姓名：黄诗棋
- 学号：2024400137
- 准考证编号：ICEC-2027045
- 院系专业：信息与通信学院 · 人工智能技术应用（2024级技师）

## 选题说明

### 阶段一（基础素养实地测评 · 10 选 2）

| 课题 | 内容 | 目录 |
|---|---|---|
| 课题 08 | 多姿态步态加速度特征采集与对比 | [`01-Field-Discovery/Task08-Gait/`](01-Field-Discovery/Task08-Gait/) |
| 课题 10 | 日常数字任务耗时审计与 AI 批处理实证 | [`01-Field-Discovery/Task10-Audit/`](01-Field-Discovery/Task10-Audit/) |

**课题 08 成果**：用 PhyPhox 采集静止 / 慢走 / 快跑 / 上下楼梯 4 种姿态三轴加速度，提取动态分量标准差 σ 与主频 f0，得到可判别四类动作的阈值规则（σ<0.5 静止、0.5~2.0 慢走、2.0~5.0 楼梯、>5.0 快跑），4 组实测数据全部分类正确。

**课题 10 成果**：以「10 个命名混乱的文件批量规范化」为任务，人工操作实测 170.4 s，AI 脚本 0.663 s，加速比 257 倍；并给出人机校验规则与「小批量场景下脚本反而不划算」的成本边界分析。

### 阶段二（开放式项目挑战 · 8 选 1）

**项目四：解决校园真实痛点的轻量化实用程序研发与日常运行日志验证**

- 作品：**每日校园早报生成器**（最终 v0.7）—— 每天 07:30 自动生成当天的天气（双源降级 + 降温提醒）、课表实时状态、临近 DDL、官网通知、明日预告，输出单文件 HTML 供同学查看
- 目录：[`02-20Days-Challenge/`](02-20Days-Challenge/)
- 关键交付：
  - **总结报告** → [`02-20Days-Challenge/REPORT.md`](02-20Days-Challenge/REPORT.md)（日志分析、6 次迭代汇总、结论）
  - 连续 7 天自动化运行日志 → [`02-20Days-Challenge/process_logs/`](02-20Days-Challenge/process_logs/)（JSONL，22 条，含时间戳、步骤耗时、报错）
  - 基于日志的迭代记录 → [`02-20Days-Challenge/iterations/`](02-20Days-Challenge/iterations/)（6 次，含版本史 `VERSION_HISTORY.md`）
  - 完整源码 → [`02-20Days-Challenge/src/`](02-20Days-Challenge/src/)
  - 8 位真实用户反馈 → [`02-20Days-Challenge/data/feedback.csv`](02-20Days-Challenge/data/feedback.csv) + `screenshots/`

## 目录结构

```
├── README.md               # 本文件：个人简介与选题说明
├── 01-Field-Discovery/     # 阶段一：报告、原始数据、照片
│   ├── Task08-Gait/        #   课题08 步态加速度
│   └── Task10-Audit/       #   课题10 耗时审计
├── 02-20Days-Challenge/    # 阶段二：源码、process_logs/、iterations/
│   ├── src/                #   程序源码
│   ├── data/               #   课表、DDL、用户反馈表
│   ├── docs/               #   实施方案、用户反馈采集方案
│   ├── process_logs/       #   ⭐ 每日运行日志（JSONL）
│   ├── iterations/         #   ⭐ 迭代记录与版本史
│   ├── output/             #   生成的早报 HTML
│   └── screenshots/        #   用户反馈截图等过程证据
└── 03-AI-Collaboration/    # 关键 AI 提问与排障记录
```

## 设备与工具

- 数据采集：iPhone + PhyPhox（加速度传感器，100 Hz）
- 分析与开发：Python 3.13（numpy / pandas / matplotlib）、Windows 任务计划程序
- 天气数据源：wttr.in（主）+ Open-Meteo（备），双源冗余
- AI 协作工具：DeepSeek / WorkBuddy 等大模型（排障与代码生成，关键对话见 `03-AI-Collaboration/`）

## 提交说明

本仓库按「跨多日连续过程数据」要求持续提交，每次 commit 对应实际完成的工作（补数据、修 bug、改版、采集反馈），可通过 `git log --oneline` 查看完整时间线。
