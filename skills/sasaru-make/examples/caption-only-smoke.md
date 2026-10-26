---
schema: sasaru-playbook/3
id: caption-only-smoke
name: 問いかけから言い切りまでの字だけの三拍
status: draft
summary: 喋る人も映像も無く、太い白字のテロップだけで問いかけ、仕組み、言い切りを三拍で見せる。最後の句が絵の終わりまで残る。
tags: [caption-only, text-motion, smoke]
fitsContent:
  - アプリや道具の一行で言える効き目
  - 悩みの言い当てと、その答え
contentRoute: reference-world
subject:
  of: reference-world
  words: 問いかけから言い切りまでを、字だけが三拍で進む
spreadPsychology:
  plays:
    mechanism: 問いの未完了。開いた問いが、答えの一句まで注意を残す
    trigger: 最初のフレームの問いが習慣を言い当て、言い切りは最後の拍まで出さない
    basis: inferred
  comments:
    mechanism: 自分の面倒を一文で返す自己参照
    trigger: 問いが習慣の形で、見る人の別の面倒を書く穴になる
    basis: inferred
  shares:
    mechanism: 言い当てられた面倒を、同じ習慣の相手に渡す実用
    trigger: 言い切りの一句が絵の終わりまで残り、送った画面がその答えになる
    basis: inferred
source:
  kind: hand-written
  platform: none
  rightsTier: none
  measuredFiles: 0
format:
  aspect: "9:16"
  fps: 30
  durationSec: { min: 8, max: 12, reference: 10 }
  onCamera: none
  speech: none
  safeArea: { top: 0.11, bottom: 0.25, left: 0.06, right: 0.14 }
hook:
  type: question
  firstFrameHasText: true
beats:
  - { id: b1, role: hook, tIn: 0.0, tOut: 2.6, purpose: 見る人が自分の習慣だと思う問いを最初のフレームから見せる, swap: 自分の見る人がやりがちな面倒を問いの形で }
  - { id: b2, role: item, tIn: 2.6, tOut: 5.8, purpose: 面倒が何に置き換わるかを二枚で渡す, swap: 自分の道具が何をしてくれるかを二句で }
  - { id: b3, role: payoff, tIn: 5.8, tOut: 10.0, purpose: 言い切りの一句を寄りで止めて、名前を添えて残す, swap: 言い切りの一句と、道具の名前 }
captions:
  - id: c1
    role: headline
    beats: []
    unit: phrase
    writingMode: horizontal
    font: { class: extra-bold-gothic, weight: 900 }
    capHeightRatio: null
    emphasis: { scale: 1.3, color: "#FFD84D" }
    color: "#FFFFFF"
    stroke: { color: "#000000", px1080: 9 }
    shadow: true
    plate: none
    position: { cx: 0.46, cy: 0.42, align: center }
    linesMax: 2
    charsPerCard: { min: 2, max: 14 }
    motionIn: pop
    motionOut: cut
    show: before-onset
    leadSec: 0.1
    hide: next-card
    minHoldSec: 1.0
    lastCard: hold-to-end
  - id: c2
    role: label
    beats: [b3]
    unit: card
    writingMode: horizontal
    font: { class: extra-bold-gothic, weight: 700 }
    capHeightRatio: 0.026
    emphasis: null
    color: "#9EE6FF"
    stroke: null
    shadow: false
    plate: pill
    position: { cx: 0.46, cy: 0.6, align: center }
    linesMax: 1
    charsPerCard: { min: 2, max: 16 }
    motionIn: fade
    motionOut: cut
    show: beat-start
    leadSec: null
    hide: beat-end
    minHoldSec: 1.0
    lastCard: hold-to-end
camera:
  moves:
    - { beat: b1, move: static }
    - { beat: b2, move: push-in }
    - { beat: b3, move: static }
  zooms:
    - { at: { beat: b3, offsetSec: 0 }, scaleFrom: 1.0, scaleTo: 1.08, durSec: 0.25, easing: ease-out }
  transitions:
    - { at: { beat: b3, offsetSec: 0 }, type: zoom-cut }
audio:
  bgm:
    present: true
    character: 明るめで軽いループ、中くらいのテンポ、声の邪魔をしない
    entersAt: { beat: b1, offsetSec: 0 }
  sfx:
    - { cue: card-in, type: pop }
    - { cue: payoff, at: { beat: b3, offsetSec: 0 }, type: confirm }
  voice: none
  referenceAudioUsed: false
routes:
  - id: code-motion
    default: true
    container: hyperframes
    needs: [none]
    paidApi: false
    talkingHead: false
    costUsdPerVideo: { min: 0, max: 0, basis: ローカルの HyperFrames で描画し、ffmpeg で音を混ぜる。エージェントのトークン代は含まない }
    status: tested
  - id: i2v
    default: false
    container: hyperframes
    needs: [image-gen, i2v]
    paidApi: true
    talkingHead: false
    costUsdPerVideo: { min: 0.3, max: 1.2, basis: 背景の静止画 1〜3 枚と 720p の I2V を 3〜8 秒。routes.md の 2026-10-25 の公開単価から, asOf: 2026-10-25 }
    status: design-only
fonts:
  - { family: Noto Sans JP, license: OFL-1.1, source: "https://fonts.google.com/noto/specimen/Noto+Sans+JP" }
rights:
  makerSupplies:
    - 自分で書いた台本
    - CC0、CC BY 4.0、自作のどれかで、ライセンスを記録した BGM と効果音のファイル
  neverUse:
    - 他人の動画の映像、音、テロップの文言
    - 再配布できない源の音を、リポジトリに置くこと
evidence:
  measured: []
  inferred: [hook.type, beats, format.safeArea, captions.c1.position, captions.c1.emphasis, captions.c1.stroke, captions.c1.leadSec, captions.c1.minHoldSec, captions.c2.capHeightRatio, captions.c2.position, camera.zooms, camera.transitions, audio.sfx]
  unmeasured: [captions.c1.capHeightRatio]
---

# 問いかけから言い切りまでの字だけの三拍

sasaru-make の確かめ用に手で書いた型である。参照動画は無い。数はすべて推論か未計測で、`evidence` に分けた。

## 構成と尺

参照の尺 10 秒の上に三拍。問い（0〜2.6 秒）、仕組み（2.6〜5.8 秒）、言い切り（5.8〜10 秒）。ハードカットは無く、拍の切れ目は字の入れ替わりと寄りで見せる。8〜12 秒の帯で伸び縮みさせ、ビートに付いた寄りと効果音は同じ比で動く。

## フック

最初のフレームから問いの一枚が出ている。動いて出るのではなく、0 秒で全部読める。見る人が自分の習慣に当てはめて止まる。

## ビート

- b1（hook）: 問い。一枚か二枚。
- b2（item）: 面倒が何に置き換わるかを二枚。背景がゆっくり寄る。
- b3（payoff）: 言い切りの一句を寄りで止め、道具の名前を小さな札で添える。

## テロップ

- c1（headline）: 極太ゴシック 900、白、黒の縁 9 px（1080 幅）、影あり。中心 (0.46, 0.42)、二段まで、一枚 2〜12 字。強調は 1.3 倍の黄色で、強調だけの段に使う。一つの段に大小を混ぜない。0.1 秒先に出し、次の一枚まで残し、最後の一枚は絵の終わりまで残す。最短 1.0 秒。白い芯の高さは未計測で、make が見出しの帯（0.057）に上げる。
- c2（label）: b3 だけ。太さ 700、水色の字に黒い半透明の丸座布団、中心 (0.46, 0.60)、一段、拍の頭で出て拍の終わりまで残る。見出しの白と強調の黄とは別の色にして、層を色で見分けられるようにする。

## カメラとトランジションとズーム

b2 で背景がゆっくり寄る。b3 の頭で 1.0 から 1.08 へ 0.25 秒の寄り（ease-out）と、ズームカット。ズームカットでは地の色が切り替わる。b2 の頭にカットは無く、見た目の変化は字の入れ替わりだけ。

## BGM と効果音

明るめで軽いループを 0 秒から。カード c1 が出るたびに軽いポップ、b3 の頭に決定音。声は無い。

## なぜ伸びるか

推論。最初のフレームで読める問いが、見る人の習慣を言い当てて止める。二枚目以降は答えを小出しにして最後まで見せる。言い切りが絵の終わりまで残るので、読み終える前に次へ流されない。伸びない側に落ちない理由は、字が見出しの大きさで、喋る人や素材の出来に左右されないこと。

## 差し替える場所

- b1: 自分の見る人がやりがちな面倒の問い。
- b2: 道具が何をしてくれるかを二句。
- b3: 言い切りの一句と、道具の名前（c2）。

変えてはいけない部分。最初のフレームに字があること、最後の一枚を絵の終わりまで残すこと、見出しの大きさ。

## 制作ルート

### code-motion

1. `uv run --script skills/sasaru-make/scripts/plan.py <playbook> <content.yaml>` で `sasaru/cuts/<cut-id>/cut.json` を書く。
2. `uv run --script skills/sasaru-make/scripts/render_code_motion.py sasaru/cuts/<cut-id>` で HyperFrames に描かせ、ffmpeg で曲と効果音を混ぜる。
3. sasaru-gate のカット検査を通す。

### i2v

1. plan.py を `--route i2v` で走らせ、`content.generate` の各ビートのプロンプトで見積もりだけ取る。
2. 見積もりを作る人が承認したら、計画に書かれた送信コマンドを一回だけ走らせる。
3. 返ってきたクリップの音を外し、`assets` に入れて code-motion と同じ手順で組む。

## 編集の器とフォント

器は HyperFrames（Apache 2.0）。フォントは Noto Sans JP（OFL-1.1）を google/fonts から取る。ファイルはコミットしない。

## 素材の権利

作る人が用意するのは台本と、ライセンスを記録した曲と効果音のファイル。他人の動画の映像、音、文言は使わない。

## 費用の目安

code-motion は 0 USD（ローカル描画）。i2v は 1 本 0.3〜1.2 USD の見込みで、時点は 2026-10-25、根拠は routes.md の公開単価。

## 測ったことと推論

測った数は無い。手書きの型なので、ビート、位置、縁、先行秒、最短表示、寄り、効果音はすべて推論。c1 の白い芯の高さは未計測。声が無いので、声の下の BGM の差は欄ごと書かない。
