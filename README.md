# sasaru

手元のショート動画の型を読む、Cursor と Claude Code 用のスキルプラグイン。

ショート動画を一本渡すと型を読んで playbook として残し、型を選んで自分のコンテンツで作る。ルーターと原則のスキル、playbook のスキーマ（`schema/playbook.schema.json`）とテンプレート（`templates/playbook.md`）、取り込み（`sasaru-ingest`）、選択（`sasaru-pick`）、制作（`sasaru-make`）、ゲート（`sasaru-gate`）の四つの役、同梱の playbook 5 本（`playbooks/`）がある。絵の素材は動画生成モデルから取る。カット（タイミング、テロップ、組み立て）はコードで行い、器は Akari Video である。場面そのものをコードで描くことはルートにしない。今リポジトリが手元で組み立てる器は HyperFrames で、Akari Video への接続は無い。生成 API のアダプタ（`skills/sasaru-make/adapters/`）は見積もりと送信の口までで、実際の送信は試していない。インストールできるリリースは無い。

テスト。

```bash
uv run --script skills/sasaru-pick/tests/test_pick.py
uv run --script skills/sasaru-ingest/tests/test_<script>.py   # caption_boxes、camera_motion、audio_events、people_voice。重いものは SASARU_SLOW=1
uv run --script skills/sasaru-gate/scripts/selftest.py
uv run --script skills/sasaru-gate/tests/test_check_placement.py
uv run --script skills/sasaru-gate/tests/test_check_spread.py
uv run --script skills/sasaru-make/tests/test_plan_placement.py
uv run --script skills/sasaru-make/tests/test_plan_spread.py
python3 -m unittest discover -s skills/sasaru-make/adapters/tests -t skills/sasaru-make/adapters/tests
```

ライセンスは MIT。条文は `LICENSE`。

貢献と機能要望はまだ受けない。

置かないもの:

- 鍵
- 本人の顔写真
- 声の ID と参照音声
- 他人のリールファイル
- 再配布の許諾が無い BGM

株式会社ササル、CeVIO の「ささら」、Cursor、GitHub の公式製品ではない。
