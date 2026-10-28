# Mapa e cobertura

[[obsidian/Inicio|← Início]]

## Estrutura

| Pasta | Conteúdo |
|---|---|
| [[obsidian/01 - Arquitetura/Indice|01 — Arquitetura]] | Componentes, execução, dependências e limites arquiteturais |
| [[obsidian/02 - Modulos/Indice|02 — Módulos]] | Responsabilidades por pacote e fronteiras entre componentes |
| [[obsidian/03 - Fluxos/Indice|03 — Fluxos]] | Navegação, abertura, consulta/resposta e notificações |
| [[obsidian/04 - Dados/Indice|04 — Dados]] | Estado, banco SQLite, modelo de identidade e formulários |
| [[obsidian/05 - Interfaces e Integracoes/Indice|05 — Interfaces e integrações]] | HTTP do bot, Bot Framework e contratos REST do GLPI |
| [[obsidian/06 - Desenvolvimento/Indice|06 — Desenvolvimento]] | Configuração, instalação e testes |
| [[obsidian/07 - Operacao/Indice|07 — Operação]] | Execução, PyInstaller, NSSM, backup e diagnóstico |
| [[obsidian/08 - Pendencias/Indice|08 — Pendências]] | Homologação, incertezas e limitações |

## Registro de cobertura da leitura

Leitura estática da revisão presente no workspace; não foi iniciada a aplicação nem acessados serviços externos.

- **Entrada/configuração:** `main.py`, `config.py`, `config/forms.yaml`, `.env.example`, `requirements.txt`, `runtime_paths.py`, `README.md`, `.gitignore`.
- **Bot:** todos os módulos Python de `bot/`, incluindo formulários, estado, cartões, anexos, consulta, detalhes, respostas e ações de notificação.
- **Identidade:** todos os módulos de `identity/`, incluindo ingresso autenticado, resolução, banco, leitor GLPI, associação por e-mail e operações duráveis.
- **Notificações:** todos os módulos de `notifications/`, incluindo política, captura, worker, transporte e lifecycle.
- **Serviços:** `services/glpi_service.py`, `ticket_query.py`, `ticket_conversation.py`, `ticket_content.py` e `reply_sender.py`.
- **Operação e auxiliares:** ferramentas de `tools/`, `otto.spec` e scripts de `Extensoes/`; estes últimos foram lidos estaticamente, não executados.
- **Testes:** runner offline, suporte de mocks e módulos `tests/test_*.py`; casos examinados pela finalidade e nomes, sem executar a suíte nesta tarefa. `tests/` contém as verificações de identidade, formulários, consulta, resposta, notificações, SDK e transporte.
- **Documentação anterior:** README e notas preexistentes do vault foram revisados; conteúdo operacional útil foi incorporado às notas temáticas. O contrato de documentação longo `AGENTS.md` foi considerado como fonte de contexto, não como comprovação de runtime.
- **Exclusões deliberadas:** `.env`, venvs, caches, artefatos `build/`/`dist/`, bancos SQLite, executáveis e outros conteúdos gerados/binários. Nenhum valor de credencial foi consultado ou reproduzido.

## Como interpretar afirmações

- **Código confirma:** implementações e defaults observáveis no checkout.
- **Inferência:** interpretação sobre intenção ou comportamento composta a partir do código; indicada como inferência no texto.
- **Precisa confirmar:** depende de configuração do tenant, serviço GLPI/Teams, permissões ou execução no ambiente alvo.
- Comandos identificados em `README.md` ou notas anteriores são apresentados como documentados; nenhum comando de execução/build foi validado nesta leitura.

## Atalhos antigos mantidos

Os nomes planos anteriores foram preservados como redirecionamentos para não deixar referências e a navegação antiga sem destino:

- [[obsidian/00 - Índice|Índice antigo]]
- [[obsidian/01 - Funcionamento|Funcionamento antigo]]
- [[obsidian/02 - Instalação e configuração|Configuração antiga]]
- [[obsidian/03 - Execução e notificações|Execução antiga]]
- [[obsidian/04 - Gerar executável|Build antigo]]
- [[obsidian/05 - Serviço Windows NSSM|NSSM antigo]]
- [[obsidian/06 - Atualização e backup|Backup antigo]]
- [[obsidian/07 - Diagnóstico de problemas|Diagnóstico antigo]]
- [[obsidian/08 - Formulários GLPI|Formulários antigos]]
- [[obsidian/09 - Validação manual|Validação antiga]]
