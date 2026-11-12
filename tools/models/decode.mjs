// 元の GLB（meshopt 圧縮・量子化）を、調べやすい普通の GLB とテクスチャ画像にほどく。元ファイルは変えない。
import { NodeIO } from '@gltf-transform/core';
import { ALL_EXTENSIONS } from '@gltf-transform/extensions';
import { dequantize } from '@gltf-transform/functions';
import { MeshoptDecoder } from 'meshoptimizer';
import fs from 'fs';

const [src, out, texDir] = process.argv.slice(2);
await MeshoptDecoder.ready;
const io = new NodeIO().registerExtensions(ALL_EXTENSIONS).registerDependencies({ 'meshopt.decoder': MeshoptDecoder });
const doc = await io.read(src);
await doc.transform(dequantize());
for (const ext of doc.getRoot().listExtensionsUsed()) if (/meshopt|quantization/i.test(ext.extensionName)) ext.dispose();
fs.mkdirSync(texDir, { recursive: true });
for (const t of doc.getRoot().listTextures()) {
  const ext = t.getMimeType() === 'image/png' ? 'png' : 'jpg';
  fs.writeFileSync(`${texDir}/${t.getName() || 'tex'}.${ext}`, t.getImage());
  console.log('texture', t.getName(), t.getMimeType(), t.getSize(), t.getImage().length);
}
for (const m of doc.getRoot().listMaterials()) console.log('material', m.getName(), 'baseColor', m.getBaseColorFactor(), 'metal', m.getMetallicFactor(), 'rough', m.getRoughnessFactor(), 'alpha', m.getAlphaMode(), 'double', m.getDoubleSided());
for (const n of doc.getRoot().listNodes()) console.log('node', n.getName(), 'T', n.getTranslation(), 'R', n.getRotation(), 'S', n.getScale());
await io.write(out, doc);
console.log('wrote', out);
