---
schema: sasaru-playbook/1
id: talking-confession
name: カメラに向かう一人語り
status: measured
summary: 人がカメラに向かって失敗談を語り、最後に一言で返す。
tags: [talk, study]
fitsContent:
  - 一人語りの体験談
  - 勉強法のコツ
source:
  kind: hand-written
  platform: none
  rightsTier: none
  measuredFiles: 0
format:
  aspect: "9:16"
  fps: 30
  durationSec: { min: 10, max: 30 }
  hardCuts: 4
  onCamera: face
  speech: on-camera
hook:
  type: contradiction
  endsAtSec: 1.5
  firstFrameHasText: true
beats:
  - { id: b1, role: hook, tIn: 0.0, tOut: 1.5, purpose: 常識を否定して止める, swap: 自分の否定の一句 }
  - { id: b2, role: payoff, tIn: 1.5, tOut: 20.0, purpose: 体験で回収する, swap: 自分の体験 }
captions:
  role: none
camera:
  move: static
  zooms: []
  transitions: []
audio:
  bgm: { present: false }
  sfx: []
  voice: on-camera
  referenceAudioUsed: false
routes:
  - id: caption-over-footage
    default: true
    container: capcut
    needs: [own-footage]
    paidApi: false
    talkingHead: false
    costUsdPerVideo: { min: 0, max: 0, basis: 手元の映像に字幕を重ねる }
    status: design-only
  - id: r2v-talking
    default: false
    container: other
    needs: [r2v, tts]
    paidApi: true
    talkingHead: true
    costUsdPerVideo: { min: 2, max: 6, basis: 参照から人物を生成し口を合わせる }
    status: design-only
fonts: []
rights:
  makerSupplies: [自分の映像]
  neverUse: [参照動画の映像、音、テロップの文言]
evidence:
  measured: []
  inferred: [hook.type]
  unmeasured: []
---

# カメラに向かう一人語り

sasaru-pick のテスト用。本文は省く。
