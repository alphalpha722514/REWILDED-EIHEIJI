// 武器の GLB から、ゲーム用のコピーを作る（元の GLB は変えない）。docs/p2-weapon-glb.md
//   node tools/models/weapon_build.mjs [ID …]      （ID を省くと tools/models/weapons.json の全部）
// することは、武器ごとに：
//   1. 向きをそろえる：握る所が原点、刃先・穂先は -y、刃（斧・鉈の切る側）は +z（コードの武器と同じ向き）
//   2. 大きさをそろえる：いちばん下（先端）が tip の高さに来るように拡大・縮小（手で握る所は動かさない）
//   3. 絵：色の絵だけ残して tex 四方の JPEG に。金属・凹凸の絵は外す（ゲームはトゥーンの陰影なので使わない）
//   4. 光る所：glow を指定した武器は、色の絵から「青い鱗」「紫の亀裂」を色で選び、光の絵（白黒）を作る
//   5. KHR_materials_volume などの拡張を外す（three.js r128 の GLTFLoader でそのまま読める形に）
// 必要なもの：@gltf-transform/core・extensions・functions と sharp（tools/models/package.json。NODE_PATH で別の場所のものも使える）
import { NodeIO } from '@gltf-transform/core';
import { ALL_EXTENSIONS } from '@gltf-transform/extensions';
import { prune, dedup } from '@gltf-transform/functions';
import sharp from 'sharp';
import fs from 'fs';
import path from 'path';
import crypto from 'crypto';

const ROOT = path.resolve(path.dirname(new URL(import.meta.url).pathname), '..', '..');
const CFG = JSON.parse(fs.readFileSync(path.join(ROOT, 'tools/models/weapons.json'), 'utf8'));
const io = new NodeIO().registerExtensions(ALL_EXTENSIONS);
const want = process.argv.slice(2);
const AX = { x: 0, y: 1, z: 2 };
// 'x:+y' のような写し方から 3×3 の行列（元の軸 → ゲームの軸）
function basis(map) { const M = [[0, 0, 0], [0, 0, 0], [0, 0, 0]];
  for (const s of ['x', 'y', 'z']) { const t = map[s], sg = t[0] === '-' ? -1 : 1; M[AX[t[1]]][AX[s]] = sg; }
  const det = M[0][0] * (M[1][1] * M[2][2] - M[1][2] * M[2][1]) - M[0][1] * (M[1][0] * M[2][2] - M[1][2] * M[2][0]) + M[0][2] * (M[1][0] * M[2][1] - M[1][1] * M[2][0]);
  if (det !== 1) throw new Error('軸の写し方が回転になっていない（行列式 ' + det + '）: ' + JSON.stringify(map));
  return M; }
const mul = (M, v) => [0, 1, 2].map(r => M[r][0] * v[0] + M[r][1] * v[1] + M[r][2] * v[2]);
// 色の絵 → 光る所の白黒の絵。kind: blue（青い鱗）／purple（紫の亀裂）
async function glowMask(img, kind, size, cracks) {
  const { data, info } = await sharp(img).resize(size, size).removeAlpha().raw().toBuffer({ resolveWithObject: true });
  const out = Buffer.alloc(info.width * info.height); let lit = 0;
  for (let i = 0, j = 0; i < data.length; i += 3, j++) { const r = data[i] / 255, g = data[i + 1] / 255, b = data[i + 2] / 255;
    const mx = Math.max(r, g, b), mn = Math.min(r, g, b), d = mx - mn, s = mx ? d / mx : 0; let h = 0;
    if (d > 0) { h = mx === r ? ((g - b) / d) % 6 : mx === g ? (b - r) / d + 2 : (r - g) / d + 4; h *= 60; if (h < 0) h += 360; }
    let v = 0;
    if (kind === 'blue') { if (h > 195 && h < 245 && s > 0.45 && mx > 0.42) v = Math.min(1, (s - 0.45) * 2.2) * Math.min(1, (mx - 0.42) * 3); }
    else if (kind === 'purple') { if (h > 262 && h < 320 && s > 0.4 && mx > 0.3) v = Math.min(1, (s - 0.4) * 2.5) * Math.min(1, (mx - 0.3) * 3); }
    out[j] = Math.round(v * 255); }
  // cracks：変異鱗の武器。絵に紫がないので、細い亀裂（枝分かれする折れ線）を絵の上に描いて光らせる（決まった乱数。作り直しても同じ）
  if (cracks) { const W = info.width; let sd = cracks.seed >>> 0; const rnd = () => ((sd = (sd * 1664525 + 1013904223) >>> 0) / 4294967296);
    const stamp = (x, y, w) => { for (let dy = -2; dy <= 2; dy++) for (let dx = -2; dx <= 2; dx++) { const px = Math.round(x) + dx, py = Math.round(y) + dy; if (px < 0 || py < 0 || px >= W || py >= W) continue;
      const k = Math.max(0, 1 - Math.hypot(px - x, py - y) / w); const j = py * W + px; out[j] = Math.max(out[j], Math.round(k * 255)); } };
    const walk = (x, y, a, n, w, depth) => { for (let i = 0; i < n; i++) { a += (rnd() - 0.5) * 0.9; const st = 2 + rnd() * 2.5; x += Math.cos(a) * st; y += Math.sin(a) * st; stamp(x, y, w);
      if (depth < 2 && rnd() < 0.06) walk(x, y, a + (rnd() < 0.5 ? 1 : -1) * (0.6 + rnd() * 0.6), Math.floor(n * 0.4), w * 0.8, depth + 1); } };
    for (let k = 0; k < cracks.n; k++) walk(rnd() * W, rnd() * W, rnd() * Math.PI * 2, 14 + Math.floor(rnd() * 26), 1.7, 0); }
  for (const v of out) if (v > 76) lit++;
  const jpg = await sharp(out, { raw: { width: info.width, height: info.height, channels: 1 } }).blur(0.7).jpeg({ quality: 88 }).toBuffer();
  return { jpg, litPct: +(lit / (info.width * info.height) * 100).toFixed(2) };
}
const report = [];
for (const a of CFG.assets) {
  if (want.length && !want.includes(a.id)) continue;
  if (process.env.WB_TEX) a.tex = +process.env.WB_TEX; // 比べるとき：絵の大きさと出力先を変える（WB_TEX=512 WB_OUT=別のフォルダ）
  const src = path.join(ROOT, a.src), out = process.env.WB_OUT ? path.join(process.env.WB_OUT, path.basename(a.out)) : path.join(ROOT, a.out);
  const doc = await io.read(src); const root = doc.getRoot();
  for (const e of root.listExtensionsUsed()) e.dispose();
  const prim = root.listMeshes()[0].listPrimitives()[0];
  const pos = prim.getAttribute('POSITION'), nor = prim.getAttribute('NORMAL');
  const M = basis(a.map), P = pos.getArray(), N = nor.getArray(), n = P.length / 3;
  const Q = new Float32Array(P.length);
  // preRotY：斜めに置かれた形（変異の槍）を、先に y 軸のまわりに回してから軸を写す（度）
  const ry = (a.preRotY || 0) * Math.PI / 180, cr = Math.cos(ry), sr = Math.sin(ry), RY = v => [v[0] * cr + v[2] * sr, v[1], -v[0] * sr + v[2] * cr];
  for (let i = 0; i < n; i++) { const v = mul(M, RY([P[i * 3], P[i * 3 + 1], P[i * 3 + 2]])); Q.set(v, i * 3); const w = mul(M, RY([N[i * 3], N[i * 3 + 1], N[i * 3 + 2]])); N.set(w, i * 3); }
  let ymin = 1e9, ymax = -1e9; for (let i = 1; i < Q.length; i += 3) { ymin = Math.min(ymin, Q[i]); ymax = Math.max(ymax, Q[i]); }
  const L = ymax - ymin; let gy, cx = 0, cz = 0, s;
  // twist：長い軸（y）のまわりにひねる（度）。'auto' は、握る所より先（刃・頭）の断面がいちばん広がる向きを +z にそろえる。flip で 180° 回す
  let tw = 0;
  if (a.twist === 'auto') { const g0 = ymax - (a.grip || 0) * L; let mx = 0, mz = 0, k = 0;
    for (let i = 0; i < n; i++) if (Q[i * 3 + 1] < g0) { mx += Q[i * 3]; mz += Q[i * 3 + 2]; k++; } mx /= k; mz /= k; let sxx = 0, szz = 0, sxz = 0;
    for (let i = 0; i < n; i++) if (Q[i * 3 + 1] < g0) { const dx = Q[i * 3] - mx, dz = Q[i * 3 + 2] - mz; sxx += dx * dx; szz += dz * dz; sxz += dx * dz; }
    const th = 0.5 * Math.atan2(2 * sxz, sxx - szz); // 広がる向きの x 軸からの角度
    tw = th - Math.PI / 2; } else if (a.twist) tw = a.twist * Math.PI / 180;
  if (a.flip) tw += Math.PI;
  if (tw) { const c = Math.cos(tw), sn = Math.sin(tw); for (const A of [Q, N]) for (let i = 0; i < n; i++) { const x = A[i * 3], z = A[i * 3 + 2]; A[i * 3] = x * c + z * sn; A[i * 3 + 2] = -x * sn + z * c; } }
  if (a.hub) { // 投げ具：平たい形の真ん中（頂点の重心）を回る中心に。直径を hub に
    let x0 = 1e9, x1 = -1e9; for (let i = 0; i < n; i++) { cx += Q[i * 3]; cz += Q[i * 3 + 2]; x0 = Math.min(x0, Q[i * 3]); x1 = Math.max(x1, Q[i * 3]); }
    cx /= n; cz /= n; gy = (ymin + ymax) / 2; s = a.hub / (x1 - x0);
  } else { // 握る所：上端から grip の割合だけ下。その高さの輪切りの真ん中を原点に
    gy = ymax - a.grip * L; const band = L * 0.03; let x0 = 1e9, x1 = -1e9, z0 = 1e9, z1 = -1e9;
    for (let i = 0; i < n; i++) if (Math.abs(Q[i * 3 + 1] - gy) < band) { x0 = Math.min(x0, Q[i * 3]); x1 = Math.max(x1, Q[i * 3]); z0 = Math.min(z0, Q[i * 3 + 2]); z1 = Math.max(z1, Q[i * 3 + 2]); }
    cx = (x0 + x1) / 2; cz = (z0 + z1) / 2;
    s = a.tip / (ymin - gy); } // 先端が tip（負）に来る
  for (let i = 0; i < n; i++) { Q[i * 3] = (Q[i * 3] - cx) * s; Q[i * 3 + 1] = (Q[i * 3 + 1] - gy) * s; Q[i * 3 + 2] = (Q[i * 3 + 2] - cz) * s; }
  pos.setArray(Q); nor.setArray(N);
  const node = root.listNodes()[0]; node.setTranslation([0, 0, 0]).setRotation([0, 0, 0, 1]).setScale([1, 1, 1]);
  // 絵
  const mat = root.listMaterials()[0], base = mat.getBaseColorTexture();
  const baseImg = base.getImage();
  base.setImage(await sharp(baseImg).resize(a.tex, a.tex, { kernel: 'lanczos3' }).removeAlpha().jpeg({ quality: 86 }).toBuffer()).setMimeType('image/jpeg');
  const mr = mat.getMetallicRoughnessTexture(), nm = mat.getNormalTexture();
  mat.setMetallicRoughnessTexture(null).setNormalTexture(null).setOcclusionTexture(null).setMetallicFactor(0).setRoughnessFactor(1);
  if (mr) mr.dispose(); if (nm) nm.dispose();
  let lit = null;
  if (a.glow) { const g = await glowMask(baseImg, a.glow, a.glowTex || 512, a.cracks ? { n: a.cracks, seed: [...a.id].reduce((h, c) => (h * 31 + c.charCodeAt(0)) >>> 0, 7) } : null); const t = doc.createTexture('glow').setImage(g.jpg).setMimeType('image/jpeg');
    mat.setEmissiveTexture(t).setEmissiveFactor([1, 1, 1]); lit = g.litPct;
    const ti = mat.getBaseColorTextureInfo(), ei = mat.getEmissiveTextureInfo(); ei.setTexCoord(ti.getTexCoord()); }
  await doc.transform(prune(), dedup());
  fs.mkdirSync(path.dirname(out), { recursive: true });
  await io.write(out, doc);
  const buf = fs.readFileSync(out);
  const r = { id: a.id, out: a.out, bytes: buf.length, tris: prim.getIndices().getCount() / 3, verts: n, scale: +s.toFixed(4), twistDeg: +(tw * 180 / Math.PI).toFixed(1), lengthGame: +(L * s).toFixed(3), gripGame: a.hub ? null : +(a.grip * L * s).toFixed(3), glowPct: lit,
    sha256: crypto.createHash('sha256').update(buf).digest('hex'), srcSha256: crypto.createHash('sha256').update(fs.readFileSync(src)).digest('hex') };
  report.push(r); console.log(JSON.stringify(r));
}
if (!want.length && !process.env.WB_OUT) fs.writeFileSync(path.join(ROOT, 'assets/models/weapons/game-build.json'), JSON.stringify({ built: new Date().toISOString().slice(0, 10), tool: 'tools/models/weapon_build.mjs', assets: report }, null, 1) + '\n');
