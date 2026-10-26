---
schema: sasaru-playbook/3
id: timestamp-vlog-lecture-day
name: タイムスタンプ無言 vlog（講義のある1日）
status: draft
summary: 朝から夜までを、時刻ラベル付きの1〜2秒のカットでつなぐ喋らない vlog。時刻が進むたびに場面が替わり、講義の終わりに答えの画（出来上がったノートなど）を置く。顔は出さない。
tags: [vlog, timestamp, day-in-the-life, mini-vlog, no-talking, faceless, student]
audience:
  - 講義のある大学生
  - 専門学校生や、試験前の高校生
  - 他人の一日をのぞいて、自分の時間の使い方の参考にしたい人
fitsContent:
  - 一日の流れの中で使うアプリや道具（録音、ノート、学習アプリ）
  - 講義の日、テスト期間、課題の日のルーティン
  - 朝活や夜の復習のように、時刻で区切れる習慣
contentRoute: reference-world
subject:
  of: reference-world
  words: 講義のある一日を、顔を出さずに時刻の順でたどる
spreadPsychology:
  plays:
    mechanism: 時刻の進行が作る完了への予期。一日が閉じるまで、次の時刻が小さな未完了として残る
    trigger: 最初の時刻が一日の順を約束し、講義の答えの画は終わりに近い拍まで出さない
    basis: inferred
  comments:
    mechanism: 自分の一日と照合して、同じ時刻の自分を一文で重ねる
    trigger: 時刻の表示と手元の画が、見る人の講義の日の穴になる
    basis: inferred
  shares:
    mechanism: 生活の見本として相手に渡す実用
    trigger: 顔が無く時刻の順だけなので、送った相手が自分の日の型として辿れる
    basis: inferred
source:
  kind: hand-written
  platform: youtube-shorts
  rightsTier: none
  measuredFiles: 0
  reference: { onCamera: face, speech: none, hardCuts: null }
format:
  aspect: "9:16"
  fps: 30
  durationSec: { min: 19, max: 62, reference: 30 }
  onCamera: body-no-face
  speech: none
  safeArea: { top: 0.11, bottom: 0.25, left: 0.03, right: 0.18 }
hook:
  type: text-promise
  firstFrameHasText: true
beats:
  - { id: b1, role: hook, tIn: 0.0, tOut: 2.5, purpose: 朝の最初の時刻と一日の題で、この先が時刻の順に進むと約束する, swap: 起きた直後の手元か窓の一画と、自分の一日の題 }
  - { id: b2, role: setup, tIn: 2.5, tOut: 6.0, purpose: 支度と移動で、今日が講義の日だと分からせる, swap: 支度の手元、通学の足元、校舎へ向かう道。他人の顔が判別できない画 }
  - { id: b3, role: item, tIn: 6.0, tOut: 10.0, purpose: 講義の始まり。机に置いた道具を起動する手元で、答えの前振りを置く, swap: 自分の道具を使い始める操作の手元と、動いている画面 }
  - { id: b4, role: item, tIn: 10.0, tOut: 13.0, purpose: 講義の最中。手が空いて聞くことに向いている様子で、時刻だけが進む, swap: ペンを置いた手、窓、腕時計。黒板とスライドの中身は映さない }
  - { id: b5, role: payoff, tIn: 13.0, tOut: 17.5, purpose: 講義が終わった時刻に、結果がもう出来ている。この型の答えの画, swap: 講義の直後に開いた成果物の画面 }
  - { id: b6, role: item, tIn: 17.5, tOut: 21.0, purpose: 昼と午後。浮いた時間で生活が回る様子で息を抜かせる, swap: 学食のトレイ、移動、カフェの手元 }
  - { id: b7, role: item, tIn: 21.0, tOut: 25.0, purpose: 夜の短い見直し。答えの画をもう一度、短く使う, swap: 机で成果物を見返す手元と画面 }
  - { id: b8, role: loop, tIn: 25.0, tOut: 30.0, purpose: 消灯で一日を閉じる。最初の朝の画に近い暗さと構図で、二周目に入りやすくする, swap: 照明を消す手、伏せたスマホ、閉じたノート }
captions:
  - id: c1
    role: counter
    beats: []
    unit: card
    writingMode: horizontal
    font: { class: thin-sans, weight: 500 }
    capHeightRatio: null
    emphasis: null
    color: "#FFFFFF"
    stroke: null
    shadow: true
    plate: none
    position: { cx: 0.5, cy: 0.42, align: center }
    linesMax: 1
    charsPerCard: { min: 4, max: 8 }
    motionIn: cut
    motionOut: cut
    show: beat-start
    leadSec: null
    hide: next-card
    minHoldSec: 2.5
    lastCard: hold-to-end
  - id: c2
    role: subtitle
    beats: [b2, b3, b4, b5, b6, b7, b8]
    unit: phrase
    writingMode: horizontal
    font: { class: thin-sans, weight: 500 }
    capHeightRatio: null
    emphasis: null
    color: "#FFFFFF"
    stroke: null
    shadow: true
    plate: none
    position: { cx: 0.5, cy: 0.47, align: center }
    linesMax: 1
    charsPerCard: { min: 2, max: 12 }
    motionIn: cut
    motionOut: cut
    show: beat-start
    leadSec: null
    hide: beat-end
    minHoldSec: 3.0
    lastCard: hold-to-end
  - id: c3
    role: headline
    beats: [b1]
    unit: line
    writingMode: horizontal
    font: { class: rounded, weight: 800 }
    capHeightRatio: 0.056
    emphasis: null
    color: "#FFFFFF"
    stroke: { color: "#333333", px1080: 8 }
    shadow: false
    plate: none
    position: { cx: 0.5, cy: 0.30, align: center }
    linesMax: 2
    charsPerCard: { min: 4, max: 10 }
    motionIn: fade
    motionOut: fade
    show: beat-start
    leadSec: null
    hide: beat-end
    minHoldSec: 2.5
    lastCard: phrase-end
camera:
  moves:
    - { beat: b1, move: static }
    - { beat: b2, move: handheld }
    - { beat: b3, move: static }
    - { beat: b4, move: static }
    - { beat: b5, move: handheld }
    - { beat: b6, move: handheld }
    - { beat: b7, move: static }
    - { beat: b8, move: static }
  zooms: []
  transitions:
    - { at: { beat: b2, offsetSec: 0 }, type: hard-cut }
    - { at: { beat: b3, offsetSec: 0 }, type: hard-cut }
    - { at: { beat: b4, offsetSec: 0 }, type: hard-cut }
    - { at: { beat: b5, offsetSec: 0 }, type: hard-cut }
    - { at: { beat: b6, offsetSec: 0 }, type: hard-cut }
    - { at: { beat: b7, offsetSec: 0 }, type: hard-cut }
    - { at: { beat: b8, offsetSec: 0 }, type: hard-cut }
audio:
  bgm:
    present: true
    character: 静かなアコースティックかローファイ。ゆっくりで拍が前に出ず、生活音が上に聞こえる小ささ
    entersAt: { beat: b1, offsetSec: 0 }
  sfx:
    - { cue: card-in, type: 時刻が替わる合図の小さいクリックかポン }
    - { cue: payoff, at: { beat: b5, offsetSec: 0 }, type: 短いきらめき音を一回 }
    - { cue: cut, type: 自分で別に録った生活音（ドア、足音、ペン、キーボード、カップ）を画に合わせて }
  voice: none
  referenceAudioUsed: false
routes:
  - id: caption-over-footage
    default: true
    container: ffmpeg-ass
    needs: [own-footage, screen-capture]
    paidApi: false
    talkingHead: false
    costUsdPerVideo: { min: 0, max: 0, basis: 自分のスマホで撮り、ローカルの ffmpeg と libass で組む。エージェントのトークン代は含めない }
    status: design-only
  - id: t2v
    default: false
    container: ffmpeg-ass
    needs: [t2v, own-footage, screen-capture]
    paidApi: true
    talkingHead: false
    costUsdPerVideo: { min: 0.36, max: 2.88, basis: 人のいない B ロールを 720p・音声なしで計 12〜24 秒生成する。下限は Grok Imagine Video 1.5 lite の 0.03 USD/秒 × 12 秒、上限は Runway Gen-4.5 の 0.12 USD/秒 × 24 秒。公開料金表の値で、やり直しとエージェントのトークン代は含めない, asOf: "2026-10-25" }
    status: design-only
fonts:
  - { family: Zen Kaku Gothic New, license: OFL-1.1, source: "https://fonts.google.com/specimen/Zen+Kaku+Gothic+New" }
  - { family: M PLUS Rounded 1c, license: OFL-1.1, source: "https://fonts.google.com/specimen/M+PLUS+Rounded+1c" }
rights:
  makerSupplies:
    - 自分で撮った映像（手元、足元、後ろ姿、物、景色）。他人の顔と名札が判別できないもの
    - 講義室で撮影と録音をしてよいという、大学か担当教員の許可
    - 画面に出す成果物の元になる素材で、公開してよい内容のもの（自分で話した模擬講義の録音など）
    - 画面録画した自分のアプリの画面
    - 再配布か動画内利用の許諾が記録された BGM ファイル
    - ライセンスを記録した効果音ファイルと、自分で録った生活音
  neverUse:
    - 参照動画の映像、音、テロップの文言、作者名
    - 教員と他の学生の声、顔、名前
    - 講義のスライド、板書、配布資料の中身（画面のノートに写り込む分も含む）
    - 撮影か録音が禁止された講義室での撮影
    - アプリ内付与の音源（TikTok の商用音源ライブラリなど）を焼き込んだ書き出しを、別のプラットフォームへ流用すること
    - 生成した写実的な人物（t2v ルート）
evidence:
  measured: []
  inferred:
    - source.reference.onCamera
    - source.reference.speech
    - format.aspect
    - format.fps
    - format.durationSec
    - format.onCamera
    - format.safeArea
    - hook.type
    - hook.firstFrameHasText
    - beats
    - captions.c1.font
    - captions.c1.position
    - captions.c1.charsPerCard
    - captions.c1.motionIn
    - captions.c1.minHoldSec
    - captions.c2.font
    - captions.c2.position
    - captions.c2.charsPerCard
    - captions.c2.minHoldSec
    - captions.c3.font
    - captions.c3.capHeightRatio
    - captions.c3.stroke
    - captions.c3.position
    - captions.c3.minHoldSec
    - camera.moves
    - camera.zooms
    - camera.transitions
    - audio.bgm.character
    - audio.sfx
    - routes.t2v.costUsdPerVideo
  unmeasured:
    - source.reference.hardCuts
    - captions.c1.capHeightRatio
    - captions.c2.capHeightRatio
---

# タイムスタンプ無言 vlog（講義のある1日）

一日を時刻のラベルで区切り、短いカットを時刻の順に並べる。誰も喋らない。見る人は時刻が進むのを追いながら、他人の一日をのぞく。このレシピは、講義のある一日を朝から夜まで扱い、講義が終わった時刻に「答えの画」を置く。顔は出さず、手元、足元、後ろ姿、物、画面で組む。

## 構成と尺

参照に使った4本の尺は 19、62、108、78 秒（公開ページの表示）。どれも一日の一部、多くは朝だけを扱っている。1秒刻みのストーリーボードで見ると、隣り合うコマの多くで画が替わり、同じ画が3コマ以上続く箇所は少ない。1カットは1〜2秒が中心と読める（推論。カット点は測っていない）。

このレシピは参照の尺を 30 秒に置き、帯を 19〜62 秒にする。

- 8 ビート = 8 つの時刻。1 ビートに 2〜3 カット、1 カット 1〜2 秒。
- 時刻が全編に出る参照2本は、朝の1〜2時間ほどを数分〜十数分刻みで進める。講義のある一日は朝から夜までを扱うので、刻みを粗くし、30分〜数時間で進める。
- 短くする（19 秒前後）ときは b4 と b6 を落とす。長くする（60 秒前後）ときはビートの数を変えず、各ビートのカットを増やす。ビートを足すと、時刻が進む速さが鈍る。
- 30 秒の理由。8 場面を 3〜5 秒ずつ見せると、各場面に「何をしているか」が一目で読める 2〜3 カットが入り、答えの画（b5）に 4.5 秒を取れる。

## フック

0〜2.5 秒（b1）。1フレーム目から、朝の最初の時刻（c1）と一日の題（c3）を出す。画は起きた直後の手元か、カーテンを開けた窓。約束は「このあと時刻の順に一日が進む」こと。題は「何の日か」を一行で言い、答えは言わない。

参照の題の置き方は分かれていた。冒頭だけ題と時刻を重ねる本、冒頭に題のカードを置く本、題を置かず時刻だけで始める本。このレシピは、講義の日だと最初に分からせたいので題を置く。

## ビート

- **b1 hook（0〜2.5 秒）** 朝の時刻と題。窓か手元の静かな画。次へ進ませるのは、時刻の数字が「次の時刻」を予告していること。
- **b2 setup（2.5〜6.0 秒）** 支度と移動。手元で支度、足元で歩く、校舎へ向かう道。今日が講義の日だと分かる。
- **b3 item（6.0〜10.0 秒）** 講義の始まり。机に道具を置き、起動する手元。ここで答えの前振りを置く。何が起きるかはまだ見せない。
- **b4 item（10.0〜13.0 秒）** 講義の最中。手が空き、聞くことに向いている画（ペンを置いた手、窓、腕時計）。時刻が一つ進むだけで、時間が過ぎたと伝わる。
- **b5 payoff（13.0〜17.5 秒）** 講義が終わった時刻に、成果物がもう出来ている。画面を持つ手元か、画面録画。この型の答え。
- **b6 item（17.5〜21.0 秒）** 昼と午後。学食、移動、カフェ。浮いた時間で生活が回り、見る人は一息つく。
- **b7 item（21.0〜25.0 秒）** 夜の短い見直し。b5 の画面を短く再登場させ、答えを念押しする。
- **b8 loop（25.0〜30.0 秒）** 消灯。照明を消す手、伏せたスマホ。最初の朝の画に近い暗さと構図にして、ループの継ぎ目を目立たなくする。

## テロップ

参照で見たこと（1秒刻みのストーリーボード、101×180 px で目視。大きさは測っていない）。時刻のラベルは小さい白の細字で、横は中央、縦は画面の中ほどか上寄り。2本は全編に時刻が出続け、場面が替わっても時刻が同じ間は残り、時間が進むと数字だけ替わる。1本は冒頭だけ時刻と一言を重ねる。1本は冒頭の題のカードのあと、カットごとに一行の小さい字幕を出す。英語の2本は細いセリフ体に近い字に見えた。

- **c1 counter（時刻）** 全ビート。細いゴシック 500、白、影あり、縁なし、座布団なし。中央揃え、cx 0.5・cy 0.42。一行、4〜8 字（「7:30」から「AM 10:30」まで）。ビートの頭に切り替えで出し、次の時刻が来たら消す。最短 2.5 秒。最後の一枚は終わりまで残す。大きさは未計測。参照の小ささを写すと読めないので、書き出した一枚をスマホで見て、数字が一目で読める大きさにする。決めた値は制作記録に書く。
- **c2 subtitle（一言）** b2〜b8。c1 と同じ書体で、c1 の真下（cy 0.47）。一行、2〜12 字。何をしている時刻かを名詞か短い句で言う。ビートの頭に出し、ビートの終わりで消す。最短 3.0 秒。最後の一枚は終わりまで残す。大きさは未計測で、c1 より一段小さくする。c1 と c2 の間で大小を混ぜるのは、時刻を主、一言を従に読ませるため。一つの層の中では大小を混ぜない。
- **c3 headline（題）** b1 だけ。丸ゴシック 800、白、濃い灰の縁 8 px（1080 幅）、影なし。cy 0.30、中央揃え。二行まで、4〜10 字。白い芯の高さ / 画面高 0.056（`sasaru-principle-captions-read-as-headlines` の地の句の帯から取った値で、参照で測った値ではない）。フェードで出てフェードで消え、b1 の終わりで消える。

c1 と c2 は安全域（上 0.11、下 0.25、右 0.18）の内側、画面の中ほどに置く。下の 0.25 には UI とキャプションが重なるので、時刻を下に置かない。

## カメラとトランジションとズーム

参照で見たこと。三脚か机に置いた固定の画が中心で、そこに手持ちの手元（自分の目線）、後ろ姿、部屋全体の引きが混ざる。4本のうち3本は顔が映り、1本は顔をフレームの外に切るか、丸いステッカーで隠していた。ズームは 1 秒刻みでは見えなかった。切り替えは見た範囲ではハードカットで、短いフェードがあったかは 1 秒刻みでは見分けられない。

このレシピ。

- 固定（b1、b3、b4、b7、b8）。机は真上か斜め上から。スマホの画面を映すカットは真上から固定する。
- 手持ち（b2、b5、b6）。自分の目線で手元と足元を撮る。歩くカットは胸より下を撮り、他人を正面から入れない。
- ズームは使わない。画面の字を読ませたいときは寄りのカットを別に撮って切り替える。
- ビートの境はすべてハードカット。ビートの中のカットの継ぎ目もハードカットにする。

## BGM と効果音

参照の音は聞いていない。2本は題と説明欄に ASMR と無言の語を挙げていて、生活音を聞かせる型と読める（推論）。BGM の有無は4本とも確かめていない。

このレシピ。

- BGM は静かなアコースティックかローファイ。ゆっくりで、拍が前に出ないもの。b1 の頭から入り、b8 の終わりでフェードアウト。声が無いので、声との関係の欄は書かない。
- 生活音は、撮影とは別に自分で録るか、CC0 の素材を使う。講義室で撮った映像の音は使わない（教員と他の学生の声が入る）。撮った映像の音は全部外す。
- 時刻が替わる頭（c1 のカードが替わる時）に、小さいクリックかポンを一回。毎回同じ音にして、時刻が進む合図として覚えさせる。
- b5 の頭（答えの画）に短いきらめき音を一回だけ。他の場所では鳴らさない。

## なぜ伸びるか

以下はすべて推論。

止まる理由。1フレーム目の時刻の数字は一瞬で読め、「この人の一日をのぞく」という約束になる。生活の画の手触り（光、湯気、紙、手）は、文字より先に目に入る。

最後まで見る理由。時刻が進むこと自体が進み具合のバーになり、残りの長さが分かる。1〜2秒でカットが替わるので画が止まらない。次の時刻に何があるかが小さな引きになる。このレシピでは、講義の前振り（b3）から答え（b5）までが 7 秒で、待たせすぎない。

もう一度見る理由。カットが短いので見落としが出る。小さい時刻を読み返したくなる。最後の暗い画が最初の朝の画につながる。生活の参考として保存されやすい。

喋らないので、音を消しても成り立ち、言葉の壁も低い。

伸びない側に落ちないための注意。

- 顔を出さないと、人への親しみが落ちる。参照4本のうち3本は顔が映る。同じマグ、同じ袖、同じ机、同じ光のように、手元の一貫性で「同じ人の一日」に見せて補う。
- 製品の画面が長いと広告に見える。答えの画は b5 の 4.5 秒と b7 の再登場だけにし、操作の説明をテロップで足さない。
- 時刻が不自然に飛ぶと作り物に見える。講義の長さに合った時刻を書く。
- 毎回同じ一日だと量産のテンプレートに見える。各回で一日の中身（曜日、講義、天気、食べたもの）を変える。

## 差し替える場所

- **b1** 自分の朝の時刻、朝の画、一日の題。
- **b2** 自分の支度と移動。
- **b3** 自分の道具を使い始める手元と画面。
- **b4** 講義中の、手が空いている画。
- **b5** 自分の成果物の画面。
- **b6** 自分の昼と午後。
- **b7** 夜に成果物を見返す画。
- **b8** 自分の消灯の画。
- **c1、c2** 自分の時刻と一言。

変えてはいけない部分。

- 時刻は単調に進む。戻らない。
- 1フレーム目に時刻がある。
- 誰も喋らない。ナレーションも入れない。
- 顔を出さない。
- 答えの画は講義の直後（b5）に置き、b3 で前振りしてから見せる。
- c1 と c2 の最後の一枚は動画の終わりまで残す。

### ZuruNote の例

ZuruNote（学生向けの講義録音と AI ノート）で作る場合の台本。時刻と一言はこちらで書いた例で、参照の文言ではない。

| ビート | c1 時刻 | c2 一言 | 画 |
| --- | --- | --- | --- |
| b1 | 7:30 | （c3 の題「講義のある日」） | カーテンを開ける手、窓の朝の光 |
| b2 | 8:40 | 1限へ | 靴を履く足元、キャンパスの道を歩く足元 |
| b3 | 9:00 | 録音 ON | 机にスマホを置く手、ZuruNote の録音ボタンを押す指、録音中の画面（真上から固定） |
| b4 | 10:00 | 聞くだけ | ペンを置いた手、窓、腕時計 |
| b5 | 10:30 | もうノートある | 講義の終わりに ZuruNote を開く手、生成されたノートをスクロールする画面 |
| b6 | 12:30 | 学食 | トレイを置く手、湯気 |
| b7 | 21:00 | 復習5分 | 机で ZuruNote のノートを見返す手元と画面 |
| b8 | 23:30 | おやすみ | 照明を消す手、伏せたスマホ |

- b3 の録音中の画面と、b5・b7 のノートの画面は、ZuruNote の画面録画か、画面を持つ手元の撮影で撮る。録音とノートは、公開してよい内容のもの（自分で話した模擬講義など）を使う。実際の講義の中身、教員の名前、スライドの写り込みが画面のノートに出ないようにする。
- 講義室で撮るなら、撮影と録音の許可を先に取る。許可が無い講義室では、b3 と b4 を自室や空き教室で撮り直す。
- b5 で ZuruNote の機能を字で説明しない。「講義の時刻のあとに、ノートがもう出来ている」ことだけを時刻と画で見せる。

## 制作ルート

### caption-over-footage

1. 撮る。スマホを縦、30fps にする。ビートごとに 2〜3 カット、1 カット 2〜4 秒で撮る（編集で 1〜2 秒に切る）。b3 と b7 のスマホ画面は真上から固定、b2 と b6 は自分の目線の手持ち。顔と他人が判別できる画は撮らない。
2. アプリの画面を録る。スマホの画面収録で、ZuruNote の録音開始とノートの表示を録る。`raw/screen_b3.mp4`、`raw/screen_b5.mp4` のように置く。
3. カットを切り、音を外し、1080×1920・30fps に揃える。カットごとに一回。

   ```bash
   ffmpeg -ss 1.2 -to 2.7 -i raw/IMG_0101.MOV -an \
     -vf "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,fps=30" \
     -c:v libx264 -crf 18 -pix_fmt yuv420p shots/b3_1.mp4
   ```

4. つなぐ。`shots.txt` に `file 'shots/b1_1.mp4'` の形でビートの順に並べる。

   ```bash
   ffmpeg -f concat -safe 0 -i shots.txt -c copy body.mp4
   ```

5. テロップを ASS で書いて焼く。`PlayResX: 1080`、`PlayResY: 1920` にし、層ごとにスタイルを分ける（c1、c2 は Zen Kaku Gothic New Medium、c3 は M PLUS Rounded 1c ExtraBold で縁 8）。位置は `{\an5\pos(540,806)}`（c1、cy 0.42）、`{\an5\pos(540,902)}`（c2、cy 0.47）、`{\an5\pos(540,576)}`（c3、cy 0.30）。c3 の文字の大きさは、一枚書き出して白い芯の高さが画面高の 0.056 になる値に合わせる。c1 と c2 のカードの秒はビートの `tIn` と `tOut` を、決めた尺に伸縮して使う。最後のカードの終了秒は動画の終わりにする。

   ```bash
   ffmpeg -i body.mp4 -vf "subtitles=captions.ass:fontsdir=fonts" \
     -c:v libx264 -crf 18 -pix_fmt yuv420p -r 30 -an burned.mp4
   ```

6. 音を足す。BGM、生活音、効果音はすべて別ファイルで、ライセンスを記録したもの。効果音は `adelay` でカードの秒に置く（例は b5 の頭 13.0 秒のきらめき音）。時刻の替わりのクリックも、ビートの頭ごとに同じ形で足す。音量は耳で決め、決めた値を制作記録に書く。

   ```bash
   ffmpeg -i burned.mp4 -i bgm.wav -i ambience.wav -i chime.wav \
     -filter_complex "[1:a]volume=${BGM_GAIN},afade=t=out:st=28:d=2[m];[2:a]volume=${AMB_GAIN}[a];[3:a]adelay=13000|13000[c];[m][a][c]amix=inputs=3:normalize=0[out]" \
     -map 0:v -map "[out]" -c:v copy -c:a aac -shortest out.mp4
   ```

7. 制作記録 `sasaru/cuts/<cut-id>/cut.json` に、playbook id、ルート、素材とライセンス、カード、伸縮の比、c1・c2 の大きさとして決めた値を書き、gate のカット検査に回す。

### t2v

撮れない画、撮ると他人が入る画を、人のいない生成の B ロールで埋める。講義の場面（b3、b4、b5）、ZuruNote の画面（b3、b5、b7）は生成せず、caption-over-footage と同じく自分で撮る。

1. 生成で埋める画を決める。人を出さない画だけにする。例は b1 の窓の外の朝、b2 の並木道、b6 の学食のトレイと湯気、b8 の夜の窓。4〜6 本、1 本 3〜4 秒、合計 12〜24 秒。
2. プロンプトを書く。9:16、720p、音声なし、画面に文字なし、人なし。カメラはゆっくりか固定。毎回同じ光の色（朝は暖色、夜は暗い青）を書き、自分で撮ったカットと馴染ませる。
3. 見積もる。本数 × 秒 × 単価を出し、上限を決め、作る人の承認を取る（`sasaru-principle-quote-before-you-spend`）。このリポジトリに生成のスクリプトは無いので、提供元の API かサイトで生成する。
4. 承認のあと、一本につき一回だけ送る。見た目が違ったら、同じ入力を送り直さず、プロンプトを直した理由を記録してから送る。
5. 生成物の音を外す。

   ```bash
   ffmpeg -i gen/b1_window.mp4 -an -c:v copy gen/b1_window_noaudio.mp4
   ```

6. caption-over-footage の手順 3 で 1080×1920・30fps に揃え、手順 4〜7 で組む。制作記録に、生成したモデル、秒、金額を書く。
7. 投稿するとき、プラットフォームの AI 生成の表示を付ける。TikTok は写実的な AI 映像に表示を求めている。

## 編集の器とフォント

器は ffmpeg と ASS（libass）。理由は三つ。カットを切ってつなぎ、時刻のテロップを焼くだけの型で、動きのある文字が要らない。ローカルで無料で動く。ASS のスタイルが層の指定（書体、縁、影、位置）とそのまま対応する。ffmpeg の GPL ビルドで書き出した動画そのものに GPL の義務は及ばないと読めるが、法的な確認はしていない（推測）。

CapCut でも組めるが、CapCut の音源を使った書き出しは CapCut と TikTok の外へ持ち出せない。三つのプラットフォームに同じ動画を出すなら、音は外部のファイルで焼く。

フォントは Google Fonts の OFL 書体。ファイルはリポジトリに入れず、制作機の `fonts/` に置いて `fontsdir` で渡す。

- Zen Kaku Gothic New（OFL-1.1、300〜900）。c1 と c2。細いゴシックで、数字が素直に読める。<https://fonts.google.com/specimen/Zen+Kaku+Gothic+New>
- M PLUS Rounded 1c（OFL-1.1、100〜900）。c3。丸ゴシックの 800 で、学生の日常のやわらかさに合う。<https://fonts.google.com/specimen/M+PLUS+Rounded+1c>

## 素材の権利

作る人が用意するもの。

- 自分で撮った映像。他人の顔と名札が判別できないもの。
- 講義室で撮影と録音をしてよいという、大学か担当教員の許可。
- 画面に出す成果物の元になる素材で、公開してよい内容のもの。
- 自分のアプリの画面録画。
- BGM ファイルと、その許諾の記録。三つのプラットフォームに出すなら、アプリ内付与の音源ではなく外部の素材にする。公開リポジトリに音声ファイルを入れてよいのは CC0 と、クレジットを残す CC BY だけ。
- 効果音。クリックとポンは OpenGameArt の CC0 や Kenney（CC0）、きらめき音は Freesound の CC0 か OtoLogic（CC BY 4.0、クレジット要）で揃う。生活音は自分で録るのがいちばん安全。

使ってはいけないもの。

- 参照動画の映像、音、テロップの文言、作者名。
- 教員と他の学生の声、顔、名前。講義室で撮った映像の音は全部外す。
- 講義のスライド、板書、配布資料の中身。画面のノートに写り込む分も含む。
- 撮影か録音が禁止された講義室での撮影。
- アプリ内付与の音源を焼き込んだ書き出しを、別のプラットフォームへ流用すること。
- 生成した写実的な人物。

## 費用の目安

**caption-over-footage**。0 USD。スマホと、ローカルの ffmpeg と libass だけ。エージェントのトークン代は別で、Opus 5.5 を API で使うと 1 本 1〜4 USD 程度、Pro か Max のプランなら追加の費用は無い（推測）。

**t2v**。人のいない B ロールを 720p・音声なしで計 12〜24 秒生成したときの、一本の費用。単価は 2026-10-25 の公開料金表。

| モデル | 1 秒 | 12 秒 | 24 秒 | 商用の条件 |
| --- | --- | --- | --- | --- |
| Grok Imagine Video 1.5 lite | 0.03 USD | 0.36 USD | 0.72 USD | API 出力の透かしの有無は未確認 |
| PixVerse V6（音声なし） | 0.040 USD | 0.48 USD | 0.96 USD | 未確認 |
| Veo 3.1 Fast（音声なし） | 0.08 USD | 0.96 USD | 1.92 USD | Google Cloud の GA 版は出力の補償の対象 |
| Kling 3.0（音声なし） | 0.084 USD | 1.01 USD | 2.02 USD | 有料会員の期間中だけ商用可 |
| Runway Gen-4.5 | 0.12 USD | 1.44 USD | 2.88 USD | 商用可、クレジット表記の義務なし |

フロントマターの帯 0.36〜2.88 USD は、この表の最安と最高。やり直しとトークン代は含めない。見積もりは手順 3 で出し、上限を決めてから送る。商用の条件がはっきりしているのは Runway と、Google Cloud の GA 版の Veo。まず安いモデルで試し、商用で出す本は条件のはっきりしたモデルで作り直す。

## 測ったことと推論

測ったもの。無い（`status: draft`、`measuredFiles: 0`）。動画はダウンロードしておらず、音も聞いていない。

見たもの。2026年秋のショート動画の型の調べ（2026-10-25）で、この型の代表に挙げた4本（YouTube Shorts）の公開ページ。URL と作者名はここに書かない。

- 公開ページの埋め込み情報。尺（19、62、108、78 秒）、配信の解像度とフレームレート（4本とも縦長で、3本は 60fps、1本は 30fps の配信があった）、題と説明欄の語。
- YouTube が公開ページ用に出す 1 秒刻みのストーリーボード（101×180 px のコマ）を目で見た。時刻ラベルの出方と位置、カメラの置き方、顔の映り方、カットの替わり方はここから読んだ。字の大きさと秒は測っていない。

推論として書いたもの。`evidence.inferred` の欄。

- `format`、`beats`、`hook`、`camera`、`audio` はこのレシピの指定で、参照の目視と、型の調べの記述から組んだ。`format.fps` の 30 は作る側の選択。
- `captions.c3.capHeightRatio` の 0.056 と縁 8 px は `sasaru-principle-captions-read-as-headlines` の帯から取った。
- c1・c2 の位置と字数、層の最短秒は、参照の目視とビートの長さから決めた値。
- `source.reference.speech` の none は、2本の題と説明欄の語と、型の調べの分類から読んだ。残り2本の発話は確かめていない。
- t2v の費用は、制作ルートの調べ（2026-10-25、各社の公開料金表）の単価から計算した。

未計測のもの。`evidence.unmeasured` の欄。参照のハードカット数、c1 と c2 の白い芯の高さ。BGM と声を比べる欄は、声が無いので書いていない。取り込みのスクリプトで手元のファイルを測れば、`status: measured` に上げられる。
