---
schema: sasaru-playbook/1
id: replace-with-format-id
name: 型の短い名前
status: draft
summary: この型を一文で。何が画面に出て、どこで見る人が止まるか。
tags: [replace-me]
fitsContent:
  - この型に載せられる自分のコンテンツの種類
source:
  kind: hand-written
  platform: none
  rightsTier: none
  measuredFiles: 0
format:
  aspect: "9:16"
  fps: 30
  durationSec: { min: 6, max: 15 }
  hardCuts: 0
  onCamera: none
  speech: none
hook:
  type: text-promise
  endsAtSec: 1.0
  firstFrameHasText: true
beats:
  - { id: b1, role: hook, tIn: 0.0, tOut: 1.0, purpose: 見る人に何を約束するか, swap: 自分の約束の一句 }
  - { id: b2, role: payoff, tIn: 1.0, tOut: 6.0, purpose: 約束をどう回収するか, swap: 自分の答え }
captions:
  role: headline
  unit: phrase
  font: { class: extra-bold-gothic, weight: 900 }
  capHeightRatio: null
  emphasisScale: null
  color: "#FFFFFF"
  stroke: { color: "#000000", px1080: 8 }
  shadow: true
  plate: none
  position: { cx: 0.5, cy: null, align: center }
  linesMax: 1
  charsPerCard: { min: 2, max: 10 }
  motionIn: cut
  motionOut: cut
  show: onset
  hide: next-card
  lastCard: hold-to-end
camera:
  move: static
  zooms: []
  transitions: []
audio:
  bgm: { present: true, character: 曲の気分とテンポを言葉で。曲名は書かない, entersAtSec: 0, duckUnderVoice: null }
  sfx: []
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
    status: design-only
fonts:
  - { family: Noto Sans JP, license: OFL-1.1, source: "https://fonts.google.com/noto/specimen/Noto+Sans+JP" }
rights:
  makerSupplies:
    - 自分で書いた台本
    - 再配布か動画内利用の許諾が記録された BGM ファイル
  neverUse:
    - 参照動画の映像、音、テロップの文言
evidence:
  measured: []
  inferred: [hook.type, beats]
  unmeasured: [captions.capHeightRatio, captions.position.cy]
---

# 型の短い名前

本文の見出しは、この順で全部置く。書けない節は、消さずに「未計測」か「該当なし」と一行で書く。数はフロントマターが正本で、本文は理由と手順を書く。参照動画の文言、曲名、作者名、フレームの画像は書かない。

## 構成と尺

尺の帯、ビートの並び、カットの有無を、なぜその長さかと一緒に書く。

## フック

最初の何秒で、何を見せて、何を約束するか。

## ビート

ビートごとに、見る人にとっての役割と、次へ進ませる仕掛け。

## テロップ

書体の種類と太さ、大きさ（白い芯の高さ / 画面高）、位置、縁と影、一枚の字数と段数、出し方と消し方、出すタイミングと消すタイミング、最後の一枚の扱い。

## カメラとトランジションとズーム

画の動き、寄りの時刻と倍率、切り替えの種類と位置。

## BGM と効果音

曲の気分とテンポ、入る秒、声との関係、効果音を鳴らすきっかけ。

## なぜ伸びるか

推論として書く。見る人が止まる理由、最後まで見る理由、もう一度見る理由。伸びない側に落ちない理由も分けて書く。

## 差し替える場所

自分のコンテンツを入れる場所を、ビートの id ごとに。変えてはいけない部分も書く。

## 制作ルート

フロントマターの `routes` と同じ順に、ルートごとに小見出しを置く。

### code-motion

1. 手順を番号で書く。呼ぶコマンドはそのまま書く。

## 編集の器とフォント

どの器で組むか、その理由、フォントの入手先とライセンス。

## 素材の権利

作る人が用意するもの、使ってはいけないもの。

## 費用の目安

ルートごとの一本あたりの費用と、その根拠。有料の生成を呼ぶルートは、見積もりと上限の取り方。

## 測ったことと推論

どの数を測り、どれが推論で、どれが未計測か。測った手順の名前。
