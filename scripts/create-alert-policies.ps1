[CmdletBinding()]
param(
    [string]$ProjectId = "biztogmail"
)

$ErrorActionPreference = "Stop"

$policyFiles = @(
    "monitoring\\cloud-run-5xx-policy.json",
    "monitoring\\scheduler-tick-log-policy.json"
)

foreach ($policyFile in $policyFiles) {
    Write-Host ""
    Write-Host "Creating alert policy from $policyFile" -ForegroundColor Cyan
    gcloud alpha monitoring policies create --project $ProjectId --policy-from-file $policyFile
}
