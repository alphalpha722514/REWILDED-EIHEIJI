// 配列の出し入れ。node tools/mmio.mjs dump 入力.glb フォルダ  → pos/nor/uv(Float32)・idx(Uint32)・meta.json と色テクスチャ
import { NodeIO } from '@gltf-transform/core';
import { ALL_EXTENSIONS } from '@gltf-transform/extensions';
import { dequantize } from '@gltf-transform/functions';
import { MeshoptDecoder } from 'meshoptimizer';
import fs from 'fs';
const [cmd, src, dir] = process.argv.slice(2);
await MeshoptDecoder.ready;
const io = new NodeIO().registerExtensions(ALL_EXTENSIONS).registerDependencies({ 'meshopt.decoder': MeshoptDecoder });
if (cmd === 'dump') {
  const doc = await io.read(src); await doc.transform(dequantize());
  const pr = doc.getRoot().listMeshes()[0].listPrimitives()[0]; fs.mkdirSync(dir, { recursive: true });
  const w = (n, a) => fs.writeFileSync(`${dir}/${n}.bin`, Buffer.from(a.buffer, a.byteOffset, a.byteLength));
  w('pos', new Float32Array(pr.getAttribute('POSITION').getArray())); w('nor', new Float32Array(pr.getAttribute('NORMAL').getArray()));
  w('uv', new Float32Array(pr.getAttribute('TEXCOORD_0').getArray())); w('idx', new Uint32Array(pr.getIndices().getArray()));
  const m = doc.getRoot().listMaterials()[0];
  fs.writeFileSync(`${dir}/color.jpg`, m.getBaseColorTexture().getImage()); if (m.getNormalTexture()) fs.writeFileSync(`${dir}/normal.png`, m.getNormalTexture().getImage());
  fs.writeFileSync(`${dir}/meta.json`, JSON.stringify({ verts: pr.getAttribute('POSITION').getCount(), tris: pr.getIndices().getCount() / 3 }));
  console.log('dumped', dir);
}
