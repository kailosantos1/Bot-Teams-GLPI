# Byte Bot de Chamados

Bot do Microsoft Teams para abrir chamados no GLPI via Formcreator, consultar chamados do próprio requerente, ler acompanhamentos públicos e enviar respostas textuais confirmadas. Notificações públicas do suporte são opcionais e vêm desabilitadas. Integração real deve ser homologada antes de disponibilizar os novos fluxos.

## Instalação e configuração

Requer Python 3.12, uma aplicação Bot Framework/Teams configurada, acesso à API REST do GLPI e plugin Formcreator. Execute os comandos na raiz do repositório:

```sh
python3 -m venv venv
. venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
```

Preencha `.env` com as configurações do seu ambiente. O modelo contém todas as variáveis aceitas em `config.py`: credenciais Microsoft/GLPI, tenant permitido, caminho do SQLite e opções de notificações. Nunca publique `.env`, tokens, bancos ou backups.

Configure o endpoint do bot no Teams como uma URL HTTPS pública terminada em `/api/messages`. O processo local escuta na porta 3000; configure proxy HTTPS/registro do aplicativo conforme sua infraestrutura. Formulários, IDs de perguntas/opções e dependências estão em `config/forms.yaml` e precisam corresponder ao GLPI implantado. A autorização legada de domínio/cadastro está em `bot/auth.py`.

## Execução

```sh
venv/bin/python main.py
```

Endpoints: `POST /api/messages`, `GET /health` e `GET /api/status`. Saúde HTTP não comprova autenticação ou integração com Teams/GLPI. Use instância única e disco local persistente: sessões/formulários ficam em memória e se perdem em reinícios; vínculos, auditoria e filas ficam no SQLite. Não há suporte a múltiplas réplicas compartilhando esse estado.

## Vínculos e manutenção

Para consulta/resposta, configure `IDENTITY_ALLOWED_TENANT_ID`, inicialize o banco e aprove administrativamente a correspondência exata entre tenant/object ID do Entra e usuário GLPI ativo. Nome de exibição e e-mail digitado não comprovam identidade. Tenant permitido vazio desabilita esse caminho; abertura legada continua independente do vínculo.

```sh
venv/bin/python -m tools.identity_links init
venv/bin/python -m tools.identity_links create --help
venv/bin/python -m tools.identity_links revoke --help
venv/bin/python -m tools.identity_links replace --help
```

`create` e `replace` consultam o GLPI real. `get` e `audit` inspecionam vínculos; `revoke` revoga o vínculo. Use os parâmetros exibidos por `--help`, com IDs reais conferidos e referência da aprovação. Não há criação automática de vínculos.

Migrações incrementais estão no código e preservam vínculos/auditoria/operações existentes. Faça backup antes de atualizar; proteja banco, referências pessoais e backups por permissões do sistema. Não execute versões antigas incompatíveis com o esquema atualizado. O caminho padrão é `data/identity.sqlite3`.

Limpeza local de respostas expiradas e metadados de notificações:

```sh
venv/bin/python -m tools.reply_operations --db data/identity.sqlite3
venv/bin/python -m tools.notifications cleanup --db data/identity.sqlite3
```

Respostas têm prazo absoluto de quinze minutos e metadados por sete dias. Notificações conservam eventos por sete dias e desabilitam referências sem captura autenticada por trinta dias; marcos ativos permanecem para evitar repetição de histórico. Limpeza depende da execução das rotinas e não apaga fisicamente páginas/backups. Envios de resultado incerto não são repetidos automaticamente.

O utilitário administrativo legado `Extensoes/Cadastrar Emails/cadastrar_emails_glpi.py` também é preservado. Ele altera e-mails no GLPI em modo de escrita; não faz parte da inicialização do bot e não deve ser executado como teste.

## Notificações opcionais

Além das credenciais existentes, configure `NOTIFICATIONS_ENABLED=true`, `NOTIFICATIONS_SUPPORT_IDS` com IDs GLPI humanos de suporte e `NOTIFICATIONS_INTEGRATION_IDS` com todas as contas da integração/automações, inclusive a conta de `GLPI_USER_TOKEN`. As listas devem ser não vazias e disjuntas. Autores desconhecidos, integração, destinatário e mensagens privadas não geram avisos. Homologue contratos/permissões da versão GLPI implantada; o código se baseia no GLPI 10.0.18 REST v1.

O usuário deve consultar seus chamados em conversa pessoal autenticada com o bot e ter vínculo confirmado. Isso registra a referência; a primeira observação completa de cada ticket estabelece uma linha de base sem enviar histórico. O worker revalida destinatário/requerente/status/publicidade antes de avisar e envia apenas número/título sanitizado, com botão para abrir o chamado após nova autorização.

Execute em **processo dedicado**, separado do Uvicorn:

```sh
venv/bin/python -m tools.notifications once
venv/bin/python -m tools.notifications run --interval 60
venv/bin/python -m tools.notifications once --simulate
```

`--simulate` não envia Teams, mas **consulta o GLPI e grava linha de base/fila** se configurado; não é um teste offline. Não habilite envios após simulação sem revisar/descartar essas pendências. Há limites por ciclo, lease exclusivo de quinze minutos e recuperação conservadora de reservas. Timeout/queda após possível envio fica incerto, sem reenvio cego; não há garantia de entrega exatamente uma vez.

Para pausar ou reativar um destinatário, substitua os marcadores pelos IDs administrativos conferidos:

```sh
venv/bin/python -m tools.notifications pause --tenant TENANT_ID --object-id OBJECT_ID
venv/bin/python -m tools.notifications resume --tenant TENANT_ID --object-id OBJECT_ID
```

Pause remove a referência e descarta pendências ainda não enviadas. Resume exige nova consulta pessoal autenticada e cria nova geração/linha de base, sem recuperar fila antiga. Para revogar também consulta/resposta, use `tools.identity_links revoke`.

Pare o processo com SIGINT/SIGTERM. Após interrupção abrupta, aguarde o lease/reservas; não os apague para forçar envio. Apenas parar/reiniciar conserva o backlog. Para retomar sem histórico, use pause/resume nos destinatários antes de habilitar novamente. Para desativar globalmente, pare o processo dedicado e deixe `NOTIFICATIONS_ENABLED=false`, sem remover credenciais compartilhadas pela abertura.
