# -*- coding: utf-8 -*-
"""
课题10（简版）：批量重命名 10 个杂乱文件
命名规则：课题08_<类型>_<两位序号>.<扩展名>
用法：
    python rename_batch.py          # 预览，不改文件
    python rename_batch.py --run    # 真正执行
"""
import os
import sys
import time
import csv
from datetime import datetime

BASE = os.path.dirname(os.path.abspath(__file__))
SAMPLES = os.path.join(BASE, "samples")
RESULTS = os.path.join(BASE, "results")

TYPE_MAP = {
    ".jpg": ("截图", "jpg"),
    ".jpeg": ("截图", "jpg"),
    ".png": ("截图", "png"),
    ".zip": ("数据包", "zip"),
    ".csv": ("表格", "csv"),
    ".md": ("报告", "md"),
}

dry_run = "--run" not in sys.argv

files = sorted(f for f in os.listdir(SAMPLES) if os.path.isfile(os.path.join(SAMPLES, f)))

t0 = time.perf_counter()
counter = {}
plan = []
for f in files:
    ext = os.path.splitext(f)[1].lower()
    if ext not in TYPE_MAP:
        print(f"[跳过] 不支持的类型: {f}")
        continue
    label, newext = TYPE_MAP[ext]
    counter[label] = counter.get(label, 0) + 1
    new_name = f"课题08_{label}_{counter[label]:02d}.{newext}"
    plan.append((f, new_name))

print(f"{'原文件名':<45} -> 新文件名")
for old, new in plan:
    print(f"{old:<45} -> {new}")

if dry_run:
    print(f"\n[预览模式] 共 {len(plan)} 个文件，未做任何修改。加 --run 才真正执行。")
else:
    for old, new in plan:
        os.rename(os.path.join(SAMPLES, old), os.path.join(SAMPLES, new))
    elapsed = time.perf_counter() - t0
    os.makedirs(RESULTS, exist_ok=True)
    with open(os.path.join(RESULTS, "AI耗时.csv"), "a", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        if f.tell() == 0:
            w.writerow(["运行时间", "处理文件数", "总耗时_s"])
        w.writerow([datetime.now().strftime("%Y-%m-%d %H:%M:%S"), len(plan), round(elapsed, 3)])
    print(f"\n✅ 已重命名 {len(plan)} 个文件，总耗时 {elapsed:.3f} 秒")
