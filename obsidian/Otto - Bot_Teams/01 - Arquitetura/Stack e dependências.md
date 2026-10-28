# Stack e dependências

[[obsidian/01 - Arquitetura/Indice|← Arquitetura]] · [[obsidian/Inicio|Início]]

## Runtime declarado

O README descreve Python 3.12 e o projeto não contém metadados de empacotamento que imponham uma faixa de Python. `requirements.txt` declara:

| Dependência | Uso identificado |
|---|---|
| `fastapi` | Endpoint HTTP |
| `uvicorn` | Servidor ASGI |
| `botbuilder-core` | Adapter, estado, TurnContext e Teams |
| `requests` | Integrações REST GLPI e downloads |
| `python-dotenv` | Carregamento de `.env` por pydantic-settings |
| `pyyaml` | Leitura dos formulários |
| `pydantic-settings` | Settings e variáveis de ambiente |
| `aiohttp` | Transporte assíncrono importado pelo SDK/msrest; requisito mínimo e limite constam do manifesto |

As versões são faixas mínimas, exceto o limite de `aiohttp`; não há lockfile. Versões exatas observadas em relatos anteriores não garantem o venv ou servidor atuais.

## Configuração de runtime

[Settings](../../../config.py#L28) lê `.env` na raiz definida por [runtime_paths.py](../../../runtime_paths.py). O arquivo `.env.example` lista nomes de parâmetros, sem valores. A lista e os efeitos estão em [[obsidian/06 - Desenvolvimento/Configuração|Configuração]].

## Dependências não presentes no manifesto

- PyInstaller é requerido apenas para o build descrito no spec, mas não consta em `requirements.txt`.
- Não há dependência de framework de persistência ORM: SQLite é usado diretamente por `sqlite3`.
- Não foram encontrados manifests para container, migrations externas ou gerenciador de dependências com lock.

Esses pontos são constatações do inventário versionado; não provam ausência de ferramentas instaladas no ambiente de implantação.
