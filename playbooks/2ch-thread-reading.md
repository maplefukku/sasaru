---
schema: sasaru-playbook/2
id: 2ch-thread-reading
name: 2ch スレ風の文字読み（大学ネタ）
status: draft
summary: 掲示板のスレタイを一枚出して答えを伏せ、白い札のレスを画像の上に一枚ずつ積んで読ませる。最後に大きな赤字のレスで落とし、そのまま頭に戻る。
tags: [2ch, 5ch, thread-reading, text-only, faceless, campus, japanese]
audience:
  - 日本の大学生
  - 講義、テスト、単位、課題の話題を追う学生
fitsContent:
  - 大学生活を題材にした創作スレ（講義、テスト、単位、課題、研究室）
  - アプリの使い方を、スレ民の反応として見せる話
  - 画面のスクリーンショットか図が一枚あれば成り立つ小ネタ
contentRoute: reference-world
subject:
  of: reference-world
  words: 大学のスレで、伏せた結末にレスが積まれていく
source:
  kind: hand-written
  platform: youtube-shorts
  rightsTier: none
  measuredFiles: 0
format:
  aspect: "9:16"
  fps: 30
  durationSec: { min: 59, max: 70, reference: 70 }
  onCamera: none
  speech: none
  safeArea: { top: 0.04, bottom: 0.12, left: 0.01, right: 0.02 }
hook:
  type: text-promise
  firstFrameHasText: true
beats:
  - { id: b1, role: hook, tIn: 0, tOut: 6, purpose: スレタイ一枚で出来事と「結果」を約束し、中身を伏せる, swap: 創作タグ付きの自分のスレタイと、話の舞台になる一枚の画像 }
  - { id: b2, role: setup, tIn: 6, tOut: 11, purpose: スレ主の長めの一レスで前提を渡し、読む姿勢に入らせる, swap: 何が起きたかを三行で説明するスレ主のレスと、根拠に見える画面 }
  - { id: b3, role: item, tIn: 11, tOut: 22, purpose: 最初の反応を四枚積み、ツッコミと疑問で次のページを待たせる, swap: 疑う、驚く、自分語りをする反応レス }
  - { id: b4, role: item, tIn: 22, tOut: 31, purpose: 画像を寄りに替えて細部を見せ、反応を三枚足す, swap: 同じ画面の寄りと、細部に気づく反応 }
  - { id: b5, role: item, tIn: 31, tOut: 40, purpose: 根拠の画面に戻り、事情を知る住人のレスで話を一段深くする, swap: 仕組みや事情を説明する住人のレス }
  - { id: b6, role: turn, tIn: 40, tOut: 50, purpose: 意外な数字か事実で話の向きを変える, swap: 見る人の予想を裏切る一点 }
  - { id: b7, role: item, tIn: 50, tOut: 61, purpose: 向きが変わったあとの反応を四枚積み、結論を予感させる, swap: 手のひら返し、納得、羨む反応 }
  - { id: b8, role: payoff, tIn: 61, tOut: 70, purpose: 最後に大きな一レスで落とし、絵を残したまま頭へ滑らせる, swap: 自分の落ちの一句 }
captions:
  - id: c1
    role: headline
    beats: [b1]
    unit: card
    writingMode: horizontal
    font: { class: rounded, weight: 800 }
    capHeightRatio: 0.039
    emphasis: null
    color: "#430BEE"
    stroke: null
    shadow: false
    plate: box
    position: { cx: 0.5, cy: 0.223, align: center }
    linesMax: 4
    charsPerCard: { min: 30, max: 45 }
    motionIn: cut
    motionOut: other
    show: beat-start
    leadSec: null
    hide: beat-end
    minHoldSec: 6
    lastCard: phrase-end
  - id: c2
    role: subtitle
    beats: [b2, b3, b4, b5, b6, b7, b8]
    unit: card
    writingMode: horizontal
    font: { class: rounded, weight: 800 }
    capHeightRatio: 0.034
    emphasis: null
    color: "#23477E"
    stroke: null
    shadow: false
    plate: box
    position: { cx: null, cy: null, align: left }
    linesMax: 3
    charsPerCard: { min: 4, max: 40 }
    motionIn: other
    motionOut: other
    show: onset
    leadSec: null
    hide: beat-end
    minHoldSec: 2
    lastCard: hold-to-end
  - id: c3
    role: headline
    beats: [b8]
    unit: card
    writingMode: horizontal
    font: { class: rounded, weight: 800 }
    capHeightRatio: 0.049
    emphasis: null
    color: "#E90621"
    stroke: null
    shadow: false
    plate: box
    position: { cx: 0.5, cy: null, align: center }
    linesMax: 2
    charsPerCard: { min: 14, max: 20 }
    motionIn: other
    motionOut: other
    show: onset
    leadSec: null
    hide: beat-end
    minHoldSec: 2
    lastCard: hold-to-end
  - id: c4
    role: label
    beats: []
    unit: line
    writingMode: horizontal
    font: { class: rounded, weight: 500 }
    capHeightRatio: 0.021
    emphasis: null
    color: "#384459"
    stroke: null
    shadow: false
    plate: none
    position: { cx: null, cy: 0.967, align: left }
    linesMax: 2
    charsPerCard: { min: 8, max: 60 }
    motionIn: cut
    motionOut: cut
    show: beat-start
    leadSec: null
    hide: beat-end
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
    - { beat: b7, move: static }
    - { beat: b8, move: static }
  zooms: []
  transitions:
    - { at: { beat: b2, offsetSec: 0 }, type: whip }
    - { at: { beat: b3, offsetSec: 0 }, type: whip }
    - { at: { beat: b4, offsetSec: 0 }, type: whip }
    - { at: { beat: b5, offsetSec: 0 }, type: whip }
    - { at: { beat: b6, offsetSec: 0 }, type: whip }
    - { at: { beat: b7, offsetSec: 0 }, type: whip }
    - { at: { beat: b8, offsetSec: 0 }, type: whip }
    - { at: { beat: b8, offsetSec: 8 }, type: whip }
audio:
  bgm:
    present: true
    character: 明るく軽いループ曲。中くらいのテンポで、文字を読む邪魔をしない（参照は聞いていない。作る側の指定）
    entersAt: { beat: b1, offsetSec: 0 }
  sfx:
    - { cue: card-in, type: レスの札が入るたびの短く軽いポップ音 }
    - { cue: cut, type: ページが横に滑るときの短い風切り音 }
    - { cue: payoff, at: { beat: b8, offsetSec: 7 }, type: 落ちの大きな札に合わせた低い打撃音 }
  voice: none
  referenceAudioUsed: false
routes:
  - id: code-motion
    default: true
    container: hyperframes
    needs: [none]
    paidApi: false
    talkingHead: false
    costUsdPerVideo: { min: 0, max: 0, basis: HyperFrames でローカルに描画して書き出す。ページの画像も HTML と CSS で描く。エージェントのトークン代は別 }
    status: design-only
  - id: screen-recording
    default: false
    container: hyperframes
    needs: [screen-capture]
    paidApi: false
    talkingHead: false
    costUsdPerVideo: { min: 0, max: 0, basis: 自分のアプリ画面の静止画か短い録画をページの画像に使い、HyperFrames でローカルに書き出す }
    status: design-only
  - id: image-gen-stills
    default: false
    container: hyperframes
    needs: [image-gen]
    paidApi: true
    talkingHead: false
    costUsdPerVideo: { min: 0.27, max: 0.77, basis: "ページの画像 8 枚を画像生成で作る。Nano Banana 2.1 の 9:16 1K が 1 枚 $0.0336、FLUX 3 Image の 1K が $0.048（routes.md）。8 枚で $0.27〜0.38、作り直しを 1 回ずつ見込んで上限 $0.77", asOf: 2026-10-25 }
    status: design-only
fonts:
  - { family: M PLUS Rounded 1c, license: OFL-1.1, source: "https://fonts.google.com/specimen/M+PLUS+Rounded+1c" }
  - { family: Noto Sans JP, license: OFL-1.1, source: "https://fonts.google.com/noto/specimen/Noto+Sans+JP" }
rights:
  makerSupplies:
    - 自分で書いた創作スレの台本（スレタイ、レス、落ち）
    - 各ページの画像（自分のアプリの画面、自分で撮った写真、コードで描いた図のどれか）
    - 動画内で使う許諾が記録された BGM ファイル
    - 動画内で使う許諾が記録された効果音ファイル（CC0、またはクレジットを残す CC BY）
  neverUse:
    - 参照動画の映像、音、テロップの文言
    - 実在のスレやまとめサイトのスレタイとレスの本文
    - 他人の記事、報道写真、ニュースサイトのグラフのスクリーンショット
    - 実在の大学、教員、学生を特定できる名前と写真
    - 実在しない引用元を本物らしく見せる URL の表記
    - 掲示板の公式の投稿や転載に見える表記
evidence:
  measured: []
  inferred:
    - format.fps
    - format.durationSec
    - format.safeArea
    - hook.type
    - hook.firstFrameHasText
    - beats
    - captions.c1.font
    - captions.c1.capHeightRatio
    - captions.c1.color
    - captions.c1.plate
    - captions.c1.position
    - captions.c1.linesMax
    - captions.c1.charsPerCard
    - captions.c1.motionIn
    - captions.c1.motionOut
    - captions.c1.minHoldSec
    - captions.c2.font
    - captions.c2.capHeightRatio
    - captions.c2.color
    - captions.c2.plate
    - captions.c2.position
    - captions.c2.linesMax
    - captions.c2.charsPerCard
    - captions.c2.motionIn
    - captions.c2.motionOut
    - captions.c2.hide
    - captions.c2.minHoldSec
    - captions.c3.font
    - captions.c3.capHeightRatio
    - captions.c3.color
    - captions.c3.position
    - captions.c3.linesMax
    - captions.c3.charsPerCard
    - captions.c3.motionIn
    - captions.c3.minHoldSec
    - captions.c4.capHeightRatio
    - captions.c4.color
    - captions.c4.position
    - captions.c4.linesMax
    - camera.moves
    - camera.transitions
    - audio.bgm.present
    - audio.bgm.character
    - audio.bgm.entersAt
    - audio.sfx
    - audio.voice
    - routes
  unmeasured:
    - captions.c2.position.cx
    - captions.c2.position.cy
    - captions.c3.position.cy
    - captions.c4.position.cx
    - captions.c4.minHoldSec
---

# 2ch スレ風の文字読み（大学ネタ）

この型は手書きである。参照は 2026-08〜10 に公開された日本語の YouTube Shorts 4 本（掲示板のスレ読み、59〜70 秒、公開ページの表示で約 36 万〜175 万回）。動画は再生もダウンロードもしていない。見たのは公開ページの HTML、ストーリーボード画像（1 秒 1 コマ、101×180 px）、1080×1920 の自動サムネイル静止画 6 枚（2 本ぶん、各 3 枚）だけ。秒は大学ネタの 1 本（70 秒）のストーリーボードで読んだ。元のスレタイ、レス、曲、チャンネル名、URL はこのファイルに書かない。

## 構成と尺

尺は 59〜70 秒。4 本とも 1 分前後で、ショートとしては長い。レスを 20 枚前後読ませるので、短くすると読み切れない。長さそのものが総再生時間を稼ぐ。

ページは 8 枚（b1〜b8）。ページごとに背景の上の画像が一枚替わり、その上にレスの札が 1〜4 枚積まれる。ページが替わると札は全部消える。ページの長さは 5〜11 秒。人は映らず、喋る人もいない。カメラの動きは無く、変化はページの切り替えと札の追加だけ。

書き出しは 30 fps にする。参照の公開ページは 1080p60 の形式を持っていたが、静止した札と横スライドだけなら 30 fps で足りる。

## フック

最初のフレームからスレタイの札（c1）が出ている。上に【画像】のような角括弧のタグ、続けて出来事と「〜した結果」型の言い回しで、答えを伏せる。画面中段には話の舞台の写真が一枚。6 秒間、何も足さずにスレタイを読ませる。

ZuruNote ではタグを【創作】にする。創作だと最初に明かすことと、スレの見た目を保つことが両立する。

## ビート

- b1（0〜6 秒）フック。スレタイ一枚と舞台の画像。
- b2（6〜11 秒）前提。スレ主の 3 行のレスが一枚だけ出て、根拠らしい画面（記事風の画面や表）が背景に入る。長いレスをここで一度読ませると、見る人が「読むモード」に入る。
- b3（11〜22 秒）最初の反応が 4 枚。疑い、驚き、ツッコミ。2〜3 秒おきに一枚。
- b4（22〜31 秒）同じ画面の寄りに替えて、細部に気づく反応を 3 枚。
- b5（31〜40 秒）根拠の画面に戻り、事情を知る住人のレスで話を一段深くする。3 枚。
- b6（40〜50 秒）転。予想を裏切る数字か事実が出て、反応が 3 枚。
- b7（50〜61 秒）向きが変わったあとの反応が 4 枚。
- b8（61〜70 秒）落ち。普通の札が 3 枚積まれたあと、68 秒前後に大きな赤字の札（c3）が横から入って終わりまで残る。69 秒台で画面ごと横に滑り、参照の 1 本は頭と同じ画像に戻って終わる。ループして見え直す作り。

レスの札は全部で 22 枚前後（スレタイを除く）。次へ進ませる仕掛けは二つ。札がいつ足されるか分からないこと、ページが替わると画像が替わること。

## テロップ

層は 4 つ。札の文字は塗りの色だけで、文字の縁も影も無い。札そのものが白い座布団で、縁取りを持つ。

**c1 スレタイ（headline）**。b1 だけ。丸みのある極太ゴシック、横書き、中央揃え。一行の文字の高さは画面高の 0.039〜0.040。白い札に、文字と同じ色の枠（1080 幅で約 13 px）。色は青紫（#430BEE 前後）。札の中心は画面の上から 0.22、横は中央。3〜4 行、一枚 30〜45 字。最初のフレームから出ていて、b1 の終わりで画面ごと横に滑って消える。

make ではこの層を見出しの帯（`sasaru-principle-captions-read-as-headlines`、白い芯 0.04 以上）に上げる。0.057 まで上げると一行は 9 字前後になるので、スレタイは 25 字以内に縮めて 3 行に収める。上げたことは制作記録に書く。

**c2 レス（subtitle）**。b2〜b8。丸みのある極太ゴシック、横書き、札の中は左揃え。一行の文字の高さは画面高の 0.031〜0.038（読んだ 23 行の中央値は 0.034）。白い札に黒い枠（約 10 px）。1〜3 行、一枚 4〜40 字、一行は最大 16 字前後。

色は札ごとに替わる。読んだ 15 枚で、紺、青、青紫、くすんだ青、緑、黄緑、橙、赤、えんじ、赤紫の 10 色前後を回していた。掲示板の ID ごとの色分けに見せる作り。make では 6〜8 色を決めて順に回し、同じ色を続けない。フロントマターの `color` は基準の紺。

札の位置は上から順に積む。左端から始まる札（左端 0.02〜0.03）と、右に寄せた札（左端 0.11〜0.23、右端 0.97〜0.99）が交互に出る。ページの上半分が埋まると、画像の下の段に積む。縦の位置は札の数と行数で決まるので、定数にしない。

レス番号、名前欄、ID、日時の行は出さない（4 本とも、読めた範囲で本文だけ）。見る人が読むのは本文だけで、番号を足すと一行ぶん小さくなる。アンカー（>>）も使わない。

出し方は横から滑り込む。札が画面の左端で切れた静止画が 2 本の参照に 1 枚ずつあった。スキーマの語彙に横スライドが無いので `other` と書いた。0.3 秒前後で入れ、入るたびに c2 の効果音を鳴らす。消えるのはページの切り替え（`hide: beat-end`）で、ページごと横に滑って出る。札の出る間隔は 2〜3 秒が多く、最短の表示は 2 秒前後（ページの終わり近くに出た札）。

**c3 落ち（headline）**。b8 の最後の一枚。c2 と同じ札の形で、文字が大きい（一行の高さは画面高の 0.048〜0.049）。赤（#E90621 前後）、黒枠、2 行、一枚 14〜20 字。横は中央で、縦は画像の下の段。c2 の中に大小を混ぜず、別の層にした。落ちだけを大きくして、読む流れの終点を目で分からせる。出たら終わりまで残す（`sasaru-principle-last-card-holds`）。

**c4 下の注記（label）**。全編。小さな字（一行の高さは画面高の 0.018〜0.024）で、画面のいちばん下に 2 行、左揃え。色は灰色がかった紺（#384459 前後）。参照は画像の引用元を書いていた。ZuruNote では「※創作スレです。実在の人物・団体とは関係ありません」をここに置く。この帯はプラットフォームの UI に隠れやすいので、同じ文を投稿の説明欄にも書く。

背景は全面の模様。参照の 1 系統は薄い水色（#B6D3FF 前後）に白い水玉と、上端の白い波。ほかの 2 系統は放射状の集中線（水色か橙）。札と画像はこの上に載る。画像は横幅いっぱいの帯で、画面の中段に置く（目視で上から 0.3〜0.7 前後）。

安全域は、参照の札が実際に使った範囲を書いた（上 0.04、下 0.12、左右 0.01〜0.02）。右下の札は Shorts のボタンと重なるが、参照もそうしていた。c4 だけは下の安全域の中に置く。

## カメラとトランジションとズーム

カメラは全ビートで静止。ズームは無い。b4 の寄りは画像を差し替えて見せ、カメラでは寄らない。

切り替えはページの頭（b2〜b8 の 0 秒）と、b8 の 8 秒（69 秒前後）。画面ごと横に滑る。ページの途中で札と画像が横にずれた静止画を、2 本で確かめた。スキーマの語彙には横スライドが無いので、いちばん近い `whip` と書いた。動きの長さは 1 秒 1 コマの絵では測れないので、0.3〜0.4 秒で作る。

## BGM と効果音

BGM は入る。参照 4 本のうち 3 本は概要欄に楽曲の提供元の表記があった。曲は聞いていない。作るときは明るく軽いループ曲を最初から最後まで流す。声が無いので、下げる処理は無い。

効果音は、札が入るたびの短いポップ音、ページが滑るときの風切り音、落ちの札の打撃音の 3 種。参照 1 本の概要欄に効果音サイトの表記があった。どこで鳴っていたかは聞いていないので、この 3 種は作る側の指定である。

読み上げは無しにする。参照 4 本とも、公開ページに日本語の自動字幕の枠があった。何かの声か歌が入っている可能性はある。ただ中身は取得できず、合成音声で読んでいるかは確かめていない。この型は文字を目で読ませる型として作る。合成音声で読ませたいときは、`tts` を `needs` に持つルートを別に足す（この版には書かない）。

## なぜ伸びるか

以下は推論である。

止まる理由。最初のフレームにスレタイがあり、「〜した結果」で答えを伏せる。掲示板の見た目は、それだけで「本音の反応が読める」と期待させる。大学、テスト、AI の話題は、参照の大学ネタ 2 本が 8〜10 月に数十万回出ている。

最後まで見る理由。札が 2〜3 秒おきに一枚ずつ足されるので、読み終わる前に次が来る。ページが替わるたびに画像も替わる。落ちが最後の大きな札だと分かっているので、そこまで見ないと話が閉じない。

もう一度見る理由。60 秒で 20 枚以上の札は一度で読み切りにくい。終わりが頭の画像へ滑って戻るので、ループに入っても切れ目に気づきにくい。

伸びない側に落ちない理由。創作だと分かる表示がないと、実在スレの転載や作り話として叩かれる。スレタイの【創作】と下の注記で最初から明かす。アプリの宣伝を全部のレスに入れると、スレの見た目が崩れて広告に見える。アプリを出すのは 2〜3 枚だけにする。講義の録音は大学や教員によって禁止されている。録音してよい講義の話として書き、無断の録音を勧めない。YouTube は量産・テンプレ型の動画を収益化の対象外にしている（trends.md）。話を毎回書き下ろす。

## 差し替える場所

変えるのはスレタイ、レスの文、ページの画像、札の色の並び。変えないのは、ページ 8 枚の並び（前提 → 反応 → 寄り → 事情 → 転 → 反応 → 落ち）、b2 の長い一レス、札を積んでページごとに消すこと、落ちだけ大きな赤い札にすること、最後の札を残して頭へ滑らせること。

- b1: 【創作】タグ付きのスレタイ。舞台の画像は、自分で撮った大学の写真かコードで描いた図。
- b2: スレ主が何を見たかを 3 行で。背景は根拠になる画面（自分のアプリの画面か、コードで描いた表）。
- b3〜b5: 反応レス。疑う、驚く、事情を知る住人、自分語り。
- b6: 予想を裏切る一点。数字だと強い。
- b7: 手のひら返しと納得。
- b8: 落ちの一句（c3）。14〜20 字。

**ZuruNote の差し替え例**（創作。数字は作り話として書く）

- b1 スレタイ: 「【創作】講義を全部録音してたヤツ、期末前日に無双する」（25 字）。画像は空いた講義室の写真（自分で撮る）。
- b2 スレ主: 「同じ学科のやつ、毎回スマホを机に置いてるなと思ってたら講義を録音してたらしい。しかもノートが勝手にできてるとか言ってる」。背景はスマホが机に置かれた図。
- b3: 「録音って先生の許可いるやつでは」「うちの講義は初回に録音OKの説明あったぞ」「ノートが勝手にできるってどういうことや」「90分ずっと板書写してたワイは何やったんや」
- b4: 背景を ZuruNote のノート画面の寄りに替える。「見せてもらったら見出しと要点に分かれてた」「先生が口で言っただけのところまで入っとる」「板書に無い話がいちばんテストに出るんよな」
- b5: 「録音からAIがノートにするアプリあるんよ」「学生向けのやつ最近増えとるな」「ノート取らずに先生の話だけ聞いてたらしい」
- b6: 「そいつ先週休んだ回のノートもあった」「休んだのに誰より詳しいの意味わからん」「代わりに録音頼まれてたのワイやった」
- b7: 「ワイが頼まれて録ってたのか」「じゃあワイもノート持っとるはずやん」「アプリ入れてなかったから音だけ残っとる」「三時間ぶんの音声を今から聞くのか」
- b8: 普通の札「明日の朝までに聞き終わらんやろ」「倍速でもきつい」、最後に c3「録ったのに入れてなかったのワイだけ」。
- c4: 「※創作スレです。実在の人物・団体とは関係ありません」。

アプリの名前は出さず、使い方を反応の中で見せる。名前と導線は投稿の説明欄に書く。録音は許可された講義の話にしている（b3）。レスに書くアプリの働きは「録音から講義ノートができる」までにとどめ、確かめていない機能を足さない。

## 制作ルート

### code-motion

全部を Claude Code だけで作れる。ページの画像もコードで描く（記事風の画面、表、スマホの図、ノートの図）。有料の API は呼ばない。

1. 台本を JSON にする。ビートごとにページの画像の指定と、札の配列（層、文、色、出る秒、左寄せか右寄せか）を書く。秒は参照の尺 70 秒の上で書き、尺を変えるときは同じ比で伸び縮みさせる。
2. HyperFrames のプロジェクトを作る: `HYPERFRAMES_SKIP_SKILLS=1 npx -y hyperframes init cut --example blank --resolution portrait --non-interactive`
3. `index.html` に背景の模様、画像の帯、札の部品を書く。札は白地、枠、角丸なし、左右の位置を交互に。フォントは CSS の font-face 規則で宣言する（宣言しないと lint が止める）。GSAP のタイムラインで札の横スライドとページの横スライドを入れる。`Math.random()` と `Date.now()` は使わない。
4. 音は `<audio>` を 3 本置く。BGM、札のポップ音、ページの風切り音と落ちの打撃音。参照の音は使わない。
5. 検査する: `npx hyperframes lint --json`、`npx hyperframes check --json --caption-zone "x0=0;y0=0.04;x1=1;y1=0.88"`、`npx hyperframes snapshot --at 1,8,20,45,68,69.9`
6. 書き出す: `npx hyperframes render --fps 30 --resolution portrait --quality delivery -o renders/cut.mp4`
7. `sasaru/cuts/<cut-id>/cut.json` に、playbook の id、ルート、BGM と効果音のファイルとライセンス、札の JSON、c1 の大きさを上げたことを書き、gate のカット検査にかける。

### screen-recording

ページの画像に、自分のアプリの画面を使う。ZuruNote のノート画面を見せるならこちら。

1. アプリで、録音から出来たノートの画面を静止画か数秒の録画で撮る。他人の名前、本物の講義名、通知は写さない。
2. code-motion の 1〜3 と同じ手順で組み、b2、b4、b5 の画像の帯にその画面を入れる。寄りは画像の切り抜きで作る。
3. code-motion の 4〜7 と同じ。録画を使うときは `npx hyperframes render --video-frame-format png` で画面の文字を潰さない。

### image-gen-stills

舞台の写真や挿絵を画像生成で作る。字が主役の型なので、無くても作れる。

1. ページ 8 枚の画像の指示文を書く。画像の中に字を入れさせない（日本語の文字はどのモデルも精度を保証していない。routes.md）。実在の大学の建物や人物を指示しない。
2. 見積もりを出して止まる。8 枚、モデル、1 枚の単価、作り直しの上限を書き、承認を待つ（`sasaru-principle-quote-before-you-spend`）。
3. 承認のあとに生成し、出力ファイルを保存する。同じ指示文でも同じ絵は返らないので、ファイルを使い回す。
4. code-motion の 2〜7 と同じ手順で組む。

## 編集の器とフォント

器は HyperFrames（v0.8.196、Apache 2.0）。札とページを HTML と CSS で組めて、レンダーごとの料金も会社規模の条件も無い。同じ composition なら同じ動画が出る。マシンをまたいで揃えるなら `render --docker` を使う。Remotion でも作れるが、従業員 4 人以上の営利組織は会社ライセンスが要る。

フォントは M PLUS Rounded 1c（OFL-1.1、Google Fonts、100〜900、日本語を収録）。参照の文字は丸みのある極太ゴシックに見えたので、800 を札に、500 を注記に使う。丸みが合わなければ Noto Sans JP（OFL-1.1、可変 100〜900）の 800 にする。どちらも OFL なので商用に使える。フォントのファイルはリポジトリに入れない。

## 素材の権利

作る人が用意するもの。自分で書いた創作スレの台本、各ページの画像（自分のアプリ画面、自分で撮った写真、コードで描いた図）、BGM と効果音のファイルとライセンスの記録。

BGM と効果音は、3 つのプラットフォームに同じ動画を出すなら外部の素材を焼き込む（assets.md）。リポジトリに入れてよいのは CC0（Kenney、Freesound の CC0、OpenGameArt の CC0）と OtoLogic（CC BY 4.0、クレジットを残す）だけ。ポップ音、風切り音、打撃音はどれもこの範囲で揃う。効果音ラボ、小森平、OpenTracks、甘茶は焼き込みには使えるが、ファイルはリポジトリの外に置く。

使ってはいけないもの。参照動画の映像、音、テロップの文言。実在のスレやまとめサイトの本文。他人の記事、報道写真、ニュースのグラフのスクリーンショット（参照はこれを背景にしていたが、作るときは使わない）。実在の大学、教員、学生を特定できる名前と写真。実在しない引用元を本物らしく見せる URL。掲示板の公式の投稿や転載に見える表記。挿絵サイトの素材は、商用の枚数制限などの条件を確かめてから使う。

## 費用の目安

- code-motion: 書き出しは 0 円。かかるのはエージェントのトークン代だけで、routes.md の推測では、Opus 5.5 を API で使うと初回が 1 本 1〜4 ドル、2 本目からは台本と画像の差し替えなので下がる。Pro か Max の契約なら追加の費用は無い（利用枠は減る）。
- screen-recording: code-motion と同じ。画面を撮る手間だけが増える。
- image-gen-stills: 画像 8 枚で 0.27〜0.38 ドル（Nano Banana 2.1 の 9:16 1K が 1 枚 0.0336 ドル、FLUX 3 Image の 1K が 0.048 ドル。2026-10-25 の公開価格）。1 枚ずつ作り直す上限を入れて 0.77 ドル。見積もりを出して承認を取ってから呼ぶ。
- 読み上げを足す場合（この版のルートには無い）: Gemini 3.8 Flash TTS は 1 秒 0.000225 ドルなので、70 秒で約 0.016 ドル（routes.md の値からの計算）。呼んでいない。

## 測ったことと推論

`evidence.measured` は空。参照の動画ファイルを取り込んでいないので、ここにある数は全部 `inferred` である。

**スクリプトで画素を数えたもの**（参照の動画ではなく、公開の自動サムネイル。2 本ぶん、1080×1920 の静止画 6 枚）

- 札の文字の高さ。札の内側で「彩度が高いか暗い画素」が 2 個を超える行を数え、行のまとまりの高さを画面高 1920 で割った。外接箱の高さで、白い芯ではなく色の付いた字の高さ。c1 は 74〜77 px（3 行）、c2 は 59〜72 px（23 行、中央値 66 px）、c3 は 93〜95 px（2 行）、c4 は 34〜46 px（6 行）。
- 札の枠。暗い画素（各色の最大値 120 未満）が 300 px 以上横に続く行を枠とみなした。c2 と c3 の枠は 9〜10 px の黒。c1 の枠は文字と同じ青紫で 13 px。札の左右の端もここから取った。
- 色。札の内側の彩度の高い画素の中央値。JPEG なので数値は前後する。
- c1 の札の中心（0.50、0.223）、c4 の行の位置（下から 2 行、中心 0.967）、背景の水色。

**目で見たもの**（ストーリーボード 1 秒 1 コマ、101×180 px。大学ネタの 70 秒の 1 本を主に、4 本とも）

- ビートの秒（ページの切り替え、±1 秒）、札の枚数と出る秒、最短の表示 2 秒、スレタイの 6 秒。
- 札とページの横スライド。左端で切れた札の静止画 2 枚と、ページの途中でずれた静止画から。動きの長さは測れない。
- 字数。読めた札の字を数えた（c1 は 30〜45 字、c2 は 4〜40 字、c3 は 14〜20 字）。文言はここに写さない。
- 書体の分類（丸みのある極太ゴシック）、背景の模様、画像の帯の位置。
- 公開ページの HTML から: 尺（59〜70 秒）、形式の一覧（最大 1080p60）、概要欄の楽曲と効果音の表記の有無、日本語の自動字幕の枠の有無。

**作る側が決めたもの**: fps 30、効果音の 3 種と鳴らす場所、BGM の気分、読み上げ無し、札の色の数、ページの横スライドを 0.3〜0.4 秒にすること、ルートと器とフォント。

**測っていないもの**: 音（BGM の音量、声の有無、効果音の位置）。c2 と c3 の札の位置は札ごとに替わるので一つの値にしていない。動画ファイルを取り込んで `caption_boxes.py`、`camera_motion.py`、`audio_events.py` で測れば `status: measured` に上げられる。
