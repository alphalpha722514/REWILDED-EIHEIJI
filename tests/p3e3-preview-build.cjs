// 手元の元ファイルから作り直し、保存済みの試遊版とバイト単位で照合する。
const assert = require('node:assert/strict');
const { execFileSync } = require('node:child_process');
const { createHash } = require('node:crypto');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const root = path.resolve(__dirname, '..');
const builder = path.join(root, 'tools', 'build-p3e3-farm-preview.py');
const source = process.env.PREVIEW_BUILD_SRC || path.join(root, 'index.html');
const saved = fs.readFileSync(path.join(root, 'previews', 'p3e3-farm', 'index.html'));
const temp = fs.mkdtempSync(path.join(root, '.p3e3-preview-build-'));
try {
  const output = path.join(temp, 'index.html');
  execFileSync('python3', [builder, '--src', source, '--out', output], { stdio: 'inherit' });
  const actual = fs.readFileSync(output);
  assert.ok(actual.equals(saved), '生成結果と保存済みの試遊版のバイトが違う');
  const scripts = [...actual.toString('utf8').matchAll(/<script\b([^>]*)>([\s\S]*?)<\/script>/gi)]
    .filter(([, attrs]) => !/\b(?:src|type)\s*=/.test(attrs));
  assert.ok(scripts.length, '構文を確認するスクリプトが見つからない');
  for (const [, , script] of scripts) new vm.Script(script);
  console.log(`合格：バイト一致・スクリプト ${scripts.length} 本の構文。SHA-256 ${createHash('sha256').update(actual).digest('hex')}`);
} finally {
  fs.rmSync(temp, { recursive: true, force: true });
}
