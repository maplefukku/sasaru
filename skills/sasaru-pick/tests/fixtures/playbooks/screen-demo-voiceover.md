---
schema: sasaru-playbook/3
id: screen-demo-voiceover
name: 画面録画と読み上げ
status: draft
summary: 画面録画に読み上げと字幕を重ね、操作を三手で見せる。
tags: [app, screen]
fitsContent:
  - アプリの使い方
  - 作業の手順
contentRoute: reference-world
subject:
  of: reference-world
  words: 画面の中の操作が三手で進む
source:
  kind: hand-written
  platform: none
  rightsTier: none
  measuredFiles: 0
format:
  aspect: "9:16"
  fps: 30
  durationSec: { min: 20, max: 40, reference: 25 }
  onCamera: none
  speech: voiceover
hook:
  type: question
  firstFrameHasText: true
beats:
  - { id: b1, role: hook, tIn: 0.0, tOut: 2.0, purpose: 困りごとを問いで出す, swap: 自分の利用者の困りごと }
  - { id: b2, role: item, tIn: 2.0, tOut: 25.0, purpose: 操作を三手で見せる, swap: 自分のアプリの画面録画 }
captions:
  - id: c1
    role: subtitle
    beats: []
    unit: phrase
    writingMode: horizontal
    font: { class: bold-gothic, weight: 700 }
    capHeightRatio: null
    emphasis: null
    color: "#FFFFFF"
    stroke: { color: "#000000", px1080: 6 }
    shadow: false
    plate: box
    position: { cx: 0.5, cy: null, align: center }
    linesMax: 2
    charsPerCard: { min: 4, max: 16 }
    motionIn: cut
    motionOut: cut
    show: onset
    leadSec: null
    hide: phrase-end
    minHoldSec: null
    lastCard: hold-to-end
camera:
  moves:
    - { beat: b1, move: static }
    - { beat: b2, move: push-in }
  zooms: []
  transitions: []
audio:
  bgm: { present: true, character: 控えめなピアノ, entersAt: { beat: b1, offsetSec: 0 }, duckUnderVoice: true, levelDbUnderVoice: null }
  sfx: []
  voice: tts-voiceover
  referenceAudioUsed: false
routes:
  - id: screen-recording
    default: true
    container: ffmpeg-ass
    needs: [screen-capture, tts]
    paidApi: false
    talkingHead: false
    costUsdPerVideo: { min: 0, max: 0, basis: 画面録画とローカルの読み上げ }
    status: design-only
  - id: image-gen-stills
    default: false
    container: remotion
    needs: [image-gen, tts]
    paidApi: true
    talkingHead: false
    costUsdPerVideo: { min: 0.1, max: 0.5, basis: 静止画を 5〜10 枚生成する, asOf: 2026-10-25 }
    status: design-only
fonts:
  - { family: Noto Sans JP, license: OFL-1.1, source: "https://fonts.google.com/noto/specimen/Noto+Sans+JP" }
rights:
  makerSupplies: [自分のアプリの画面録画]
  neverUse: [参照動画の映像、音、テロップの文言]
evidence:
  measured: []
  inferred: [hook.type, beats]
  unmeasured: [captions.c1.capHeightRatio]
---

# 画面録画と読み上げ

sasaru-pick のテスト用。本文は省く。
