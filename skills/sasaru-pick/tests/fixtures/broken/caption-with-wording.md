---
schema: sasaru-playbook/1
id: caption-with-wording
name: 文言を書いてしまった型
status: draft
summary: captions に文言の欄を足したので、スキーマで止まる。
tags: [broken]
fitsContent:
  - 勉強法のコツ
source: { kind: hand-written, platform: none, rightsTier: none, measuredFiles: 0 }
format:
  aspect: "9:16"
  fps: 30
  durationSec: { min: 7, max: 15 }
  hardCuts: 0
  onCamera: none
  speech: none
hook: { type: text-promise, endsAtSec: 1.0, firstFrameHasText: true }
beats:
  - { id: b1, role: hook, tIn: 0.0, tOut: 1.0, purpose: 約束する, swap: 自分の一句 }
  - { id: b2, role: payoff, tIn: 1.0, tOut: 6.0, purpose: 回収する, swap: 自分の答え }
captions:
  role: none
  text: 元のテロップ
camera: { move: static, zooms: [], transitions: [] }
audio:
  bgm: { present: false }
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
    costUsdPerVideo: { min: 0, max: 0, basis: ローカル }
    status: design-only
fonts: []
rights: { makerSupplies: [], neverUse: [参照動画の映像] }
evidence: { measured: [], inferred: [], unmeasured: [] }
---

# 文言を書いてしまった型
