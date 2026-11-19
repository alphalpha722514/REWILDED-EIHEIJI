// P3-C：新しい住民3人の見た目の候補（指示書 v1.1 §7・§7.4。ユーザーの承認の前の案。ゲームにはまだ入れない）
// tools/char-studio.py で STUDIO_CANDS=tools/p3c-npc-candidates.js を指定すると、ここの名前で並べられる。
// ページの中で評価する（mesh・mat・G・outline・THREE はゲームの関数）。
(() => {
  const {mesh, mat, bmat, outline, G, THREE} = window.__studio; // ゲームの関数（char-studio.py が出す口）
  const headC = head => head.children.find(c => c.isGroup && c.position.y > 0.05) || head; // 頭の形の中心（帽子・眼鏡と同じ所）
  // 作業用のゴーグル（額に上げている）
  const goggles = (lens, strap) => ({head, R}) => { const h = headC(head), y = R * 0.48, z = R * 0.84;
    const st = mesh(G.cyl, mat(strap), 0, y - R * 0.02, -R * 0.02, R * 1.03, R * 0.16, R * 1.03); h.add(st);
    for (const s of [-1, 1]) { const f = mesh(G.cyl8, mat(0x2a2a2c), s * R * 0.34, y, z, R * 0.27, R * 0.2, R * 0.27); f.rotation.x = Math.PI / 2 - 0.35; h.add(outline(f, 0.02));
      const l = mesh(G.circ, bmat(lens), s * R * 0.34, y + R * 0.035, z + R * 0.095, R * 0.2, 1, R * 0.2); l.rotation.x = Math.PI / 2 - 0.35; h.add(l); } };
  // 背中の釣り竿と腰の魚籠（びく）
  const fisher = (rodCol, creel, back = true) => ({chest, body, T}) => { if (back) { const r = new THREE.Group(); r.position.set(0.02, T(0.7) - T(0.62), -0.2); r.rotation.z = 0.42; chest.add(r);
    r.add(mesh(G.cyl8, mat(0x2a2420), 0, -0.2, 0, 0.035, 0.42, 0.035)); r.add(mesh(G.cyl8, mat(rodCol), 0, 0.62, 0, 0.014, 1.25, 0.014)); r.add(mesh(G.cyl8, mat(0xb0a890), 0.03, -0.05, 0.03, 0.05, 0.05, 0.05)); }
    const b = new THREE.Group(); b.position.set(0.27, T(0.4), 0.04); body.add(b); const box = mesh(G.box, mat(creel), 0, 0, 0, 0.13, 0.16, 0.09); b.add(outline(box, 0.02));
    b.add(mesh(G.box, mat(0x5a4632), 0, 0.085, 0, 0.14, 0.02, 0.1)); };
  // 手に持つ釣り竿
  const rodInHand = rodCol => ({armR}) => { const h = armR.userData.hand; const r = mesh(G.cyl8, mat(rodCol), 0, 0.55, 0.12, 0.013, 1.5, 0.013); r.rotation.x = 0.35; h.add(r); h.add(mesh(G.cyl8, mat(0x2a2420), 0, -0.05, 0.02, 0.03, 0.2, 0.03)); };
  const both = (...fs) => a => { for (const f of fs) f(a); };

  // 山下澄江（60代後半の女性・短い白髪・作業用の上着とズボン）
  const sumie = {scale: 0.84, girth: 1.12, waist: 1.02, headR: 0.44, limb: 0.9};
  // リオ（20代前半の女性・短髪・作業着・腰に工具ポーチ）
  const rio = {scale: 0.8, tall: 1.14, legLen: 1.75, armLen: 1.4, girth: 0.8, waist: 0.78, neck: 0.88, headR: 0.44, limb: 0.78, legGap: 1.15}; // 若い人は主人公・スズキと同じすらっとした体（年配の村人は丸い体）
  // 川村宗一（50代の男性・作業着・長靴・使い込まれた釣り具）
  const soichi = {scale: 1.0, girth: 1.12, headR: 0.41, limb: 0.95};
  const C = window.__cands = {
    sumieA: Object.assign({}, sumie, {outfit: { // A 紺の作業ジャンパー・もんぺ風のズボン・首にタオル
      top: {col: 0x34405a, col2: 0x283248, hem: 0.38, sleeve: 'long', cut: 0.93, collar: 'stand', zip: true, pockets: true, t: 0.034},
      bottom: {col: 0x6a6258, col2: 0x58514a, top: 0.5, wide: 0.045, taper: true, t: 0.032},
      shoes: {kind: 'shoes', col: 0x4a4440, sole: 0x2a2624}, neckTowel: 0xf2efe6, hair: {style: 'perm', col: 0xe6e4de}, armband: false}}),
    sumieB: Object.assign({}, sumie, {outfit: { // B えんじの上着・綿入れのベスト（ちゃんちゃんこ）
      top: {col: 0x8e4a4a, col2: 0x7a3a3a, hem: 0.4, sleeve: 'long', cut: 0.95, collar: 'v', collarCol: 0xd8cbb8, t: 0.032},
      vest: {col: 0x3e5a48, col2: 0x2e4638, hem: 0.47, t: 0.04},
      bottom: {col: 0x4a4a52, col2: 0x3a3a42, top: 0.5, wide: 0.04, taper: true, t: 0.03},
      shoes: {kind: 'shoes', col: 0x6a5a48, sole: 0x2a2420}, hair: {style: 'perm', col: 0xe6e4de}, armband: false}}),
    sumieC: Object.assign({}, sumie, {outfit: { // C 日よけ帽の野良着・長靴
      top: {col: 0x8a9a6a, col2: 0x76865a, hem: 0.38, sleeve: 'rolled', cut: 0.62, collar: 'stand', pockets: true, t: 0.032},
      bottom: {col: 0x5a5448, col2: 0x4a453a, top: 0.5, wide: 0.035, kneePad: 0x4a4438, t: 0.03},
      shoes: {kind: 'rubber', col: 0x2f4a3a, sole: 0x1e2a22}, neckTowel: 0xf6f2e6, hat: 'brim', hatCol: 0xe6dcc2, hatCol2: 0xcfbf9c,
      hair: {style: 'perm', col: 0xe6e4de}, armband: false}}),
    rioA: Object.assign({}, rio, {outfit: { // A グレーのつなぎ・腕まくり・ゴーグル
      top: {col: 0x6c737a, col2: 0x5a6168, hem: 0.36, sleeve: 'rolled', cut: 0.6, collar: 'stand', zip: true, pockets: true, t: 0.032},
      bottom: {col: 0x6c737a, col2: 0x5a6168, top: 0.5, kneePad: 0x4a5056, t: 0.03},
      belt: {col: 0x5a3e2a, w: 0.04, y: 0.43, over: true, pouch: 0x7a5a3a, buckle: true},
      shoes: {kind: 'boots', col: 0x2a2624, col2: 0x3a3430}, hair: {style: 'bob', col: 0x2a1c14}, armband: false},
      extra: goggles(0x9ad0e0, 0x3a3a3a)}),
    rioB: Object.assign({}, rio, {outfit: { // B 紺の作業ジャケット（反射の線）・カーゴパンツ
      top: {col: 0x2c3a56, col2: 0x223048, hem: 0.4, sleeve: 'long', cut: 0.93, collar: 'stand', zip: true, pockets: true, refl: 0xc8d0d8, t: 0.034},
      bottom: {col: 0x8a7a5a, col2: 0x76684a, top: 0.48, cargo: true, cargoBig: true, taper: true, t: 0.03},
      belt: {col: 0x3a2a1e, w: 0.04, y: 0.43, over: true, pouch: 0x6a4a30, buckle: true},
      shoes: {kind: 'boots', col: 0x5a4a38, col2: 0x7a6048}, hair: {style: 'bob', col: 0x161412}, armband: false}}),
    rioC: Object.assign({}, rio, {outfit: { // C オレンジの作業着・紺のズボン・ゴーグル
      top: {col: 0xc8642a, col2: 0xa84e20, hem: 0.38, sleeve: 'rolled', cut: 0.62, collar: 'stand', zip: true, pockets: true, t: 0.032},
      bottom: {col: 0x2e3440, col2: 0x242a34, top: 0.48, cargo: true, t: 0.03},
      belt: {col: 0x2a2420, w: 0.04, y: 0.43, over: true, pouch: 0x5a5a48, buckle: true},
      shoes: {kind: 'boots', col: 0x2a2a2a, col2: 0x3a3a3a}, hair: {style: 'bob', col: 0x4a3020}, armband: false},
      extra: goggles(0xd8e8ec, 0x2a2a2a)}),
    soichiA: Object.assign({}, soichi, {outfit: { // A 釣りのベスト・長靴・つばの帽子・背中の竿と腰の魚籠
      top: {col: 0x6a6e66, col2: 0x5a5e56, hem: 0.4, sleeve: 'long', cut: 0.93, collar: 'stand', pockets: true, t: 0.032},
      vest: {col: 0x5e6a3e, col2: 0x4a5430, hem: 0.5, patch: 0x4a5230, t: 0.035},
      bottom: {col: 0x3e4048, col2: 0x30323a, top: 0.5, t: 0.03},
      shoes: {kind: 'rubber', col: 0x2a3a2a, sole: 0x161e16}, hat: 'brim', hatCol: 0x9a8e6a, hatCol2: 0x7e7454,
      hair: {style: 'cropped', col: 0x4a4540}, armband: false},
      extra: fisher(0x3a3028, 0x8a7048)}),
    soichiB: Object.assign({}, soichi, {outfit: { // B 胴長（ウェーダー）・紺の上着・首にタオル・手に竿
      top: {col: 0x3a4a5e, col2: 0x2e3c4e, hem: 0.42, sleeve: 'long', cut: 0.93, collar: 'stand', zip: true, t: 0.034},
      bottom: {col: 0x4a5a3a, col2: 0x3c4a2e, top: 0.62, t: 0.034},
      shoes: {kind: 'rubber', col: 0x4a5a3a, sole: 0x262e1e}, neckTowel: 0xe8e2d4, hair: {style: 'cropped', col: 0x6a6660}, armband: false},
      extra: both(rodInHand(0x3a3028), fisher(0x3a3028, 0x8a7048, false))}),
  };
  return Object.keys(C);
})()
