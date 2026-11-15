# -*- coding: utf-8 -*-
"""
课题08 多姿态步态加速度特征采集与对比 —— 特征提取与可视化
数据来源：Phyphox「加速度(含 g)」iPhone 14,3，约 100 Hz
运行：python analysis.py
输出：features.csv / figures/*.png
"""
import os
import glob
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "Arial Unicode MS"]
plt.rcParams["axes.unicode_minus"] = False

BASE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(BASE, "raw_data")
FIG = os.path.join(BASE, "figures")
os.makedirs(FIG, exist_ok=True)

LABELS = {
    "standing": "静止",
    "walk": "平地慢走",
    "run": "快跑",
    "stairs": "上下楼梯",
}
ORDER = ["standing", "walk", "run", "stairs"]


def load(key):
    path = glob.glob(os.path.join(RAW, f"{key}_*.csv"))[0]
    df = pd.read_csv(path)
    df.columns = ["t", "ax", "ay", "az", "amag"]
    return df


def dominant_freq(t, sig, band=(0.4, 8.0)):
    """对去均值后的合加速度做 FFT，返回分析频段内的主频与相对能量占比"""
    dt = np.median(np.diff(t))
    x = sig - sig.mean()
    win = np.hanning(len(x))
    spec = np.abs(np.fft.rfft(x * win))
    freqs = np.fft.rfftfreq(len(x), dt)
    m = (freqs >= band[0]) & (freqs <= band[1])
    if not m.any():
        return 0.0, 0.0
    idx = np.argmax(spec[m])
    f0 = freqs[m][idx]
    ratio = spec[m][idx] / spec[m].sum()
    return float(f0), float(ratio)


def count_peaks(sig, k=1.0):
    """简易峰计数：超过 mean+k*std 的局部极大值个数"""
    thr = sig.mean() + k * sig.std()
    above = sig > thr
    peaks = 0
    for i in range(1, len(sig) - 1):
        if above[i] and sig[i] >= sig[i - 1] and sig[i] > sig[i + 1]:
            peaks += 1
    return peaks


rows, data = [], {}
for key in ORDER:
    df = load(key)
    t = df["t"].to_numpy()
    amag = df["amag"].to_numpy()
    az = df["az"].to_numpy()
    dt = np.median(np.diff(t))
    dyn = amag - amag.mean()          # 动态分量（去除重力与佩戴姿态偏置）
    f0, ratio = dominant_freq(t, amag)
    n_peaks = count_peaks(amag)
    rows.append({
        "姿态": LABELS[key],
        "采样率_Hz": round(1 / dt, 1),
        "时长_s": round(t[-1] - t[0], 2),
        "样本数": len(t),
        "合加速度均值_m_s2": round(amag.mean(), 2),
        "合加速度标准差_m_s2": round(amag.std(), 2),
        "合加速度峰峰值_m_s2": round(amag.max() - amag.min(), 2),
        "动态分量RMS_m_s2": round(np.sqrt((dyn ** 2).mean()), 2),
        "z轴标准差_m_s2": round(az.std(), 2),
        "主频_Hz": round(f0, 2),
        "主频能量占比": round(ratio, 3),
        "超阈值峰个数": n_peaks,
        "等效步频_步每分": round(f0 * 60, 1),
    })
    data[key] = dict(t=t, amag=amag, ax=df["ax"].to_numpy(), ay=df["ay"].to_numpy(),
                     az=az, dyn=dyn, f0=f0)

feat = pd.DataFrame(rows)
feat.to_csv(os.path.join(BASE, "features.csv"), index=False, encoding="utf-8-sig")
print(feat.to_string(index=False))

# 图1：四姿态合加速度波形对比
fig, axes = plt.subplots(3, 2, figsize=(13, 9))
axes = axes.ravel()
for i, key in enumerate(ORDER):
    d = data[key]
    ax = axes[i]
    ax.plot(d["t"], d["amag"], lw=0.8, color="#c0392b")
    ax.axhline(d["amag"].mean(), ls="--", lw=1, color="#555",
               label=f"均值 {d['amag'].mean():.2f} m/s²")
    ax.set_title(f"{LABELS[key]}（σ={d['dyn'].std():.2f}, 主频={d['f0']:.2f} Hz）", fontsize=11)
    ax.set_xlabel("时间 (s)")
    ax.set_ylabel("合加速度 (m/s²)")
    ax.grid(alpha=.3)
    ax.legend(fontsize=8, loc="upper right")
for j in range(len(ORDER), 6):
    fig.delaxes(axes[j])
fig.suptitle("图1  四种姿态的合加速度波形对比（iPhone 内置加速度计，约100 Hz）", fontsize=13)
fig.tight_layout()
fig.savefig(os.path.join(FIG, "fig1_四姿态合加速度波形对比.png"), dpi=160)
plt.close(fig)

# 图2：动态分量箱线图（阈值依据）
fig, ax = plt.subplots(figsize=(8, 5))
box = ax.boxplot([data[k]["dyn"] for k in ORDER], tick_labels=[LABELS[k] for k in ORDER],
                 patch_artist=True, widths=.55)
for p, c in zip(box["boxes"], ["#8ecae6", "#95d5b2", "#f4a261", "#e07a5f"]):
    p.set_facecolor(c)
    p.set_alpha(.85)
ax.axhline(2.0, ls="--", color="#c0392b", lw=1.2)
ax.text(0.6, 2.15, "阈值1：σ动态 > 2.0 m/s²  → 判定为运动态", color="#c0392b", fontsize=9)
ax.axhline(5.0, ls="--", color="#7b2d8e", lw=1.2)
ax.text(0.6, 5.15, "阈值2：σ动态 > 5.0 m/s²  → 判定为高冲击（快跑/楼梯）", color="#7b2d8e", fontsize=9)
ax.set_ylabel("动态加速度 a-mean (m/s²)")
ax.set_title("图2  四种姿态动态加速度分布（箱线图）", fontsize=12)
ax.grid(axis="y", alpha=.3)
fig.tight_layout()
fig.savefig(os.path.join(FIG, "fig2_动态分量箱线图.png"), dpi=160)
plt.close(fig)

# 图3：以动态标准差为主判据的阈值分区
fig, ax = plt.subplots(figsize=(9, 5.5))
bands = [(0, 0.5, "#eaf4fb", "静止区 σ<0.5"),
         (0.5, 2.0, "#e7f6ec", "慢走区 0.5<σ<2.0"),
         (2.0, 5.0, "#fdf1e3", "楼梯区 2.0<σ<5.0"),
         (5.0, 12, "#fbe4e0", "快跑区 σ>5.0")]
for lo, hi, c, name in bands:
    ax.axvspan(lo, hi, color=c, zorder=0, label=name)
for lo, hi, c, name in bands[:3]:
    ax.axvline(hi, ls="--", color="#888", lw=1)
colors = {"standing": "#2980b9", "walk": "#27ae60", "run": "#e74c3c", "stairs": "#e67e22"}
for k in ORDER:
    d = data[k]
    spm = d["f0"] * 60
    ax.scatter(d["dyn"].std(), spm, s=220, color=colors[k],
               edgecolor="#222", zorder=3, label=None)
    ax.annotate(f"{LABELS[k]}\n(σ={d['dyn'].std():.2f})", (d["dyn"].std(), spm),
                textcoords="offset points", xytext=(10, -6), fontsize=9)
ax.set_xlim(0, 11)
ax.set_xlabel("动态加速度标准差 σ (m/s²)  ← 判据主变量 →")
ax.set_ylabel("等效步频 f0×60 (步/分，辅助变量)")
ax.set_title("图3  四姿态在特征空间的分布与阈值分区规则", fontsize=12)
ax.grid(alpha=.25)
ax.legend(fontsize=8, loc="upper left", ncol=2)
fig.tight_layout()
fig.savefig(os.path.join(FIG, "fig3_特征空间阈值.png"), dpi=160)
plt.close(fig)

print("\n图表已输出到", FIG)
