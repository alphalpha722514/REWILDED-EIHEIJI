// git 内: node tests/p3e3-preview-build.cjs（ビルドスクリプトの REF のコミットが必要）
// git 外: PREVIEW_BUILD_SRC=/path/to/index.html node tests/p3e3-preview-build.cjs
// PREVIEW_BUILD_EXPECTED=/path/to/expected.html で比較相手を指定できる。
const assert = require('node:assert/strict');
const { execFileSync } = require('node:child_process');
const { createHash } = require('node:crypto');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const root = path.resolve(__dirname, '..');
const builder = path.join(root, 'tools', 'build-p3e3-farm-preview.py');
const saved = path.join(root, 'previews', 'p3e3-farm', 'index.html');

function verifyBuild() {
  const script = fs.readFileSync(builder, 'utf8');
  const ref = script.match(/^REF = '([0-9a-f]{40})'/m)?.[1];
  const blob = script.match(/^BLOB = '([0-9a-f]{40})'/m)?.[1];
  if (!ref || !blob) {
    throw new Error('古い農家のビルドスクリプトから REF・BLOB を読み取れない');
  }

  const args = [builder];
  const src = process.env.PREVIEW_BUILD_SRC;
  if (src !== undefined) {
    const bytes = fs.readFileSync(src);
    const actualBlob = createHash('sha1')
      .update(`blob ${bytes.length}\0`)
      .update(bytes)
      .digest('hex');
    if (actualBlob !== blob) {
      throw new Error(`PREVIEW_BUILD_SRC の blob が違う（実際: ${actualBlob}、期待: ${blob}）`);
    }
    args.push('--src', src);
  } else {
    try {
      execFileSync('git', ['-C', root, 'rev-parse', '--verify', `${ref}^{commit}`], {
        stdio: 'ignore',
      });
    } catch {
      throw new Error(`REF のコミット ${ref} を確認できない。git fetch で取得するか、PREVIEW_BUILD_SRC にそのコミットの index.html を指定する`);
    }
  }

  const expected = fs.readFileSync(process.env.PREVIEW_BUILD_EXPECTED ?? saved);
  const temp = fs.mkdtempSync(path.join(root, '.p3e3-preview-build-'));
  try {
    const output = path.join(temp, 'index.html');
    execFileSync('python3', [...args, '--out', output], { stdio: 'inherit' });
    const actual = fs.readFileSync(output);
    assert.ok(actual.equals(expected), '古い農家の試遊版の生成結果と比較相手のバイトが違う');
    const scripts = [...actual.toString('utf8').matchAll(/<script\b([^>]*)>([\s\S]*?)<\/script>/gi)]
      .filter(([, attrs]) => !/\b(?:src|type)\s*=/.test(attrs));
    assert.ok(scripts.length, '構文を確認するスクリプトが見つからない');
    for (const [, , script] of scripts) new vm.Script(script);
    console.log(`合格：バイト一致・スクリプト ${scripts.length} 本の構文。SHA-256 ${createHash('sha256').update(actual).digest('hex')}`);
  } finally {
    fs.rmSync(temp, { recursive: true, force: true });
  }
}

try {
  verifyBuild();
} catch (error) {
  console.error(`FAIL: ${error.message}`);
  process.exitCode = 1;
}
