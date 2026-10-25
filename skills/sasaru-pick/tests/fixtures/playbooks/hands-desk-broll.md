---
schema: sasaru-playbook/1
id: hands-desk-broll
name: 手元の机と字幕
status: draft
summary: 机の上の手元映像に見出しテロップを重ね、一日の記録を短く見せる。
tags: [study, routine]
fitsContent:
  - 勉強記録
  - 朝のルーティン
source:
  kind: hand-written
  platform: none
  rightsTier: none
  measuredFiles: 0
format:
  aspect: "9:16"
  fps: 30
  durationSec: { min: 10, max: 20 }
  hardCuts: 5
  onCamera: hands
  speech: none
hook:
  type: pov
  endsAtSec: 1.0
  firstFrameHasText: true
beats:
  - { id: b1, role: hook, tIn: 0.0, tOut: 1.0, purpose: 見る人の立場を一句で決める, swap: 自分の立場の一句 }
  - { id: b2, role: item, tIn: 1.0, tOut: 15.0, purpose: 手元の作業を短く並べる, swap: 自分の手元映像 }
captions:
  role: none
camera:
  move: handheld
  zooms: []
  transitions: [{ atSec: 1.0, type: hard-cut }]
audio:
  bgm: { present: true, character: 明るいアコースティック, entersAtSec: 0, duckUnderVoice: null }
  sfx: []
  voice: none
  referenceAudioUsed: false
routes:
  - id: caption-over-footage
    default: true
    container: ffmpeg-ass
    needs: [own-footage]
    paidApi: false
    talkingHead: false
    costUsdPerVideo: { min: 0, max: 0, basis: 手元の映像に字幕を重ねる }
    status: design-only
  - id: t2v
    default: false
    container: ffmpeg-ass
    needs: [t2v]
    paidApi: true
    talkingHead: false
    costUsdPerVideo: { min: 0.5, max: 2, basis: 5 秒のクリップを 3 本生成する }
    status: design-only
fonts: []
rights:
  makerSupplies: [自分の手元映像]
  neverUse: [参照動画の映像、音、テロップの文言]
evidence:
  measured: []
  inferred: [hook.type]
  unmeasured: []
---

# 手元の机と字幕

sasaru-pick のテスト用。本文は省く。
