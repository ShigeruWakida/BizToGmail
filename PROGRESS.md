進捗ログ（BizToGmail / MVP）

2026-04-11
- 初期要件整理（日本語）
  - 会社 POP3(SSL) → SMTP 転送
  - 重複防止: POP3 UIDL を SQLite 管理
- MVP 実装
  - `biztogmail.py` を正規入口に統一
  - `biztogmail_app/` へ分割（CLI / POP3 / SMTP / 状態管理 / logging）
  - `services.py` 追加（候補選定、削除判定を分離）
  - `tests/` 追加（CLI / POP3 / state / services）
  - 依存と実行手順を `README.md` に記載
- 残タスク（次の小改良）
  - 429/5xx の指数バックオフ、ログファイル出力
  - `.gitignore` 整備（`state.db` 等）
  - （完了）`.gitignore` 追加

2026-04-12
- SMTP 転送方式を主系統として整理
  - Gmail API `import` 系の実装を削除
  - POP3 / IMAP 取得 + SMTP 転送に一本化
- web UI 強化
  - Google ログイン必須化
  - アカウントの追加 / 編集 / 削除 / 即時実行
  - UI 文言、配置、groupbox、入力補助を整理
  - メールっぽい favicon を追加
- Secret 管理
  - メール用パスワードは GCP Secret Manager へ保存
  - 実行時はメモリキャッシュ優先、無ければ Secret Manager 参照
- 永続化のクラウド対応
  - `DATABASE_URL` 対応を追加
  - SQLite 依存を外し、Cloud SQL for PostgreSQL を使える形へ変更
- Google Cloud 側の整備
  - Cloud Run デプロイ成功
  - Google OAuth ログイン成功
  - Cloud Scheduler 1ジョブ構成で `/scheduler/tick` 実行成功
  - Cloud SQL 接続成功
- インフラ secret 整理
  - `BIZTOGMAIL_SESSION_SECRET`
  - `BIZTOGMAIL_SCHEDULER_TOKEN`
  - `GOOGLE_OIDC_CLIENT_SECRET`
  - `DATABASE_URL`
  を Secret Manager へ移行
  - Cloud Run は Secret Manager 経由で参照する構成に更新
- 実確認
  - Cloud Run 上で再ログイン OK
  - 保存済みアカウント表示 OK
  - `今すぐ実行` OK
  - scheduler token 更新後の `/scheduler/tick` 200 OK

現在の到達点
- Cloud Run / Cloud Scheduler / Cloud SQL / Secret Manager 構成で基本運用可能
- README にクラウド運用手順と確認コマンドを反映済み

残タスク（次の小改良）
- 監視と障害時の確認手順の整備
- 分散ロックやジョブ排他の検討
