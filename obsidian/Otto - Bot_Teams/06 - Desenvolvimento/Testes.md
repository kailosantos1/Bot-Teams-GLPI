# Testes e verificação local

[[obsidian/06 - Desenvolvimento/Indice|← Desenvolvimento]] · [[obsidian/Inicio|Início]]

## Suíte isolada atual

O runner [tests/run_offline_suite.py](../../../tests/run_offline_suite.py) descobre testes em `tests/` e bloqueia requests, sockets/DNS e o request aiohttp. O comando identificado nas notas e instruções do projeto é:

```sh
venv/bin/python -m tests.run_offline_suite
```

O comando não foi executado nesta tarefa. A revisão estática dos testes confirma mocks para Teams/GLPI e SQLite temporário em diversos módulos; essa suíte não valida JWT real, chamadas GLPI reais, cartões renderizados no cliente, nem produção.

## Grupos de casos

- Identidade manual, auto-link por e-mail, SDK, tenant e adapter: `test_identity.py`, `test_auto_link.py`, `test_identity_sdk.py`.
- Menu, formas de botão e transições do formulário: `test_menu.py`, `test_form_choices.py`, `test_maintenance_form.py`.
- Criação do FormAnswer e separação dos IDs: `test_form_creation_result.py`.
- Consulta, detalhes, privacidade, acompanhamento, respostas e deduplicação: `test_ticket_query.py`, `test_ticket_consult.py`, `test_ticket_detail.py`, `test_ticket_conversation.py`, `test_reply_operations.py`, `test_activity_attachments.py`.
- Notificações, grupos, transporte e execução unificada: `test_notifications.py`, `test_notification_groups.py`, `test_unified_notifications.py`.
- Cartões SDK e diagnósticos seguros: `test_cards_sdk.py`, `test_homologation_diagnostics.py`, `test_ticket_presentation.py`.
- `tests/support.py` fabrica contextos e accessors de teste; seu MockTurnContext não equivale a contexto real do SDK.

## Scripts de legado

Os dois scripts em `Extensoes/Testar...` não são o runner isolado e têm mocks/assinaturas antigas. Scripts de inspeção Formcreator e cadastro de e-mail em `Extensoes/` podem conectar ou escrever no GLPI; não foram executados. Veja [[obsidian/02 - Modulos/Ferramentas e scripts|Inventário de ferramentas]].

## Classificação da evidência

Uma passagem dos testes significa apenas comportamento coberto com fixtures/mocks no processo testado. Use [[obsidian/08 - Pendencias/Homologação|checklist de homologação]] para evidências externas. Testes e build não foram repetidos porque a tarefa alterou somente documentação.
