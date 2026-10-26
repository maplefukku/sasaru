---
schema: sasaru-playbook/4
id: replace-with-format-id
name: 型の短い名前
status: draft
summary: この型を一文で。何が画面に出て、どこで見る人が止まるか。
tags: [replace-me]
audience:
  - 誰に向けた型か（任意の欄）
fitsContent:
  - この型に載せられる自分のコンテンツの種類
contentRoute: reference-world
subject:
  of: reference-world
  words: 参照の世界で起きる出来事を一文で書く
spreadPsychology:
  plays:
    mechanism: 約束の未完了。先に出した約束が、回収の拍まで注意を残す
    trigger: フックが約束の一句を出し、回収は後の拍まで出さない
    basis: inferred
  comments:
    mechanism: 自分の題材で約束を言い換えたくなる参加
    trigger: 約束が一般の形で、見る人の一件を一文で足す穴が残る
    basis: inferred
  shares:
    mechanism: 相手がまだ知らない回収を渡す実用
    trigger: 答えが最後の拍にあり、途中の画面では約束だけが残る
    basis: inferred
verbalization:
  picture:
    - sec: 0
      seen:
        onScreen: 画面の中央に、到達の名前を持つ完成が既にある
        entered: なし
        left: なし
        camera: 止まっている
      inferred:
        pointAt: 見る人は、その完成の輪郭を指せる
    - sec: 1
      seen:
        onScreen: 同じ完成が残り、普通の一手が始められない状態が見える
        entered: なし
        left: なし
        camera: 止まっている
      inferred:
        pointAt: 見る人は、止められている手順の側を指せる
  edit:
    missing: []
    events:
      - { tIn: 0, tOut: 1, kind: hold, basis: seen, holdSec: 1 }
      - {
          tIn: 0.2,
          tOut: 0.6,
          kind: zoom,
          basis: seen,
          direction: 寄る,
          zoomSec: 0.4,
        }
      - { tIn: 1, kind: cut, basis: seen, job: 新しい段を開く }
  words:
    missing: []
    intervals:
      - {
          order: 1,
          tIn: 0,
          tOut: 1,
          role: 終状態の名前,
          capHeightRatio: 未計測,
          cx: 未計測,
          cy: 未計測,
          nameKind: カテゴリ,
          basis: inferred,
        }
  sound:
    sourceFile: local-format.mp4
    durationSec: 6
    durationBasis: seen
    probe: ffprobe
    spans:
      - {
          tIn: 0,
          tOut: 6,
          entered: start,
          dropped: false,
          class: bed,
          basis: seen,
        }
  pull:
    basis: inferred
    beats:
      - tIn: 0
        tOut: 1
        wantsNext: 次の画で、止められていた一手がどうほどけるかを見たい
        openPromise: 完成の名前は出ていて、まだ画面の上で果たされていない
        leaveSec: 1
      - tIn: 1
        tOut: 6
        wantsNext: ほどけた完成が、最後のフレームまで残るのを見たい
        openPromise: この拍で約束は閉じた。閉じた理由は、指させるものが画面に留まったことである
        leaveSec: 6
  accountPattern:
    繰り返すところ:
      冒頭: 複数本の始まりは、完成の名前を先に置いて、見る人にその到達を約束する。普通の説明から入らない。
      不可能な制約: その完成は、見る人が知っている最初の一手では届かない条件のまま、複数本で同じように止まる。
      エスカレーション: 同じ条件のまま、次の一手が前の一手より届きにくい方へ進む。進み方は複数本で揃っている。
      回収: 制約がほどける着地で、先に置いた完成の名前が画面の上で果たされる。着地の役割は複数本で同じである。
    繰り返さないところ: 本ごとに変わるのは、完成が指す物の種類と、止まりが画面に出る秒である。機械の順は変えない。
    物語の機械: 完成の名前が先に出て、普通の一手では届かない止まりが続き、その止まりがほどけるまで見る人は次の秒を待つ。人がその場でこの順を言い直せる。
spread:
  open:
    claim: 完成の名前が最初の三秒に既にあり、そこへ届く道はまだ画面に無い
    endStateWordOnScreen: true
    howTo: false
    basis: inferred
  lock:
    blockedMethod: 見る人が普通は最初に取る一手が、画面の状態では始められない
    blockSecond: 0.4
    straightWhatIfFails: 最初の普通の一手を先に成功させると、止まりが起きず、不可能なロックが立たない
    basis: inferred
  escalation:
    - build: 届ける先の輪郭だけを、最初の画に置く
      change: 何を見届けるかが、最初の段ではっきりする
      basis: inferred
    - build: 同じ輪郭に、届かない障害を一つ足す
      change: 到達までの距離が、その障害の分だけ遠くなる
      flatIfRepeated: payoff
      basis: inferred
  payoff:
    paidOffAtSec: 4
    pointAt: 見る人が画面の一点を指して示せる、先に名前のあった完成
    beats:
      anticipation:
        {
          tIn: 1,
          tOut: 3,
          onScreen: 主張はまだ果たされず、止まりが画面に残っていることが、次の変化で見える,
        }
      hit:
        {
          tIn: 3,
          tOut: 5,
          onScreen: 先に置いた主張が、絵の変化で果たされ、完成が画面の上に現れる,
        }
      settle:
        {
          tIn: 5,
          tOut: 6,
          onScreen: 当たりのあと別の変化で、指させるものが画面に残って止まる,
        }
    basis: inferred
  comment:
    beat: 手順が途中で止まり、次の一手が画面の中で済んでいない
    closed: false
    reply: 見る人が、自分の次の一手を一文で返す
    count: コメント数は取得していない
    basis: inferred
  share:
    pointAt: 変化のあとで像になる、名前の付いた到達を、送る人が指させる
    recipient: その到達の像をまだ持っておらず、同じ止まりの前にいる人
    unnamedMiddle: 到達がまだ像になっていない途中には名前が無く、相手に渡せる物が無い
    basis: inferred
  leave:
    firstSecond:
      stalls: false
      stays: 最初の一秒は、この先にある完成の名前を置いていて、約束は止まっていない
    repeatedStep:
      repeats: false
      stays: 次の一歩は前の一歩と同じ役割ではなく、新しい差が足されている
    unnamedWord:
      misses: false
      stays: 画面の語は、見えている物の役割を指していて、ずれは無い
    ending:
      mismatches: false
      stays: 最後の絵は、開きで置いた同じ約束を閉じていて、別の物ではない
    basis: inferred
scenario:
  story: 完成の名前が先に出て、その完成は普通の一手では届かない。見る人は、その名前が画面の上で果たされるまで次の秒を待つ。最初の画は、すでにその完成である。次の拍で止まりがほどけ、指させるものが画面に残る。見る人はその絵を最後まで残して見たい。
source:
  kind: hand-written
  platform: none
  rightsTier: none
  measuredFiles: 0
format:
  aspect: "9:16"
  fps: 30
  durationSec: { min: 6, max: 15, reference: 6 }
  onCamera: none
  speech: voiceover
  safeArea: { top: 0.11, bottom: 0.25, left: 0.03, right: 0.18 }
hook:
  type: text-promise
  firstFrameHasText: true
beats:
  - {
      id: b1,
      role: hook,
      tIn: 0.0,
      tOut: 1.0,
      purpose: 見る人に何を約束するか,
      swap: 自分の約束の一句,
    }
  - {
      id: b2,
      role: payoff,
      tIn: 1.0,
      tOut: 6.0,
      purpose: 約束をどう回収するか,
      swap: 自分の答え,
    }
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
    linesMax: 1
    charsPerCard: { min: 2, max: 10 }
    motionIn: cut
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
    character: 曲の気分とテンポを言葉で。曲名は書かない
    entersAt: { beat: b1, offsetSec: 0 }
    duckUnderVoice: null
    levelDbUnderVoice: null
  sfx:
    - { cue: card-in, type: 効果音の種類を言葉で。素材名は書かない }
  voice: own-voiceover
  referenceAudioUsed: false
routes:
  - id: code-motion
    default: true
    container: html-canvas
    needs: [none]
    paidApi: false
    talkingHead: false
    costUsdPerVideo:
      { min: 0, max: 0, basis: ローカルで描画して ffmpeg で書き出す }
    status: design-only
fonts:
  - {
      family: Noto Sans JP,
      license: OFL-1.1,
      source: "https://fonts.google.com/noto/specimen/Noto+Sans+JP",
    }
rights:
  makerSupplies:
    - 自分で書いた台本
    - 再配布か動画内利用の許諾が記録された BGM ファイル
  neverUse:
    - 参照動画の映像、音、テロップの文言
evidence:
  measured: []
  inferred:
    - hook.type
    - beats
    - format.safeArea
    - captions.c1.stroke
    - verbalization.edit
    - verbalization.words
    - verbalization.sound
    - verbalization.pull
    - verbalization.accountPattern
    - spread.open
    - spread.lock
    - spread.escalation
    - spread.payoff
    - spread.comment
    - spread.share
    - spread.leave
    - scenario.story
  unmeasured:
    - captions.c1.capHeightRatio
    - captions.c1.position.cy
    - captions.c1.minHoldSec
    - audio.bgm.duckUnderVoice
    - audio.bgm.levelDbUnderVoice
---

# 型の短い名前

本文の見出しは、この順で全部置く。null の意味は欄ごとに一つで、スキーマの各欄の説明にある。未計測の null は `evidence.unmeasured` に載せる。型に無い任意の欄（声の無い型の `audio.bgm.levelDbUnderVoice` など）は null にせず書かない。書けない節は、消さずに「未計測」か「該当なし」と一行で書く。数はフロントマターが正本で、本文は理由と手順を書く。参照動画の文言、曲名、作者名、フレームの画像は書かない。

## 構成と尺

尺の帯、ビートの並び、カットの有無を、なぜその長さかと一緒に書く。

## フック

最初の何秒で、何を見せて、何を約束するか。

## ビート

ビートごとに、見る人にとっての役割と、次へ進ませる仕掛け。

## テロップ

層（`captions[]` の id）ごとに書く。書体の種類と太さ、大きさ（白い芯の高さ / 画面高）、位置、縁と影、一枚の字数と段数、出し方と消し方、出すタイミングと消すタイミング、最短の表示秒、最後の一枚の扱い。一つの層の中で大小を混ぜるなら、その理由。

## カメラとトランジションとズーム

画の動き、寄りの時刻と倍率、切り替えの種類と位置。

## BGM と効果音

曲の気分とテンポ、入る秒、声との関係、効果音を鳴らすきっかけ。

## なぜ伸びるか

推論として書く。見る人が止まる理由、最後まで見る理由、もう一度見る理由。伸びない側に落ちない理由も分けて書く。

`spreadPsychology` に、再生（`plays`）、コメント（`comments`）、共有（`shares`）を三つに分けて書く。それぞれ心理の機構（`mechanism`）と、型の何がそれを起こすか（`trigger`）を言葉で書く。出どころは `basis: inferred`。再生数は書かない。`payoff` のビートがある型は最後まで見ることが仕事なので、この欄を省けない。`null` は書かない。

`payoff` のビートがある型は、最後まで見る物語でもある。そのときは `verbalization`、`spread`、`scenario` を省けない。省いてよいのは、最後まで見る物語ではない型だけである。省略は分析を飛ばしたことではない。`null` は書かない。`scenario.story` は散文である。ショット番号の一覧や、単語を並べただけの行は、この欄にならない。空なら make はカットの計画を書かない。

## 差し替える場所

自分のコンテンツを入れる場所を、ビートの id ごとに。変えてはいけない部分も書く。

商品の置き場は `productPlacement` に言葉で書く。どのビートか、役割（`absent` 出さない、`prop` 世界の中の小道具、`payoff` 回収、`spoken` 名前を言う、`end-card` エンドカード）、どれだけ直接か（`directness`）。決めるのはアカウントの型で、一本の台本では動かさない。この欄を省くのは、その型に商品の置き場が一度も無いときだけ。`null` は書かない。省いた欄はエンドカードの宣伝ではない。`contentRoute` は参照の世界を残すか、Moguno の IP に置き換えるか、世界の中の要素としてだけ商品を出すか。動画の主題 `subject` は参照の世界か Moguno で、商品の説明を主題にしない。

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
