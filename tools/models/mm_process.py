#!/usr/bin/env python3
"""変異したサルの加工（共通の修正＋版ごとの形）。元の配列は変えない。

python3 mm_process.py 元の配列フォルダ 出力フォルダ real|deform

共通（2026-11-13 ユーザー回答）：
  - 離れた小さな三角形を消す
  - 股の出っ張り（生殖器）をならして消す（「消してよい」）
  - 尾：お尻に貼りついた板状の尾をならして体に収め、丸い尾を新しく付ける（後ろ下がり。「まかせる」）
  - 前を +Z、足の裏を y=0、高さは通常の猿（1.56）の 1.2 倍（「よい」）
deform（少しデフォルメ）：頭を 1.3 倍、手足を少し太く、テクスチャの色を少し整理
"""
import json
import math
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter
from scipy import sparse

sys.path.insert(0, __file__.rsplit('/', 1)[0])
import mm  # noqa: E402

src, out, ver = sys.argv[1], sys.argv[2], sys.argv[3]
P, N, UV, I = mm.load(src)
tex = Image.open(f'{src}/color.jpg').convert('RGB')
TS = tex.size[0]
wid, n = mm.weld(P)
nb = mm.adjacency(I, wid, n)
WP = mm.wpos(P, wid, n)
log = {}

# ---- 1) 離れた小さな部品（三角形1〜2枚）を消す ----
comp = -np.ones(n, np.int64)
c = 0
for s in range(n):
    if comp[s] >= 0:
        continue
    st = [s]; comp[s] = c
    while st:
        v = st.pop()
        for u in nb[v]:
            if comp[u] < 0:
                comp[u] = c; st.append(u)
    c += 1
fc = comp[wid[I[:, 0]]]
sizes = np.bincount(fc, minlength=c)
keep = sizes[fc] > 2
# 辺でどこともつながらない三角形（頂点1つだけで触れている破片）も消す
E = np.sort(np.stack([wid[I[:, [0, 1]]], wid[I[:, [1, 2]]], wid[I[:, [2, 0]]]], 1), axis=2)  # (面, 3辺, 2)
ek = E[:, :, 0] * n + E[:, :, 1]
uq, cnt = np.unique(ek.ravel(), return_counts=True)
ecount = dict(zip(uq.tolist(), cnt.tolist()))
lone = np.array([all(ecount[int(e)] == 1 for e in row) for row in ek])
keep &= ~lone
log['removed_small_faces'] = int((~keep).sum())
I = I[keep]

# 行ごとに隣の平均をとる行列（ならすのに使う）
rows, cols = [], []
for v in range(n):
    rows += [v] * len(nb[v]); cols += list(nb[v])
A = sparse.csr_matrix((np.ones(len(rows)), (rows, cols)), shape=(n, n))
deg = np.asarray(A.sum(1)).ravel(); deg[deg == 0] = 1
M = sparse.diags(1 / deg) @ A


def smooth_region(region, iters):
    """region（溶接番号の集合）の内側だけを、まわりを止めたまま何度もならす（出っ張りが縮んで消える）。"""
    reg = np.zeros(n, bool); reg[list(region)] = True
    bnd = np.array([v for v in region if any(not reg[u] for u in nb[v])], dtype=np.int64)
    inner = reg.copy(); inner[bnd] = False
    idx = np.where(inner)[0]
    # 内側の点が「隣の平均」になる形を一度に解く（何度もならした行き着く先。長い出っ張りも残らない）
    from scipy.sparse.linalg import spsolve
    pos = -np.ones(n, np.int64); pos[idx] = np.arange(len(idx))
    Lm = (sparse.identity(n, format='csr') - M)[idx]
    Aii = Lm[:, idx]; rest = np.setdiff1d(np.arange(n), idx)
    rhs = -(Lm[:, rest] @ WP[rest])
    for k in range(3):
        WP[idx, k] = spsolve(Aii.tocsc(), rhs[:, k])
    return idx, bnd


def region_faces(region):
    reg = np.zeros(n, bool); reg[list(region)] = True
    return np.where(reg[wid[I]].all(1))[0]


def ring_color(region):
    """region に接するがその外の面の、テクスチャの平均の色（UV の重心で取る）。"""
    reg = np.zeros(n, bool); reg[list(region)] = True
    W = reg[wid[I]]
    ring = np.where(W.any(1) & ~W.all(1))[0]
    a = np.asarray(tex)
    cols = []
    for f in ring:
        u, v = UV[I[f]].mean(0)
        cols.append(a[int(v * TS) % TS, int(u * TS) % TS])  # glTF の UV は画像の左上が (0,0)
    return np.median(np.array(cols), 0)


def paint_faces(faces, col, seed):
    """faces の UV の三角形を、col の色（少しまだら）で塗る。"""
    rng = np.random.default_rng(seed)
    d = ImageDraw.Draw(tex)
    for f in faces:
        jit = rng.normal(0, 6, 3)
        cc = tuple(int(np.clip(col[k] + jit[k], 0, 255)) for k in range(3))
        d.polygon([(UV[i, 0] * TS, UV[i, 1] * TS) for i in I[f]], fill=cc, outline=cc)


# ---- 2) 股（生殖器）：出っ張りを縮めてならし、色を周りの毛に合わせる ----
box_g = lambda p: -0.24 < p[0] < -0.11 and -0.02 < p[1] < 0.07 and abs(p[2]) < 0.032
cand = [v for v in range(n) if box_g(WP[v]) and -0.21 < WP[v, 0] < -0.14 and abs(WP[v, 2]) < 0.02]
seed = min(cand, key=lambda v: WP[v, 1])
G = mm.grow(seed, nb, lambda u: box_g(WP[u]))
gcol = ring_color(G)
gi, gb = smooth_region(G, 600)
paint_faces(region_faces(G), gcol, 1)
log['genital_vertices'] = len(G)

# ---- 3) 尾：お尻に貼りついた板状の尾をならして体に収める ----
cand = np.where((WP[:, 0] < -0.33) & (WP[:, 1] < -0.05))[0]
tip = int(cand[np.argmin(WP[cand, 1])])
T = mm.grow(tip, nb, lambda u: WP[u, 0] < -0.30 and abs(WP[u, 2]) < 0.04 and WP[u, 1] < 0.14)
tcol = ring_color(T)
smooth_region(T, 2500)
paint_faces(region_faces(T), tcol, 2)
log['old_tail_vertices'] = len(T)

# ここまでの位置を、溶接前の頂点へ戻す
P = WP[wid].copy()

# ---- 4) 新しい尾（丸い筒。後ろ下がり35°、先が少し垂れる） ----
# UV は元の尾の毛の部分（1024 で 20×80 の長方形）。尾の色をそのまま使う
du0, dv0, dw, dh = 64 / 1024, 460 / 1024, 20 / 1024, 80 / 1024  # 画像の左上から（行 = v）
# この長方形（元の尾の毛の所。元の尾は体に収めたので見えない）に、お尻の毛の色で縦の毛すじを描き直す
rng = np.random.default_rng(7)
rx, ry, rw, rh = int(du0 * TS), int(dv0 * TS), int(dw * TS), int(dh * TS)
fur = np.zeros((rh, rw, 3))
fur[:] = tcol * 0.97
for _ in range(rw * 3):
    x = rng.integers(0, rw); y0 = rng.integers(-rh // 4, rh); ln = rng.integers(rh // 6, rh // 2)
    shade = rng.normal(0, 14)
    for yy in range(max(0, y0), min(rh, y0 + ln)):
        fur[yy, x] += shade * (1 - abs((yy - y0) / ln - 0.5))
fur = np.clip(fur + rng.normal(0, 3, fur.shape), 0, 255).astype(np.uint8)
tex.paste(Image.fromarray(fur).filter(ImageFilter.GaussianBlur(0.6)), (rx, ry))
R0 = np.array([-0.318, 0.122, 0.0])
ang = math.radians(-10)  # 付け根は水平より少し上向き。先へ行くほど垂れる（正面から脚の間に見えないように）
dvec = np.array([-math.cos(ang), -math.sin(ang), 0.0])
L, RINGS, SIDES = 0.215, 13, 10
TR = 1.2 if ver == 'deform' else 1.0  # デフォルメ版は少し太い
cen = []
for k in range(RINGS):
    t = k / (RINGS - 1)
    cen.append(R0 + dvec * L * t + np.array([0, -0.08 * t * t, 0]))
cen = np.array(cen)
newP, newUV = [], []
for k in range(RINGS):
    t = k / (RINGS - 1)
    tang = cen[min(k + 1, RINGS - 1)] - cen[max(k - 1, 0)]; tang /= np.linalg.norm(tang)
    side = np.array([0, 0, 1.0]); up = np.cross(side, tang); up /= np.linalg.norm(up)
    r = TR * (0.036 * (1 - 0.62 * t) * (math.sqrt(max(0.0, 1 - ((t - 0.86) / 0.14) ** 2)) if t > 0.86 else 1.0) + 0.0015)  # 先は丸く閉じる
    for s in range(SIDES + 1):
        a = 2 * math.pi * s / SIDES + math.pi / 2  # 継ぎ目は下側
        newP.append(cen[k] + r * (math.cos(a) * side + math.sin(a) * up))
        newUV.append([du0 + dw * s / SIDES, dv0 + dh * t])
newP.append(cen[-1] + (cen[-1] - cen[-2]) * 0.3); newUV.append([du0 + dw / 2, dv0 + dh])
base = len(P)
newI = []
for k in range(RINGS - 1):
    for s in range(SIDES):
        a = base + k * (SIDES + 1) + s; b = a + 1; c2 = a + SIDES + 1; d2 = c2 + 1
        newI += [[a, c2, b], [b, c2, d2]]
tipv = base + RINGS * (SIDES + 1)
last = base + (RINGS - 1) * (SIDES + 1)
for s in range(SIDES):
    newI.append([last + s, tipv, last + s + 1])
newI = np.array(newI)
# 向きの確認：外向きでなければ裏返す
f0 = newI[len(newI) // 3]; nn = np.cross(np.array(newP[f0[1] - base]) - newP[f0[0] - base], np.array(newP[f0[2] - base]) - newP[f0[0] - base])
ring_k = (f0[0] - base) // (SIDES + 1)
if np.dot(nn, np.array(newP[f0[0] - base]) - cen[ring_k]) < 0:
    newI = newI[:, [0, 2, 1]]
P = np.vstack([P, np.array(newP)]); UV = np.vstack([UV, np.array(newUV)]); I = np.vstack([I, newI])
N = np.vstack([N, np.zeros((len(newP), 3))])
log['new_tail_tris'] = len(newI)

# ---- 5) デフォルメ版：頭を大きく、手足を少し太く ----
wid2, n2 = mm.weld(P)


def vnormals(P, I, wid, n):
    fn = np.cross(P[I[:, 1]] - P[I[:, 0]], P[I[:, 2]] - P[I[:, 0]])
    acc = np.zeros((n, 3))
    for k in range(3):
        np.add.at(acc, wid[I[:, k]], fn)
    acc /= np.maximum(np.linalg.norm(acc, axis=1, keepdims=True), 1e-12)
    return acc[wid]


feet_y0 = float(P[(P[:, 0] < 0.1) & (P[:, 1] < -0.3)][:, 1].min())  # 大きさは加工前の足の裏から決める（両方の版で同じ倍率）
if ver == 'deform':
    # v2（2026-11-13 ユーザー指示）：頭の大きさは控えめ、鱗のある前腕を大きく太く強調
    HEAD, INFL, FOREARM, HAND, FEET = 1.15, 0.006, 1.55, 1.25, 1.08
    sm = lambda e0, e1, x: np.clip((x - e0) / (e1 - e0), 0, 1) ** 2 * (3 - 2 * np.clip((x - e0) / (e1 - e0), 0, 1))
    H0 = np.array([0.065, 0.27, 0.0])
    hd = np.array([0.87, 0.49, 0.0]); hd /= np.linalg.norm(hd)
    w = sm(-0.02, 0.06, (P - H0) @ hd) * (1 - sm(0.13, 0.17, np.abs(P[:, 2]))) * sm(0.08, 0.14, P[:, 1])  # 頭
    NN = vnormals(P, I, wid2, n2)
    P = P + NN * (INFL * (1 - w))[:, None]  # 体と手足を少し太く
    # 前腕：左右それぞれ、高さごとの断面の中心から外へ広げる（肘の下から手首まで。肘と手首でなめらかにつなぐ）
    EL_Y, FULL_Y, WR_Y = 0.07, -0.03, -0.34
    for sgn in (-1, 1):
        arm = (np.sign(P[:, 2]) == sgn) & (P[:, 0] > 0.06) & (np.abs(P[:, 2]) > 0.11) & (P[:, 1] < 0.16) & (P[:, 1] > -0.52)
        ys = np.arange(0.16, -0.52, -0.02); cx, cz = [], []
        for y in ys:
            sl = arm & (np.abs(P[:, 1] - y) < 0.015)
            cx.append(P[sl, 0].mean() if sl.any() else np.nan); cz.append(P[sl, 2].mean() if sl.any() else np.nan)
        cx, cz = np.array(cx), np.array(cz); ok = ~np.isnan(cx)
        fx = lambda y: np.interp(-y, -ys[ok], cx[ok]); fz = lambda y: np.interp(-y, -ys[ok], cz[ok])
        y = P[arm, 1]
        wf = sm(EL_Y, FULL_Y, y) * (1 - 0.25 * sm(WR_Y + 0.02, WR_Y - 0.06, y))  # 肘で0→下で1、手首の先で少し戻す
        k = 1 + (FOREARM - 1) * wf
        Q = P[arm].copy(); Q[:, 0] = fx(y) + (Q[:, 0] - fx(y)) * k; Q[:, 2] = fz(y) + (Q[:, 2] - fz(y)) * k
        P[arm] = Q
        # 手：地面につく所を中心に大きく（手首から下ほど強く）
        hand = arm & (P[:, 1] < WR_Y)
        if hand.any():
            pv = P[hand].mean(0); pv[1] = P[hand][:, 1].min()
            wt = sm(WR_Y, WR_Y - 0.07, P[:, 1]) * hand
            P = pv + (P - pv) * (1 + (HAND - 1) * wt)[:, None]
    # 足：少しだけ大きく
    for sgn in (-1, 1):
        ft = (np.sign(P[:, 2]) == sgn) & (P[:, 0] < 0.08) & (P[:, 0] > -0.3) & (P[:, 1] < -0.36) & (np.abs(P[:, 2]) > 0.05)
        if ft.any():
            pv = P[ft].mean(0); pv[1] = P[ft][:, 1].min()
            wt = sm(-0.36, -0.41, P[:, 1]) * ft
            P = pv + (P - pv) * (1 + (FEET - 1) * wt)[:, None]
    P = H0 + (P - H0) * (1 + (HEAD - 1) * w)[:, None]
    log.update({'variant': 'deform v2', 'head_scale': HEAD, 'inflate': INFL, 'forearm_thickness': FOREARM, 'hand_scale': HAND, 'feet_scale': FEET})

# ---- 6) 向き・原点・大きさ ----
feet = P[(P[:, 0] < 0.1) & (P[:, 1] < -0.3)]
feet_y = float(feet[:, 1].min())
TOP_A = 0.4814  # そのまま版の頭の上（元の形）。大きさはそのまま版で決め、デフォルメ版も同じ倍率にする
SCALE = 1.2 * 1.56 / (TOP_A - feet_y0)
OX = -0.05  # 体の中心（元の x）。ここを原点にする
Q = np.empty_like(P)
Q[:, 0] = -P[:, 2]
Q[:, 1] = P[:, 1] - feet_y
Q[:, 2] = P[:, 0] - OX
Q *= SCALE
P = Q
NN = vnormals(P, I, wid2, n2)
log.update({'scale': SCALE, 'feet_y': feet_y, 'height': float(P[:, 1].max()), 'min_y': float(P[:, 1].min()),
            'verts': len(P), 'tris': len(I)})

# ---- 7) テクスチャ（デフォルメ版は色を少し整理） ----
if ver == 'deform':
    # 細かい毛の模様と焼き込まれた陰を弱め、色の面をまとめる（ゲームの塗りに寄せる）
    t2 = tex.filter(ImageFilter.MedianFilter(7)).filter(ImageFilter.SMOOTH_MORE).filter(ImageFilter.SMOOTH_MORE)
    low = t2.filter(ImageFilter.GaussianBlur(24))
    t2 = Image.blend(t2, low, 0.35)
    t2 = ImageEnhance.Color(t2).enhance(1.22)
    t2 = ImageEnhance.Brightness(t2).enhance(1.12)
    q = t2.quantize(colors=24, method=Image.Quantize.MEDIANCUT).convert('RGB')
    tex = Image.blend(t2, q, 0.5)
    # 前腕の鱗（青みの所）を少し鮮やかに・明るくして目立たせる（v2）
    hsv = np.asarray(tex.convert('HSV')).astype(np.float64)
    hue = hsv[:, :, 0] * 360 / 255
    mk = ((hue > 150) & (hue < 260) & (hsv[:, :, 1] > 12)).astype(np.float64)
    from scipy.ndimage import gaussian_filter
    mk = gaussian_filter(mk, 2.0)
    hsv[:, :, 1] = np.clip(hsv[:, :, 1] * (1 + 0.6 * mk), 0, 255)
    hsv[:, :, 2] = np.clip(hsv[:, :, 2] * (1 + 0.12 * mk), 0, 255)
    tex = Image.fromarray(hsv.astype(np.uint8), 'HSV').convert('RGB')
    log['scale_color_boost'] = 'saturation x1.6, value x1.12 (blue hue)'
mm.save(out, P, NN, UV, I)
meta = json.load(open(f'{out}/meta.json')); meta['keep_tail_tris'] = int(log['new_tail_tris']); json.dump(meta, open(f'{out}/meta.json', 'w'))  # 尾は減らさない（最後の面）
tex.save(f'{out}/color.jpg', quality=92)
json.dump(log, open(f'{out}/log.json', 'w'), indent=1)
print(json.dumps(log))
