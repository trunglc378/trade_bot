param(
    [string]$Server = '54.66.15.21',
    [string]$KeyPath = (Join-Path $PSScriptRoot '../docs/bot_trade.pem')
)
$ErrorActionPreference = 'Stop'
$resolvedKey = (Resolve-Path -LiteralPath $KeyPath).Path
$sshArgs = @(
    '-i', ('"' + $resolvedKey + '"'), '-N',
    '-o', 'BatchMode=yes', '-o', 'ExitOnForwardFailure=yes',
    '-o', 'ServerAliveInterval=30', '-o', 'ServerAliveCountMax=3',
    '-L', '127.0.0.1:8080:127.0.0.1:8080',
    '-L', '127.0.0.1:8081:127.0.0.1:8081',
    '-L', '127.0.0.1:8090:127.0.0.1:8090',
    ('ubuntu@' + $Server)
)
foreach ($port in @(8080, 8081, 8090)) {
    if (Get-NetTCPConnection -State Listen -LocalPort $port -ErrorAction SilentlyContinue) {
        throw "Local port $port is already in use. Check existing tunnels or local servers first."
    }
}
$tunnel = Start-Process -FilePath 'ssh.exe' -ArgumentList $sshArgs -WindowStyle Hidden -PassThru
try {
    $ready = $false
    for ($attempt = 0; $attempt -lt 20; $attempt++) {
        Start-Sleep -Milliseconds 500
        if ($tunnel.HasExited) { throw 'SSH tunnel exited; check server IP, security group and key permissions.' }
        $listeners = @(Get-NetTCPConnection -State Listen -LocalPort 8080,8081,8090 -ErrorAction SilentlyContinue |
            Where-Object { $_.OwningProcess -eq $tunnel.Id })
        if ($listeners.Count -eq 3) { $ready = $true; break }
    }
    if (-not $ready) { throw 'SSH tunnel did not become ready.' }
    Write-Host "SSH tunnel PID: $($tunnel.Id). To close: Stop-Process -Id $($tunnel.Id)"
    Write-Host 'Dashboard: http://127.0.0.1:8090'
    Write-Host 'Binance API: http://127.0.0.1:8080 | OKX API: http://127.0.0.1:8081'
    Write-Host 'Credentials: freqtrade-bot/user_data/deployment-access.private.json (keep private).'
    Start-Process 'http://127.0.0.1:8090'
} catch {
    if (-not $tunnel.HasExited) { Stop-Process -Id $tunnel.Id }
    throw
}
