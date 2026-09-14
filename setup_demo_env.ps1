# CampusConnect local/demo SMTP configuration helper.
# Enter the Gmail App Password when prompted; it is written only to .env.local.
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$gmail = Read-Host "CampusConnect sender Gmail address"
$appPassword = Read-Host "Google App Password (hidden)" -AsSecureString
$ptr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($appPassword)
try { $plain = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($ptr) } finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ptr) }
@"
CAMPUSCONNECT_EMAIL_MODE=smtp
CAMPUSCONNECT_SMTP_HOST=smtp.gmail.com
CAMPUSCONNECT_SMTP_PORT=587
CAMPUSCONNECT_SMTP_USERNAME=$gmail
CAMPUSCONNECT_SMTP_APP_PASSWORD=$plain
CAMPUSCONNECT_SMTP_FROM_NAME=Campus Connect
CAMPUSCONNECT_ENV=development
"@ | Set-Content -Path (Join-Path $root '.env.local') -Encoding UTF8
Write-Host "Created .env.local. It is ignored by Git and should never be committed."
