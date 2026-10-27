# Comando somente leitura - execute no servidor onde o bot roda
# Não exibe tokens/credenciais. Usa configuração do ambiente do bot.
# Salva o content bruto do ticket #1033 em UTF-8 sem BOM

param(
  [int]$TicketId = 1033,
  [string]$OutFile = "ticket_$TicketId_content_raw.txt"
)

# Carrega variáveis do ambiente (ou .env conforme configuração)
$GLPI_URL = $env:GLPI_URL
$GLPI_APP_TOKEN = $env:GLPI_APP_TOKEN
$GLPI_USER_TOKEN = $env:GLPI_USER_TOKEN

if (-not $GLPI_URL -or -not $GLPI_APP_TOKEN -or -not $GLPI_USER_TOKEN) {
  Write-Error "Configure GLPI_URL, GLPI_APP_TOKEN e GLPI_USER_TOKEN no ambiente antes de executar."
  exit 1
}

# Inicializa sessão
$initHeaders = @{
  "Content-Type" = "application/json"
  "App-Token" = $GLPI_APP_TOKEN
  "Authorization" = "user_token $GLPI_USER_TOKEN"
}
$init = Invoke-RestMethod -Method Post -Uri "$($GLPI_URL.TrimEnd('/'))/initSession" -Headers $initHeaders -TimeoutSec 30
$sessionToken = $init.session_token

try {
  $headers = @{
    "Content-Type" = "application/json"
    "App-Token" = $GLPI_APP_TOKEN
    "Session-Token" = $sessionToken
    "X-GLPI-Sanitized-Content" = "false"
  }
  # Busca ticket completo (somente leitura)
  $uri = "$($GLPI_URL.TrimEnd('/'))/Ticket/$TicketId?get_hateoas=false"
  $resp = Invoke-RestMethod -Method Get -Uri $uri -Headers $headers -TimeoutSec 30
  # Salva apenas o campo content em UTF-8
  $content = $resp.content
  if ($null -eq $content) {
    $content = ""
  }
  [System.IO.File]::WriteAllText((Join-Path -Path (Get-Location) -ChildPath $OutFile), $content, [System.Text.UTF8Encoding]::new($false))
  Write-Output "Salvo em $OutFile (somente leitura)"
}
finally {
  try {
    $killHeaders = @{
      "App-Token" = $GLPI_APP_TOKEN
      "Session-Token" = $sessionToken
    }
    Invoke-RestMethod -Method Get -Uri "$($GLPI_URL.TrimEnd('/'))/killSession" -Headers $killHeaders -TimeoutSec 10 | Out-Null
  } catch {}
}
