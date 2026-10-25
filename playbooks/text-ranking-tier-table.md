---
schema: sasaru-playbook/1
id: text-ranking-tier-table
name: 文字だけランキング・Tier 表
status: draft
summary: 表題と、帯ごとに項目を詰めた表を最初のフレームから全部出し、5〜18秒動かさずに置く。読み切れない密度で一時停止とループを誘い、終盤に一行だけ印を付ける。
tags: [ranking, tier-list, text-only, static, loop, faceless, education]
audience:
  - 受験生と大学生
  - 勉強法や道具を他人と比べたい人
fitsContent:
  - 勉強法やノート術の格付け
  - 講義や授業のあるあるの格付け
  - アプリや道具の比較（自社を含むときは個人の見解と明記する）
  - 数字で並べられる自前のデータの順位表
source:
  kind: hand-written
  platform: youtube-shorts
  rightsTier: none
  measuredFiles: 0
  reference: { onCamera: none, speech: none, hardCuts: null }
format:
  aspect: "9:16"
  fps: 30
  durationSec: { min: 5, max: 18, reference: 15 }
  onCamera: none
  speech: none
  safeArea: { top: 0.11, bottom: 0.25, left: 0.03, right: 0.18 }
hook:
  type: list-promise
  firstFrameHasText: true
beats:
  - { id: b1, role: hook, tIn: 0.0, tOut: 1.0, purpose: 何の格付けかと、最上位の帯に何が置かれたかを最初のフレームで同時に読ませる, swap: 自分の格付けの題と、最上位に置く項目 }
  - { id: b2, role: item, tIn: 1.0, tOut: 10.0, purpose: 表を動かさずに読ませる。下の帯ほど項目を詰め、一回では読み切れない量にして一時停止か二周目を促す, swap: 中位から最下位までの帯の項目 }
  - { id: b3, role: payoff, tIn: 10.0, tOut: 14.0, purpose: 一つの行にだけ枠と札を足し、読み終えかけた目を伝えたい行へ戻す, swap: 印を付ける行と、札の短い語 }
  - { id: b4, role: loop, tIn: 14.0, tOut: 15.0, purpose: 印を消して最初のフレームと同じ絵に戻し、ループの継ぎ目を見せない, swap: 差し替えなし }
captions:
  - id: c1
    role: headline
    beats: []
    unit: card
    writingMode: horizontal
    font: { class: extra-bold-gothic, weight: 900 }
    capHeightRatio: 0.045
    emphasis: { scale: 1.0, color: "#E60033" }
    color: "#1A1A1A"
    stroke: null
    shadow: false
    plate: none
    position: { cx: 0.5, cy: 0.15, align: center }
    linesMax: 2
    charsPerCard: { min: 6, max: 20 }
    motionIn: cut
    motionOut: cut
    show: beat-start
    leadSec: null
    hide: beat-end
    minHoldSec: 5.0
    lastCard: hold-to-end
  - id: c2
    role: label
    beats: []
    unit: card
    writingMode: horizontal
    font: { class: extra-bold-gothic, weight: 900 }
    capHeightRatio: null
    emphasis: null
    color: "#FFFFFF"
    stroke: null
    shadow: false
    plate: box
    position: { cx: 0.08, cy: null, align: center }
    linesMax: 1
    charsPerCard: { min: 1, max: 3 }
    motionIn: cut
    motionOut: cut
    show: beat-start
    leadSec: null
    hide: beat-end
    minHoldSec: 5.0
    lastCard: hold-to-end
  - id: c3
    role: label
    beats: []
    unit: card
    writingMode: horizontal
    font: { class: bold-gothic, weight: 700 }
    capHeightRatio: 0.016
    emphasis: null
    color: "#2A2A2A"
    stroke: null
    shadow: false
    plate: none
    position: { cx: null, cy: null, align: left }
    linesMax: 5
    charsPerCard: { min: 6, max: 100 }
    motionIn: cut
    motionOut: cut
    show: beat-start
    leadSec: null
    hide: beat-end
    minHoldSec: 5.0
    lastCard: hold-to-end
  - id: c4
    role: label
    beats: []
    unit: card
    writingMode: horizontal
    font: { class: thin-sans, weight: 400 }
    capHeightRatio: 0.012
    emphasis: null
    color: "#666666"
    stroke: null
    shadow: false
    plate: none
    position: { cx: 0.5, cy: 0.74, align: center }
    linesMax: 1
    charsPerCard: { min: 8, max: 30 }
    motionIn: cut
    motionOut: cut
    show: beat-start
    leadSec: null
    hide: beat-end
    minHoldSec: 5.0
    lastCard: hold-to-end
  - id: c5
    role: label
    beats: [b3]
    unit: card
    writingMode: horizontal
    font: { class: extra-bold-gothic, weight: 900 }
    capHeightRatio: null
    emphasis: null
    color: "#FFFFFF"
    stroke: null
    shadow: false
    plate: pill
    position: { cx: 0.72, cy: 0.23, align: center }
    linesMax: 1
    charsPerCard: { min: 2, max: 8 }
    motionIn: pop
    motionOut: fade
    show: beat-start
    leadSec: null
    hide: beat-end
    minHoldSec: 3.0
    lastCard: phrase-end
camera:
  moves:
    - { beat: b1, move: static }
    - { beat: b2, move: static }
    - { beat: b3, move: static }
    - { beat: b4, move: static }
  zooms: []
  transitions: []
audio:
  bgm:
    present: true
    character: 明るく軽いインスト。中速で一定の刻み。尺の中に盛り上がりや終止を作らず、どこで切れても頭につながる
    entersAt: { beat: b1, offsetSec: 0 }
  sfx:
    - { cue: card-in, at: { beat: b3, offsetSec: 0 }, type: 短く軽いポップ音（ポン） }
  voice: none
  referenceAudioUsed: false
routes:
  - id: code-motion
    default: true
    container: html-canvas
    needs: [none]
    paidApi: false
    talkingHead: false
    costUsdPerVideo: { min: 0, max: 0, basis: HTML の表をヘッドレス Chrome で PNG にし、ffmpeg で静止画と音を書き出す。生成 API は呼ばない。エージェントのトークン代は含まない }
    status: tested
fonts:
  - { family: Noto Sans JP, license: OFL-1.1, source: "https://fonts.google.com/specimen/Noto+Sans+JP" }
  - { family: BIZ UDPGothic, license: OFL-1.1, source: "https://fonts.google.com/specimen/BIZ+UDPGothic" }
rights:
  makerSupplies:
    - 表の中身。自分で決めた格付けで、置いた理由を自分で説明できるもの
    - 再配布か動画内利用の許諾が記録された BGM ファイル
    - 効果音を鳴らすなら、許諾が記録された効果音ファイル
  neverUse:
    - 参照動画の映像、音、表題と表の文言、項目の並び
    - 参照に貼られたスタンプ、ミーム画像、キャラクター、人物の切り抜き
    - 許諾の無い第三者の表、データ、ロゴの転載
    - 根拠を示せない実在の学校、会社、個人の格付け
evidence:
  measured: []
  inferred:
    - source.reference.onCamera
    - source.reference.speech
    - format.fps
    - format.durationSec
    - format.safeArea
    - hook.type
    - hook.firstFrameHasText
    - beats
    - captions.c1.font
    - captions.c1.capHeightRatio
    - captions.c1.emphasis
    - captions.c1.color
    - captions.c1.position
    - captions.c1.linesMax
    - captions.c1.charsPerCard
    - captions.c2.font
    - captions.c2.plate
    - captions.c2.position.cx
    - captions.c3.font
    - captions.c3.capHeightRatio
    - captions.c3.linesMax
    - captions.c3.charsPerCard
    - captions.c4.capHeightRatio
    - captions.c4.position
    - captions.c5.position
    - captions.c5.motionIn
    - captions.c5.minHoldSec
    - camera.moves
    - audio.bgm.character
    - audio.sfx
  unmeasured:
    - source.reference.hardCuts
    - captions.c2.capHeightRatio
    - captions.c2.position.cy
    - captions.c3.position.cx
    - captions.c3.position.cy
    - captions.c5.capHeightRatio
---

# 文字だけランキング・Tier 表

表題と表が最初のフレームから全部出ていて、終わりまで絵がほとんど変わらない型。人も声も無い。見る人は表を読み、読み切れずに止めるか、もう一周する。この playbook は手書きで、動画は取り込んでいない。参照は公開ページのメタデータと、YouTube が出す自動サムネイルで見た（「測ったことと推論」）。

## 構成と尺

参照は5本（以下 R1〜R5）。尺は 15、5、15、18、17 秒。

| 参照 | 表の形 | 尺 | 解像度と fps |
| --- | --- | --- | --- |
| R1 | 帯ごとに色の見出しを付けたグループ別の列挙。帯は8本 | 15秒 | 1080×1920、30fps |
| R2 | ピラミッド図。7段に項目を札で置く | 5秒 | 2160×3840、30fps |
| R3 | 順位・名前・区分・数値などの5列の順位表。30行 | 15秒 | 1080×1920、30fps |
| R4 | S 系から D までの7行の Tier 表。項目を読点でつなぐ | 18秒 | 1080×1920、30fps |
| R5 | R4 と同じ形の Tier 表 | 17秒 | 1080×1920、30fps |

尺の中の 25%、50%、75% の自動サムネイルでは、5本とも表が完成した状態で写っている。途中で行が増える、切り替わる、寄るといった変化は見えなかった。最初の 25% までの間に表が組み上がるかは見ていない。

レシピは参照の尺 15 秒の上に、フック 1 秒、読ませる 9 秒、印 4 秒、ループの戻り 1 秒を置く。カットは無い。尺の帯は参照の幅どおり 5〜18 秒。短いほどループの回数が増え、長いほど一周で読める量が増える。項目が 40 個を超えるなら 15〜18 秒、20 個前後なら 5〜10 秒にする（推論）。

ループが回る仕組み（推論）。最後のフレームと最初のフレームが同じ絵なので、二周目に入ったことに気づきにくい。読み途中で終わると、そのまま続きを読み始める。静止画なので、尺が短くても情報量は表の量で決まる。

## フック

最初のフレームで、表題（何の格付けか）と最上位の帯の項目が同時に読める。表題は2行まで、一つの語だけ赤くする。約束は「この表を読めば並びが分かる」で、答え（最上位）を伏せずに先に見せる。伏せないことで、見る人は自分の知っている項目を探しに下へ読み進める。

## ビート

- **b1（hook、0〜1秒）**: 表題と最上位の帯を読ませる。表全体も出ているので、密度で「全部は読めない」ことが一目で分かる。
- **b2（item、1〜10秒）**: 何も動かさない。下の帯ほど項目を多くして、下に行くほど時間が足りなくなるようにする。R1 は最下位の帯が一番長く、R4 も下の帯ほど行数が多い。R5 は中ほどの帯が一番長い。
- **b3（payoff、10〜14秒）**: 一つの行に枠と短い札を出す（c5）。参照に印の層は見えていない。読み終えかけた目を伝えたい行へ戻すための、この型への追加である。
- **b4（loop、14〜15秒）**: 枠と札をフェードで消し、最初のフレームと同じ絵に戻す。

## テロップ

字の大きさは、参照のサムネイル（1080×1920）の行プロファイルで見た暗い字の高さ / 画面高。白い芯ではなく、明るい地の上の黒い字の高さである。

- **c1（headline、表題）**: 極太ゴシック 900、黒に近い色、強調語だけ赤（大きさは同じ）。R4・R5 の表題は 1 行あたり 0.042〜0.050、R1 は 1 行で 0.027。レシピは 0.045 にし、見出しの下限 0.04 を上回る。縁と影は付けない。明るい地の上なので、参照も黒い縁を使っていない（R2 だけ白と黒の縁がある）。2 行まで、合わせて 6〜20 字。中心は cx 0.5、cy 0.15。全編に出したまま、最後のフレームまで残す。
- **c2（label、帯の名前）**: S、A、B や順位の数字。帯ごとに色の違う四角の座布団に白抜きの極太ゴシックで1〜3字。表の左端の列（cx 0.08）。帯の色は上から金、紫、青、緑、灰のように、上位ほど目立つ色にする。R1 は帯の見出しの帯色を8色で変えている。大きさは参照で測れていない。
- **c3（label、項目）**: 表の本体。太めのゴシック 700、濃い灰色、左揃え。高さは参照で 0.0141〜0.0177。レシピは 0.016。一つの帯が1枚のカードで、最大5行、6〜100字。項目は読点でつなぐ（R4・R5）か、空白で区切る（R1）。表の中の字の行数は、R1 で帯の見出しを含めて約35行、R4 で約23行、R5 で約21行。レシピの安全域では 18〜20 行が入る。これ以下にすると一回で読み切れてしまう（推論）。
- **c4（label、注記）**: 表の下に細いゴシックで一行。「個人の見解」「出典」のような断り書きを置く場所。R1 は表の最下部に 0.0125 の高さの一行がある。cy 0.74。
- **c5（label、印の札）**: b3 だけに出る。赤い丸い座布団に白い極太ゴシックで2〜8字。同時に、その行全体を赤い枠で囲む（枠は字ではないので器の側で描く）。ポンと出し、b3 の終わりからフェードで消す。最後のフレームに残さないのはループの継ぎ目を消すためで、最後のカードを残す原則の例外にあたる。c1〜c4 は最後まで残る。

一つの層の中で大小は混ぜない。強調は c1 の赤一語と c5 の札だけにする。R5 は項目の一部の色を時間とともに変えているように見える（サムネイル間で色の付いた位置が違う）が、レシピには入れない。

## カメラとトランジションとズーム

全ビートで静止。ズームもトランジションも無い。R2 だけ背景の写真の上に図を置いていて、背景が動くかは見ていない。R4 と R5 は、行ごとに小さな動くスタンプを貼っている（サムネイル間の差の大半がこれ）。スタンプは第三者の人物やキャラクターなので使わない。

## BGM と効果音

参照の音は聞いていない。公開ページの表示では、R1〜R3 の音は「オリジナルの音声」、R4 と R5 は音楽ライブラリの曲の表示が付いていた（曲名は書かない）。YouTube が出す音の大きさ（ラウドネス）は R1 −14.2、R2 −26.3、R3 −13.3、R4 −9.6、R5 −8.7 LKFS で、R2 だけほかより 12 dB 以上小さかった。声が入っているかは確かめていない。

レシピは BGM だけ。明るく軽いインストを頭から鳴らし、尺の中に山を作らない。ループで頭に戻ったときに音が途切れて聞こえないよう、終わり 0.5 秒前後をフェードアウトし、頭は 0.3 秒でフェードインする。全体を −14 LUFS に揃える（YouTube の基準値）。効果音は b3 の札が出る瞬間に軽いポップ音を一つだけ。b2 の間は何も鳴らさない。

## なぜ伸びるか

以下は推論。数は 2026-10-25 に公開ページで読んだ値。

| 参照 | 再生 | 高評価 | コメント |
| --- | --- | --- | --- |
| R1 | 800,620 | 685 | 29 |
| R2 | 369,990 | 258 | 29 |
| R3 | 128,656 | 186 | 17 |
| R4 | 208,632 | 257 | 26 |
| R5 | 158,745 | 214 | 30 |

**止まる理由**: 最初のフレームで、自分に関係のある格付け（自分の志望校、自分のやり方）だと分かる。表全体が見えるので、内容を探しに来た人には検索結果の一覧のように働く。

**最後まで見る理由**: 尺が短く、静止しているので離脱の切り替わりが無い。自分の項目がどの帯にあるかを探すうちに尺が終わる。

**もう一度見る理由**: 読み切れない密度と、継ぎ目の無いループ。高評価は再生の 0.07〜0.15%、コメントは 1 本 17〜30 件で、どちらも小さい。反論のコメントで伸びているとは言えず、再生の大半は止まって読む、ループして読むという受け身の再生だと読む方が数に合う。

**伸びない側に落ちない理由と、落ちる条件**:

- 項目が少なく一回で読み切れる表は、二周目が起きない。
- 一時停止しても読めない小ささ（本体が 0.012 を下回る）は、読む前に離脱される。
- 表題が2行に収まらない、最初のフレームに表が出ていない、のどちらかでフックが消える。
- 根拠の無い格付けで実在の学校や人を下位に置くと、通報や低評価の側に振れる。R4 と R5 は概要欄に根拠の資料と「独自の分類」である断りを長く書いている。
- 右端と下端はアプリの UI に隠れる。参照は画面の端まで表を広げているが、レシピは読む字を安全域の中に収める。

## 差し替える場所

- **b1**: 表題（何の格付けか）と、最上位の帯の項目。表題の中で一語だけ赤にする語。
- **b2**: 中位から最下位の帯の項目。項目の総数は 30〜60 を目安にし、下の帯ほど多くする。
- **b3**: 印を付ける行と、札の語（2〜8字）。
- **b4**: 差し替えない。

変えてはいけない部分。最初のフレームに表題と表の全体を出すこと。b2 の間は何も動かさないこと。最後のフレームを最初のフレームと同じ絵にすること。読む字を安全域の中に置くこと。

**ZuruNote の差し替え例（講義編のノートの取り方 Tier 表）**

- b1: 表題は「ノートの取り方」と、赤い語の「Tier 表」の2行。S 帯に「録音から AI ノート」「授業後すぐ要点を見返す」「分からない箇所に印だけ付けて後で聞き直す」。
- b2: A 帯に写真と一行まとめ系、B 帯に手書きと色ペン系、C 帯に書き写しと一夜漬け系、D 帯に何もしない系を置く。下の帯ほど項目を増やし、全体で 30 項目以上にする。
- b3: S 帯の行を赤い枠で囲み、札に「ここ」。効果音のポンを一つ。
- c4: 「個人の見解です。合う方法は人と授業で変わります」。
- 説明文とプロフィールで ZuruNote（講義の録音と AI ノート）を案内し、表の中には製品名を書かない。格付けの対象は勉強のやり方で、実在の学校や人は並べない。

## 制作ルート

### code-motion

HTML で表を一枚組み、ヘッドレス Chrome で 1080×1920 の PNG を2枚（表全体と、印だけの透明な層）撮り、ffmpeg で静止画と BGM を一本にする。2026-10-25 に Linux、Google Chrome 156、ffmpeg 6.1.1 で、下の手順で 15 秒のカットを書き出した。書き出しは約 7.5 秒、最初と最後のフレームの SSIM は 0.997、全体のラウドネスは −14.0 LUFS だった。gate のカット検査（`check_cut.py`）はまだ無いので通していない。

1. 作業フォルダを作り、フォントとライセンス文を取る。

   ```bash
   mkdir -p cut/fonts && cd cut
   curl -sL -o fonts/NotoSansJP.ttf "https://github.com/google/fonts/raw/main/ofl/notosansjp/NotoSansJP%5Bwght%5D.ttf"
   curl -sL -o fonts/OFL.txt "https://raw.githubusercontent.com/google/fonts/main/ofl/notosansjp/OFL.txt"
   ```

2. `table.html` を書く。決まりは次のとおり。
   - `html, body` を 1080×1920 に固定し、CSS の font-face 規則で `fonts/NotoSansJP.ttf` を読み、`font-family` に `"Noto Sans JP"` を当てる。
   - 安全域の内側に縦の flex の箱を置く（上 211 px、下 480 px、左右 32 px）。中身は上から表題（c1、900、76 px 前後、2 行、強調語は `<em>` で `#E60033`）、白い角丸の表（`flex: 1`）、注記（c4、24 px）。
   - 表は帯ごとに1行の flex。左に帯の名前の色の四角（c2、幅 104 px、白い 900）、右に項目（c3、700、33 px 前後、行間 1.36、幅 730 px で右端を画面幅の 0.82 に止める）。
   - 印を付ける行に、枠と札の要素を入れておく。通常は `display: none`。
   - 末尾に `<script>if(location.hash==="#note")document.body.className="note"</script>` を置き、`body.note` では背景を透明、表の中身を `visibility: hidden`、枠と札だけを見せる。こうすると印の層の位置が表と必ず揃う。

3. 二枚撮る。このマシンの Chrome は PNG を書いたあと終了しないことがあったので、`timeout` で打ち切り、PNG の有無と寸法で成否を見る。

   ```bash
   CH="timeout 15 google-chrome --headless=new --no-sandbox --disable-gpu --hide-scrollbars --force-device-scale-factor=1 --window-size=1080,1920 --user-data-dir=$PWD/.chrome"
   $CH --screenshot="$PWD/base.png" "file://$PWD/table.html"
   $CH --default-background-color=00000000 --screenshot="$PWD/note.png" "file://$PWD/table.html#note"
   ffprobe -v error -show_entries stream=width,height,pix_fmt -of csv=p=0 base.png
   ffprobe -v error -show_entries stream=width,height,pix_fmt -of csv=p=0 note.png
   ```

   `base.png` が `1080,1920,rgb24`、`note.png` が `1080,1920,rgba` なら次へ。

4. 書き出す。尺を T 秒にするなら、15 を T に、印の出る秒 10 を T×10/15 に、消える秒 14 を T×14/15 に置き換える。`bgm.wav` はライセンスを記録した曲ファイル。

   ```bash
   ffmpeg -y -loop 1 -framerate 30 -t 15 -i base.png -loop 1 -framerate 30 -t 15 -i note.png -i bgm.wav \
     -filter_complex "[1:v]format=rgba,fade=t=in:st=10:d=0.15:alpha=1,fade=t=out:st=14:d=0.5:alpha=1[n];[0:v][n]overlay=0:0,format=yuv420p[v];[2:a]atrim=0:15,afade=t=in:d=0.3,afade=t=out:st=14.4:d=0.6,loudnorm=I=-14:TP=-1.5[a]" \
     -map "[v]" -map "[a]" -c:v libx264 -crf 18 -r 30 -c:a aac -b:a 192k -ar 48000 -movflags +faststart -t 15 cut.mp4
   ```

   効果音を足すなら、`-i pop.wav` を加え、`[3:a]adelay=10000|10000[s];[a][s]amix=inputs=2:normalize=0` のように b3 の頭に重ねてから `loudnorm` をかける。

5. 確かめる。最初と最後のフレームの SSIM が 0.99 以上なら、ループの継ぎ目は見えない。

   ```bash
   ffmpeg -v error -y -i cut.mp4 -frames:v 1 f0.png
   ffmpeg -v error -y -sseof -0.04 -i cut.mp4 -update 1 -frames:v 1 flast.png
   ffmpeg -i f0.png -i flast.png -lavfi ssim -f null - 2>&1 | grep -o 'All:[0-9.]*'
   ffmpeg -i cut.mp4 -af ebur128 -f null - 2>&1 | grep -E '^\s+I:' | tail -1
   ```

6. `cut.json` に playbook id、ルート、曲と効果音のファイルとライセンス、尺、印の行を書く。

## 編集の器とフォント

器は `html-canvas`（HTML を Chrome で静止画にし、ffmpeg で組む）。表は HTML の flex で組むのが一番速く、字の折り返しも Chrome に任せられる。動くのは印の層のフェードだけなので、HyperFrames や Remotion のフレーム単位の描画は要らない。Remotion を使う場合は、従業員 4 人以上の営利組織で会社ライセンスが要る。

フォントは Noto Sans JP（OFL-1.1、可変 100〜900）を、表題 900、項目 700、注記 400 で使う。項目を小さく詰めて読みにくいときは、項目の層だけ BIZ UDPGothic（OFL-1.1、400 と 700）に替える。どちらも Google Fonts の `ofl/` にあり、日本語を収録している。フォントのファイルはリポジトリに入れず、名前と入手先だけを書く。

## 素材の権利

作る人が用意するもの。表の中身（自分で決めた格付けと、その理由）。許諾を記録した BGM。効果音を鳴らすなら、許諾を記録した効果音。焼き込む音は 3 つのプラットフォームに出すなら外部の素材にする。リポジトリに置けるのは CC0 と、クレジットを残した OtoLogic（CC BY 4.0）だけで、ほかの源はファイルをリポジトリの外に置く。

使ってはいけないもの。参照動画の映像、音、表題と表の文言、項目の並び。参照に貼られたスタンプ、ミーム画像、キャラクター、人物の切り抜き。許諾の無い第三者の表やデータやロゴの転載。根拠を示せない実在の学校、会社、個人の格付け。

## 費用の目安

`code-motion` は一本 0 ドル。生成 API を呼ばず、Chrome と ffmpeg はローカルで動く。かかるのはエージェントのトークン代で、ルートの調べでは Opus 5.5 を API で使うと一本目が $1〜4 程度、二本目以降は `table.html` の文字の差し替えだけなので大きく下がる見込み（推測）。Claude の Pro や Max の枠で動かすなら追加の費用は無い。BGM と効果音を CC0 か OtoLogic から取れば素材費も 0。

## 測ったことと推論

- **測ったもの（スクリプトで、ただし取り込みではない）**: 参照の公開ページの HTML から、尺（`lengthSeconds`）、映像の解像度と fps、再生・高評価・コメントの数、音の表示の種類、YouTube のラウドネス値を読んだ。参照ごとの 25%・50%・75% の自動サムネイル（480×360）を並べ、サムネイル間の SSIM を出した（R1 0.994・0.991、R2 0.998・1.000、R3 0.988・1.000、R4 0.981・0.991、R5 0.955・0.942）。縦長のサムネイル（1080×1920）を灰色にし、明度 100 未満の画素が5個を超える行の連なりを字の行として、高さ / 画面高を出した（表題 0.042〜0.050、項目 0.0141〜0.0177、注記 0.0125）。どれも動画ファイルを測ったものではなく、`source-text.json` も無いので、`evidence.measured` には入れず `inferred` に置いた。
- **目で見たもの**: 表の形、帯の数、色、行数、スタンプの有無はサムネイルを見て書いた。
- **レシピとして決めたもの**: ビートの秒、印の層 c5 とその位置、BGM の気分、効果音、フェードの秒、安全域（テンプレートの値）。c5 の位置は、手順の HTML で描いた札の画素から出した。
- **見ていないもの**: 動画そのもの（ダウンロードしていない）。音（聞いていない）。カットの数。最初の 25% までの表の出方。帯の名前の層の大きさ。
