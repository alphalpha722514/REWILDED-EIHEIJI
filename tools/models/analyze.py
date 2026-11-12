"""変異したサル GLB の形の検査（trimesh）。python3 analyze.py work/decoded.glb"""
import sys
import numpy as np
import trimesh

sc = trimesh.load(sys.argv[1], force='scene', process=False)
geoms = list(sc.geometry.values())
print('geometries', len(geoms))
m = geoms[0]
V, F = m.vertices, m.faces
print('vertices', len(V), 'triangles', len(F))
bb = V.min(0), V.max(0)
print('bbox min', bb[0].round(3), 'max', bb[1].round(3), 'size', (bb[1] - bb[0]).round(3))
uv = m.visual.uv if hasattr(m.visual, 'uv') and m.visual.uv is not None else None
print('uv', None if uv is None else (uv.min(0).round(3), uv.max(0).round(3)))
# 位置で溶接した形（UV の継ぎ目を除く）で、つながり・閉じ具合を見る
w = trimesh.Trimesh(V.copy(), F.copy(), process=True, merge_tex=True, merge_norm=True)
w.merge_vertices(merge_tex=True, merge_norm=True)
print('welded vertices', len(w.vertices), 'faces', len(w.faces))
comps = w.split(only_watertight=False)
sizes = sorted([len(c.faces) for c in comps], reverse=True)
print('connected parts', len(comps), 'largest', sizes[:8])
for c in sorted(comps, key=lambda c: -len(c.faces))[1:8]:
    print('  small part faces', len(c.faces), 'center', c.vertices.mean(0).round(3), 'extent', c.extents.round(3))
print('watertight', w.is_watertight, 'winding consistent', w.is_winding_consistent, 'volume', round(float(w.volume), 4) if w.is_watertight else None)
edges = w.edges_sorted
uniq, counts = np.unique(edges, axis=0, return_counts=True)
print('boundary edges', int((counts == 1).sum()), 'non-manifold edges (>2 faces)', int((counts > 2).sum()))
area = w.area_faces
print('degenerate faces (area<1e-9)', int((area < 1e-9).sum()), 'tiny faces (<1e-7)', int((area < 1e-7).sum()))
# 法線：外向きか（閉じていれば体積の符号、閉じていなければ中心から見た向き）
c0 = w.vertices.mean(0)
out = ((w.triangles_center - c0) * w.face_normals).sum(1)
print('faces pointing toward center (rough inward check)', round(float((out < 0).mean() * 100), 1), '%')
# 元の法線と面の向きの一致
vn = m.vertex_normals if m.vertex_normals is not None else None
fnv = np.asarray(m.face_normals)
vavg = np.asarray(m.vertex_normals)[F].mean(1)
dots = (fnv * vavg).sum(1)
print('stored normals vs face winding: opposite', int((dots < 0).sum()), 'of', len(F))
# 縦横の分布（どちらが上・前か）
for ax, n in enumerate('xyz'):
    h, e = np.histogram(V[:, ax], bins=10)
    print('hist', n, h.tolist(), e.round(2).tolist())
