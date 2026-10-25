---
schema: sasaru-playbook/1
id: plan-vs-reality-before-after
name: 計画 vs 現実／ノートのビフォーアフター
status: draft
summary: 上に比較の見出しを出したまま、計画どおりの絵を崩れた現実で裏切り、変化の直前で一回切ってアフターの画面で救う。最後は前と後を並べて止める。
tags: [before-after, plan-vs-reality, comparison, no-speech, hands-only, screen-recording, study]
fitsContent:
  - アプリやツールを使う前と後の比較
  - ノートの取り方や勉強法の改善
  - 計画が崩れる学生生活のあるある
  - 製品の効果を一画面で見せたいもの
source:
  kind: hand-written
  platform: youtube-shorts
  rightsTier: none
  measuredFiles: 0
format:
  aspect: "9:16"
  fps: 30
  durationSec: { min: 10, max: 25, reference: 16 }
  onCamera: hands
  speech: none
  safeArea: { top: 0.11, bottom: 0.25, left: 0.03, right: 0.18 }
hook:
  type: before-after
  firstFrameHasText: true
beats:
  - { id: b1, role: hook, tIn: 0.0, tOut: 1.2, purpose: 比較の見出しと「計画」のラベルで、このあと崩れると予告する, swap: 自分の題材の見出しと、計画どおりの最初の絵 }
  - { id: b2, role: setup, tIn: 1.2, tOut: 4.5, purpose: 理想の状態を見せ、裏切られる前提を作る, swap: 計画どおりに始めた手元の絵と、その意気込みの一句 }
  - { id: b3, role: turn, tIn: 4.5, tOut: 8.5, purpose: ラベルの色を変えて現実に落とし、見る人に自分のことだと思わせる, swap: 崩れた現物（散らかったノート、空白、消し跡）を手持ちで見せる絵と、本音の一句 }
  - { id: b4, role: payoff, tIn: 8.5, tOut: 14.0, purpose: 同じ構図のまま切り替え、アフターの画面で救う, swap: 自分の製品や方法で出来た結果の画面と、何がそうしたかの一句 }
  - { id: b5, role: loop, tIn: 14.0, tOut: 16.0, purpose: 前と後を左右に並べて止め、見比べるためにもう一周させる, swap: b3 の最後の絵と b4 の最後の絵 }
captions:
  - id: c1
    role: headline
    beats: []
    unit: card
    writingMode: horizontal
    font: { class: extra-bold-gothic, weight: 900 }
    capHeightRatio: 0.056
    emphasis: { scale: null, color: "#FFD400" }
    color: "#FFFFFF"
    stroke: { color: "#000000", px1080: 8 }
    shadow: true
    plate: none
    position: { cx: 0.5, cy: 0.16, align: center }
    linesMax: 2
    charsPerCard: { min: 6, max: 16 }
    motionIn: cut
    motionOut: cut
    show: beat-start
    leadSec: null
    hide: next-card
    minHoldSec: null
    lastCard: hold-to-end
  - id: c2
    role: label
    beats: []
    unit: card
    writingMode: horizontal
    font: { class: bold-gothic, weight: 800 }
    capHeightRatio: null
    emphasis: null
    color: "#FFFFFF"
    stroke: null
    shadow: false
    plate: pill
    position: { cx: 0.5, cy: 0.25, align: center }
    linesMax: 1
    charsPerCard: { min: 2, max: 12 }
    motionIn: pop
    motionOut: cut
    show: beat-start
    leadSec: null
    hide: next-card
    minHoldSec: null
    lastCard: hold-to-end
  - id: c3
    role: subtitle
    beats: [b2, b3, b4]
    unit: phrase
    writingMode: horizontal
    font: { class: rounded, weight: 800 }
    capHeightRatio: null
    emphasis: null
    color: "#111111"
    stroke: null
    shadow: false
    plate: box
    position: { cx: 0.5, cy: 0.33, align: center }
    linesMax: 2
    charsPerCard: { min: 6, max: 14 }
    motionIn: pop
    motionOut: cut
    show: onset
    leadSec: null
    hide: next-card
    minHoldSec: 1.0
    lastCard: phrase-end
camera:
  moves:
    - { beat: b1, move: static }
    - { beat: b2, move: static }
    - { beat: b3, move: handheld }
    - { beat: b4, move: static }
    - { beat: b5, move: static }
  zooms:
    - { at: { beat: b4, offsetSec: 2.0 }, scaleFrom: 1.0, scaleTo: 1.3, durSec: 0.6, easing: ease-in-out }
    - { at: { beat: b5, offsetSec: 0.0 }, scaleFrom: 1.15, scaleTo: 1.0, durSec: 0.4, easing: ease-out }
  transitions:
    - { at: { beat: b3, offsetSec: 0.0 }, type: hard-cut }
    - { at: { beat: b4, offsetSec: 0.0 }, type: match-cut }
    - { at: { beat: b4, offsetSec: 0.8 }, type: zoom-cut }
    - { at: { beat: b5, offsetSec: 0.0 }, type: hard-cut }
audio:
  bgm:
    present: true
    character: 明るく跳ねるポップかローファイ。テンポは BPM 100〜125 くらい。b3 の頭で半拍ほど止めるかこもらせ、b4 の頭で元に戻す
    entersAt: { beat: b1, offsetSec: 0 }
    duckUnderVoice: null
    levelDbUnderVoice: null
  sfx:
    - { "on": cut, at: { beat: b3, offsetSec: 0.0 }, type: 短いレコードスクラッチか、低いブザー }
    - { "on": cut, at: { beat: b4, offsetSec: 0.0 }, type: 風切り（シュッ） }
    - { "on": payoff, at: { beat: b4, offsetSec: 2.0 }, type: きらめき（キラーン） }
    - { "on": card-in, type: 軽いポップ（ポン）。ほかの効果音と同じフレームなら鳴らさない }
  voice: none
  referenceAudioUsed: false
routes:
  - id: screen-recording
    default: true
    container: hyperframes
    needs: [screen-capture, own-footage]
    paidApi: false
    talkingHead: false
    costUsdPerVideo: { min: 0, max: 0, basis: 前は自分で撮った手元、後は実機の画面録画。HyperFrames と FFmpeg はローカルで描画して無料。エージェントのトークン代は含めない }
    status: design-only
  - id: code-motion
    default: false
    container: hyperframes
    needs: [none]
    paidApi: false
    talkingHead: false
    costUsdPerVideo: { min: 0, max: 0, basis: 前も後も HTML と CSS で描く。ローカルで描画して無料。エージェントのトークン代は含めない }
    status: design-only
  - id: image-gen-stills
    default: false
    container: hyperframes
    needs: [image-gen, screen-capture]
    paidApi: true
    talkingHead: false
    costUsdPerVideo: { min: 0.10, max: 0.30, basis: 前の静止画 3〜6 枚を gemini-nano-banana-2.1 で作る。公式料金の 1K 画像 0.0336 ドル × 3 枚から、2K 画像 0.0504 ドル × 6 枚まで。後は実機の画面録画で無料。作り直しは含めない, asOf: "2026-10-25" }
    status: design-only
fonts:
  - { family: Noto Sans JP, license: OFL-1.1, source: "https://fonts.google.com/specimen/Noto+Sans+JP" }
  - { family: M PLUS Rounded 1c, license: OFL-1.1, source: "https://fonts.google.com/specimen/M+PLUS+Rounded+1c" }
  - { family: Yomogi, license: OFL-1.1, source: "https://fonts.google.com/specimen/Yomogi" }
rights:
  makerSupplies:
    - 自分のノートを自分の手だけで撮った映像
    - 自分のアカウントで撮った実機の画面録画（通知と個人名を消したもの）
    - 録音してよいと確かめた講義の録音と、そこから生成したノート
    - 再配布か動画内利用の許諾が記録された BGM ファイル
    - ライセンスを記録した効果音ファイル（CC0 か、クレジットを残す CC BY）
  neverUse:
    - 参照動画の映像、音、テロップの文言
    - 他人が作ったミーム素材やキャラクターの切り抜き
    - 他人のノート、顔、名前が映る絵
    - 講義のスライドや板書を写しただけの画面を、読める大きさで長く映すこと
    - 画面録画に入った講義の音声
    - 実機に無い画面や機能を作り込んだアフター
evidence:
  measured: []
  inferred:
    - format.fps
    - format.durationSec
    - format.safeArea
    - hook.type
    - beats
    - captions.c1.capHeightRatio
    - captions.c1.stroke
    - captions.c1.position.cy
    - captions.c1.charsPerCard
    - captions.c2.position.cy
    - captions.c2.charsPerCard
    - captions.c3.position.cy
    - captions.c3.charsPerCard
    - captions.c3.minHoldSec
    - camera.moves
    - camera.zooms
    - camera.transitions
    - audio.bgm.character
    - audio.sfx
    - routes.image-gen-stills.costUsdPerVideo
  unmeasured:
    - captions.c1.minHoldSec
    - captions.c2.capHeightRatio
    - captions.c2.minHoldSec
    - captions.c3.capHeightRatio
    - audio.bgm.duckUnderVoice
    - audio.bgm.levelDbUnderVoice
---

# 計画 vs 現実／ノートのビフォーアフター

## 構成と尺

参照の尺は 16 秒で、10〜25 秒の帯で作る。並びは、フック（計画の予告）、計画、現実、アフター、前後の並べ止め、の五つ。

- 期待 vs 現実の型は、Postdom の 2026 年 10 月号（9 月の TikTok 上位 559 投稿）で 8 投稿、長さの中央値 18.6 秒。帯の中心をここに置いた。記事は 10 投稿未満の型に、引用の前に読むようにと注意書きを付けている。
- 見た参照は 10〜42 秒。10 秒の一本は、ほぼ真ん中で前と後が入れ替わっていた。
- アフターの頭（b4）を全体の 53% に置く。前半で離れる人にも、半分を過ぎたあたりで答えの画面が見える位置である。
- カットは四つ。現実へのハードカット、アフターへのマッチカット、画面録画への寄りのカット、並べ止めへのハードカット。見た参照の長い版は 2〜3 秒ごとに切っていたが、この型の芯は「切り替えが一回だけ効く」ことなので、前と後の間は一回で切る。

## フック

最初のフレームから、上に比較の見出し（c1）と、ラベル「計画」（c2）を出す。絵は計画どおりの最初の一枚で、まだ何も崩れていない。見出しが「比べる」と言っているので、見る人はこの綺麗な絵がこのあと崩れると分かったうえで待つ。フックの種類は `before-after`。アフターを先に見せる変形もあるが、この型では計画を先に置き、裏切りを b3 に取っておく。

## ビート

- **b1 hook（0.0〜1.2 秒）** 見出しとラベルだけで約束する。絵は b2 と同じ撮影の頭で、切らずに b2 へつなぐ。
- **b2 setup（1.2〜4.5 秒）** 理想の状態。固定の真上撮りで、手が計画どおりに動く。字幕（c3）で意気込みを一句。見る人に「こうはならない」と思わせる時間。
- **b3 turn（4.5〜8.5 秒）** ハードカットと効果音で現実に落とす。ラベルは同じ位置のまま、座布団を赤に変えて「現実」にする。見た参照の一本でも、段階ラベルの色が変わる秒が流れの折り返しだった。絵は手持ちで少し揺らし、散らかった現物をめくって見せる。本音の一句で、見る人の経験に寄せる。
- **b4 payoff（8.5〜14.0 秒）** b3 と同じ構図・同じ手の位置でマッチカットし、0.8 秒後に画面録画の全面へ寄りのカットで入る。2.0 秒で結果の要の部分に寄り、きらめきの効果音を合わせる。字幕で「何がそうしたか」を一句。
- **b5 loop（14.0〜16.0 秒）** 左に b3 の最後の絵、右に b4 の最後の絵を並べて止める。ラベルは前と後を並べた一枚にする。見比べたくなる絵で終わり、頭の綺麗な計画へ戻るのでもう一周する。

## テロップ

三層。どの層も横書き。参照の文言は使わない。

- **c1 headline（全ビート）** 極太ゴシック 900、白、黒の縁 8 px（1080 幅）、影あり、座布団なし。白い芯の高さは画面高の 0.056 を目安にする（原則 `sasaru-principle-captions-read-as-headlines` の地の句の帯）。位置は中央揃えで cy 0.16、上の安全域 0.11 のすぐ下。二段まで、一枚 6〜16 字。比べる二語（計画と現実など）だけを黄色 `#FFD400` にし、大きさは変えない。段の中で大小を混ぜないため。最初のフレームで出し、一枚のまま最後のフレームまで残す。日本語の参照 2 本は、上の見出しを最後まで出し続けていた。
- **c2 label（全ビート）** 太ゴシック 800、白字、丸い座布団（pill）。位置は cy 0.25。一段、一枚 2〜12 字。ビートの頭でポップして出し、次の一枚で置き換える。座布団の色で段階を示す。計画は青緑、現実は赤、アフターは製品の色、b5 は前と後の二語を一枚に並べる。座布団の色はスキーマに欄が無いので、ここに書く。最後の一枚（b5）は最後のフレームまで残す。
- **c3 subtitle（b2〜b4）** 丸ゴシック 800、黒に近い `#111111` の字を白の箱の座布団に載せる。位置は cy 0.33。二段まで、一枚 6〜14 字。句の頭で出し、次の句で消す。最短 1.0 秒は出す（設計書の「1.0 秒未満の表示は警告」に合わせた）。b5 では出さない。並べ止めの絵を字で隠さないため。

字は上の 0.11〜0.38 の帯に集める。真ん中から下（0.38〜0.75）はノートと画面に空け、下 0.25 はプラットフォームの UI に譲る。右 0.18 にも字を伸ばさない。

## カメラとトランジションとズーム

- 動き。b1、b2、b4、b5 は固定。b3 だけ手持ちで小さく揺らす。固定から揺れに変わることも、現実に落ちた合図になる。
- b3 の頭はハードカット。
- b4 の頭はマッチカット。b3 の最後と同じ三脚位置・同じ真上の構図で、ノートの上にスマホを置いた絵へ切る。手の位置を合わせると、ノートが画面に置き換わったように見える。
- b4 の 0.8 秒で、スマホの画面から画面録画の全面へ寄りのカット。
- b4 の 2.0 秒で 1.0 → 1.3 倍、0.6 秒、ease-in-out。結果の要（要約、見出し、用語の一覧など）に寄る。
- b5 の頭でハードカットして並べ止め。1.15 → 1.0 倍、0.4 秒、ease-out で少し引いて止める。

## BGM と効果音

- BGM は頭から入れる。明るく跳ねるポップかローファイで、BPM 100〜125 くらい。b3 の頭で半拍ほど止めるか、こもらせて現実の落差を音でも作り、b4 の頭で元に戻す。声が無いので、声との差の dB は該当なし。
- 効果音は四種類。b3 の頭に短いレコードスクラッチか低いブザー、b4 の頭に風切り、b4 の 2.0 秒の寄りにきらめき、ラベルの入れ替わりに軽いポップ。ポップがほかの効果音と同じフレームに重なるときは鳴らさない。
- 曲と効果音は、ライセンスを記録した別ファイルから入れる（原則 `sasaru-principle-sound-from-a-licensed-file`）。曲名は書かない。参照の音は使わない。

## なぜ伸びるか

推論である。

- **止まる理由**。最初のフレームの見出しが「比べる」と予告するので、続きの絵を待つ理由ができる。計画の綺麗な絵は、崩れることが分かっているから見ていられる。
- **最後まで見る理由**。b3 の現実は、見る人が自分の経験で知っている絵である。笑うか刺さるかしたところで、すぐに「じゃあどうするか」の答えが b4 に来る。答えは変化の直前の一回のカットで切り替わるので、その瞬間を見逃したくない。
- **もう一度見る理由**。b5 の並べ止めは、左右の差を細かく見比べたくなる。終わりの絵から頭の綺麗な計画に戻ると、皮肉としてもう一度読める。
- **小さいアカウントでも届く理由**。Postdom の同じ号で、期待 vs 現実の型はフォロワー比の中央値が 79.2 倍で、記事の型の中で一番高かった（8 投稿で、記事が注意書きを付けている型）。ビフォーアフター（Day 1 vs later）は 44 投稿で一番多く、再生数の中央値は 667,150 回。どちらも記事の数で、こちらでは確かめていない。
- **伸びない側に落ちない理由**。製品の操作だけを見せるデモは、見る人にとって自分の話にならない。この型は製品を「現実を救う答え」の数秒にだけ置くので、デモに見えにくい。逆に、アフターが長すぎたり、実機に無い画面を作り込んだりすると広告に見えて離れる。アフターは全体の 3 分の 1 くらいに抑え、実機の画面だけを使う。
- **置き換えで失うもの**。参照の人物版は、人の表情と身ぶりで現実の落差を伝えていた。この型は顔を使わないので、その分を手の動き（めくる、止まる、置く）、カメラの揺れ、ラベルの色、音の止めで補う。表情ほど強くないので、b3 の絵は「一目で散らかっていると分かる現物」にする。

## 差し替える場所

- **b1** 見出し（c1）の二段を自分の題材にする。比べる二語を黄色にする。絵は b2 の撮影の頭。
- **b2** 計画どおりに始めた手元の絵と、意気込みの一句（c3）。
- **b3** 崩れた現物を手持ちで見せる絵と、本音の一句。ラベル（c2）は「現実」にあたる語に替える。
- **b4** 自分の製品や方法で出来た結果の画面と、何がそうしたかの一句。ラベルはアフターにあたる語か製品名。
- **b5** b3 と b4 の最後の絵を左右に並べる。ラベルは前と後の二語を一枚に。

変えてはいけないもの。見出しを最後まで出し続けること。前と後の間を一回のカットで切ること。ラベルの位置を全ビートで動かさないこと。アフターが全体の半分を少し過ぎたところで始まること。最後に並べて止めること。人の顔と声を入れないこと。

**ZuruNote の差し替え例**

学生向けの講義録音と AI ノートのアプリ。前は手書きの散らかったノート、後は ZuruNote が生成したノートの実機画面。既定ルート（画面録画）で作る。テロップの文は例で、自分の言葉に替えてよい。

| ビート | 絵 | c1 見出し | c2 ラベル | c3 字幕 |
| --- | --- | --- | --- | --- |
| b1 | 真上から、新しいノートの一ページ目。手が日付と講義名をきれいに書き始める | 講義ノート／計画 vs 現実（二段。「計画」と「現実」を黄色） | 計画（青緑） | なし |
| b2 | 同じ撮影の続き。罫線に沿って丁寧に一行目、二行目を書く | 同じ | 計画 | 板書も話も全部書く |
| b3 | 手持ち。同じノートの数ページ後をめくる。途中で切れた行、矢印、空白、消し跡が続く | 同じ | 現実（赤） | 15分で追いつけない |
| b4 | b3 と同じ三脚位置で、ノートの上に置いたスマホへマッチカット。0.8 秒で画面録画の全面へ。録音済みの講義を開き、生成されたノートを上から下へスクロール。2.0 秒で要約の部分に 1.3 倍で寄る | 同じ | ZuruNote（製品の色） | 録音からノートが出来てた |
| b5 | 左に b3 の最後のページ、右に b4 の最後の画面を並べて止める | 同じ | Before ｜ After | なし |

撮る前に決めること。

- 講義の録音は、担当の教員と大学の決まりで許されている講義だけにする。
- 画面録画は機内モードかおやすみモードで撮り、通知を出さない。生成ノートに出る教員や学生の名前、講義の固有の資料はぼかすか、自分で作った練習用の講義に差し替える。
- 画面録画の音は消す（講義の声を入れない）。
- 生成ノートは実際に出た画面をそのまま使う。精度や時間の数字を画面に足さない。

## 制作ルート

### screen-recording

前は自分の手元の撮影、後は実機の画面録画。ZuruNote の既定。

1. 三脚でスマホかカメラを真上に固定し、9:16、30fps で撮る。b1〜b2 の「計画」を一本、同じ位置のまま b3 用の散らかったページを手持ちで一本、最後に同じ三脚位置でノートの上にスマホを置いた絵を一本撮る。顔と他人のノートを画角に入れない。
2. 実機で画面録画を撮る（iOS はコントロールセンターの画面収録、Android は標準の画面録画）。講義の一覧からノートを開き、ゆっくりスクロールする。5〜8 秒あれば足りる。
3. 画面録画の音を外し、幅 1080 にそろえる。

   ```bash
   ffmpeg -i screen.mov -an -vf "scale=1080:-2,fps=30" -c:v libx264 -crf 18 -pix_fmt yuv420p after_screen.mp4
   ```

4. 台本を JSON にする。ビートごとの秒、c1〜c3 の文、c2 の座布団の色、効果音の秒。尺を 16 秒から変えるなら、ビートの秒と、ビートに付いたズームと効果音を同じ比で伸び縮みさせる（sasaru-make の手順）。
5. HyperFrames の縦の雛形を作る。

   ```bash
   npx hyperframes init plan-vs-reality --example blank --resolution portrait --non-interactive
   ```

6. `index.html` にクリップを置く。b1〜b2 の撮影、b3 の撮影、b4 のスマホの絵と `after_screen.mp4`、b5 の左右二分割。テロップの三層は HTML の要素で組み、書体は `@font-face` で宣言する。BGM と効果音は `<audio>` で別トラックに置く。
7. 書体の宣言漏れを止めてから、決めた秒の静止画で見た目を確かめる。

   ```bash
   npx hyperframes lint --json
   npx hyperframes snapshot --at 0.5,3.0,5.0,9.5,10.6,15.5
   ```

8. 書き出す。マシンをまたいで同じ画素にそろえたいときは `--docker` を足す。

   ```bash
   npx hyperframes render --fps 30 --output plan-vs-reality.mp4
   ```

9. sasaru-gate のカット検査を通す。

### code-motion

前も後もコードで描く。実機の画面が無い題材（勉強法そのものなど）か、撮影できない日の代わり。ZuruNote の実機の画面を描いて作ることはしない。製品の画面は実機の録画だけを使う。

1. 前のページを HTML で描く。罫線の紙の上に手書き風の書体（Yomogi）で途切れた行、矢印、消し線を置き、b3 では紙を少し傾けて揺らす。
2. 後のページも HTML で描く。見出し、箇条書き、色付きの用語の、整ったノートの見た目にする。特定の製品の画面に似せない。
3. 以降は screen-recording の手順 4〜9 と同じ。b4 のマッチカットは、前の紙と後の紙を同じ位置・同じ大きさに置いて切り替える。

### image-gen-stills

前の静止画だけを画像生成で作り、後は実機の画面録画にする。手元を撮れないときの代わり。

1. 散らかった机、開いたノート、消しゴムのかすなど、前の静止画を 3〜6 枚分プロンプトにする。人物を入れない。画像の中に字を書かせない。生成された字の正しさを確かめる手段が無いので、ノートの字はコードで重ねる。
2. 見積もりを出し、上限を決め、作る人が金額を承認してから送る（原則 `sasaru-principle-quote-before-you-spend`）。同じ入力の作り直しで見た目を探さない。
3. 出来た静止画は出力ファイルを保存して使い回す。b2〜b3 では静止画に小さな寄りと手持ち風の揺れを付ける。
4. 後は screen-recording の手順 2〜3 と同じ画面録画を使う。以降は手順 4〜9 と同じ。

## 編集の器とフォント

器は三つのルートとも HyperFrames。Apache 2.0 で、書き出しの料金も商用の閾値も無い。同じ composition なら同じ動画になると公式の文書が書いている（マシンをまたぐと 1 画素ずれうるので、厳密にそろえるなら Docker で描画する）。`lint` が `@font-face` の宣言漏れを止めるので、書体の取り違えを防げる。`init`、`lint`、`snapshot`、`render --fps` は v0.8.96 で試した書き方、`render --docker --output` は公式の文書の書き方である。現行版は `--help` で確かめる。Remotion は使わない。

フォントは三つとも Google Fonts の OFL-1.1。ファイルはリポジトリに入れず、制作機に入れる。

- Noto Sans JP（c1 は 900、c2 は 800）
- M PLUS Rounded 1c（c3 は 800）
- Yomogi（code-motion の手書きのページ）

## 素材の権利

作る人が用意するもの。自分のノートを自分の手だけで撮った映像。自分のアカウントの実機の画面録画。録音してよいと確かめた講義の録音と、そこから生成したノート。許諾を記録した BGM。CC0 か、クレジットを残す CC BY の効果音（Kenney、Freesound の CC0、OtoLogic など）。

使ってはいけないもの。参照動画の映像、音、テロップの文言。他人のミーム素材やキャラクターの切り抜き（参照の一本は他人の動物動画の切り抜きで組まれていた）。他人のノート、顔、名前。講義のスライドや板書を写しただけの画面を読める大きさで長く映すこと。画面録画に入った講義の音声。実機に無い画面や機能を作り込んだアフター。

TikTok、Instagram、YouTube に同じ動画を出すなら、焼き込む曲と効果音はアプリ内の音源ではなく外部の素材にする。アプリ内の音源はそのプラットフォームの中でしか使えない。

## 費用の目安

| ルート | 一本あたり | 根拠 |
| --- | --- | --- |
| screen-recording | 0 ドル | 撮影と画面録画は自前。HyperFrames と FFmpeg はローカルで無料 |
| code-motion | 0 ドル | すべてローカルで描画 |
| image-gen-stills | 0.10〜0.30 ドル | gemini-nano-banana-2.1 の公式料金、1K 画像 0.0336 ドル × 3 枚から 2K 画像 0.0504 ドル × 6 枚まで（2026-10-25 に料金ページで確認）。作り直しは含めない |

エージェントのトークン代はどのルートにも含めていない。2 本目からはビートと文の差し替えで済むので、1 本目より小さくなる見込み。image-gen-stills は、見積もりで止めて上限を決めてから送る。

## 測ったことと推論

スクリプトで測った数は無い（`status: draft`、`measuredFiles: 0`）。参照のファイルは手元に無く、動画はダウンロードしていない。

2026-10-25 に、YouTube Shorts の参照 5 本の公開ページを読んだ。ページの HTML から尺と再生数を、YouTube が公開している静止画（途中 3 点のサムネイルと、シークバー用のストーリーボード）から絵の流れを見た。ストーリーボードは尺 25 秒以上の 3 本で 1 秒に 1 コマ、10 秒と 15 秒の 2 本は全体を 100 コマに割った小さな画像である。音は聞いていない。

| 参照 | 尺 | 再生数（10-25） | 目で見たこと |
| --- | --- | --- | --- |
| 英語圏の学生ネタ（期待 vs 現実） | 10 秒 | 25,439 | 100 コマのうち 50 コマ目で前から後へ一回切り替わる。上に一段の見出し。人物の顔が映る |
| 日本語の学生ネタ（計画 vs 現実、動物の切り抜き） | 42 秒 | 1,223 | 上に二段の見出しが最後まで残る。その下に時刻ラベル、その下に箱の字幕。ラベルの色が約 22 秒で変わり、約 31 秒で背景ごと当日の場面へ切り替わる。2〜3 秒ごとにカット |
| 英語圏の学生 2 人の対比 | 37 秒 | 2,349,949 | 人物の場面の間に、勉強道具の画面の差し込みが何度も入る。字幕は中央より下の暗い座布団 |
| 手芸のビフォーアフター | 15 秒 | 115,321 | 手だけ。真上の固定で、紙をめくって前と後を見せる。見出しは見えない |
| 日本語の大学生ネタ（締め切り前の変化） | 25 秒 | 10,817 | 上に白い座布団の二段の見出しが最後まで残る。中ほどに赤い段階ラベルが五段階で替わる。人物の顔が映る |

推論として決めた値と、その出どころ。

- 尺の帯と参照の尺 16 秒。Postdom の期待 vs 現実の中央値 18.6 秒と、見た参照の 10〜42 秒から決めた。
- ビートの秒。10 秒の参照の真ん中での切り替えと、アフターを半分すぎに置く判断から決めた。
- c1 の 0.056 と縁 8 px。原則 `sasaru-principle-captions-read-as-headlines` の帯から持ってきた。参照で測っていない。
- 各層の cy。見た参照に共通する「上に見出し、その下にラベル、その下に字幕」の並びを、安全域に合わせて置いた。
- c3 の最短 1.0 秒。設計書の警告の基準に合わせた。
- カメラ、ズーム、トランジション、BGM のテンポ、効果音。この型の芯（一回の切り替え）から決めた。参照では測っていない。
- 安全域はテンプレートの値のまま。
- image-gen-stills の費用。公式料金ページの単価から計算した。

未計測。c1 と c2 の最短の表示秒、c2 と c3 の白い芯の高さ、BGM と声の関係（声が無いので該当なし）。

外部の数の出典。Postdom の TikTok トレンド調査 2026 年 10 月号（9 月の上位 559 投稿、2026-10-05 更新、データは CC BY 4.0）。期待 vs 現実は 8 投稿・再生数の中央値 395,010 回・フォロワー比の中央値 79.2 倍・長さの中央値 18.6 秒、ビフォーアフター（Day 1 vs later）は 44 投稿・中央値 667,150 回・長さの中央値 67.2 秒。記事の数で、こちらでは確かめていない。
