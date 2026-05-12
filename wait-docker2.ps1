$docker = 'C:\Program Files\Docker\Docker\resources\bin\docker.exe'
for ($i = 0; $i -lt 24; $i++) {
    Start-Sleep -Seconds 5
    $result = & $docker info --format '{{.ServerVersion}}' 2>&1
    if ($LASTEXITCODE -eq 0 -and $result -notmatch 'error' -and $result -notmatch 'Error') {
        Write-Host "Docker engine ready: $result"
        exit 0
    }
    Write-Host "Still waiting for Docker engine... attempt $i"
}
Write-Host "Docker engine not ready after 2 minutes"
exit 1
