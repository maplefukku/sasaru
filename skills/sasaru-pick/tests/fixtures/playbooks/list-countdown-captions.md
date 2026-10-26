---
schema: sasaru-playbook/3
id: list-countdown-captions
name: 字幕だけの三つ数え
status: measured
summary: 黒地に大きな見出しテロップが三枚出て、三つ目で言い切る。人は映らない。
tags: [list, captions-only, study]
audience:
  - 中高生
fitsContent:
  - 勉強法のコツ
  - 習慣化のヒント
  - アプリの機能紹介
contentRoute: reference-world
subject:
  of: reference-world
  words: 三つ数える字幕だけで、言い切りまで進む
spreadPsychology:
  plays:
    mechanism: 数えの未完了。約束した個数に届くまで、課題が閉じない
    trigger: 最初の拍が三つあると約束し、言い切りは最後の拍まで出さない
    basis: inferred
  comments:
    mechanism: 空いた項目に自分の一件を足したくなる自己生成
    trigger: 三つが一般のコツで、見る人の別の一つを書く穴が残る
    basis: inferred
  shares:
    mechanism: 短い手順を相手の役に立つものとして渡す実用
    trigger: 言い切りが最後の一枚に残り、送り先が三つの中身をそのまま読める
    basis: inferred
source:
  kind: hand-written
  platform: none
  rightsTier: none
  measuredFiles: 0
format:
  aspect: "9:16"
  fps: 30
  durationSec: { min: 7, max: 15, reference: 11 }
  onCamera: none
  speech: none
hook:
  type: list-promise
  firstFrameHasText: true
beats:
  - { id: b1, role: hook, tIn: 0.0, tOut: 1.2, purpose: 三つあると約束して止める, swap: 自分の約束の一句 }
  - { id: b2, role: item, tIn: 1.2, tOut: 8.0, purpose: 一つずつ短く渡す, swap: 自分のコツ三つ }
  - { id: b3, role: payoff, tIn: 8.0, tOut: 11.0, purpose: 三つ目で言い切って残す, swap: 自分の結論 }
captions:
  - id: c1
    role: headline
    beats: []
    unit: phrase
    writingMode: horizontal
    font: { class: extra-bold-gothic, weight: 900 }
    capHeightRatio: null
    emphasis: null
    color: "#FFFFFF"
    stroke: { color: "#000000", px1080: 8 }
    shadow: true
    plate: none
    position: { cx: 0.5, cy: null, align: center }
    linesMax: 2
    charsPerCard: { min: 2, max: 12 }
    motionIn: pop
    motionOut: cut
    show: onset
    leadSec: null
    hide: next-card
    minHoldSec: null
    lastCard: hold-to-end
camera:
  moves:
    - { beat: b1, move: static }
  zooms: []
  transitions: []
audio:
  bgm:
    present: true
    character: 軽いローファイ、遅め
    entersAt: { beat: b1, offsetSec: 0 }
    duckUnderVoice: null
    levelDbUnderVoice: null
  sfx:
    - { cue: card-in, type: 短いポップ }
  voice: none
  referenceAudioUsed: false
routes:
  - id: code-motion
    default: true
    container: html-canvas
    needs: [none]
    paidApi: false
    talkingHead: false
    costUsdPerVideo: { min: 0, max: 0, basis: ローカルで描画して ffmpeg で書き出す }
    status: written
fonts:
  - { family: Noto Sans JP, license: OFL-1.1, source: "https://fonts.google.com/noto/specimen/Noto+Sans+JP" }
rights:
  makerSupplies: [自分で書いた台本, 許諾が記録された BGM ファイル]
  neverUse: [参照動画の映像、音、テロップの文言]
evidence:
  measured: [format.durationSec]
  inferred: [hook.type, beats]
  unmeasured: [captions.c1.capHeightRatio, captions.c1.position.cy]
---

# 字幕だけの三つ数え

sasaru-pick のテスト用。本文は省く。
