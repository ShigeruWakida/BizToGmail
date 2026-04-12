param(
    [string]$ProjectId = "biztogmail",
    [string]$Region = "asia-northeast1",
    [string]$ServiceName = "biztogmail",
    [string]$ImageName = "biztogmail",
    [string]$OidcJsonPath = ".\\google_oidc_cloud_run_web_client.json",
    [string]$SessionSecret = "",
    [string]$SchedulerToken = "",
    [string]$RedirectUri = "",
    [string]$DatabaseUrl = "",
    [string]$CloudSqlInstance = "",
    [string]$SessionSecretName = "biztogmail-session-secret",
    [string]$SchedulerTokenName = "biztogmail-scheduler-token",
    [string]$OidcClientSecretName = "biztogmail-google-oidc-client-secret",
    [string]$DatabaseUrlSecretName = "biztogmail-database-url"
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path $OidcJsonPath)) {
    throw "OIDC json not found: $OidcJsonPath"
}

$json = Get-Content $OidcJsonPath -Raw | ConvertFrom-Json
if (-not $json.web.client_id -or -not $json.web.client_secret) {
    throw "OIDC json is missing client_id or client_secret: $OidcJsonPath"
}

if (-not $SessionSecret) {
    $SessionSecret = $env:BIZTOGMAIL_SESSION_SECRET
}

if (-not $SchedulerToken) {
    $SchedulerToken = $env:BIZTOGMAIL_SCHEDULER_TOKEN
}

if (-not $SessionSecret) {
    throw "SessionSecret is required. Pass -SessionSecret or set BIZTOGMAIL_SESSION_SECRET."
}

if (-not $SchedulerToken) {
    $SchedulerToken = [Guid]::NewGuid().ToString("N")
}

$image = "gcr.io/$ProjectId/$ImageName"
$envPairs = @(
    "BIZTOGMAIL_GCP_PROJECT=$ProjectId",
    "GOOGLE_OIDC_CLIENT_ID=$($json.web.client_id)"
)

if ($RedirectUri) {
    $envPairs += "GOOGLE_OIDC_REDIRECT_URI=$RedirectUri"
}
$envVarString = $envPairs -join ","

function Set-SecretValue {
    param(
        [string]$SecretName,
        [string]$SecretValue
    )

    if (-not $SecretValue) {
        return
    }

    $secretExists = $true
    try {
        $null = & gcloud secrets describe $SecretName --project $ProjectId 2>$null
    }
    catch {
        $secretExists = $false
    }

    if (-not $secretExists) {
        & gcloud secrets create $SecretName --project $ProjectId --replication-policy automatic | Out-Null
        if ($LASTEXITCODE -ne 0) {
            throw "Failed to create secret: $SecretName"
        }
    }

    $tempFile = [System.IO.Path]::GetTempFileName()
    try {
        [System.IO.File]::WriteAllText($tempFile, $SecretValue, [System.Text.UTF8Encoding]::new($false))
        & gcloud secrets versions add $SecretName --project $ProjectId --data-file=$tempFile | Out-Null
        if ($LASTEXITCODE -ne 0) {
            throw "Failed to add secret version: $SecretName"
        }
    }
    finally {
        if (Test-Path $tempFile) {
            Remove-Item -LiteralPath $tempFile -Force
        }
    }
}

$secretPairs = @(
    "BIZTOGMAIL_SESSION_SECRET=${SessionSecretName}:latest",
    "BIZTOGMAIL_SCHEDULER_TOKEN=${SchedulerTokenName}:latest",
    "GOOGLE_OIDC_CLIENT_SECRET=${OidcClientSecretName}:latest"
)

Set-SecretValue -SecretName $SessionSecretName -SecretValue $SessionSecret
Set-SecretValue -SecretName $SchedulerTokenName -SecretValue $SchedulerToken
Set-SecretValue -SecretName $OidcClientSecretName -SecretValue $json.web.client_secret

if ($DatabaseUrl) {
    Set-SecretValue -SecretName $DatabaseUrlSecretName -SecretValue $DatabaseUrl
    $secretPairs += "DATABASE_URL=${DatabaseUrlSecretName}:latest"
}

Write-Host "Deploying Cloud Run service..."
Write-Host "Project: $ProjectId"
Write-Host "Region: $Region"
Write-Host "Service: $ServiceName"
Write-Host "Image: $image"
Write-Host "SchedulerToken: $SchedulerToken"
if ($RedirectUri) {
    Write-Host "RedirectUri: $RedirectUri"
}
if ($DatabaseUrl) {
    Write-Host "DatabaseUrlSecret: $DatabaseUrlSecretName"
}
if ($CloudSqlInstance) {
    Write-Host "CloudSqlInstance: $CloudSqlInstance"
}
Write-Host "SessionSecretName: $SessionSecretName"
Write-Host "SchedulerTokenName: $SchedulerTokenName"
Write-Host "OidcClientSecretName: $OidcClientSecretName"

$deployArgs = @(
    "run", "deploy", $ServiceName,
    "--image", $image,
    "--region", $Region,
    "--platform", "managed",
    "--allow-unauthenticated",
    "--set-env-vars=$envVarString"
)

if ($CloudSqlInstance) {
    $deployArgs += @("--add-cloudsql-instances", $CloudSqlInstance)
}

& gcloud @deployArgs

function Update-ServiceSecret {
    param(
        [string]$EnvName,
        [string]$SecretRef
    )

    & gcloud run services update $ServiceName --region $Region --update-secrets "${EnvName}=${SecretRef}" | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to update Cloud Run secret binding: $EnvName"
    }
}

Update-ServiceSecret -EnvName "BIZTOGMAIL_SESSION_SECRET" -SecretRef "${SessionSecretName}:latest"
Update-ServiceSecret -EnvName "BIZTOGMAIL_SCHEDULER_TOKEN" -SecretRef "${SchedulerTokenName}:latest"
Update-ServiceSecret -EnvName "GOOGLE_OIDC_CLIENT_SECRET" -SecretRef "${OidcClientSecretName}:latest"
if ($DatabaseUrl) {
    Update-ServiceSecret -EnvName "DATABASE_URL" -SecretRef "${DatabaseUrlSecretName}:latest"
}
