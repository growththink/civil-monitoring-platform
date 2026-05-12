for ($i = 0; $i -lt 30; $i++) {
    Start-Sleep -Seconds 5
    try {
        $v = & 'C:\Program Files\Docker\Docker\resources\bin\docker.exe' info --format '{{.ServerVersion}}' 2>$null
        if ($LASTEXITCODE -eq 0) {
            Write-Host "Docker ready: $v"
            exit 0
        }
    } catch {}
    Write-Host "Waiting for Docker engine... ($i)"
}
Write-Host "Timeout waiting for Docker"
exit 1
