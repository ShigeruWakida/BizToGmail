[CmdletBinding()]
param(
    [string]$ProjectId = "biztogmail",
    [string]$Region = "asia-northeast1",
    [string]$ServiceName = "biztogmail",
    [string]$SchedulerJob = "biztogmail-tick",
    [string]$SqlInstance = "biztogmail-db",
    [int]$LogLimit = 20
)

$ErrorActionPreference = "Stop"

function Write-Section {
    param([string]$Title)
    Write-Host ""
    Write-Host "=== $Title ===" -ForegroundColor Cyan
}

Write-Host "BizToGmail cloud operations check" -ForegroundColor Green
Write-Host "Project: $ProjectId"
Write-Host "Region:  $Region"
Write-Host "Service: $ServiceName"
Write-Host "Job:     $SchedulerJob"
Write-Host "SQL:     $SqlInstance"

Write-Section "Cloud Run"
$run = gcloud run services describe $ServiceName --region $Region --project $ProjectId --format=json | ConvertFrom-Json
$runStatus = $run.status
Write-Host "URL:            $($runStatus.url)"
Write-Host "Latest Ready:   $($runStatus.latestReadyRevisionName)"
Write-Host "Latest Created: $($runStatus.latestCreatedRevisionName)"
Write-Host "Traffic:"
foreach ($traffic in $runStatus.traffic) {
    $rev = $traffic.revisionName
    $pct = $traffic.percent
    Write-Host "  - $rev : $pct%"
}

Write-Section "Cloud Scheduler"
$job = gcloud scheduler jobs describe $SchedulerJob --location $Region --project $ProjectId --format=json | ConvertFrom-Json
Write-Host "State:          $($job.state)"
Write-Host "Schedule:       $($job.schedule)"
Write-Host "Last Attempt:   $($job.lastAttemptTime)"
Write-Host "Next Schedule:  $($job.scheduleTime)"
if ($job.status) {
    Write-Host "Status Code:    $($job.status.code)"
}
if ($job.httpTarget -and $job.httpTarget.headers) {
    $headerNames = @($job.httpTarget.headers.PSObject.Properties.Name) -join ", "
    Write-Host "Headers:        $headerNames"
}

Write-Section "Cloud SQL"
$sql = gcloud sql instances describe $SqlInstance --project $ProjectId --format=json | ConvertFrom-Json
Write-Host "State:          $($sql.state)"
Write-Host "Region:         $($sql.region)"
Write-Host "Version:        $($sql.databaseVersion)"
Write-Host "ConnectionName: $($sql.connectionName)"
if ($sql.settings -and $sql.settings.backupConfiguration) {
    $backup = $sql.settings.backupConfiguration
    Write-Host "Backup Enabled: $($backup.enabled)"
    Write-Host "Backup Start:   $($backup.startTime)"
    if ($null -ne $backup.pointInTimeRecoveryEnabled) {
        Write-Host "PITR Enabled:   $($backup.pointInTimeRecoveryEnabled)"
    }
}

Write-Section "Recent Cloud Run Logs"
$filter = "resource.type=cloud_run_revision AND resource.labels.service_name=$ServiceName"
gcloud logging read $filter --project $ProjectId --limit $LogLimit --format="value(timestamp,textPayload,httpRequest.status)"
