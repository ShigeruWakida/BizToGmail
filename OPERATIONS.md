# BizToGmail Operations

クラウド運用時の確認手順と、障害時の一次切り分けメモです。

監視方針は [MONITORING.md](MONITORING.md) を参照してください。

## 現在の構成
- Project: `biztogmail`
- Region: `asia-northeast1`
- Cloud Run service: `biztogmail`
- Cloud Scheduler job: `biztogmail-tick`
- Cloud SQL instance: `biztogmail-db`
- Web URL: `https://biztogmail-29155682529.asia-northeast1.run.app`

## 日常確認
1. Web にアクセスして Google ログインできるか確認
2. 保存済みアカウント一覧が表示されるか確認
3. 必要なら `今すぐ実行` を 1 回試す
4. Cloud Scheduler が有効か確認
5. Cloud Run / Cloud SQL の障害通知が出ていないか確認

## よく使うコマンド

### Cloud Run の最新ログ
```powershell
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=biztogmail" --project biztogmail --limit 50 --format json
```

### Cloud Scheduler ジョブ確認
```powershell
gcloud scheduler jobs describe biztogmail-tick --location asia-northeast1
```

### Cloud Scheduler を手動実行
```powershell
gcloud scheduler jobs run biztogmail-tick --location asia-northeast1
```

### Cloud SQL インスタンス確認
```powershell
gcloud sql instances describe biztogmail-db --project biztogmail
```

### Cloud Run サービス確認
```powershell
gcloud run services describe biztogmail --region asia-northeast1 --project biztogmail
```

### まとめて確認
```powershell
.\scripts\check-cloud-ops.ps1
```

### 監視ポリシー作成
```powershell
.\scripts\create-alert-policies.ps1
```

## 障害時の見る順番

### 1. ログインできない
確認点:
- Google アカウントが OAuth 同意画面のテストユーザーに入っているか
- OAuth クライアントの JavaScript 生成元と redirect URI が現在の Cloud Run URL と一致しているか
- Cloud Run ログに `invalid_client`, `redirect_uri_mismatch`, `Missing OAuth state` が出ていないか

まず見るもの:
- Cloud Run ログ
- Google Cloud Console の OAuth クライアント設定

### 2. 保存済みアカウントが表示されない
確認点:
- ログイン中 Google アカウントが期待どおりか
- `POST /accounts` が Cloud Run に届いているか
- Cloud SQL に接続できているか

まず見るもの:
- Cloud Run ログ
- Cloud SQL 接続設定

### 3. `今すぐ実行` が失敗する
確認点:
- Secret Manager 権限
- Cloud SQL 接続
- POP/IMAP / SMTP 認証
- 対象メールが存在するか

まず見るもの:
- Cloud Run ログ
- Secret Manager secret の存在
- 失敗時メッセージ

### 4. 定期実行が動かない
確認点:
- Cloud Scheduler `biztogmail-tick` が `ENABLED` か
- `X-Scheduler-Token` が Cloud Run 側と一致しているか
- Cloud Run 側で `/scheduler/tick` が `200` になっているか

まず見るもの:
- `gcloud scheduler jobs describe biztogmail-tick --location asia-northeast1`
- Cloud Run ログの `POST /scheduler/tick`

## 典型的なログの見分け方
- `POST /scheduler/tick HTTP/1.1" 200 OK`
  - 定期実行の認証と到達は成功
- `POST /scheduler/tick HTTP/1.1" 401 Unauthorized`
  - scheduler token 不一致
- `secretmanager.versions.access`
  - Secret Manager 権限や secret 参照設定を確認
- `InvalidClientError`
  - Google OIDC client secret や OAuth クライアント設定を確認
- `redirect_uri_mismatch`
  - OAuth クライアントの redirect URI が不一致

## Secret 一覧
- `biztogmail-session-secret`
- `biztogmail-scheduler-token`
- `biztogmail-google-oidc-client-secret`
- `biztogmail-database-url`
- 各メールアカウント用 POP/IMAP secret
- 各メールアカウント用 SMTP secret

## ローテーション時の注意
- `BIZTOGMAIL_SESSION_SECRET`
  - 変更後は全ユーザー再ログイン
- `BIZTOGMAIL_SCHEDULER_TOKEN`
  - 変更後は Cloud Scheduler ジョブ設定も更新必須
- `DATABASE_URL`
  - DB パスワード変更後は Cloud SQL 側ユーザー更新も必要
- `GOOGLE_OIDC_CLIENT_SECRET`
  - 変更後は Cloud Run 再デプロイ後にログイン確認

## バックアップ
- Cloud SQL の自動バックアップを有効化しておく
- 必要なら手動バックアップ:
```powershell
gcloud sql backups create --instance=biztogmail-db --project biztogmail
```

## メモ
- Cloud Run の revision が増えるのは異常ではありません
- `scripts/deploy-cloud-run.ps1` は secret 更新のため複数 revision を作ります
- 最後の revision が有効です
