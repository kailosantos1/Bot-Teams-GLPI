# Instalação e configuração

[[obsidian/06 - Desenvolvimento/Indice|← Desenvolvimento]] · [[obsidian/Inicio|Início]]

## Passos documentados

O README identifica o uso de Python 3.12 e estes comandos para ambiente Linux/macOS:

```sh
python3 -m venv venv
. venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
```

Estes comandos foram identificados em [README.md](../../../README.md), não executados como parte desta documentação. No Windows, ativação e executável virtualenv variam; as notas operacionais mantêm exemplos Windows.

## Configurações aceitas

Somente nomes de variáveis são listados; segredos são preenchidos pelo operador em `.env` ou ambiente do processo.

| Nome | Default observado | Uso |
|---|---|---|
| `MICROSOFT_APP_ID` | vazio | Aplicação Bot Framework |
| `MICROSOFT_APP_PASSWORD` | vazio | Credencial do bot |
| `MICROSOFT_APP_TENANT_ID` | vazio | Tenant do provider/bot |
| `GLPI_URL` | vazio | Base da API REST GLPI |
| `GLPI_APP_TOKEN` | vazio | App Token GLPI |
| `GLPI_USER_TOKEN` | vazio | User Token GLPI |
| `IDENTITY_ALLOWED_TENANT_ID` | vazio | Tenant permitido pela consulta/resposta |
| `IDENTITY_AUTO_LINK_ENABLED` | `false` | Opt-in para associação exata por e-mail autenticado |
| `IDENTITY_DB_PATH` | `data/identity.sqlite3` | Banco persistente relativo à raiz de deploy |
| `NOTIFICATIONS_ENABLED` | `false` | Ativa worker quando configuração completa |
| `NOTIFICATIONS_SUPPORT_GROUP_IDS` | vazio | IDs GLPI de grupos autores permitidos |
| `NOTIFICATIONS_INTEGRATION_IDS` | vazio | IDs GLPI de usuários de integração excluídos |
| `NOTIFICATIONS_INTERVAL` | `10` | Intervalo de ciclo em segundos; worker aplica faixa válida |

Fonte de defaults: [config.py](../../../config.py#L28). `.env.example` é o modelo versionado. Nunca commitar `.env`, banco ou backups.

## Ordem de configuração operacional

1. Validar conectividade/permissões do Bot Framework e GLPI no ambiente homologado.
2. Ajustar `config/forms.yaml` para IDs e opções efetivos do Formcreator.
3. Definir `IDENTITY_ALLOWED_TENANT_ID` para consultas; vazio bloqueia esse caminho.
4. Inicializar e proteger o banco SQLite. Criar vínculos pela CLI aprovada ou habilitar conscientemente a política automática.
5. Ativar notificações somente depois de definir grupos e contas de integração corretos.

Detalhes de vínculo e ferramentas em [[obsidian/02 - Modulos/Identidade|Identidade]] e [[obsidian/02 - Modulos/Ferramentas e scripts|Ferramentas]].
