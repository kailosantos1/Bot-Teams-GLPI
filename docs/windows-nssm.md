# Build e execução unificada no Windows

Não havia comando/spec de PyInstaller no repositório inspecionado. `otto.spec`
passa a definir um executável one-file com console para encerramento por NSSM.
Não inclui .env, YAML nem bancos: são arquivos externos persistentes.

Na raiz do projeto, **no Windows**, com dependências e PyInstaller disponíveis:

```powershell
.\venv\Scripts\python.exe -m PyInstaller --clean --noconfirm .\otto.spec
```

O build Windows não pode ser homologado por um build Linux. Não foi instalado
PyInstaller nem executado esse build nesta revisão.

Exemplo de instalação existente em `C:\Otto`:

- Application do NSSM: `C:\Otto\Otto.exe` (artefato `dist\Otto.exe`).
- AppDirectory / Startup directory: `C:\Otto`.
- Configuração: `C:\Otto\.env` e `C:\Otto\config\forms.yaml`.
- Banco padrão: `C:\Otto\data\identity.sqlite3`; `IDENTITY_DB_PATH` absoluto
  mantém o banco em outro local. Nunca substituir por banco vazio ou executar
  init para contornar um banco ausente.

Com o Prompt de Comando elevado e `nssm.exe` disponível no PATH:

```bat
nssm install Otto "C:\Otto\Otto.exe"
nssm set Otto AppDirectory "C:\Otto"
nssm set Otto AppNoConsole 0
nssm set Otto AppStopMethodSkip 0
nssm set Otto AppStopMethodConsole 180000
nssm set Otto Start SERVICE_AUTO_START
```

`AppDirectory` é o diretório de trabalho concreto. O console deve permanecer
habilitado para o primeiro método de parada ser Control-C. Os demais métodos
continuam habilitados como fallback do NSSM. O tempo de 180 segundos se aplica
à espera após Control-C; validar esse valor no NSSM instalado e ajustar à maior
latência observada, pois o ciclo não tem prazo absoluto para uma thread presa.

Antes de trocar de instalação, conferir o caminho efetivo do banco atual e
preservá-lo, inclusive backup consistente e ACL da conta do serviço. Para
manter um banco fora dessa pasta, configurar seu caminho absoluto existente.
Atualizar somente o executável; não sobrescrever .env, config ou data. Nenhuma
migração/cópia de banco real foi realizada nesta revisão.

Em código-fonte a raiz é o diretório do projeto; congelado é o diretório do
executável. O cwd e `_MEIPASS` não definem caminhos persistentes. Variáveis do
ambiente continuam tendo precedência sobre .env. Não colocar segredos no spec.

Usar um único processo Uvicorn, sem reload. O startup inicia o manager somente
quando habilitado e com política válida. Manager e CLI usam um lock OS no
arquivo `<caminho-absoluto-do-banco>.notifications.lock`, com flock no Linux e
msvcrt.locking no Windows. O arquivo permanece após release; não apagá-lo.
O lease SQLite continua sendo uma segunda barreira por ciclo. A CLI contra o
mesmo banco é recusada enquanto o manager detém o lock, inclusive administração;
parar o serviço antes de pause/resume/cleanup pela CLI.

O shutdown espera o ciclo corrente e os trabalhos em threads terminarem;
não cancela após 15 segundos e não inicia outro ciclo após solicitar parada.
120 segundos são orçamento cooperativo, não prazo absoluto de HTTP/encerramento.
Requests pode ultrapassá-lo, especialmente com corpo lento. Confira efetivamente
a sequência de parada usada pela versão instalada. Isso não garante um limite
absoluto: se o NSSM avançar aos métodos seguintes e matar o processo, a
recuperação continua conservadora.
Envios marcados submitting sem confirmação recuperam como uncertain, sem retry
automático. Não apagar leases/reservas para forçar reenvio.

Pendente no Windows: executar build, iniciar executável pela conta NSSM, validar
carregamento dos arquivos externos e banco existente, disputa real entre dois
processos msvcrt, parada normal e forçada durante envio, certificados/imports SDK
e renderização Teams. Testes Linux com API msvcrt simulada validam o protocolo
(chave byte zero, unlock, arquivo persistente), não o kernel Windows nem NSSM.
