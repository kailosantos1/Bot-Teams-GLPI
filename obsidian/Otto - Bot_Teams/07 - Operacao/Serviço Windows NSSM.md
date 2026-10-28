# Serviço Windows com NSSM

[[obsidian/07 - Operacao/Indice|← Operação]] · [[obsidian/Inicio|Início]]

Este vault tinha notas sobre um serviço `GLPI_Teams_Otto` e parâmetros NSSM. O nome/configuração não são comprovados por código versionado; verifique no Windows com o administrador antes de operar o serviço.

## Campos a verificar

- `Application`: caminho do executável.
- `AppDirectory`: diretório de trabalho que contém configuração e dados persistentes.
- `AppParameters`: argumentos, se houver.
- Conta do serviço e permissões de leitura/escrita, particularmente do banco, diretório `data` e logs.
- Um único processo Uvicorn, sem reload/múltiplos workers.

Comandos anteriores apenas identificados na nota, não executados:

```bat
nssm get GLPI_Teams_Otto Application
nssm get GLPI_Teams_Otto AppDirectory
nssm get GLPI_Teams_Otto AppParameters
```

## Parada e manutenção

`otto.spec` está atualmente `console=False`; não conte com Control-C como método de parada garantido. O shutdown do worker espera operações e threads. Prove a configuração e a parada real em ambiente Windows autorizado antes de atualizar ou reiniciar.

Notas anteriores também mencionavam `AppNoConsole`, `AppStopMethodConsole` e `SERVICE_AUTO_START`. Essas escolhas não foram confirmadas no serviço real e não devem ser copiadas automaticamente: como o spec atual define `console=False`, o método de parada por console precisa ser validado na instalação efetiva.

[[obsidian/07 - Operacao/Build PyInstaller|Build]] · [[obsidian/07 - Operacao/Atualização e backup|Backup]]
