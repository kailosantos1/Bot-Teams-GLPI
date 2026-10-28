# Build com PyInstaller

[[obsidian/07 - Operacao/Indice|← Operação]] · [[obsidian/Inicio|Início]]

## Spec do checkout

O [otto.spec](../../../otto.spec) atual descreve build **onedir**, executável chamado `GLPI_Teams_Otto`, `console=False` e diretório `_internal`, com `main.py` como entrada. Isto corrige a nota antiga que descrevia one-file/`Otto.exe`; a configuração efetiva do servidor continua desconhecida.

Comando documentado nas notas operacionais para Windows:

```powershell
venv\Scripts\python.exe -m PyInstaller --clean --noconfirm .\otto.spec
```

PyInstaller não é declarado em `requirements.txt`; spec não foi executado nesta tarefa e não se afirma que o build funcione no Windows atual.

## Arquivos externos

O spec exclui `.env`, YAML de formulários e banco persistente do artefato. Mantenha `.env`, `config/forms.yaml`, `data/identity.sqlite3`, lock e logs no diretório de deploy adequado, acessíveis ao usuário do serviço. Caminhos de fonte/congelado são definidos em [runtime_paths.py](../../../runtime_paths.py).

## Limites

`console=False` está no spec, portanto as antigas instruções sobre Control-C/console não são garantia de parada. Validar logs, imports dinâmicos, certificados, arquivos externos e comportamento de shutdown em Windows antes de usar em produção.

[[obsidian/07 - Operacao/Serviço Windows NSSM|NSSM]] · [[obsidian/07 - Operacao/Atualização e backup|Atualização]]
