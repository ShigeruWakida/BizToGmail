# BizToGmail

会社メールを `POP3` または `IMAP` で取得し、`SMTP` で Gmail へ転送する小規模な Python アプリです。  
Web UI は Google ログイン必須で、**ログイン中の Google アカウントの Gmail アドレス**を転送先として使います。

このリポジトリは、次のような用途を想定しています。

- 会社メールを Gmail 上でも確認したい
- Gmail 側の迷惑メール判定や検索性を活かしたい
- 受信元サーバーには POP3 / IMAP で接続したい
- 少人数、または小規模運用で使いたい

現在は、次のクラウド構成での利用を前提に整備されています。

- Cloud Run
- Cloud Scheduler
- Cloud SQL for PostgreSQL
- Secret Manager
- Google OAuth（テストユーザー運用）

## 特長

- Gmail API ではなく、**SMTP 転送方式**を採用
- 受信元は `POP3` / `IMAP` の両対応
- 転送先は Web UI で入力せず、**Google ログイン中ユーザーの Gmail**
- POP/IMAP パスワード、SMTP パスワードは **Secret Manager 保存**
- Cloud Run 用のデプロイスクリプトあり
- Cloud Scheduler 1 ジョブで全アカウントを定期確認
- Cloud SQL による永続化
- アカウント単位の**二重実行防止**
- 運用・監視ドキュメントあり

## 現在の構成

### アプリ構成

- `biztogmail_app/`
  - アプリ本体
- `biztogmail_web/`
  - FastAPI による Web UI / API
- `scripts/`
  - Cloud Run デプロイやクラウド確認用スクリプト
- `tests/`
  - `unittest` ベースの自動テスト

### クラウド構成

- **Cloud Run**
  - Web UI / API 本体
- **Cloud Scheduler**
  - `/scheduler/tick` を定期的に呼び出す
- **Cloud SQL for PostgreSQL**
  - アカウント情報、既処理メール情報、排他ロック情報を保存
- **Secret Manager**
  - メール用 secret
  - インフラ用 secret

## 動作の流れ

1. ユーザーが Web UI に Google ログイン
2. メールアカウント設定を登録
3. 入力したパスワードは Secret Manager に保存
4. アカウント情報は Cloud SQL に保存
5. `今すぐ実行` または Cloud Scheduler により対象アカウントを実行
6. 受信元サーバーから POP3 / IMAP でメールを取得
7. SMTP で Gmail 宛に再送
8. 処理済み情報を DB に保存し、必要に応じて元サーバーから削除

## リポジトリ構成

```text
.
├─ biztogmail_app/
│  ├─ accounts.py
│  ├─ db.py
│  ├─ imap_client.py
│  ├─ locks.py
│  ├─ logging_utils.py
│  ├─ pop3_client.py
│  ├─ scheduler.py
│  ├─ secrets.py
│  ├─ services.py
│  ├─ settings.py
│  ├─ smtp_client.py
│  ├─ state.py
│  └─ workflows.py
├─ biztogmail_web/
│  ├─ app.py
│  ├─ auth.py
│  ├─ schemas.py
│  └─ static/
├─ monitoring/
├─ scripts/
├─ tests/
├─ OPERATIONS.md
├─ MONITORING.md
└─ PROGRESS.md
```

## 必要なもの

- Google Cloud プロジェクト
- Google OAuth クライアント（Web application）
- Gmail へ転送できる SMTP サーバー
- 受信元の POP3 または IMAP サーバー

## Web UI でできること

- Google ログイン
- メールアカウントの追加
- 編集
- 削除
- `今すぐ実行`
- 定期確認の有効 / 無効
- POP3 / IMAP の選択
- 元サーバーへコピーを残すかどうか
- 指定日数経過後の元サーバー削除

## データ保存

### Cloud Run では外部 DB を使う

Cloud Run のローカルファイルは永続化されません。  
そのため、本番運用では必ず外部 DB を使ってください。

### 現在の推奨

- Cloud SQL for PostgreSQL
- `DATABASE_URL` で接続

例:

```text
postgresql+pg8000://USER:PASSWORD@/DBNAME?unix_sock=/cloudsql/PROJECT:REGION:INSTANCE/.s.PGSQL.5432
```

## Secret 管理

### アプリ利用者が入力する secret

Web UI で入力した次の値は Secret Manager に保存されます。

- POP/IMAP パスワード
- SMTP パスワード

DB には secret 本体ではなく、`secret_ref` だけを保存します。

### インフラ secret

Cloud Run 本番では次の値も Secret Manager 経由で渡す構成です。

- `BIZTOGMAIL_SESSION_SECRET`
- `BIZTOGMAIL_SCHEDULER_TOKEN`
- `GOOGLE_OIDC_CLIENT_SECRET`
- `DATABASE_URL`

## Cloud Run デプロイ

### 1. 必要 API を有効化

例:

```powershell
gcloud services enable run.googleapis.com --project <PROJECT_ID>
gcloud services enable cloudbuild.googleapis.com --project <PROJECT_ID>
gcloud services enable artifactregistry.googleapis.com --project <PROJECT_ID>
gcloud services enable secretmanager.googleapis.com --project <PROJECT_ID>
gcloud services enable cloudscheduler.googleapis.com --project <PROJECT_ID>
```

### 2. コンテナをビルド

```powershell
gcloud builds submit --tag gcr.io/<PROJECT_ID>/biztogmail
```

### 3. デプロイスクリプトを使う

Cloud Run デプロイには、PowerShell スクリプト [scripts/deploy-cloud-run.ps1](scripts/deploy-cloud-run.ps1) を使う前提です。

初回例:

```powershell
.\scripts\deploy-cloud-run.ps1 -ProjectId <PROJECT_ID> -SessionSecret "change-this-session-secret" -SchedulerToken "change-this-scheduler-token"
```

OAuth redirect URI まで確定している場合:

```powershell
.\scripts\deploy-cloud-run.ps1 `
  -ProjectId <PROJECT_ID> `
  -OidcJsonPath ".\path\to\google_oidc_cloud_run_web_client.json" `
  -SessionSecret "change-this-session-secret" `
  -SchedulerToken "change-this-scheduler-token" `
  -RedirectUri "https://<CLOUD_RUN_URL>/auth/callback"
```

Cloud SQL 利用例:

```powershell
.\scripts\deploy-cloud-run.ps1 `
  -ProjectId <PROJECT_ID> `
  -OidcJsonPath ".\path\to\google_oidc_cloud_run_web_client.json" `
  -SessionSecret "change-this-session-secret" `
  -SchedulerToken "change-this-scheduler-token" `
  -RedirectUri "https://<CLOUD_RUN_URL>/auth/callback" `
  -CloudSqlInstance "<PROJECT_ID>:<REGION>:<INSTANCE>" `
  -DatabaseUrl "postgresql+pg8000://USER:PASSWORD@/DBNAME?unix_sock=/cloudsql/<PROJECT_ID>:<REGION>:<INSTANCE>/.s.PGSQL.5432"
```

### 4. Cloud Run で必要な権限

Cloud Run 実行サービスアカウントには少なくとも次が必要です。

- `roles/cloudsql.client`
- `roles/secretmanager.admin`

### 5. Google OAuth 設定

Cloud Run の URL に合わせて、OAuth クライアントへ次を追加します。

承認済みの JavaScript 生成元:

- `https://<CLOUD_RUN_URL>`

承認済みのリダイレクト URI:

- `https://<CLOUD_RUN_URL>/auth/callback`

## Cloud Scheduler

Cloud Scheduler は 1 ジョブで十分です。  
毎分 `POST /scheduler/tick` を叩き、アプリ側で due のアカウントだけ実行します。

例:

```powershell
gcloud scheduler jobs create http biztogmail-tick `
  --location asia-northeast1 `
  --schedule "* * * * *" `
  --uri "https://<CLOUD_RUN_URL>/scheduler/tick" `
  --http-method POST `
  --headers "X-Scheduler-Token=<BIZTOGMAIL_SCHEDULER_TOKEN>"
```

## 監視

監視方針は [MONITORING.md](MONITORING.md) を参照してください。

作成済みの雛形:

- Cloud Run `5xx`
- `/scheduler/tick` の `401/500`

アラートポリシー作成スクリプト:

```powershell
.\scripts\create-alert-policies.ps1
```

## 運用

日常運用・障害切り分けは [OPERATIONS.md](OPERATIONS.md) に分離しています。

一次確認スクリプト:

```powershell
.\scripts\check-cloud-ops.ps1
```

## セキュリティ上の注意

- `.env` をコミットしない
- OAuth クライアント JSON を公開しない
- 実運用のパスワードや token を README に直書きしない
- secret をローテーションしたら、関連設定も必ず更新する
  - `SESSION_SECRET` 更新後は再ログイン
  - `SCHEDULER_TOKEN` 更新後は Cloud Scheduler 更新
  - DB パスワード更新後は Cloud SQL 側も更新

## 既知の制限

- Google OAuth は現時点では **テストユーザー運用** 前提
- 大規模分散運用向けの高度なジョブ制御は未実装
- Cloud Run デプロイスクリプトは secret 反映のため revision を複数作ります
- 通知チャンネルやアラートポリシーは環境ごとに確認が必要です

## 参考ドキュメント

- [OPERATIONS.md](OPERATIONS.md)
- [MONITORING.md](MONITORING.md)
- [PROGRESS.md](PROGRESS.md)

## ライセンス

MIT License
