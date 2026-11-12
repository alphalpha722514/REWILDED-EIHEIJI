// 配列とテクスチャから GLB を作る。三角形を減らし、テクスチャを小さくする。
// node mm_build.mjs 配列フォルダ 出力.glb 目標三角形数 テクスチャ大きさ
import { Document, NodeIO } from '@gltf-transform/core';
import { MeshoptSimplifier } from 'meshoptimizer';
import { execFileSync } from 'child_process';
import fs from 'fs';
import os from 'os';

const [dir, out, targetS, texS] = process.argv.slice(2);
await MeshoptSimplifier.ready;
const rd = (n, T) => { const b = fs.readFileSync(`${dir}/${n}.bin`); return new T(b.buffer.slice(b.byteOffset, b.byteOffset + b.byteLength)); };
let P = rd('pos', Float32Array), N = rd('nor', Float32Array), UV = rd('uv', Float32Array), I = rd('idx', Uint32Array);
const t0 = I.length / 3;
let err = 0;
const meta = JSON.parse(fs.readFileSync(`${dir}/meta.json`)); const keepT = meta.keep_tail_tris || 0; // 最後の keepT 面（新しい尾）は減らさない
if (+targetS < t0) { const body = I.subarray(0, (t0 - keepT) * 3), tail = I.subarray((t0 - keepT) * 3);
  const [res, e] = MeshoptSimplifier.simplify(body, P, 3, (+targetS - keepT) * 3, 0.05, []); const J = new Uint32Array(res.length + tail.length); J.set(res); J.set(tail, res.length); I = J; err = e; }
// 使う頂点だけに詰める
const nv = P.length / 3, remap = new Int32Array(nv).fill(-1); let k = 0;
for (const v of I) if (remap[v] < 0) remap[v] = k++;
const pack = (A, es) => { const o = new Float32Array(k * es); for (let v = 0; v < nv; v++) if (remap[v] >= 0) for (let j = 0; j < es; j++) o[remap[v] * es + j] = A[v * es + j]; return o; };
P = pack(P, 3); N = pack(N, 3); UV = pack(UV, 2); I = Uint32Array.from(I, v => remap[v]);
// テクスチャ
const tmp = os.tmpdir() + '/_mm_b';
execFileSync('python3', ['-c', `from PIL import Image; im=Image.open('${dir}/color.jpg').convert('RGB').resize((${texS},${texS}), Image.LANCZOS); im.save('${tmp}', 'JPEG', quality=85)`]);
const doc = new Document(); const buf = doc.createBuffer();
const acc = (arr, type) => doc.createAccessor().setArray(arr).setType(type).setBuffer(buf);
const tex = doc.createTexture('color').setImage(fs.readFileSync(tmp)).setMimeType('image/jpeg');
const mat = doc.createMaterial('mutant_monkey').setBaseColorTexture(tex).setMetallicFactor(0).setRoughnessFactor(0.9);
const prim = doc.createPrimitive().setAttribute('POSITION', acc(P, 'VEC3')).setAttribute('NORMAL', acc(N, 'VEC3'))
  .setAttribute('TEXCOORD_0', acc(UV, 'VEC2')).setIndices(acc(k < 65536 ? Uint16Array.from(I) : I, 'SCALAR')).setMaterial(mat);
const mesh = doc.createMesh('mutant_monkey').addPrimitive(prim);
doc.createScene().addChild(doc.createNode('mutant_monkey').setMesh(mesh));
await new NodeIO().write(out, doc);
console.log(JSON.stringify({ before: t0, after: I.length / 3, verts: k, simplifyError: +err.toFixed(5), bytes: fs.statSync(out).size }));
