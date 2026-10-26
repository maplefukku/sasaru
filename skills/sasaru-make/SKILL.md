---
name: sasaru-make
description: "Make one cut from a chosen playbook and the maker's own content, along the playbook's default route. Use only when the sasaru router routes a make."
disable-model-invocation: true
---

# sasaru-make

選ばれた playbook と、作る人のコンテンツ（台本、素材、ブランド、ライセンスを記録した曲と効果音）から、一本の制作計画を書き、カットをコードで組み立てて書き出す。生成 API が要る手順は `adapters/` の口を呼び、口が無ければ「未実装」として計画に残して先へ進む。

同梱のファイルはこのファイルから見て次の場所にある。

- 計画: `scripts/plan.py`
- カットの組み立て: `scripts/render_code_motion.py`
- 生成の口: `adapters/<need>.py`（別の担当が持つ。下の「アダプタの口」）
- 確かめ用の型と台本: `examples/caption-only-smoke.md`、`examples/zurunote-smoke.content.yaml`

## 制作の規則

絵の素材は動画生成モデルから取る。カット（タイミング、テロップ、組み立て）はコードで行い、器は Akari Video である。場面そのものをコードで描くことはルートにしない。

## 器の既定は HyperFrames

この節は、今リポジトリにある組み立てである。上の規則が置く器は Akari Video で、ここにはその接続は無い。`render_code_motion.py` はテロップとタイミングと組み立てを手元で書く。

`code-motion` の手元の器は HyperFrames（`hyperframes@0.8.196`、Apache 2.0）である。候補は AKARI Video、HyperFrames、Remotion の三つで、決定性と導入の軽さで比べた。

- HyperFrames。時刻をフレーム番号から整数で決めてヘッドレス Chrome でシークするので、同じ composition は同じ動画になる。このリポジトリの確かめでは、同じ機械で並列数 4、1、4 の三回の書き出しが、映像、音の混合、最終の mp4 のどれも sha256 で一致した。ただし HyperFrames 自身の MP4 符号化は並列数で変わる（PNG のフレームは変わらない）ので、make は PNG 連番を描かせて ffmpeg で符号化する。導入は `npx -y hyperframes@<版>` だけで、Chrome と ffmpeg は手元のものを使う。テロップは HTML と CSS で書けるので、エージェントが直接書ける。マシンをまたいで揃えるなら `--docker`。
- AKARI Video。同一機で二回の SHA-256 一致をゲートにしていて決定性は強いが、書き出し本体 `render-cut` は npm に公開されておらず（`private: true`）、アプリは macOS と Windows、Linux は CLI だけ。GUI の無い Linux で書き出せるかは確かめられていない。導入が重い。
- Remotion。フレーム番号の純関数として書けば決定的だが、MP4 のバイト一致までは公式に書いていない。従業員 4 人以上の営利組織は会社ライセンスが要り、playbook ごとに利用者の組織の規模を確かめる手間が残る。このリポジトリでは試していない。

playbook のルートの `container` が `html-canvas` なら HyperFrames で描き、制作記録に逸脱として残す。`remotion`、`three-js`、`ffmpeg-ass`、`capcut`、`other` は描画器を持たないので、compose の手順を「未実装」にする。

GSAP 3.14.2 は HyperFrames のタイムラインに要る。描画のたびに取らず、`SASARU_CACHE`（無ければ `~/.cache/sasaru`）に一度だけ取って composition に同梱する。

## Start

1. ルーターの `../sasaru/SKILL.md` を読んでいること。原則は使うときにリーフを全文読む。このスキルが使うのは **Captions Read as Headlines**、**Last Card Holds**、**Sound from a Licensed File**、**No Talking Head by Default**、**Quote Before You Spend**、**Measure or Label**。
2. playbook を決める。pick の出力の id か、ファイルのパス。利用者のライブラリ `sasaru/playbooks/` を先に、同梱の `../../playbooks/` を次に探す。
3. 作る人のコンテンツを `content.yaml` に書く。形は次のとおり。台本の文は自分の内容だけで、参照動画の文言を入れない。

```yaml
cut: my-cut-id                 # kebab-case。sasaru/cuts/<cut>/ に出る
durationSec: 10                # 省けば参照の尺を帯に収めた値
route: code-motion             # 省けば playbook の既定ルート
brand:
  ground: "#0F1B2D"            # 背景の色
  groundAlt: "#2F6BFF"         # カット（hard-cut、zoom-cut など）で切り替える地の色
  pattern: ruled               # plain | ruled | grid
  patternColor: "#1E3150"
  accent: "#FFD84D"            # 層の強調色が null のときの色
  ink: null                    # 字の色を全層で上書きするとき
  font: null                   # { family, license, source, file } 自前のフォント
  layerFonts: { c2: "M PLUS Rounded 1c" }   # 層ごとに書体を変えるとき
beats:                         # ビート id ごと、層 id ごとに一枚ずつの文
  b1: { c1: ["一枚目\n二段目", "[[強調]]の一枚"] }
assets:                        # 素材を使うルートのとき。ビートごとに一本
  b2: { file: clip.mp4, kind: own-footage }   # own-footage | screen-capture | stock-footage
generate:                      # 生成のルートのとき。ビートごとのプロンプト
  b3: { need: i2v, prompt: "...", inputs: [still.png] }
audio:
  bgm: { file: ${SASARU_ASSETS}/bgm.ogg, license: CC0-1.0, source: <ページの URL>, offsetSec: 0 }
  sfx:
    - { type: pop, file: ..., license: CC0-1.0, source: ..., gainDb: -8 }   # type は playbook の audio.sfx[].type。鳴る秒は sfx の cue と at で決まる
  voice: none                  # 自分の声なら { file, license: own-work }、TTS なら { text }
```

`\n` は段の区切り、`[[...]]` は強調。ファイルのパスは `content.yaml` から見た相対か、`${VAR}` と `~` を展開した絶対パス。

## Tools

### check-product-placement

ルーターの Tools と同じ道具。計画を書く前に必ず読む。

- 名前: `check-product-placement`
- いつ: `cut.json` を書く前。台本に `subject` があるとき。
- 引数:
  - `playbook`: 選んだ playbook のファイル
  - `content`: 作る人の content.yaml
- 入口: `../sasaru-gate/scripts/check_placement.py` の `check_placement`。`scripts/plan.py` が呼ぶ
- 戻り: `productPlacement` を `cut.json` にそのまま書く。`{"slot": false}` や役割 `absent` の型には、商品のカードもエンドカードも足さない。主題が商品なら計画を書かず終了コード 3

## Phase 1. 計画を書く

```bash
uv run --script skills/sasaru-make/scripts/plan.py <playbook.md|id> <content.yaml> [--route ID] [--duration SEC] [--home DIR]
```

`sasaru/cuts/<cut>/cut.json`（`SASARU_HOME` か `--home` があればその下）に計画を書き、要約を JSON で出す。終了コードは 0 書いた、2 入力の誤り、3 拒否。

plan.py がすること。

1. 道具 `check-product-placement` を読む。playbook の `productPlacement` と、台本の `subject` を見る。不合格なら `cut.json` を書かない。合格なら、読んだ `productPlacement` を計画に書く。省略は `{"slot": false}` で、エンドカードの宣伝ではない。説明動画の台本は作らない。
2. playbook のフロントマターをスキーマで検証し、id とファイル名、ビートの重なり、`at.beat` と層の `beats` の参照先を見る。YAML は 1.2 の真偽値で読み、日付を文字列のまま扱う。
3. ルートを決める。絵は動画生成モデルの素材にし、コードが担うのはタイミング、テロップ、組み立て（器は Akari Video）だけにする。場面そのものをコードで描くルートは選ばない。`--route` か `content.route` で既定でないルートを選んだときは `routeRequestedByMaker: true` を書く。`talkingHead: true` のルートは `--allow-talking-head` が無ければ拒否する。作る人がこのカットのために名指ししたときだけ付ける。
4. 尺を決め、参照の尺からの伸縮の比を出す。ビートの秒、ズーム、トランジション、効果音、BGM の入りを同じ比で動かす。帯の外の尺は入力の誤り。
5. 層ごとの大きさを決める。`headline` の白い芯の高さが 0.04 未満か未計測なら 0.057 に上げ、逸脱に書く。ほかの層の未計測は役ごとの既定値で埋め、逸脱に書く。字の大きさは芯の高さ ÷ 0.92（Noto Sans JP 900 の漢字の行の実測）。漢字も仮名も無い英字だけの段は芯が大文字の高さ（0.74 em）までしか届かないので、その段だけ 0.92 ÷ 0.74 倍にする。
6. テロップのカードの秒を決める。ビートの中を字数で割り、層の `show`（`onset`、`before-onset` と `leadSec`、`beat-start`）で出し、`hide`（`next-card`、`phrase-end`、`beat-end`）で消す。`lastCard: hold-to-end` の層の最後の一枚は絵の最後まで残す。`hook.firstFrameHasText` なら 0 秒の一枚を動かさずに出す。声のある型で声の時刻が無いときは、字数で割った推定だと警告する。
7. 検査して警告に残す。`minHoldSec`（null なら 1.0 秒）より短い一枚、`charsPerCard` の外、`linesMax` を超える段、安全域からはみ出す幅（縮めて逸脱に書く。見出しが 0.04 を割るなら分けるよう警告）、安全域の上下からはみ出す段数（段を減らすよう警告）、強調の倍率で一つの段に大小が混ざること（その段は色だけにする）。
8. 音を決める。BGM と効果音は別ファイルだけで、カットのフォルダの `audio/` に写し、sha256 とライセンスを記録する。効果音の秒は playbook の `cue`（`card-in` は最初の層のカードの出、`cut` はビートの頭、`zoom`、`payoff`、`beat-drop`）か `at` で決める。鳴る一回ごとに `audio.sources[]` に一行書く。既定にしてよいライセンスは `CC0-1.0`、`CC-BY-4.0`（`credit` が必須）、`own-work`。それ以外は「要承認」になり、描画は `--accept-license` が無いと止まる。参照動画の音を入力に指定したら拒否する。声と BGM が両方あるとき、`levelDbUnderVoice` が playbook にも content にも無ければ「要決定」にする。既定値は持たない。
9. ルートの `needs` を手順にする。素材（`own-footage`、`screen-capture`、`stock-footage`）が無ければ「要決定」。生成（`image-gen`、`t2v`、`i2v`、`v2v`、`tts`）はアダプタの口で見積もりだけ取り「要承認」、口が無ければ「未実装」で残す。`r2v` はこのスキルの既定の手順に入れない。

手順の状態は `todo`、`done`、`要決定`（作る人が足すもの）、`要承認`（金額か権利の承認）、`未実装`（口か器が無い）、`blocked`。

## Phase 2. 描く

```bash
uv run --script skills/sasaru-make/scripts/render_code_motion.py sasaru/cuts/<cut> [--workers N] [--quality delivery] [--accept-license] [--html-only]
```

1. フォントを取る。playbook の `fonts`（OFL-1.1 か Apache-2.0 だけ）を github.com/google/fonts の `ofl/` か `apache/` から `SASARU_CACHE/fonts/` に取り、ライセンス文と一緒に置く。再配布できない書体は `brand.font.file` を渡されたときだけ使う。フォントのファイルはコミットしない。
2. `sasaru/cuts/<cut>/hf/index.html` に composition を書く。背景（色と罫線か方眼。カットの秒で `groundAlt` と交互に切り替える。`groundAlt` も素材も無いビートへのカットは何も変わらないので、plan.py が警告する）、ビートごとの素材（音は消す）、カメラの動き、ズーム、トランジション、層ごとのカード。カードの出し方は `cut`、`pop`、`fade`、`slide-up`、`scale-in`、`typewriter`、`word-by-word`、消し方は `cut`、`fade`、`slide`。絵の最後まで残る一枚には消しの動きを付けない。
3. `hyperframes lint --json` の結果を `cut.json` に入れ、`hyperframes render --format png-sequence` でフレームを書き、ffmpeg の libx264（`delivery` は CRF 14、スレッド 4 で固定、bt709、bitexact）で `picture.mp4`（音なし）にする。フレームの md5 を記録して PNG は消す。
4. ffmpeg で `mix.wav` を作る。BGM は入りの秒から、効果音はきっかけの秒に置き、最後 0.4 秒で BGM を下げ、全体を −14 LUFS、真のピーク −1.5 dB に合わせる。声があれば声と BGM をそれぞれ −20 LUFS に揃えてから、BGM を `levelDbUnderVoice` だけ下げる。
5. `cut.mp4` に映像をそのまま、音を AAC 192 kbps で入れる。メタデータは消し、bitexact で書く。CC BY の素材があれば `credits.txt` を書く。
6. `cut.json` の `render` に、器と版、GSAP の sha256、フォントのファイルとライセンス、lint、各ファイルの sha256、ffprobe、聞こえる音の源のファイル一覧、飛ばした手順を書く。

compose が `未実装` か `blocked`、または権利の「要承認」が残っていれば書き出さずに止まる（終了コード 3）。生成の手順が「未実装」や「要承認」のまま残っていても、コードで描ける部分は描き、飛ばした手順を記録する。

## Phase 3. ゲートに渡す

`cut.json` の最後の手順が gate のカット検査である。

```bash
uv run --script skills/sasaru-gate/scripts/check_cut.py sasaru/cuts/<cut> --fetch-models --out sasaru/cuts/<cut>/gate.json
```

`--fetch-models` は無料の顔検出モデル YuNet を `SASARU_CACHE` に取る。gate の不合格を make が合格に書き換えない。測り方の限界による不合格（強調色の行、拡大して出るカード、声の無い型の発話判定など）も、そのまま作る人に返す。gate が無ければ「ゲート未実装、未検査」と返す。

## アダプタの口

生成は `adapters/<need>.py`（`image-gen` は `image_gen.py`）を `uv run --script` で呼ぶ。make が呼ぶのは見積もりだけで、送信は計画にコマンドを書き、作る人が金額を承認してから回す。

```bash
uv run --script adapters/<need>.py quote --request <req.json>
# stdout: {"usdMin": n, "usdMax": n, "asOf": "YYYY-MM-DD", "basis": "..."}
uv run --script adapters/<need>.py run --request <req.json> --out <dir> --cap-usd <n> --yes
# stdout: {"files": [...], "usd": n}
```

`req.json` は plan.py が `sasaru/cuts/<cut>/requests/<need>[-<beat>].json` に書く。欄は `need`、`cutId`、`beat`、`durationSec`、`aspect`、`fps`、`prompt`（TTS は `text`）、`inputs`、`routeNeeds`（選んだルートの `needs`。アダプタは喋る人と顔の参照の許可をここだけで決める）。生成されたクリップの音は外してから `assets` に入れ、計画を書き直して描く。同じ入力の生成をやり直して見た目を探さない。

## Outputs

`sasaru/cuts/<cut>/` に次を置く。コミットしてよいのは `cut.json` と `gate.json` だけで、映像、音、composition の素材はコミットしない。

- `cut.json`（`sasaru-cut/1`）。形は `../sasaru-gate/SKILL.md` の Outputs が正本で、gate が読む鍵を必ず書く。`playbook`（id）、`playbookPath`（`cut.json` から見たパス）、`video`（`cut.mp4`）、`route` と `container`（文字列）、`routeRequestedByMaker`、`stretch`、`costUsd`（実際に払った額。このスキルは 0）、`cards[]`（`layer`、`start`、`end`、`text`、`emphasis`）、`captionStyle.<層>`（`fontFamily`、`fontClass`、`weight`、`shadow`、`plate`、`color`）、`audio.sources[]`（`role`、`path`、`license`、`atSec`、`inSec`）と `audio.referenceAudioUsed: false`、`deviations[]`（`path`、`from`、`to`、`reason`）。声の結びの窓 `lastMora` は TTS の時刻が来たら書く。make が足す鍵は `cutId`、`playbookSha256`、`content`、`productPlacement`（道具が読んだ置き場。置き場が無い型は `{"slot": false}`）、`routeInfo`、`format`、`beats`、`layers`、`camera`、`visuals`、`fonts`、`credits`、`steps`、`warnings`、`render` で、カードには `beat`、`lines`、`fitScale`、`lineScales` も付く。
- `audio/`。聞こえる音の各ファイルの写し。`audio.sources[].path` はここを指す。
- `gate.json`。gate のカット検査の結果。
- `requests/*.json`。生成の口に渡す依頼。
- `hf/`。HyperFrames の composition。
- `picture.mp4`、`mix.wav`、`cut.mp4`、あれば `credits.txt`。

作る人への返事は、`cut.mp4` のパス、尺、gate の合否と不合格と未計測の欄、手順のうち `要決定`、`要承認`、`未実装` のもの、逸脱（大きさの引き上げ、縮め、動きの差し替え）、警告、使った有料の金額（このスキルは 0）を先に書く。
