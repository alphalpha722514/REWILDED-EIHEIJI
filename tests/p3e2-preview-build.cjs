// git 内: node tests/p3e2-preview-build.cjs（ビルドスクリプトの REF のコミットが必要）
// git 外: PREVIEW_BUILD_SRC=/path/to/index.html node tests/p3e2-preview-build.cjs
// PREVIEW_BUILD_EXPECTED=/path/to/expected.html で比較相手を指定できる。
const { execFileSync } = require('node:child_process');
const { createHash } = require('node:crypto');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');

const root = path.resolve(__dirname, '..');
const builder = path.join(root, 'tools', 'build-p3e2-forest-preview.py');
const saved = path.join(root, 'previews', 'p3e2-forest', 'index.html');

function sha256(bytes) {
  return createHash('sha256').update(bytes).digest('hex');
}

function verifyBuild() {
  const script = fs.readFileSync(builder, 'utf8');
  const ref = script.match(/^REF = '([0-9a-f]{40})'/m)?.[1];
  const blob = script.match(/^BLOB = '([0-9a-f]{40})'/m)?.[1];
  if (!ref || !blob) {
    throw new Error('ビルドスクリプトから REF・BLOB を読み取れない');
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
      throw new Error(`${ref} を確認できない。git fetch origin main か v0.88-integration をしてから実行する`);
    }
  }

  const savedBefore = fs.readFileSync(saved);
  const savedHash = sha256(savedBefore);
  const expectedPath = process.env.PREVIEW_BUILD_EXPECTED;
  const expected = expectedPath === undefined ? savedBefore : fs.readFileSync(expectedPath);
  const temp = fs.mkdtempSync(path.join(os.tmpdir(), 'p3e2-preview-build-'));
  try {
    const output = path.join(temp, 'index.html');
    execFileSync('python3', [...args, '--out', output], { stdio: 'inherit' });
    const actual = fs.readFileSync(output);
    console.log(`生成: ${actual.length} bytes, SHA-256 ${sha256(actual)}`);
    console.log(`比較: ${expected.length} bytes, SHA-256 ${sha256(expected)}`);
    if (!actual.equals(expected)) {
      const sharedLength = Math.min(actual.length, expected.length);
      let offset = 0;
      while (offset < sharedLength && actual[offset] === expected[offset]) {
        offset += 1;
      }
      throw new Error(`最初に違う位置: バイト ${offset}（0 始まり）`);
    }
  } finally {
    fs.rmSync(temp, { recursive: true, force: true });
    if (sha256(fs.readFileSync(saved)) !== savedHash) {
      throw new Error('保存済みの試遊版の SHA-256 がビルド前後で変わった');
    }
  }
}

try {
  verifyBuild();
  console.log('PASS: 保存済みの試遊版の SHA-256 は変わらず、生成結果と比較相手はバイト単位で一致');
} catch (error) {
  console.error(`FAIL: ${error.message}`);
  process.exitCode = 1;
}
