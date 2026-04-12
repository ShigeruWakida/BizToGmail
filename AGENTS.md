# Repository Guidelines

## プロジェクト構成
このリポジトリは、POP3 サーバーのメールを SMTP で Gmail へ転送する小規模な Python CLI / web API です。CLI の入口は `biztogmail.py`、実装本体は `biztogmail_app/` に分割され、web 層は `biztogmail_web/` にあります。作業メモは `README.md` と `PROGRESS.md`、補助資料は PDF / PNG としてリポジトリ直下に置かれています。

## 開発・実行コマンド
作業はリポジトリ直下で行ってください。

- `python -m venv .venv` : 仮想環境を作成
- `.venv\Scripts\Activate.ps1` : PowerShell で仮想環境を有効化
- `pip install --upgrade fastapi uvicorn` : web API を使う場合に追加
- `python -m unittest discover -s tests -v` : ローカルの自動テストを実行
- `python biztogmail.py run --host <host> --user <user> --destination <gmail> --max 1 --dry-run` : 転送前の安全確認
- `python biztogmail.py scheduler --once` : 保存済みアカウントの scheduler を1回実行

## コーディング規約
Python は 4 スペースインデントを使用し、関数・変数は `snake_case`、定数は `DB_FILE` のように大文字スネークケースで統一してください。責務ごとに `biztogmail_app/` の既存モジュールへ寄せ、CLI に直接ロジックを増やさないでください。コメントは最小限にし、POP3 や SMTP の挙動など読み取りづらい箇所だけに付けてください。

## テスト方針
自動テストは `tests/` にあります。変更時はまず `python -m unittest discover -s tests -v` を実行し、そのうえで必要な手動確認を `biztogmail.py` や FastAPI エンドポイントで行ってください。

- POP 一覧取得や抽出条件の変更時は `run --dry-run`
- 実転送確認は `--max 1` など小さな値で実施

将来テストを追加する場合は `tests/` ディレクトリを作り、`test_<feature>.py` 形式で命名してください。

## コミット・PR方針
この作業環境には Git 履歴がないため、コミットメッセージは命令形で簡潔に書いてください。例: `Add dry-run guard for POP deletion`。PR では変更内容、実行した確認コマンド、認証情報への影響有無を明記してください。

## セキュリティと設定
`state.db` とメールアカウント固有の秘密情報はコミット禁止です。認証情報はコードへ直書きせず、必要なら `POP3_PASSWORD` のような環境変数を使ってください。scheduler 用アカウント設定では `pop_password` のほかに `secret_ref` で `env:NAME` 形式の環境変数参照も使えます。本番移行時は平文保存より `secret_ref` を優先してください。新しいローカル生成物を増やした場合は `.gitignore` も更新します。
