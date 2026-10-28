# Serviço Windows NSSM

## Serviço existente
- Nome: `GLPI_Teams_Otto`.

## Consultar/configurar
```bat
nssm get GLPI_Teams_Otto Application
nssm get GLPI_Teams_Otto AppDirectory
nssm get GLPI_Teams_Otto AppParameters
```

## Parâmetros aplicáveis
- `Application`: caminho do executável.
- `AppDirectory`: diretório de trabalho (onde estão `.env`, `config/`, `data/`).
- `AppNoConsole`: 0 para manter console (necessário para parada por console).
- `AppStopMethodConsole`: timeout após Control-C (ex.: 180000 ms).
- `Start`: `SERVICE_AUTO_START`.

## Conta e permissões
- Leitura: `.env`, `config/forms.yaml`, executável e bibliotecas.
- Escrita: somente `data/identity.sqlite3` (e `-wal`/`-shm`), lock e logs, se houver.
- Preservar ACL do banco existente em atualizações.
- Não conceder escrita desnecessária em `.env` ou `config/`.

## console=True vs console=False
- Com `console=True`: parada por console é aplicável; NSSM pode enviar Control-C.
- Com `console=False`: não recomendar mecanismos de parada por console como garantidos; usar métodos de processo do NSSM e validar.

## Inicialização, logs e encerramento
- Um único processo Uvicorn, sem reload.
- Startup inicia manager apenas se habilitado e política válida.
- Shutdown aguarda ciclo corrente e threads; sem cancelamento por timeout após o marcador `submitting`.

## Referências
- [[04 - Gerar executável]], [[06 - Atualização e backup]], [[07 - Diagnóstico de problemas]]
