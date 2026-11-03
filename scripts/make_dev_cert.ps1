# Creates a SELF-SIGNED certificate for local HTTPS testing (for example opening the app on your phone over Wi-Fi, where
# browsers only allow the camera on https). Not for the internet: browsers will warn that it is not trusted.
# Output: certs\dev.pem and certs\dev-key.pem (git-ignored). Needs openssl (it ships with Git for Windows).
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$certs = Join-Path $root "certs"
New-Item -ItemType Directory -Force $certs | Out-Null

$openssl = (Get-Command openssl -ErrorAction SilentlyContinue).Source
if (-not $openssl) {
  foreach ($p in "C:\Program Files\Git\usr\bin\openssl.exe", "C:\Program Files\Git\mingw64\bin\openssl.exe") { if (Test-Path $p) { $openssl = $p; break } }
}
if (-not $openssl) { throw "openssl not found. Install Git for Windows (includes openssl) or add openssl to PATH." }

# every IPv4 address of this computer goes into the certificate, so https://<your-ip>:5173 matches it
$ips = Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue | Where-Object { $_.IPAddress -notlike "169.254.*" } | ForEach-Object { $_.IPAddress } | Sort-Object -Unique
$san = @("DNS:localhost") + ($ips | ForEach-Object { "IP:$_" })
if ($san -notcontains "IP:127.0.0.1") { $san += "IP:127.0.0.1" }

$cfg = Join-Path $certs "openssl.cnf"
@"
[req]
distinguished_name = dn
x509_extensions = v3
prompt = no
[dn]
CN = ARVR local development
[v3]
subjectAltName = $($san -join ",")
basicConstraints = CA:FALSE
keyUsage = digitalSignature, keyEncipherment
extendedKeyUsage = serverAuth
"@ | Set-Content -Encoding ascii $cfg

$ErrorActionPreference = "Continue"  # openssl prints progress to stderr, which PowerShell 5.1 treats as an error
& $openssl req -x509 -newkey rsa:2048 -nodes -days 365 -keyout (Join-Path $certs "dev-key.pem") -out (Join-Path $certs "dev.pem") -config $cfg 2>$null
$code = $LASTEXITCODE
$ErrorActionPreference = "Stop"
if ($code -ne 0) { throw "openssl failed" }
Remove-Item $cfg
Write-Host "Created certs\dev.pem and certs\dev-key.pem for: $($san -join ', ')"
Write-Host "Valid for 365 days. Start the frontend with:  `$env:ARVR_HTTPS='1'; npm run dev -- --host"
Write-Host "Then open https://<this computer's IP>:5173 on your phone and accept the browser warning."
