$rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
$bytes = New-Object byte[] 32
$rng.GetBytes($bytes)
$hex = -join ($bytes | ForEach-Object { $_.ToString("x2") })
Write-Host $hex
