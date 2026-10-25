---
schema: sasaru-playbook/1
id: cat-meme-aruaru-own-character
name: 猫ミーム合成のあるある（自前キャラ化）
status: draft
summary: 上の黒帯に固定の題、場面ごとに時刻や分類のラベルと台詞、背景の上に切り抜きのキャラを置いて一場面ずつ差し替える。反応の大きいキャラと、時間が進むほど刻みが細かくなる流れで最後まで見せる。猫は自前キャラに置き換える。
tags: [aruaru, meme-composite, own-character, cutout-character, no-talking, caption-led, timeline-list]
audience:
  - テスト前や講義中のあるあるに覚えのある大学生
  - 音を出さずにショートを流し見する人
fitsContent:
  - 学生生活のあるある（テスト前、講義中、レポートの締切、履修登録）
  - 時間が進むほど感じ方が変わる話（テストまでの日数、一日の時刻、学期の週）
  - タイプごとに反応が分かれる話（学部別、座る席別、ノートの取り方別）
  - 計画と現実のずれ
source:
  kind: hand-written
  platform: youtube-shorts
  rightsTier: none
  measuredFiles: 0
format:
  aspect: "9:16"
  fps: 30
  durationSec: { min: 45, max: 70, reference: 62 }
  onCamera: none
  speech: none
  safeArea: { top: 0.11, bottom: 0.25, left: 0.03, right: 0.18 }
hook:
  type: list-promise
  firstFrameHasText: true
beats:
  - id: b1
    role: hook
    tIn: 0.0
    tOut: 4.0
    purpose: 黒帯の題で何の分類か何の時間軸かを約束し、ラベルとキャラを一秒ずつ切り替えて、この速さで最後まで進むと見せる
    swap: 自分の題と、序盤の軽い場面を三〜四つ（一場面一秒）
  - id: b2
    role: item
    tIn: 4.0
    tOut: 16.0
    purpose: 一場面を数秒に伸ばし、キャラの反応と台詞で一つ目のあるあるを見せる。ここから場面ごとにキャラと背景が替わる
    swap: 最初の山場に向かう場面を三〜四つ。ラベル、台詞、キャラの表情
  - id: b3
    role: item
    tIn: 16.0
    tOut: 33.0
    purpose: 一番浮かれている場面を重ね、背景も派手にして高いところまで上げる。後の落差を大きくする
    swap: 一番気が緩んでいる場面。背景を集中線や夜空など気分の背景に替える
  - id: b4
    role: turn
    tIn: 33.0
    tOut: 45.0
    purpose: 気分が反転する。同じキャラの表情が曇り、背景が暗くなり始める
    swap: 現実を思い出す場面と、その気付きの台詞
  - id: b5
    role: item
    tIn: 45.0
    tOut: 57.0
    purpose: ラベルの刻みを細かくして時間が遅く感じる様子を見せ、反応を一段ずつ大きくする
    swap: 終わりに向かう場面を細かい刻みで三〜四つ
  - id: b6
    role: payoff
    tIn: 57.0
    tOut: 62.0
    purpose: 一番大きな反応で落とす。最後のラベルと台詞を絵の終わりまで残す。終わりの場面が冒頭の場面につながると見返しやすい
    swap: 落ちの場面。自分の商品はここか b4 の転換に置く
captions:
  - id: c1
    role: headline
    beats: []
    unit: card
    writingMode: horizontal
    font: { class: extra-bold-gothic, weight: 900 }
    capHeightRatio: 0.061
    emphasis: { scale: null, color: "#E60006" }
    color: "#FAE20E"
    stroke: null
    shadow: false
    plate: box
    position: { cx: 0.5, cy: 0.17, align: center }
    linesMax: 2
    charsPerCard: { min: 6, max: 16 }
    motionIn: cut
    motionOut: cut
    show: beat-start
    leadSec: null
    hide: beat-end
    minHoldSec: null
    lastCard: hold-to-end
  - id: c2
    role: counter
    beats: []
    unit: card
    writingMode: horizontal
    font: { class: extra-bold-gothic, weight: 900 }
    capHeightRatio: 0.075
    emphasis: null
    color: "#E80005"
    stroke: { color: "#FFFFFF", px1080: 15 }
    shadow: false
    plate: none
    position: { cx: 0.5, cy: 0.31, align: center }
    linesMax: 2
    charsPerCard: { min: 2, max: 8 }
    motionIn: cut
    motionOut: cut
    show: onset
    leadSec: null
    hide: next-card
    minHoldSec: 1.0
    lastCard: hold-to-end
  - id: c3
    role: subtitle
    beats: []
    unit: phrase
    writingMode: horizontal
    font: { class: bold-gothic, weight: 700 }
    capHeightRatio: 0.059
    emphasis: null
    color: "#FFFFFF"
    stroke: { color: "#000000", px1080: 10 }
    shadow: false
    plate: none
    position: { cx: 0.5, cy: 0.40, align: center }
    linesMax: 2
    charsPerCard: { min: 2, max: 14 }
    motionIn: cut
    motionOut: cut
    show: onset
    leadSec: null
    hide: next-card
    minHoldSec: 1.5
    lastCard: hold-to-end
  - id: c4
    role: label
    beats: []
    unit: word
    writingMode: horizontal
    font: { class: extra-bold-gothic, weight: 900 }
    capHeightRatio: 0.050
    emphasis: { scale: null, color: "#F9E212" }
    color: "#FFFFFF"
    stroke: { color: "#000000", px1080: 10 }
    shadow: false
    plate: none
    position: { cx: null, cy: 0.72, align: center }
    linesMax: 1
    charsPerCard: { min: 2, max: 8 }
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
    - { beat: b2, move: static }
    - { beat: b3, move: static }
    - { beat: b4, move: static }
    - { beat: b5, move: static }
    - { beat: b6, move: static }
  zooms: []
  transitions:
    - { at: { beat: b2, offsetSec: 0 }, type: hard-cut }
    - { at: { beat: b3, offsetSec: 0 }, type: hard-cut }
    - { at: { beat: b4, offsetSec: 0 }, type: hard-cut }
    - { at: { beat: b5, offsetSec: 0 }, type: hard-cut }
    - { at: { beat: b6, offsetSec: 0 }, type: hard-cut }
audio:
  bgm:
    present: true
    character: 明るく軽い、跳ねるリズムの短いループ。中くらいのテンポで、最後まで同じ曲を流す
    entersAt: { beat: b1, offsetSec: 0 }
    duckUnderVoice: null
    levelDbUnderVoice: null
  sfx:
    - { cue: card-in, type: キャラが替わるときの短いポップ音 }
    - { cue: cut, type: 背景が替わるときの軽い風切り音 }
    - { cue: payoff, at: { beat: b6, offsetSec: 0 }, type: 落ちを締める短いベルかスティング }
  voice: none
  referenceAudioUsed: false
routes:
  - id: code-motion
    default: true
    container: hyperframes
    needs: [none]
    paidApi: false
    talkingHead: false
    costUsdPerVideo: { min: 0, max: 0, basis: キャラと背景を SVG でコードに描き、HyperFrames でローカルに書き出す。エージェントのトークン代は含めない }
    status: design-only
  - id: image-gen-stills
    default: false
    container: hyperframes
    needs: [image-gen]
    paidApi: true
    talkingHead: false
    costUsdPerVideo:
      min: 0.17
      max: 0.87
      basis: 9:16 の 1K 静止画を一本で 5〜18 枚。Nano Banana 2.1 は 1 枚 0.0336 ドル、FLUX 3 Image は 0.048 ドル。下限は二本目以降で背景と新しい表情だけ 5 枚、上限は一本目でキャラの表情 12 枚と背景 6 枚。背景の切り抜きはローカル
      asOf: 2026-10-25
    status: design-only
  - id: i2v
    default: false
    container: hyperframes
    needs: [image-gen, i2v]
    paidApi: true
    talkingHead: false
    costUsdPerVideo:
      min: 0.77
      max: 3.39
      basis: image-gen-stills の静止画に加え、反応の動きを 3 秒ずつ 6〜10 本（計 18〜30 秒、720p、音なし）。下限は Grok Imagine 1.5 lite の 0.03 ドル/秒と入力画像 0.01 ドル/枚、上限は Kling 3.0 の音なし 0.084 ドル/秒
      asOf: 2026-10-25
    status: design-only
fonts:
  - { family: Noto Sans JP, license: OFL-1.1, source: "https://fonts.google.com/specimen/Noto+Sans+JP" }
rights:
  makerSupplies:
    - 自前キャラの絵。自分で描いた SVG や絵、または自分が出力の権利を持つ画像生成の結果と、その生成の記録（モデル、日付、規約）
    - 背景。コードで描いた絵、自分で撮った写真、または自分が権利を持つ生成画像
    - 自分で書いた台本（題、ラベル、台詞）
    - 再配布か動画内利用の許諾が記録された BGM ファイル
    - 許諾が記録された効果音ファイル
  neverUse:
    - 他人の猫動画や猫ミーム素材の切り抜き（グリーンバック素材を含む）
    - 有名な猫ミームの猫や既存キャラ、実在の人物に似せたキャラ、それを狙った生成のプロンプト
    - 猫ミームの定番の音源と、そこから切り出した音
    - 参照動画の映像、音、テロップの文言
    - アプリ内でだけ使える音源（TikTok の CML、CapCut の Commercial Sounds など）を焼き込んで他のプラットフォームに出すこと
evidence:
  measured: []
  inferred:
    - format.aspect
    - format.fps
    - format.durationSec
    - format.safeArea
    - hook.type
    - hook.firstFrameHasText
    - beats
    - captions.c1.capHeightRatio
    - captions.c1.color
    - captions.c1.emphasis
    - captions.c1.plate
    - captions.c1.position
    - captions.c1.charsPerCard
    - captions.c2.capHeightRatio
    - captions.c2.color
    - captions.c2.stroke
    - captions.c2.position
    - captions.c2.minHoldSec
    - captions.c3.capHeightRatio
    - captions.c3.stroke
    - captions.c3.position
    - captions.c3.minHoldSec
    - captions.c4.capHeightRatio
    - captions.c4.emphasis
    - captions.c4.stroke
    - captions.c4.position.cy
    - captions.c1.motionIn
    - captions.c2.motionIn
    - captions.c3.motionIn
    - captions.c4.motionIn
    - camera.moves
    - camera.transitions
    - audio.bgm.present
    - audio.bgm.character
    - audio.sfx
    - routes.costUsdPerVideo
  unmeasured:
    - captions.c1.minHoldSec
    - captions.c4.minHoldSec
    - captions.c4.position.cx
    - captions.c1.shadow
    - captions.c2.shadow
    - captions.c3.shadow
    - captions.c4.shadow
    - audio.bgm.duckUnderVoice
    - audio.bgm.levelDbUnderVoice
---

# 猫ミーム合成のあるある（自前キャラ化）

元の型は、定番の猫ミーム素材（他人の猫動画をグリーンバックで切り抜いたもの）を背景に合成し、テロップで人間の状況を演じさせる。この playbook は、猫を ZuruNote 用の自前キャラに置き換える前提で書く。他人の猫の切り抜き、猫ミームの定番の音、参照の文言と音は使わない。

## 構成と尺

尺は 45〜70 秒。ビートの秒は参照の 62 秒の流れの上で書いた。参照 3 本は 62 秒、67 秒、107 秒で、どれも喋る人はいない。107 秒の一本は日数の区切り（始めの日、半ば、終わり）を三回繰り返す長い版で、この playbook の帯からは外した。

並びは「固定の題」と「場面の列」。題は最初から最後まで上の黒帯に出たまま変わらない。その下で、場面ごとにラベル（曜日と時刻、日数と時刻、分類の名前）、台詞、キャラ、背景が入れ替わる。場面の切り替えはすべてハードカットで、一場面は 1〜3 秒。ビートは場面を束ねた区切りで、場面の刻み方が変わるところで切った。

- b1（0〜4 秒）は一場面 1 秒で四つ進む。速さそのものが「ここは飛ばす」という笑いになる。
- b2 から一場面が数秒に伸び、b3 で一番浮かれたところまで上がる。
- b4 で気分が反転し、b5 では時刻の刻みが細かくなる（終わりが近いほど時間が遅く感じる）。
- b6 は一番大きな反応で、最後の場面を 5 秒ほど残して終わる。

分類別の版（タイプごとに反応が分かれる話）も同じ形で、b2〜b5 が分類ごとの場面になり、普通のものから珍しいものへ順に進め、一番珍しいものを b6 に置く。参照の 67 秒の一本はこの並びで、各分類が 9〜12 秒ほどだった（1 秒間隔のサムネイルでの目測）。

## フック

最初のフレームに、黒帯の題（二段）と最初のラベルとキャラが全部出ている。題は「何の分類か」「何の時間軸か」を言い、全部の場面を見せると約束する（`list-promise`）。問いの形の二段目で、見る人に自分が当てはまるかを考えさせる。b1 の四場面を 1 秒ずつで切り替え、この速さで最後まで進むことを最初の 4 秒で見せる。

## ビート

- **b1 hook**: 題と、序盤の軽い場面を一秒ずつ。ラベルの切り替えだけで時間が飛ぶのが分かる。次へ進ませるのは、まだ山場が来ていないこと。
- **b2 item**: 一場面を伸ばし、キャラの反応と台詞で一つ目のあるあるを見せる。場面ごとにキャラか背景が替わり、毎回新しい絵が出る。
- **b3 item**: 一番気が緩んでいる場面を重ねる。参照では、ここで背景が集中線や夜空のような気分の絵に替わり、キャラの反応も一番大きい。高く上げるほど後の落差が効く。
- **b4 turn**: 同じキャラの表情が曇り、背景が暗くなる。台詞は「思い出した」側の一言にする。
- **b5 item**: ラベルの刻みを細かくする（一時間ごと、三十分ごと）。反応を一段ずつ大きくし、落ちまで待たせる。
- **b6 payoff**: 一番大きな反応。最後のラベルと台詞は絵の終わりまで残す。終わりの場面が冒頭の場面につながると、ループで見返しやすい。

## テロップ

数は公開サムネイル 1 枚ずつの画素の数え方で拾った値で、推論として扱う（「測ったことと推論」）。

- **c1 headline（題）**: 極太ゴシック 900。白い芯ではなく黄色の芯で、高さは画面高の 0.061（参照のもう一本は 0.052 と 0.043）。画面幅いっぱいの黒い帯（画面高の 0.10〜0.25 あたり）を座布団にし、縁は付けない。二段、一枚 6〜16 字。分類や時間軸の語だけ赤にする。最初の秒に出して、最後のフレームまで一枚のまま残す。
- **c2 counter（場面ラベル）**: 極太ゴシック 900、赤に白の太い縁（1080 幅で約 15 px）。芯の高さ 0.075 で、画面の中で一番大きい字。cy 0.31。一枚 2〜8 字、二段まで（日数と時刻を分けるとき）。場面の頭で出して次の場面で替える。b1 では 1 秒で替わるので、最短の表示は 1.0 秒。
- **c3 subtitle（台詞）**: 太いゴシック 700、白に黒の縁（約 10 px）。芯の高さ 0.059、キャラの頭の上（cy 0.40）。一枚 2〜14 字、二段まで。参照のもう一本は 0.041 と小さく、それより読みやすい側を採った。台詞が無い場面は出さない。最短 1.5 秒は、この型で決めた値。
- **c4 label（名札）**: 極太ゴシック 900、白に黒の縁、芯 0.050。キャラの足元（cy 0.72）に、そのキャラが誰かを一語で出す。横の位置はキャラに付いて動くので固定しない。主役の名札だけ黄色にする。

四つの層は役ごとに大きさを分け、一つの層の中では大小を混ぜない。どの層も出し方と消し方はカット。見出し級の大きさの基準（`sasaru-principle-captions-read-as-headlines`）は c1 と c2 が満たしている。

## カメラとトランジションとズーム

画面は動かさない（全ビート `static`）。動くのはキャラだけで、参照では切り抜きの猫クリップそのものが叫ぶ、踊る、倒れる。自前キャラでは、この動きをキャラ自身のアニメーション（上下の弾み、小刻みな震え、拡大して叫ぶ、縦につぶれる、左右に揺れる、倒れる）で作る。ズームは使わない。場面の切り替えはすべてハードカットで、フロントマターにはビートの頭のカットだけを書いた。ビートの中の場面ごとのカットも同じハードカットにする。

## BGM と効果音

参照の音は聞いていない。参照は猫ミームの定番の音源と、その猫クリップの元の音を使っていると推定されるが、どちらも使わない。

この型で作るカットは、明るく軽い短いループの曲を最初の秒から最後まで流す。声は無いので、曲を下げる相手は無い。効果音は、キャラが替わるときの短いポップ音、背景が替わるときの軽い風切り音、落ちの頭のベルかスティング。猫クリップの鳴き声の代わりを効果音に持たせ、場面ごとに一つまでにする。曲と効果音は、許諾を記録した別ファイルだけ（`sasaru-principle-sound-from-a-licensed-file`）。公開リポジトリに置けるのは CC0 と OtoLogic（クレジット付き）で、効果音ラボや小森平のファイルはリポジトリの外に置く。

## なぜ伸びるか

推論である。

- **止まる理由**: 一枚目で題が全部読め、分類か時間軸かがすぐ分かる。大きな顔のキャラが、字より先に感情を伝える。
- **最後まで見る理由**: 場面が 1〜3 秒で替わり、毎回新しい絵が出る。時間軸の版では、時刻の刻みが細かくなるほど落ちが近いと分かり、待たされる。分類の版では、一番珍しいものが最後に来ると分かる。
- **もう一度見る理由**: 一場面の字が少なく速いので、見落とした台詞を見返す。終わりの場面が冒頭につながる。
- **コメントが付く理由**: 「自分はこれ」「この時刻が一番つらい」と、自分の位置を書きやすい。

伸びない側に落ちない理由。

- 喋らないので、音を出さずに見ても成り立つ。
- 置き換えで失うものがある。参照の強さの一部は、見覚えのある猫ミームの猫と音の「知っている」感じから来ている。自前キャラにはそれが無い。補うのは、毎回同じキャラで続けて覚えてもらうこと、表情の差を大きく描くこと、学生の具体的な場面の当たり方。
- YouTube は量産・テンプレ型のチャンネルの収益化を認めない方針を 2026 年 7 月に確かめている。題と場面の中身は毎回変え、同じ台本の言い換えを並べない。生成した動画を使うルートでは、プラットフォームの AI 表示の設定に従う。

## 差し替える場所

- **c1（題）**: 自分の分類か時間軸を二段で。一段目は何の話か、二段目は問いか言い切り。
- **b1**: 序盤の軽い場面を 3〜4 つ。ラベルと、キャラの表情だけでよい。
- **b2〜b3**: 浮かれていく場面。台詞と表情、背景（気分の背景を b3 に）。
- **b4**: 反転の場面。商品を出すならここが自然。
- **b5**: 細かい刻みの場面。反応を一段ずつ大きく。
- **b6**: 落ち。最後のラベルと台詞は終わりまで残す。
- **キャラ**: 全場面で同じ自前キャラを使い、表情と動きだけを替える。脇役（友達、先生）も自前で、名札（c4）で誰かを示す。

変えてはいけない部分。題を最後まで出し続けること。場面の切り替えをハードカットにすること。一場面の字を少なくすること（c2 は 8 字、c3 は 14 字まで）。終盤ほど刻みを細かくすること。最後の一枚を残すこと。他人の猫や猫ミームの素材を入れないこと。

### ZuruNote の例（期末テストまでの 7 日間）

- c1: 「期末テストまでの7日間 / 体感こうなる」。一段目の「7日間」を赤。
- 主役は自前キャラ（ZuruNote 用に描く丸い動物のキャラ）。脇役に友達キャラ。
- b1: 「7日前」「6日前」「5日前」「4日前」を一秒ずつ。主役は寝転んだまま、表情は変えない。
- b2: 「3日前」で友達が範囲表を見せ、主役が固まる。台詞は「範囲こんなに？」。
- b3: 「2日前 昼」で主役は現実から逃げる（夜空の背景で踊る）。台詞は「まだ二日ある」。
- b4: 「前日 20時」で背景が暗くなる。主役がスマホを見て「講義の録音、残ってた」。画面には ZuruNote のノートの画面を小さく出す（アプリの画面は自前の画面録画の静止画）。
- b5: 「前日 22時」「22時30分」「23時」。録音から出来た AI ノートで要点だけを回していき、主役の表情が少しずつ戻る。友達は震えが大きくなる。
- b6: 「当日 朝」。友達は白目で倒れ、主役は眠そうでも立っている。主役の名札だけ黄色で「録音してた人」。ここで 5 秒残して終わる。

## 制作ルート

### code-motion

キャラと背景を SVG で描き、HyperFrames（v0.8.196、Apache 2.0）で組んでローカルに書き出す。有料の生成は呼ばない。

1. 匿名テレメトリを切り、縦の器を作る。`npx hyperframes@0.8.196 telemetry disable`、`npx hyperframes@0.8.196 init cat-aruaru --resolution portrait --non-interactive`
2. 主役のキャラを SVG で一体描く。同じ骨格のまま、目と口と眉だけを替えた表情を 6〜8 枚（`assets/chara/<表情>.svg`）。有名な猫ミームの猫や既存キャラに寄せない。脇役も同じ描き方で一体ずつ。
3. 背景を SVG で描く（講義室、夜の机、図書館、集中線、夜空）。時間が進むほど暗い色にする。自分で撮った写真を使うなら、このルートの `needs` に `own-footage` が加わる。
4. 台本を JSON にする（`script.json`）。場面ごとにビートの id、開始秒と長さ、背景、キャラと表情、動き（弾む、震える、叫ぶ、つぶれる、揺れる、倒れる）、c2 のラベル、c3 の台詞、c4 の名札。尺を 62 秒から変えるときは、伸縮の比をビートの秒に掛ける。
5. `index.html` を書く。ルート要素に `data-composition-id`、`data-width="1080"`、`data-height="1920"`、`data-duration` を付け、場面ごとに `class="clip"` と `data-start`、`data-duration` を付ける。キャラの動きは GSAP のタイムラインで書き、`window.__timelines` に一本登録する。`Math.random()` と `Date.now()` は使わない。c1 の黒帯は全尺の一つのクリップにし、最後のフレームまで残す。
6. フォントは `@font-face` で Noto Sans JP を宣言する。BGM と効果音は `<audio>` で別トラックにし、ファイルはリポジトリの外に置く。
7. 検査する。`npx hyperframes@0.8.196 lint --json`（`font_family_without_font_face` が出たら直す）、`npx hyperframes@0.8.196 check --json`
8. 書き出す。`npx hyperframes@0.8.196 render . -o renders/cut.mp4 --fps 30 --resolution portrait --quality delivery`。マシンをまたいで揃えるなら `--docker` を足す。
9. `cut.json` に playbook id、ルート、素材とライセンス、カード、伸縮の比、逸脱を書き、gate のカット検査にかける。

### image-gen-stills

キャラの表情と背景を画像生成で作り、動きと字はコードで付ける。

1. 見積もる。枚数（一本目はキャラの表情 8〜12 枚と背景 4〜6 枚、二本目以降は新しい表情と背景だけ）に 1 枚の単価を掛け、上限を決め、作る人の承認を取ってから送る（`sasaru-principle-quote-before-you-spend`）。鍵は環境変数から読む。
2. 最初にキャラの設定画を一枚作り、それを参照画像にして表情を一枚ずつ作る。背景は一色の平らな地にする。画像の中に字を入れさせない。字はコードで載せる。
3. 出力ファイルを保存し、モデル、日付、規約、プロンプトを生成の記録に残す。見た目を探して同じ生成を送り直さない。直すのは入力。
4. キャラの背景をローカルで抜く。`npx hyperframes@0.8.196 remove-background assets/chara/<表情>.png -o assets/chara/<表情>-cut.png`
5. 背景の画像は 9:16 で作り、CSS の `object-fit: cover` で 1080×1920 に敷く。
6. 以降は code-motion の 4〜9 と同じ。キャラは SVG の代わりに切り抜いた画像を置き、動きは同じく GSAP で付ける。

### i2v

image-gen-stills の静止画を先頭フレームにして、キャラの反応を数秒の動画にする。参照の猫クリップの「叫ぶ、踊る、倒れる」に一番近い。

1. 見積もる。本数と秒（一本 3 秒、6〜10 本）に秒の単価を掛け、静止画の見積もりと足して上限を決め、承認を取ってから送る。
2. 静止画を先頭フレームにして、小さく繰り返す動きを指示する。人の顔は出さない。音は付けない設定にする。
3. 生成クリップの音を外す。`ffmpeg -i in.mp4 -an -c:v copy out.mp4`
4. キャラの背景をローカルで抜き、透過の WebM にする。`npx hyperframes@0.8.196 remove-background out.mp4 -o assets/clips/<場面>.webm`
5. `index.html` に `<video muted>` のクリップとして置き、`data-start` と `data-duration` を場面に合わせる。字、背景、音は code-motion と同じ。
6. 出すプラットフォームの AI 表示の設定に従う。以降は code-motion の 7〜9 と同じ。

## 編集の器とフォント

器は三つのルートとも HyperFrames（v0.8.196、Apache 2.0、レンダーごとの料金なし）。場面ごとのクリップを `data-start` と `data-duration` で並べるだけで、この型のハードカットの列になる。画像と動画の背景抜き（`remove-background`）もローカルで持っている。同じ composition なら同じ動画になるが、フォントや Chrome の差でマシン間は 1 画素ずれうるので、揃えるなら `--docker` で書き出す。Remotion でも組めるが、従業員 4 人以上の営利組織は会社ライセンスが要るので、この playbook では使わない。

フォントは Noto Sans JP（OFL-1.1、Google Fonts）を全層に使う。c1、c2、c4 は 900、c3 は 700。入手先は https://fonts.google.com/specimen/Noto+Sans+JP 。ファイルは同梱しない。代わりに M PLUS 1p の Black（OFL）も使える。台詞をやわらかくしたいなら M PLUS Rounded 1c の 800〜900（OFL）にしてもよいが、その場合は c3 の `font.class` を `rounded` にし、`fonts` に足す。

## 素材の権利

作る人が用意するもの。自前キャラの絵（自分で描いた SVG や絵、または自分が出力の権利を持つ画像生成の結果と生成の記録）、背景（コードの絵、自分の写真、権利のある生成画像）、自分の台本、許諾を記録した BGM と効果音のファイル。アプリの画面を見せるなら、自分で録った画面。

使ってはいけないもの。他人の猫動画や猫ミーム素材の切り抜き（配布されているグリーンバック素材を含む）。有名な猫ミームの猫、既存キャラ、実在の人物に似せたキャラと、それを狙ったプロンプト。猫ミームの定番の音源と、そこから切り出した音。参照動画の映像、音、テロップの文言。アプリ内でだけ使える音源（TikTok の CML、Meta Sound Collection、CapCut の Commercial Sounds）を焼き込んだ書き出しを、別のプラットフォームに出すこと。

生成画像の権利は提供元で違う。OpenAI は出力を利用者に譲渡、Google は所有権を主張しない、BFL の API は商用利用可、Recraft の無料プランは商用不可。Kling は有料会員の期間中だけ商用利用できる。使う前にその時点の規約を読み、生成の記録に残す。

## 費用の目安

時点は 2026-10-25 の公開価格。実際の請求は確かめていない。

- **code-motion**: 書き出しは 0 ドル。別にエージェントのトークン代がかかる（Opus 5.5 を API で使うと一本 1〜4 ドルの見込み。Pro や Max の定額なら追加は無いが枠を使う）。二本目以降はキャラと背景を使い回せるので軽くなる。
- **image-gen-stills**: 一本 0.17〜0.87 ドル。9:16 の 1K の静止画が 5〜18 枚。Nano Banana 2.1 は 1 枚 0.0336 ドル、FLUX 3 Image は 0.048 ドル。下限は二本目以降で 5 枚、上限は一本目で 18 枚。
- **i2v**: 一本 0.77〜3.39 ドル。静止画に加えて、3 秒の反応クリップ 6〜10 本（計 18〜30 秒、720p、音なし）。下限は Grok Imagine 1.5 lite（0.03 ドル/秒、入力画像 0.01 ドル/枚）、上限は Kling 3.0 の音なし（0.084 ドル/秒）。

有料のルートは、見積もり、上限、承認の順で進める。キャラの表情と反応クリップは一本目で作って保存し、二本目からは使い回す。

## 測ったことと推論

スクリプトで参照のファイルを測った数は無い（`measured` は空、`status: draft`）。動画はダウンロードしていない。参照 3 本は、2026 年 8 月に投稿された日本語の YouTube Shorts（62 秒、67 秒、107 秒）。2026-10-25 に次のものだけを見た。

- **公開ページの HTML**: 尺、配信フォーマットの寸法と fps（1080×1920。二本は 60 fps、一本は 24 fps）。作るカットは 30 fps に決めた。
- **公開のストーリーボード**（101×180 の縮小画を 1 秒間隔）: 場面の切り替えの間隔、ビートの区切り、題が全尺で出続けること、ラベルの刻みが終盤ほど細かくなること、層の配置。目で見た値で、1 秒より細かい時刻は分からない。ハードカットの数は数えられない。
- **公開の静止画 1 枚ずつ**（1080×1920）: 色のしきい値（白は RGB すべて 215 超、黄、赤、黒もそれぞれのしきい値）で画素を取り、行ごとの画素数のプロファイルから、各行の上下端と中心、色の中央値、縁の幅を拾った。一枚の絵の値なので、取り込みの計測ではなく推論として `inferred` に入れた。外接箱ではなく行プロファイルで、黄と赤の字は色の芯の高さ。

推論。ビートの秒と役、層の大きさと位置と色と縁、最短の表示秒（c2 は b1 の 1 秒刻みから、c3 はこの型で決めた値）、カメラが動かないこと、トランジションがハードカットであること、BGM と効果音の付け方（音は聞いていない）、各ルートの費用（公開価格からの計算）。

未計測。c1 と c4 の最短の表示秒、c4 の横の位置（キャラに付いて動く）、影の有無（縮小画では見分けられない）、BGM を声の下で下げるかと、その dB（声が無い）。参照に声があったかは確かめていない（音を聞いていない）ので、`source.reference` は書いていない。
