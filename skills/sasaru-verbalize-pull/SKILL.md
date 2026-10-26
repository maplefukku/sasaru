---
name: sasaru-verbalize-pull
description: "Apply when writing what keeps a viewer on a short, one beat at a time. For each beat, say what the viewer wants to see next, which promise is still open, and the second they would leave if the next beat failed. Write verbalization.pull and label it an inference. Do not copy a source sentence or add a CLI."
disable-model-invocation: true
---

# sasaru-verbalize-pull

注意の細かいフロー。ビートごとに、見る人が次に見たいもの、まだ開いている約束、次のビートが外れたら離れる秒を書く。出力は `verbalization.pull` だけである。新しいコマンドは足さない。動画は作らない。

形は `../sasaru/SKILL.md` の「役の形」に従う。ルーターは四つの役を振り、このファイルは振らない。スキーマ、ルーター、テンプレート、他のスキル、設計ノートは変えない。

書く前に `../sasaru-principle-describe-the-form-not-the-work/SKILL.md` と `../sasaru-principle-measure-or-label/SKILL.md` を全文読む。画面の字、せりふ、キャプション、題は、出力に写さない。

## Start

todo を Phase ごとに一つずつ開く。ビートは、見る人の「次に見たいもの」が変わる区切りである。カットのたびに切らない。

1. ビートを切る
2. 次に見たいものを書く
3. 開いている約束を書く
4. 離れる秒を書く

秒は、渡された動画のタイムライン上の数である。再生数、完走率、いいねの数は書かない。

## Phase A: ビートを切る

動画を見て、次に見たいものが変わるたびにビートを一つ置く。同じ求めが続いているあいだは、一つのビートにまとめる。

各ビートに、始まりの秒と終わりの秒を書く。終わりの秒は、次のビートの始まりの秒と同じにする。最後のビートの終わりは、動画の終わりの秒にする。

画面に出ている文で区切らない。文が替わっても、次に見たいものが同じなら、ビートは割らない。

## Phase B: 次に見たいもの

そのビートの終わりに、見る人が次の画面へ何を求めているかを書く。求めは、いま画面にあるものの続きである。

画面の文、ナレーションの文、タイトルの文は写さない。物の役割で書く。

## Phase C: 開いている約束

そのビートが終わっても、まだ画面が返していない約束を書く。約束は、見る人が「まだ見ていない結末」である。

約束がこのビートで閉じたときは、閉じた、と書く。閉じた理由は、画面に出た役割で書き、参照の文では書かない。

## Phase D: 離れる秒

次のビートが Phase B の求めを出さなかったとき、見る人が再生を閉じる秒を書く。その秒は、次のビートが始まる秒である。求めがそこまでに出ていなければ、見る人はそこを境に離れる、という推論である。

最後のビートに次は無い。最後のビートが約束を閉じなかったとき、見る人が離れる秒を書く。その秒は、閉じる絵が来るべき秒である。

この秒は、測った離脱率ではない。`evidence` に載せるなら `inferred` である。`measured` には入れない。

## Outputs

`verbalization.pull` だけを書く。出どころは推論である。`basis` は `inferred` と書く。再生数、再生回数、割合、いいねの数は書かない。参照の文は写さない。スクリプトもコマンドも足さない。

アカウントの言語化ディレクトリを渡されたときは、その直下の `pull.md` にだけ書く。絵、編集、語、音、シナリオ、動画ファイルは書かない。渡されたフォルダに動画が無いときは、`pull.md` を推測で埋めない。無い、と書いて止まる。一覧にあってファイルが無い動画は、名前だけを書き、中身は作らない。

中身は次の形だけ。

```markdown
# verbalization.pull

basis: inferred

## <動画の呼び名>

### <始まりの秒>–<終わりの秒>

- wantsNext: 見る人が次に見たいもの
- openPromise: まだ開いている約束
- leaveSec: 次のビートが外れたら離れる秒
```

`leaveSec` は数である。ビートが複数ある動画は、この三つをビートの数だけ繰り返す。一つのビートに、次に見たいものが二つある書き方はしない。
