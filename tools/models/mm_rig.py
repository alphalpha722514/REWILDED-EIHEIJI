#!/usr/bin/env python3
"""変異したサル（デフォルメ v2）に骨と重みを付け、ゲーム用のデータ（data/models/mutant-monkey.js）を作る。

python3 mm_rig.py 配列フォルダ（mmio.mjs dump の出力） 出力.js [重みの確認画像.json]

- 座標はゲームの単位（前 +Z・上 +Y・足の裏 y=0）。骨の位置は v2 の形の断面と正投影の目盛り画像から決めた（docs/mutant-monkey-rig.md）。
- 重み：骨の線分からの距離で付け、部位の区切り（左右・腕と脚・尾）を守り、面のつながりに沿ってならし、上位4本に絞る。
- 輪郭線用に、毛先のとげを体に収めた「ならした形」と、その法線も入れる（ゲームの線の作り方に合わせる）。
"""
import base64
import json
import sys

import numpy as np
from scipy import sparse

sys.path.insert(0, __file__.rsplit('/', 1)[0])
import mm  # noqa: E402

src, out = sys.argv[1], sys.argv[2]
dbg = sys.argv[3] if len(sys.argv) > 3 else None
P, N, UV, I = mm.load(src)
nv = len(P)

# ---- 骨（名前・親・関節の位置）。右（+x）を決めて左は鏡写し ----
R = {  # 体の左（+x）側の関節。右は鏡写し
    'upperArm': (0.36, 1.45, 0.10), 'foreArm': (0.54, 0.90, 0.30), 'hand': (0.58, 0.26, 0.64), 'handEnd': (0.63, 0.02, 0.86),
    'thigh': (0.18, 1.10, -0.36), 'shin': (0.26, 0.72, -0.13), 'foot': (0.18, 0.22, -0.40), 'footEnd': (0.22, 0.03, -0.04),
}
BONES = [
    ('root', None, (0, 0, 0)),
    ('hips', 'root', (0, 1.10, -0.38)),
    ('spine', 'hips', (0, 1.30, -0.15)),
    ('chest', 'spine', (0, 1.50, 0.05)),
    ('neck', 'chest', (0, 1.55, 0.25)),
    ('head', 'neck', (0, 1.62, 0.42)),
    ('tail1', 'hips', (0, 1.156, -0.542)),
    ('tail2', 'tail1', (0, 1.163, -0.683)),
    ('tail3', 'tail2', (0, 1.135, -0.825)),
]
# 前が +Z・上が +Y なので、体の左は +x、右は −x（向かって見たとき左右が逆）
for s, sx in (('L', 1), ('R', -1)):
    m = lambda k: (R[k][0] * sx, R[k][1], R[k][2])
    BONES += [('upperArm' + s, 'chest', m('upperArm')), ('foreArm' + s, 'upperArm' + s, m('foreArm')), ('hand' + s, 'foreArm' + s, m('hand')),
              ('thigh' + s, 'hips', m('thigh')), ('shin' + s, 'thigh' + s, m('shin')), ('foot' + s, 'shin' + s, m('foot'))]
names = [b[0] for b in BONES]
pos = {b[0]: np.array(b[2], float) for b in BONES}
# 重みを付ける線分（骨の始まり → 終わり）
END = {'hips': pos['spine'], 'spine': pos['chest'], 'chest': pos['neck'], 'neck': pos['head'], 'head': np.array([0, 1.48, 0.72]),
       'tail1': pos['tail2'], 'tail2': pos['tail3'], 'tail3': np.array([0, 1.07, -0.97])}
for s, sx in (('L', 1), ('R', -1)):
    END['upperArm' + s] = pos['foreArm' + s]; END['foreArm' + s] = pos['hand' + s]
    END['hand' + s] = np.array([R['handEnd'][0] * sx, R['handEnd'][1], R['handEnd'][2]])
    END['thigh' + s] = pos['shin' + s]; END['shin' + s] = pos['foot' + s]
    END['foot' + s] = np.array([R['footEnd'][0] * sx, R['footEnd'][1], R['footEnd'][2]])
DEF = [n for n in names if n != 'root']


def seg_dist(p, a, b):
    ab = b - a; t = np.clip(((p - a) @ ab) / max(ab @ ab, 1e-9), 0, 1)
    return np.linalg.norm(p - (a + np.outer(t, ab)), axis=1), t


# ---- 部位の区切り ----
wid, n = mm.weld(P)
nb = mm.adjacency(I, wid, n)
comp = -np.ones(n, np.int64); c = 0
for s0 in range(n):
    if comp[s0] >= 0:
        continue
    st = [s0]; comp[s0] = c
    while st:
        v = st.pop()
        for u in nb[v]:
            if comp[u] < 0:
                comp[u] = c; st.append(u)
    c += 1
WP = mm.wpos(P, wid, n)
csz = np.bincount(comp)
# 尾：体と離れた部品のうち、後ろにある一番大きいもの
cand = [k for k in range(c) if WP[comp == k][:, 2].mean() < -0.5 and csz[k] > 50]
tail_c = max(cand, key=lambda k: csz[k])
is_tail = (comp == tail_c)[wid]
x, y, z = P[:, 0], P[:, 1], P[:, 2]
W = np.zeros((nv, len(DEF)))
for j, b in enumerate(DEF):
    d, t = seg_dist(P, pos[b], END[b])
    w = 1.0 / (d + 0.02) ** 4
    if b.startswith('tail'):
        w *= is_tail
    else:
        w *= ~is_tail if b != 'hips' else (~is_tail + is_tail * 0.0)
    side = 1 if b.endswith('L') else -1 if b.endswith('R') else 0
    if side:
        w *= np.clip((x * side - 0.04) / 0.06, 0, 1)  # 反対側には付けない
    if b[:-1] in ('upperArm', 'foreArm', 'hand'):
        w *= np.clip((z + 0.02) / 0.10, 0, 1) * (y < 1.75)  # 腕は体の前側
        if b[:-1] == 'upperArm':
            w *= 1.0
    if b[:-1] in ('thigh', 'shin', 'foot'):
        w *= np.clip((0.10 - z) / 0.10, 0, 1) * np.clip((1.22 - y) / 0.08, 0, 1)  # 脚は後ろ側・腰より下
    if b in ('head',):
        w *= np.clip((z - 0.18) / 0.10, 0, 1) * np.clip((y - 1.22) / 0.08, 0, 1)
    W[:, j] = w
# 尾の付け根は腰へ少しつなぐ
tj = DEF.index('tail1'); hj = DEF.index('hips')
dt_, tt = seg_dist(P, pos['tail1'], END['tail1'])
W[is_tail, hj] += W[is_tail, tj] * np.clip(1 - tt[is_tail] / 0.4, 0, 1) * 0.6
W /= np.maximum(W.sum(1, keepdims=True), 1e-12)
# 面のつながりに沿ってならす（溶接した点ごと）
rows, cols = [], []
for v in range(n):
    rows += [v] * len(nb[v]); cols += list(nb[v])
A = sparse.csr_matrix((np.ones(len(rows)), (rows, cols)), shape=(n, n))
deg = np.asarray(A.sum(1)).ravel(); deg[deg == 0] = 1
M = sparse.diags(1 / deg) @ A
WW = np.zeros((n, len(DEF)))
np.add.at(WW, wid, W); cnt = np.bincount(wid, minlength=n)[:, None]; WW /= np.maximum(cnt, 1)
for _ in range(4):
    WW = 0.5 * WW + 0.5 * (M @ WW)
W = WW[wid]
# 上位4本
idx4 = np.argsort(-W, axis=1)[:, :4]
w4 = np.take_along_axis(W, idx4, 1)
w4[w4 < 0.02] = 0
w4 /= np.maximum(w4.sum(1, keepdims=True), 1e-12)
bone_index = np.array([names.index(DEF[j]) for j in range(len(DEF))])
skin_i = bone_index[idx4]
skin_w = np.round(w4 * 255).astype(np.int32)
fix = 255 - skin_w.sum(1); skin_w[np.arange(nv), 0] += fix  # 合計を 255 に
skin_w = skin_w.astype(np.uint8)

# ---- 輪郭線用のならした形（ゲームの lineup と同じ：Taubin 10回） ----
X = WP.copy()
for _ in range(10):
    X = X + 0.6 * (M @ X - X); X = X - 0.62 * (M @ X - X)
fn = np.cross(X[wid[I[:, 1]]] - X[wid[I[:, 0]]], X[wid[I[:, 2]]] - X[wid[I[:, 0]]])
HN = np.zeros((n, 3))
for k in range(3):
    np.add.at(HN, wid[I[:, k]], fn)
HN /= np.maximum(np.linalg.norm(HN, axis=1, keepdims=True), 1e-12)
hullP, hullN = X[wid], HN[wid]

# ---- 詰める（位置は範囲で int16、法線は int8、UV は uint16） ----
lo = np.minimum(P.min(0), hullP.min(0)) - 0.01; hi = np.maximum(P.max(0), hullP.max(0)) + 0.01
q = lambda A_: np.round((A_ - lo) / (hi - lo) * 65535).astype(np.uint16)
qn = lambda A_: np.round(np.clip(A_, -1, 1) * 127).astype(np.int8)
b64 = lambda a: base64.b64encode(np.ascontiguousarray(a).tobytes()).decode()
data = {
    'name': '変異したサル', 'version': 'deform v2 / rig 1', 'verts': nv, 'tris': len(I),
    'lo': lo.round(5).tolist(), 'hi': hi.round(5).tolist(),
    'pos': b64(q(P)), 'nor': b64(qn(N)), 'uv': b64(np.round(np.clip(UV, 0, 1) * 65535).astype(np.uint16)),
    'skinIndex': b64(skin_i.astype(np.uint8)), 'skinWeight': b64(skin_w),
    'hullPos': b64(q(hullP)), 'hullNor': b64(qn(hullN)),
    'index': b64(I.astype(np.uint16)),
    'bones': [[b[0], b[1], [round(v, 4) for v in b[2]]] for b in BONES],
    'tex': 'data:image/jpeg;base64,' + base64.b64encode(open(f'{src}/color.jpg', 'rb').read()).decode(),
}
js = '// 変異したサル（P2）。tools/models/mm_rig.py で作成。元：assets/models/mutant-monkey/game/mutant_monkey_B_deform_v2.glb\n'
js += 'window.MUTANT_MONKEY_MODEL=' + json.dumps(data, ensure_ascii=False, separators=(',', ':')) + ';\n'
open(out, 'w', encoding='utf8').write(js)
# 確認用：頂点ごとの一番重い骨
main_b = skin_i[np.arange(nv), np.argmax(skin_w, 1)]
summary = {nm: int((main_b == k).sum()) for k, nm in enumerate(names)}
print(json.dumps({'bytes': len(js), 'tail_verts': int(is_tail.sum()), 'main_bone_counts': summary}, ensure_ascii=False))
if dbg:
    json.dump({'P': P.round(4).tolist(), 'main': main_b.tolist(), 'names': names}, open(dbg, 'w'))
