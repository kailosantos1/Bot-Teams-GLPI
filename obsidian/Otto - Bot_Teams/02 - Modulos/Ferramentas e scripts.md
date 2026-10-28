# Ferramentas e scripts

[[obsidian/02 - Modulos/Indice|← Módulos]] · [[obsidian/06 - Desenvolvimento/Testes|Testes]]

## CLI locais/administrativas

- `tools/identity_links.py`: `init`, `get`, `audit`, `create`, `revoke`, `replace`. Criação/substituição validam ID do GLPI via HTTP real; demais ações são locais, exceto inicialização do schema.
- `tools/notifications.py`: `once`, `run`, `pause`, `resume`, `cleanup`. `once --simulate` ainda pode consultar GLPI e gravar baseline/fila, portanto não é uma simulação offline.
- `tools/reply_operations.py`: limpeza local de conteúdo expirado e metadados antigos, requer banco existente.
- `tools/inspect_identity_configuration.py`: inspeção offline de presença/UUID/schema sem exibir valores ou linhas; `--db-path` imprime caminho resolvido.
- `tools/inspect_identity_sdk.py`: inspeção de versão, assinatura e modelos SDK; local, sem rede e sem carregar configuração.
- `tools/get_ticket_content.ps1`: utilitário PowerShell somente leitura para obter conteúdo de um ticket específico. Não foi executado nesta análise.

## Extensões legadas

- `Extensoes/Testar Formularios/testar_formularios.py` e `Extensoes/Testar Validacoes/testar_sistema_completo.py`: scripts de simulação antigos com mocks próprios; suas assinaturas/patches não equivalem à suíte isolada atual.
- `Extensoes/Formularios/perguntas.py` e `debug_question_options.py`: consultam GLPI real para inspecionar perguntas; não são testes offline.
- `Extensoes/Cadastrar Emails/cadastrar_emails_glpi.py`: contém caminho de escrita de endereços GLPI; não execute como teste.

Os scripts de `Extensoes/` foram examinados estaticamente e não executados. Não rode ferramentas que escrevem dados sem autorização e ambiente de teste isolado.
