---
name: sasaru
description: Turn a local short video into a format playbook, pick a playbook for your own content, make a cut from it, or check a playbook or a cut. Use for /sasaru, a reference mp4 or reel to analyze, "make one in this format", or a cut to check. Not for posting or account work.
---

# sasaru

sasaru は、流行っているショート動画の型を playbook として残し、その型で自分のコンテンツを量産する。playbook は型ごとのレシピで、取り込むたびに一本増える。

同梱のファイルはこのファイルから見て次の場所にある。

- 役のスキル: `../sasaru-<role>/SKILL.md`
- 原則リーフ: `../sasaru-principle-<title>/SKILL.md`
- スキーマ: `../../schema/playbook.schema.json`
- テンプレート: `../../templates/playbook.md`
- 同梱の例: `../../playbooks/*.md`
- スクリプト: 各役の `../sasaru-<role>/scripts/`。playbook の検査の正本は `../sasaru-gate/scripts/validate_playbook.py`

`sasaru-agent` に作業を渡すときは、このファイルの絶対パスをプロンプトに入れる。

## Non-negotiables

依頼を次の四つの役のどれか一つに振る。複数にまたがる依頼は、この順に一つずつ進める。

- ローカルの動画ファイルを渡され、型を読んでほしい → **sasaru-ingest**。出力は playbook 一本。
- 自分のコンテンツがあり、どの型で作るか決めたい → **sasaru-pick**。
- playbook が決まっていて、一本作りたい → **sasaru-make**。
- playbook のファイル、または書き出した動画を確かめたい → **sasaru-gate**。gate は報告だけで、直さない。ingest と make は、終わる前に必ず gate を通す。

迷いやすい依頼。

- 「この動画みたいに、自分の内容で作って」 → ingest、pick、make の順。ingest のあと、取り込んだ id をブリーフの `playbook: <id>` として pick に渡す。pick はその一本に決めるだけで終わる。
- 「このカットを直して」 → make。直したあと gate。
- 「この playbook を直して」 → ingest の最後の手順（playbook を書く）からやり直し、gate。

止まるところ。

- URL だけを渡されたとき。取得はしない。手元に保存したファイルを渡すよう頼む。
- 投稿、予約、アカウントの操作。
- 四つの役のどれにも合わない依頼。五つ目の役は開かない。
- 役の SKILL.md の本文が「未執筆」のとき。その役は未実装と返す。
- 最後まで見る型で、下の十四の読みが揃う前に make を開くこと。欄を省いて分析を飛ばさない。
- `scenario.story` が空、無い、`null`、ショット番号の一覧、または単語の一覧のとき。make はカットの計画を書かない。

既定にしないもの。人がカメラに向かって喋るルート（**sasaru-principle-no-talking-head-by-default**）。商品の説明動画と、書いていないエンドカード。商品をどこに出すかはアカウントの型が決め、一本のリールでは動かさない。

## Tools

スキルが呼ぶ道具。名前、引数、いつ呼ぶか。引数を別の形に組み直さない。

### check-product-placement

アカウントの型が決めた商品の置き場を読む。欄は playbook の `productPlacement`（どのビートか、役割 `absent` / `prop` / `payoff` / `spoken` / `end-card`、どれだけ直接か）。省いてよいのは、その型に商品の置き場が一度も無いときだけ。`null` はエンドカードの宣伝ではない。動画の主題は `subject` で、参照の世界か Moguno。主題が商品の台本は不合格。中身のルート `contentRoute` は三つ。`reference-world` は参照の概念と世界を残す。`moguno` は世界を Moguno の IP に置き換える。`in-world` は世界を残し、商品は世界の中の小道具としてだけ出す。

- 名前: `check-product-placement`
- いつ: playbook をライブラリに置く前。pick が型を読むとき。make が計画を書くとき。
- 引数:
  - `playbook`: playbook のファイル
  - `content`: 作る人の content.yaml。省略できる。あるときは主題を見る
- 入口: `skills/sasaru-gate/scripts/check_placement.py` の `check_placement`
- 起動: `uv run --script <プラグイン>/skills/sasaru-gate/scripts/check_placement.py --playbook <playbook.md> [--content <content.yaml>]`
- 戻り: JSON の `ok`、`errors`、`productPlacement`。置き場が無い型は `{"slot": false}` で、エンドカードではない。終了コードは 0 合格、2 入力の誤り、3 不合格。

pick の `scripts/pick.py` と make の `scripts/plan.py` は、この入口と同じ `check_placement` を呼ぶ。合格しない playbook は選ばず、計画も書かない。

### check-spread-psychology

型が再生・コメント・共有を得る理由を、三つの心理として読む。欄は playbook の `spreadPsychology`。`plays`、`comments`、`shares` のそれぞれに、心理の機構（`mechanism`）と、型の何がそれを起こすか（`trigger`）を言葉で書く。出どころは `basis: inferred`。再生数の主張ではない。`payoff` のビートがある型は、最後まで見ることが仕事なので、欄を省けない。`null` は書けない。

- 名前: `check-spread-psychology`
- いつ: playbook をライブラリに置く前。pick が型を読むとき。make が計画を書くとき。
- 引数:
  - `playbook`: playbook のファイル
- 入口: `skills/sasaru-gate/scripts/check_spread.py` の `check_spread`
- 起動: `uv run --script <プラグイン>/skills/sasaru-gate/scripts/check_spread.py --playbook <playbook.md>`
- 戻り: JSON の `ok`、`errors`、`spreadPsychology`。最後まで見ることが仕事ではない型は `{"watchToEnd": false}`。終了コードは 0 合格、2 入力の誤り、3 不合格。

pick の `scripts/pick.py` と make の `scripts/plan.py` は、この入口と同じ `check_spread` を呼ぶ。合格しない playbook は選ばず、計画も書かない。

## 最後まで見る型

四つの役は変えない。ここから先は五つめの役ではない。`payoff` のビートがある型は、最後まで見る物語なので、make の前に次の十四をこの順で読む。各ファイルを全文読んでから、その欄だけを書く。プラグインの中に、この十四のディレクトリは作らない。本文が無い段は未実装と返し、次の段にも make にも飛ばない。飛ばした省略は分析ではない。

`payoff` が無い型では、`verbalization`、`spread`、`scenario` を書かなくてよい。その省略は、最後まで見る物語ではない、という意味である。分析を飛ばした印ではない。`null` は書かない。

1. `sasaru-verbalize-picture`。`verbalization.picture`。下書き `<home>/work/<id>/<id>.md` が無いときは playbook を新しく作らず、下書きが無いと返して止まる。0 秒から、尺を超えない最後の整数秒まで、一秒も飛ばさない。各秒は画面、出入り、見えたカメラ、指させるもの。0 秒の出入りは「なし」。見た動きは `seen.camera` で、止まっている、大きくなった、小さくなった、横へ流れた、縦へ流れた、揺れた、別の画に切り替わった、のどれか。操作名や機材の推測は `inferred.camera` にだけ書き、推測が無ければその鍵は書かない。指の先が無ければ `pointAt` は「決められない」。画面の字、声、看板、作者名、アカウント名、題は写さない。一語の引用もしない。この手順は `evidence` を動かさない。`picture.md` は先に作らない。
2. `sasaru-verbalize-edit`。`verbalization.edit`。時間順にカット、ホールド、ズーム、トランジション。ホールドは見た始点から見た終点までの長さで、途中のズームはその長さに畳まない。ズームは始点、終点、寄るか引くか、その長さ。つなぎは `whip`、`zoom-cut`、`fade`、`match-cut`、`glitch` のどれかで、フレームにそれが出ているときだけ。一フレームの境界はカットで、つなぎに混ぜない。カットの仕事は「ジャンプを隠す」か「新しい段を開く」か「決められない」の一つ。絵の中身は書かない。`seen` はフレームを指せた秒で、`evidence.measured` には入れない。開けないファイルは `missing` に名前だけ書き、その本の出来事は書かない。`edit.md` は、動画が開けてからこの手順が書く。先に作らない。
3. `sasaru-verbalize-words`。出力は `words.md` で、これが `verbalization.words` である。playbook の区間に元の字は書かない。綴りの鍵は無い。欠ける動画は名前だけ残し、その動画の語は書かない。欠ける動画が無ければ missing は空で、見出しは「なし」。区間は、出る秒と消える秒が決まっている語だけ。重なっている語は別区間。消えずに残る語は割らない。消えてまた出たら別区間。役は「終状態の名前」「手順」「喝」「なし」の一つで、推論である。芯の高さと中心は、測った比か「未計測」。目の印象をその数に混ぜない。定数で埋めない。ショット一覧ではない。`words.md` は、この手順が書く。先に作らない。
4. `sasaru-verbalize-sound`。`verbalization.sound`。入りと落ち、`hit` / `bed` / `voice` / `silence`。ヒットの同期、無音が回収の前の溜めか。歌詞も曲名も写さない。`sound.md` は、この手順が書く。先に作らない。
5. `sasaru-verbalize-pull`。`verbalization.pull`。ビートごとに、次に見たいもの、まだ開いている約束、外れたら離れる秒。出どころは `inferred`。動画が無いフォルダの `pull.md` は推測で埋めない。
6. `sasaru-verbalize-account`。`verbalization.accountPattern`。`picture.md`、`edit.md`、`words.md`、`sound.md`、`pull.md` が揃い、区別できる動画が二本以上あるときだけ。一本のショット一覧では書かない。揃う前に `account-pattern.md` を作らない。記憶で型を補わない。
7. `sasaru-spread-open`。`spread.open`。最初の三秒の主張、終状態の語が画面にあるか、冒頭がハウツーか。`howTo` が真ならこの流れは不合格で、読みは残す。`basis` は `inferred`。`open.md` は、この手順が書く。先に作らない。
8. `sasaru-spread-lock`。`spread.lock`。止められている通常の手順、その秒、直線の what-if が失敗する理由。`lock.md` は、この手順が書く。先に作らない。
9. `sasaru-spread-escalation`。`spread.escalation`。積みの列。最初の段に `flatIfRepeated` は無い。一語の形容詞では閉じない。`escalation.md` は、この手順が書く。先に作らない。
10. `sasaru-spread-payoff`。`spread.payoff`。回収の秒、指させるもの、待ち・当たり・着地。変化の無い名前だけは不合格。`payoff.md` は、この手順が書く。先に作らない。
11. `sasaru-spread-comment`。`spread.comment`。返信を招く拍と、招く返信。閉じている拍に返信の種類は作らない。取得していないコメント数は作らない。`comment.md` は、この手順が書く。先に作らない。
12. `sasaru-spread-share`。`spread.share`。指させる物、送る相手、名前の無い途中。`share.md` は、この手順が書く。先に作らない。
13. `sasaru-spread-leave`。`spread.leave`。最初の一秒、同じ手順、名指ししない語、終わりが主張と違うか。`leave.md` は、この手順が書く。先に作らない。
14. `sasaru-scenario`。`scenario.story`。言語化の六ファイルと、開きを含む切れが揃ったあとだけ。散文で、人が言い直せる。ショット番号の一覧でも、単語の一覧でもない。ハウツーの開きは写さない。揃う前に `scenario.story` も `docs/bridge-scenario-v2.md` も作らない。記憶で物語を書かない。

make は `scripts/plan.py` がスキーマを読んでから計画を書く。`scenario.story` が空、無い、`null`、ショット番号の一覧、単語の一覧なら、計画は書かない。

## Principles

原則を使うときは、そのリーフを全文読む。各行は、いつ効くか。

- **Describe the Form, Not the Work.** playbook や例を書くとき、コミットするとき。型を数と分類で持ち、元の文言、音、フレーム、曲名、作者を持たない。
- **Measure or Label.** playbook の欄やゲートの欄に数を入れるとき。測った数だけを入れ、推論と未計測を分けて残す。
- **No Talking Head by Default.** 制作ルートを書くとき、選ぶとき。
- **Quote Before You Spend.** 有料の生成 API を呼ぶ手順の前。
- **Captions Read as Headlines.** テロップの書体と大きさを決めるとき。
- **Last Card Holds.** テロップの終了秒を決めるとき。
- **Sound from a Licensed File.** BGM と効果音を足すとき、書き出すとき。

## Library

playbook のライブラリは二か所を読む。

- 利用者のライブラリ。作業フォルダの `sasaru/playbooks/<id>.md`。取り込みはここに書く。環境変数 `SASARU_HOME` があればそちらを `sasaru/` の代わりにする。
- 同梱の例。`../../playbooks/<id>.md`。読むだけで書き換えない。

取り込みの下処理は `sasaru/work/<id>/` に置く。作った動画と記録は `sasaru/cuts/<cut-id>/` に置く。`work/` と `cuts/` の中の映像、音、画像はコミットしない。

playbook の形は、スキーマとテンプレートが正本である。フロントマターはスキーマに合格し、本文はテンプレートの見出しを同じ順で全部持つ。

## Autonomy

確認なしで進める。ローカルの下処理、測定、playbook の下書き、ライブラリへの書き込み、無料のローカル描画、有料 API の見積もり、ゲート。

止まって確認する。有料 API への送信と、その金額。第三者の動画（権利 tier C）を外部のモデルやサービスへ送ること。喋る人のルートを使うこと。鍵の値を表示すること。

## Subagents

重い読みは `sasaru-agent` に分ける。シートの読み、ビートの切り分け、ルートごとの描画などである。数の合否はスクリプトの出力で決め、文章だけで合格にしない。「なぜ伸びるか」のような判断は、強い判断モデルに書かせ、推論と明記する。機械的な欄の転記は速いモデルでよい。

## 役の形

四つの役の SKILL.md は同じ形にする。frontmatter は `name`、`description`、`disable-model-invocation: true`。見出しは Start、Phase、Outputs の順。呼ぶスクリプトは、起動の一行をそのまま本文に書く。

## Claude Code

Claude Code では、`Task` を `Agent` に、`sasaru-agent` を `sasaru:sasaru-agent` に読み替える。他のスキルは `Read` で SKILL.md を開いて従う。`~/.cursor/plugins/` は `~/.claude/plugins/` である。

## Reply

結果を先に書く。作った playbook や動画のパス、ゲートの合否、未計測の欄、有料で使った金額。数には、それを出したファイルのパスを付ける。推論は推論と書く。
