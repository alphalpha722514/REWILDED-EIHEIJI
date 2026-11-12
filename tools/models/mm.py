"""変異したサルの加工用の共通部品（配列の読み書き・溶接・つながり）。"""
import json
import os
import numpy as np


def load(d):
    P = np.fromfile(f'{d}/pos.bin', np.float32).reshape(-1, 3).astype(np.float64)
    N = np.fromfile(f'{d}/nor.bin', np.float32).reshape(-1, 3).astype(np.float64)
    UV = np.fromfile(f'{d}/uv.bin', np.float32).reshape(-1, 2).astype(np.float64)
    I = np.fromfile(f'{d}/idx.bin', np.uint32).reshape(-1, 3).astype(np.int64)
    return P, N, UV, I


def save(d, P, N, UV, I):
    os.makedirs(d, exist_ok=True)
    P.astype(np.float32).tofile(f'{d}/pos.bin'); N.astype(np.float32).tofile(f'{d}/nor.bin')
    UV.astype(np.float32).tofile(f'{d}/uv.bin'); I.astype(np.uint32).tofile(f'{d}/idx.bin')
    json.dump({'verts': len(P), 'tris': len(I)}, open(f'{d}/meta.json', 'w'))


def weld(P):
    """同じ位置の頂点（UV の継ぎ目）に共通の番号をつける。"""
    key = np.round(P * 1e6).astype(np.int64)
    _, wid, inv = np.unique(key, axis=0, return_index=True, return_inverse=True)
    return inv.reshape(-1), len(wid)


def adjacency(I, wid, n):
    nb = [set() for _ in range(n)]
    W = wid[I]
    for a, b, c in W:
        nb[a].update((b, c)); nb[b].update((a, c)); nb[c].update((a, b))
    return [np.array(sorted(s - {i}), dtype=np.int64) for i, s in enumerate(nb)]


def grow(seed_w, nb, ok):
    """溶接番号 seed_w から、ok(溶接番号) が真の所をつながりに沿って広げる。"""
    seen = {seed_w}; st = [seed_w]
    while st:
        v = st.pop()
        for u in nb[v]:
            if u not in seen and ok(u):
                seen.add(u); st.append(u)
    return seen


def wpos(P, wid, n):
    W = np.zeros((n, 3)); W[wid] = P
    return W
