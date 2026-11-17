// KEI truck（修理前・修理後）の Tripo の GLB から、ゲーム用のコピーを作る（元の GLB は変えない）。docs/kei-truck-glb.md
//   node tools/models/kei_truck_build.mjs            （tools/models/kei_truck.json の2台）
// することは、1台ごとに：
//   1. 大きさ・原点・向き：前は +Z のまま。前後の車輪の真ん中を原点（z=0）、タイヤの接地を y=0。全長 lengthM（m）になるよう拡大
//   2. 車輪を4つに分ける：1つのつながった形なので、タイヤ（ホイールを含む）の円柱の中にある三角形だけを車輪の形へ移す
//      （車輪の形の原点は車軸の中心。ゲームで回す・切る）。車体には残りを置く
//   3. フロントガラス（修理後）：元の形にガラスが無い（窓枠だけ）ので、枠の内側に曲面のガラスを足す（別の材質・半透明）
//   4. 絵：色の絵だけ残して tex 四方の JPEG に。金属・凹凸の絵は外す（ゲームはトゥーンの陰影なので使わない）
//   5. KHR_materials_volume を外す（three.js r128 の GLTFLoader でそのまま読める形に）。必要なら車体の三角形を減らす（simplify）
//   6. ドア2枚・荷台のあおり（v0.78。2026-11-17 ユーザー「開け閉めできるようにする」）：箱と斜めの線で決めた範囲（ゲームの大きさの m）に3つの頂点が
//      すべて入る三角形を別の形へ移す（door_r・door_l・tailgate。原点はちょうつがい）。車体にはその分の穴が開き、閉じると元の姿に戻る
// 必要なもの：@gltf-transform/core・extensions・functions・meshoptimizer と sharp（tools/models/package.json）
import { NodeIO, Document } from '@gltf-transform/core';
import { ALL_EXTENSIONS } from '@gltf-transform/extensions';
import { MeshoptSimplifier } from 'meshoptimizer';
import sharp from 'sharp';
import fs from 'fs';
import path from 'path';
import crypto from 'crypto';

const ROOT = path.resolve(path.dirname(new URL(import.meta.url).pathname), '..', '..');
const CFG = JSON.parse(fs.readFileSync(path.join(ROOT, 'tools/models/kei_truck.json'), 'utf8'));
const io = new NodeIO().registerExtensions(ALL_EXTENSIONS);
const sha = b => crypto.createHash('sha256').update(b).digest('hex');
const log = { built: new Date().toISOString().slice(0, 10), tool: 'tools/models/kei_truck_build.mjs', lengthM: CFG.lengthM, assets: [] };
await MeshoptSimplifier.ready;

for (const V of CFG.variants) {
  const srcPath = path.join(ROOT, V.src), srcBuf = fs.readFileSync(srcPath);
  const src = await io.read(srcPath);
  const prim0 = src.getRoot().listMeshes()[0].listPrimitives()[0], mat0 = prim0.getMaterial();
  const P = prim0.getAttribute('POSITION').getArray(), N = prim0.getAttribute('NORMAL').getArray(), UV = prim0.getAttribute('TEXCOORD_0').getArray(), I0 = prim0.getIndices().getArray();
  const nv = P.length / 3;
  // 1. 大きさと原点
  let zmin = 1e9, zmax = -1e9; for (let i = 0; i < nv; i++) { zmin = Math.min(zmin, P[3 * i + 2]); zmax = Math.max(zmax, P[3 * i + 2]); }
  const S = CFG.lengthM / (zmax - zmin), zMid = (V.wheels.front.z + V.wheels.rear.z) / 2;
  const tp = i => [P[3 * i] * S, P[3 * i + 1] * S, (P[3 * i + 2] - zMid) * S];
  // 2. 車輪：[右前, 左前, 右後ろ, 左後ろ]（ゲームの TRUCK_WHEELS と同じ順。+x が左）
  const W = [];
  for (const [ax, w] of [['front', V.wheels.front], ['rear', V.wheels.rear]]) for (const sx of [-1, 1])
    W.push({ name: `wheel_${ax === 'front' ? 'f' : 'r'}${sx > 0 ? 'l' : 'r'}`, sx, xin: w.xin, xout: w.xout, cy: w.r, cz: w.z, r: w.r });
  const inWheel = (i, w) => { const x = P[3 * i] * w.sx, y = P[3 * i + 1], z = P[3 * i + 2];
    return x > w.xin - CFG.wheelPadIn && x < w.xout + CFG.wheelPadOut && Math.hypot(y - w.cy, z - w.cz) < w.r + CFG.wheelPadR; };
  const part = new Int32Array(I0.length / 3).fill(-1); // -1 = 車体
  for (let t = 0; t < I0.length / 3; t++) for (let k = 0; k < W.length; k++) { const a = I0[3 * t], b = I0[3 * t + 1], c = I0[3 * t + 2];
    if (inWheel(a, W[k]) && inWheel(b, W[k]) && inWheel(c, W[k])) { part[t] = k; break; } }
  // 6. ドア・あおり（設定 CFG.parts。座標はゲームの大きさ・原点の m）。境目をまたぐ三角形は境目で切り分ける（ぎざぎざにしない）
  //    sel：三角形の重心で選ぶ（ドアの外板・内張りの厚み x、あおりの z）。regions：凸な範囲（平面 [ax,ay,az,d]、ax·x+ay·y+az·z+d ≥ 0 が内側）のリスト
  const PARTS = (CFG.parts || []).flatMap(q => q.mirror ? [{ ...q, name: q.name + '_r', s: -1 }, { ...q, name: q.name + '_l', s: 1 }] : [{ ...q, s: 1 }]);
  const corner = v => ({ k: v, p: tp(v), n: [N[3 * v], N[3 * v + 1], N[3 * v + 2]], uv: [UV[2 * v], UV[2 * v + 1]] });
  const lerpC = (A, B, t) => ({ k: null, p: A.p.map((v, i) => v + (B.p[i] - v) * t), n: A.n.map((v, i) => v + (B.n[i] - v) * t), uv: A.uv.map((v, i) => v + (B.uv[i] - v) * t) });
  const fP = (h, c) => h[0] * c.p[0] + h[1] * c.p[1] + h[2] * c.p[2] + h[3];
  const clip = (poly, h) => { const out = []; for (let i = 0; i < poly.length; i++) { const A = poly[i], B = poly[(i + 1) % poly.length], da = fP(h, A), db = fP(h, B);
    if (da >= 0) out.push(A); if ((da >= 0) !== (db >= 0)) out.push(lerpC(A, B, da / (da - db))); } return out; };
  const fan = poly => { const t = []; for (let i = 1; i + 1 < poly.length; i++) t.push([poly[0], poly[i], poly[i + 1]]); return t; };
  const soup = { body: [] }; PARTS.forEach(q => soup[q.name] = []);
  for (let t = 0; t < I0.length / 3; t++) { if (part[t] >= 0) continue; const tri = [corner(I0[3 * t]), corner(I0[3 * t + 1]), corner(I0[3 * t + 2])];
    const cx = (tri[0].p[0] + tri[1].p[0] + tri[2].p[0]) / 3, cy = (tri[0].p[1] + tri[1].p[1] + tri[2].p[1]) / 3, cz = (tri[0].p[2] + tri[1].p[2] + tri[2].p[2]) / 3;
    let rest = [tri];
    for (const q of PARTS) { const sl = q.sel, ax = cx * q.s;
      if (sl.x && (ax < sl.x[0] || ax > sl.x[1])) continue; if (sl.ax && Math.abs(cx) > sl.ax) continue; if (sl.z && (cz < sl.z[0] || cz > sl.z[1])) continue; if (sl.y && (cy < sl.y[0] || cy > sl.y[1])) continue;
      for (const reg of q.regions) { const planes = reg.map(h => [h[0] * q.s, h[1], h[2], h[3]]); const next = [];
        for (const poly0 of rest) { let cur = poly0; for (const h of planes) { const outside = clip(cur, [-h[0], -h[1], -h[2], -h[3]]); if (outside.length >= 3) next.push(outside); cur = clip(cur, h); if (cur.length < 3) break; }
          if (cur.length >= 3) soup[q.name].push(...fan(cur)); }
        rest = next; } }
    for (const poly of rest) soup.body.push(...(poly.length === 3 ? [poly] : fan(poly))); }
  // 部分ごとに頂点を詰め直す（車輪は車軸の中心を原点に）。元の頂点はそのまま共有し、切り分けで増えた頂点は新しく足す
  const fromSoup = (tris, origin) => { const map = new Map(), pos = [], nor = [], uv = [], idx = [];
    for (const tri of tris) { const area = (() => { const [a, b, c] = tri.map(x => x.p); const u = [b[0] - a[0], b[1] - a[1], b[2] - a[2]], v = [c[0] - a[0], c[1] - a[1], c[2] - a[2]]; return Math.hypot(u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0]); })();
      if (area < 1e-9) continue; for (const c of tri) { const key = c.k !== null ? 'v' + c.k : 'n' + c.p.map(v => v.toFixed(5)).join(',') + '|' + c.uv.map(v => v.toFixed(5)).join(','); let m = map.get(key);
        if (m === undefined) { m = pos.length / 3; map.set(key, m); pos.push(c.p[0] - origin[0], c.p[1] - origin[1], c.p[2] - origin[2]); const L = Math.hypot(...c.n) || 1; nor.push(c.n[0] / L, c.n[1] / L, c.n[2] / L); uv.push(c.uv[0], c.uv[1]); }
        idx.push(m); } }
    return { pos: new Float32Array(pos), nor: new Float32Array(nor), uv: new Float32Array(uv), idx: new Uint32Array(idx) }; };
  const build = (sel, origin) => fromSoup([...Array(part.length).keys()].filter(sel).map(t => [corner(I0[3 * t]), corner(I0[3 * t + 1]), corner(I0[3 * t + 2])]), origin);
  let body = fromSoup(soup.body, [0, 0, 0]);
  const partParts = PARTS.map(q => { const o = [q.hinge[0] * q.s, q.hinge[1], q.hinge[2]]; return { q, o, g: fromSoup(soup[q.name], o) }; }); // 原点はちょうつがい（ゲームの m）
  const wheelParts = W.map((w, k) => { const o = [w.sx * (w.xin + w.xout) / 2 * S, w.cy * S, (w.cz - zMid) * S]; return { w, o, g: build(t => part[t] === k, o) }; });
  // 5. 車体の三角形を減らす（設定があるとき）
  const bodyTris0 = body.idx.length / 3;
  if (V.simplify) { const [idx2, err] = MeshoptSimplifier.simplify(body.idx, body.pos, 3, Math.floor(body.idx.length * V.simplify.ratio / 3) * 3, V.simplify.error, ['LockBorder']);
    // 使わなくなった頂点を詰める
    const map = new Int32Array(body.pos.length / 3).fill(-1), pos = [], nor = [], uv = [], idx = new Uint32Array(idx2.length);
    for (let k = 0; k < idx2.length; k++) { const v = idx2[k]; if (map[v] < 0) { map[v] = pos.length / 3; pos.push(body.pos[3 * v], body.pos[3 * v + 1], body.pos[3 * v + 2]); nor.push(body.nor[3 * v], body.nor[3 * v + 1], body.nor[3 * v + 2]); uv.push(body.uv[2 * v], body.uv[2 * v + 1]); } idx[k] = map[v]; }
    body = { pos: new Float32Array(pos), nor: new Float32Array(nor), uv: new Float32Array(uv), idx }; console.log(V.id, '車体を減らす', bodyTris0, '→', idx2.length / 3, '誤差', err.toFixed(5)); }
  // 新しい GLB を組み立てる
  const doc = new Document(); const buf = doc.createBuffer(); const root = doc.getRoot();
  const tex0 = mat0.getBaseColorTexture();
  const jpg = await sharp(Buffer.from(tex0.getImage())).resize(CFG.tex, CFG.tex).jpeg({ quality: CFG.jpegQ, mozjpeg: true }).toBuffer();
  const tex = doc.createTexture('kei_truck_' + V.id + '_color').setImage(jpg).setMimeType('image/jpeg');
  const mat = doc.createMaterial('kei_truck_' + V.id).setBaseColorTexture(tex).setMetallicFactor(0).setRoughnessFactor(1);
  const acc = (arr, type) => doc.createAccessor().setArray(arr).setType(type).setBuffer(buf);
  const mkPrim = (g, m) => { const n = g.pos.length / 3, idx = n < 65536 ? new Uint16Array(g.idx) : g.idx;
    return doc.createPrimitive().setAttribute('POSITION', acc(g.pos, 'VEC3')).setAttribute('NORMAL', acc(g.nor, 'VEC3')).setAttribute('TEXCOORD_0', acc(g.uv, 'VEC2')).setIndices(acc(idx, 'SCALAR')).setMaterial(m); };
  const scene = doc.createScene('kei_truck_' + V.id); const rootNode = doc.createNode('kei_truck_' + V.id); scene.addChild(rootNode);
  const bodyMesh = doc.createMesh('body').addPrimitive(mkPrim(body, mat)); rootNode.addChild(doc.createNode('body').setMesh(bodyMesh));
  // 3. フロントガラス（設定があるとき）。z(x,y) = z0 + (y0 - y)*k - c*x^2 - inset（元の大きさで）
  let glassTris = 0;
  if (V.glass) { const G = V.glass, nx = 12, ny = 6, pos = [], nor = [], idx = [];
    for (let j = 0; j <= ny; j++) for (let i = 0; i <= nx; i++) { const x = G.x0 + (G.x1 - G.x0) * i / nx, y = G.y0 + (G.y1 - G.y0) * j / ny;
      const z = G.z0 + (G.yRef - y) * G.k - G.c * x * x - G.inset; pos.push(x * S, y * S, (z - zMid) * S);
      const nzv = [2 * G.c * x, G.k, 1], L = Math.hypot(...nzv); nor.push(nzv[0] / L, nzv[1] / L, nzv[2] / L); }
    for (let j = 0; j < ny; j++) for (let i = 0; i < nx; i++) { const a = j * (nx + 1) + i, b = a + 1, c = a + nx + 1, d = c + 1; idx.push(a, b, d, a, d, c); }
    glassTris = idx.length / 3;
    const gm = doc.createMaterial('kei_truck_glass').setBaseColorFactor(G.color).setAlphaMode('BLEND').setDoubleSided(true).setMetallicFactor(0).setRoughnessFactor(0.15);
    const gp = doc.createPrimitive().setAttribute('POSITION', acc(new Float32Array(pos), 'VEC3')).setAttribute('NORMAL', acc(new Float32Array(nor), 'VEC3')).setIndices(acc(new Uint16Array(idx), 'SCALAR')).setMaterial(gm);
    rootNode.addChild(doc.createNode('windshield').setMesh(doc.createMesh('windshield').addPrimitive(gp))); }
  for (const { w, o, g } of wheelParts) rootNode.addChild(doc.createNode(w.name).setTranslation(o).setMesh(doc.createMesh(w.name).addPrimitive(mkPrim(g, mat))));
  for (const { q, o, g } of partParts) { if (!g.idx.length) { console.log(V.id, q.name, '三角形が無い'); continue; } rootNode.addChild(doc.createNode(q.name).setTranslation(o).setMesh(doc.createMesh(q.name).addPrimitive(mkPrim(g, mat)))); }
  const outPath = path.join(ROOT, V.out); fs.mkdirSync(path.dirname(outPath), { recursive: true });
  const bin = await io.writeBinary(doc); fs.writeFileSync(outPath, bin);
  // 寸法
  const bb = [[1e9, 1e9, 1e9], [-1e9, -1e9, -1e9]]; for (let i = 0; i < nv; i++) { const p = tp(i); for (let a = 0; a < 3; a++) { bb[0][a] = Math.min(bb[0][a], p[a]); bb[1][a] = Math.max(bb[1][a], p[a]); } }
  const rec = { id: 'kei_truck.' + V.id, src: V.src, srcSha256: sha(srcBuf), out: V.out, bytes: bin.length, sha256: sha(bin), scale: +S.toFixed(4), zShiftSrc: +zMid.toFixed(4),
    size: { x: +(bb[1][0] - bb[0][0]).toFixed(3), y: +(bb[1][1] - bb[0][1]).toFixed(3), z: +(bb[1][2] - bb[0][2]).toFixed(3) },
    trisSrc: I0.length / 3, trisBody: body.idx.length / 3, trisWheels: wheelParts.map(p => p.g.idx.length / 3), trisGlass: glassTris,
    trisParts: Object.fromEntries(partParts.map(p => [p.q.name, p.g.idx.length / 3])), parts: partParts.map(p => ({ name: p.q.name, hinge: p.o.map(v => +v.toFixed(4)) })),
    trisTotal: body.idx.length / 3 + wheelParts.reduce((a, p) => a + p.g.idx.length / 3, 0) + partParts.reduce((a, p) => a + p.g.idx.length / 3, 0) + glassTris,
    wheels: wheelParts.map(p => ({ name: p.w.name, center: p.o.map(v => +v.toFixed(4)), radius: +(p.w.r * S).toFixed(4) })), tex: CFG.tex, texBytes: jpg.length };
  log.assets.push(rec); console.log(JSON.stringify(rec));
}
fs.writeFileSync(path.join(ROOT, 'assets/models/kei-truck/game/kei_truck_build.json'), JSON.stringify(log, null, 1) + '\n');
