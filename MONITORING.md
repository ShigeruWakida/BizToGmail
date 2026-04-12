# BizToGmail Monitoring

最低限の監視対象と、先に作るべきアラート条件のメモです。

## 監視対象
- Cloud Run `biztogmail`
- Cloud Scheduler `biztogmail-tick`
- Cloud SQL `biztogmail-db`
- Secret Manager 参照失敗
- Google OAuth ログイン失敗

## まず見るべきシグナル

### 1. Cloud Run エラー率
見るもの:
- `5xx` 応答
- `POST /accounts/{id}/run`
- `POST /scheduler/tick`

目安:
- 5分で 1 回以上の継続的な `500`
- `scheduler/tick` の `401` / `500`

### 2. Cloud Scheduler 失敗
見るもの:
- `biztogmail-tick` の最終実行状態
- `status.code`

危険な状態:
- `state != ENABLED`
- 実行失敗が連続
- `401 Unauthorized`
- `500 Internal Server Error`

### 3. Cloud SQL 異常
見るもの:
- 接続失敗
- CPU / メモリ / ストレージ逼迫
- 自動バックアップ失敗

ログ上の兆候:
- DB connection error
- timeout
- authentication failed

### 4. Secret Manager 異常
見るもの:
- `secretmanager.versions.access`
- `Permission denied`
- secret not found

### 5. Google OAuth 異常
見るもの:
- `redirect_uri_mismatch`
- `InvalidClientError`
- `Missing OAuth state`

## 推奨アラート

### 優先度高
- Cloud Run の `5xx` が連続したら通知
- `POST /scheduler/tick` が `401` または `500` なら通知
- Cloud Scheduler ジョブ失敗で通知
- Cloud SQL インスタンス停止 / 接続失敗で通知

### 優先度中
- Google ログイン失敗が連続したら通知
- Secret Manager アクセス失敗で通知
- Cloud SQL バックアップ失敗で通知

## 手動確認コマンド

### Cloud Run ログ
```powershell
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=biztogmail" --project biztogmail --limit 50 --format json
```

### scheduler/tick だけ確認
```powershell
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=biztogmail AND textPayload:\"POST /scheduler/tick\"" --project biztogmail --limit 20 --format json
```

### Cloud Scheduler 状態
```powershell
gcloud scheduler jobs describe biztogmail-tick --location asia-northeast1
```

### Cloud SQL 状態
```powershell
gcloud sql instances describe biztogmail-db --project biztogmail
```

## 雛形ファイル
- [monitoring/cloud-run-5xx-policy.json](monitoring/cloud-run-5xx-policy.json)
- [monitoring/scheduler-tick-log-policy.json](monitoring/scheduler-tick-log-policy.json)

## アラートポリシー作成
```powershell
.\scripts\create-alert-policies.ps1
```

補足:
- `gcloud alpha monitoring policies create` を使います
- 通知先チャンネルは Google Cloud Console 側で先に作成しておくと運用しやすいです
- この雛形はまず「気づく」ための最小構成です

## 監視導入の順番
1. Cloud Scheduler の失敗通知
2. Cloud Run の `5xx` 通知
3. Cloud SQL の稼働 / バックアップ通知
4. Google OAuth / Secret Manager 失敗のログベース通知

## メモ
- まずは Google Cloud Console のアラートポリシーで十分
- 最初から細かく作りすぎず、`scheduler/tick` と Cloud Run `5xx` を先に押さえる
- 監視は「気づけること」が目的なので、最初は少数の高信頼アラートに絞る
