---
schema: sasaru-playbook/3
id: talking-confession
name: 一人語りを手元映像に置き換えた型
status: measured
summary: 参照は人がカメラに失敗談を語る。作るカットは手元映像に字幕と読み上げを載せる。
tags: [talk, study]
audience:
  - 資格勉強中の社会人
fitsContent:
  - 一人語りの体験談
  - 勉強法のコツ
contentRoute: reference-world
subject:
  of: reference-world
  words: 失敗談の中身を、手元の映像と字幕でたどる
spreadPsychology:
  plays:
    mechanism: 矛盾への注意。否定された常識の穴を、回収まで閉じたくなる
    trigger: フックが常識を否定し、体験による回収は後の拍まで出さない
    basis: inferred
  comments:
    mechanism: 空いた主語に自分の一件を入れる同一視
    trigger: 体験の回収が一人の話のままで、似た体験を書く場所が残る
    basis: inferred
  shares:
    mechanism: この否定に同意する自分を、相手に見せる身份の提示
    trigger: 否定の一句が短く、送った相手が同じ否定を自分のこととして読める
    basis: inferred
source:
  kind: ingested
  platform: instagram-reels
  rightsTier: A
  ingestedAt: 2026-10-25
  measuredFiles: 1
  reference: { onCamera: face, speech: on-camera, hardCuts: 4 }
format:
  aspect: "9:16"
  fps: 30
  durationSec: { min: 10, max: 30, reference: 20 }
  onCamera: hands
  speech: voiceover
hook:
  type: contradiction
  firstFrameHasText: true
beats:
  - { id: b1, role: hook, tIn: 0.0, tOut: 1.5, purpose: 常識を否定して止める, swap: 自分の否定の一句 }
  - { id: b2, role: payoff, tIn: 1.5, tOut: 20.0, purpose: 体験で回収する, swap: 自分の体験 }
captions: []
camera:
  moves:
    - { beat: b1, move: handheld }
  zooms: []
  transitions: []
audio:
  bgm: { present: false }
  sfx: []
  voice: own-voiceover
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
    costUsdPerVideo: { min: 2, max: 6, basis: 参照の動きで人物を生成し口を合わせる, asOf: 2026-10-25 }
    status: design-only
fonts: []
rights:
  makerSupplies: [自分の手元映像, 自分の声]
  neverUse: [参照動画の映像、音、テロップの文言]
evidence:
  measured: [source.reference.hardCuts]
  inferred: [hook.type]
  unmeasured: []
---

# 一人語りを手元映像に置き換えた型

sasaru-pick のテスト用。本文は省く。
