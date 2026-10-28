# Gerar executável

## Build no Windows
```powershell
python -m PyInstaller --clean --noconfirm .\otto.spec
```

## Layouts: onefile vs onedir
- Atual (`otto.spec`): one-file. Gera `dist/Otto.exe` com binários/dados embutidos; não há pasta `_internal` separada.
- Desejado para produção: onedir. Gera pasta com executável e `_internal`; executável e `_internal` devem ser atualizados juntos, vindos do mesmo build.

## Spec atual
- `Analysis(['main.py'], ...)`
- `EXE(..., name='Otto', console=True)`
- Sem `COLLECT`.
- Artefato: `Otto.exe`, não `GLPI_Teams_Otto.exe`.

## Divergências documentadas
- Spec encontrado no repositório: one-file, `Otto.exe`, `console=True`.
- Configuração desejada/informada para Windows: onedir, `_internal`, `GLPI_Teams_Otto.exe`, `console=False`.
- Não foi conferido o spec ou executável do servidor; apenas o arquivo do repositório.
- Ajustar o spec é tarefa futura autorizada; não alterar código nesta tarefa.

## Arquivos externos necessários
- `.env`
- `config/forms.yaml`
- `data/identity.sqlite3` (se existir)
- `<banco>.notifications.lock` (não apagar)

## Caminhos persistentes
- Em fonte: raiz do projeto.
- Congelado: diretório do executável (`sys.executable`).
- `_MEIPASS` não define caminhos persistentes.

## Limitações de noconsole
- Sem console, não há entrada/saída de texto via stdin/stdout.
- Encerramento por Control-C não é garantido; usar NSSM/AppStopMethodConsole apenas se console=True.
- Logs dependem do logger e do serviço; validar comportamento real.
- Não considerar executável homologado sem teste real no Windows.
