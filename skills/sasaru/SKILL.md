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
- スクリプト: `../../scripts/`

`sasaru-agent` に作業を渡すときは、このファイルの絶対パスをプロンプトに入れる。

## Non-negotiables

依頼を次の四つの役のどれか一つに振る。複数にまたがる依頼は、この順に一つずつ進める。

- ローカルの動画ファイルを渡され、型を読んでほしい → **sasaru-ingest**。出力は playbook 一本。
- 自分のコンテンツがあり、どの型で作るか決めたい → **sasaru-pick**。
- playbook が決まっていて、一本作りたい → **sasaru-make**。
- playbook のファイル、または書き出した動画を確かめたい → **sasaru-gate**。gate は報告だけで、直さない。ingest と make は、終わる前に必ず gate を通す。

迷いやすい依頼。

- 「この動画みたいに、自分の内容で作って」 → ingest、pick、make の順。pick は、いま取り込んだ一本に決めるだけで終わる。
- 「このカットを直して」 → make。直したあと gate。
- 「この playbook を直して」 → ingest の最後の手順（playbook を書く）からやり直し、gate。

止まるところ。

- URL だけを渡されたとき。取得はしない。手元に保存したファイルを渡すよう頼む。
- 投稿、予約、アカウントの操作。
- 四つの役のどれにも合わない依頼。五つ目の役は開かない。
- 役の SKILL.md の本文が「未執筆」のとき。その役は未実装と返す。

既定にしないもの。人がカメラに向かって喋るルート（**sasaru-principle-no-talking-head-by-default**）。

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
