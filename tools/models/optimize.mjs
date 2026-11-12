// 試作：三角形を減らし、テクスチャを小さくする（元ファイルは変えない）。
// node optimize.mjs 入力.glb 出力.glb 目標三角形数 テクスチャ大きさ [normal]
// 三角形は meshoptimizer の simplify を1回だけかける（UV の継ぎ目は同じ位置の頂点として守られる）。
import { NodeIO } from '@gltf-transform/core';
import { ALL_EXTENSIONS } from '@gltf-transform/extensions';
import { dequantize, prune, dedup } from '@gltf-transform/functions';
import { MeshoptDecoder, MeshoptSimplifier } from 'meshoptimizer';
import { execFileSync } from 'child_process';
import fs from 'fs';
import os from 'os';

const [src, out, targetS, texS, keepNormal] = process.argv.slice(2);
const target = +targetS, texSize = +texS;
await MeshoptDecoder.ready; await MeshoptSimplifier.ready;
const io = new NodeIO().registerExtensions(ALL_EXTENSIONS).registerDependencies({ 'meshopt.decoder': MeshoptDecoder });
const doc = await io.read(src);
await doc.transform(dequantize());
for (const ext of doc.getRoot().listExtensionsUsed()) if (/meshopt|quantization/i.test(ext.extensionName)) ext.dispose();
const prim = doc.getRoot().listMeshes()[0].listPrimitives()[0];
const pos = prim.getAttribute('POSITION'), idx = prim.getIndices();
const P = new Float32Array(pos.getArray()), I = new Uint32Array(idx.getArray());
const t0 = I.length / 3;
// 1枚だけ離れた三角形（頭の上の小さな破片）を先に除く：ほかとつながらない三角形
const key = i => `${P[i * 3]},${P[i * 3 + 1]},${P[i * 3 + 2]}`;
const cnt = new Map(); for (const v of I) cnt.set(key(v), (cnt.get(key(v)) || 0) + 1);
const keep = []; let removed = 0;
for (let t = 0; t < I.length; t += 3) { const lone = [0, 1, 2].every(k => cnt.get(key(I[t + k])) === 1); if (lone) { removed++; continue; } keep.push(I[t], I[t + 1], I[t + 2]); }
let errOut = 0, J = Uint32Array.from(keep);
if (target < J.length / 3) {
  const [res, e] = MeshoptSimplifier.simplify(J, P, 3, target * 3, 0.05, []);
  J = res; errOut = e;
}
// 使う頂点だけに詰める
const remap = new Int32Array(P.length / 3).fill(-1); let n = 0; for (const v of J) if (remap[v] < 0) remap[v] = n++;
for (const name of prim.listSemantics()) { const a = prim.getAttribute(name), es = a.getElementSize(), src2 = a.getArray(), dst = new src2.constructor(n * es);
  for (let v = 0; v < remap.length; v++) if (remap[v] >= 0) for (let k = 0; k < es; k++) dst[remap[v] * es + k] = src2[v * es + k];
  a.setArray(dst); }
idx.setArray(Uint32Array.from(J, v => remap[v]));
// テクスチャ：色だけ残し、指定の大きさの JPEG に（ORM は使わない。法線は指定時だけ）
const mat = doc.getRoot().listMaterials()[0];
const shrink = (tex, q) => {
  const tin = os.tmpdir() + '/_mm_t_in', tout = os.tmpdir() + '/_mm_t_out'; fs.writeFileSync(tin, tex.getImage());
  execFileSync('python3', ['-c', `from PIL import Image; im=Image.open('${tin}').convert('RGB').resize((${texSize},${texSize}), Image.LANCZOS); im.save('${tout}', 'JPEG', quality=${q})`]);
  tex.setImage(fs.readFileSync(tout)).setMimeType('image/jpeg');
};
shrink(mat.getBaseColorTexture(), 85);
mat.setMetallicRoughnessTexture(null); mat.setMetallicFactor(0).setRoughnessFactor(0.9);
if (keepNormal) shrink(mat.getNormalTexture(), 90); else mat.setNormalTexture(null);
await doc.transform(prune(), dedup());
await io.write(out, doc);
console.log(JSON.stringify({ before: t0, loneRemoved: removed, after: J.length / 3, verts: n, simplifyError: +errOut.toFixed(5), bytes: fs.statSync(out).size }));
