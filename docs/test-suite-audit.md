# Auditoria da suíte local — 26/10/2026

A suíte atual completa passa: **191 testes, zero falhas, erros ou skips**, em ordem normal e inversa, em processos distintos. A correção dos cartões foi preservada. Isso valida lógica isolada e contratos locais do SDK; não homologa Teams/JWT/GLPI ou renderização no cliente.

## Ambiente confirmado

Interpretador: `/home/contratos/Documentos/VSCode/Bot-Teams-GLPI/venv/bin/python`, Python 3.12.3. Botbuilder core/schema e botframework connector 4.17.1, msrest 0.7.1, aiohttp 3.14.5. Esses são os mesmos números registrados na verificação anterior. Demais metadados atuais: FastAPI 0.162.0, Uvicorn 0.54.0, Requests 2.34.2, python-dotenv 1.2.4, PyYAML 6.0.3, Pydantic 2.14.1, pydantic-settings 2.16.1. Não existe inventário histórico completo para afirmar igualdade de todas as dependências daquela execução. Nenhum pacote instalado/atualizado; `pip check` aprovou.

As execuções completas usaram esse interpretador fora do sandbox devido ao travamento de encerramento de threads já documentado. O runner mantém bloqueio global de Requests, sockets de saída e aiohttp; fixtures podem substituí-los apenas por mocks locais. Não copia `.env`, bancos ou dados para snapshots históricos. Não houve consulta GLPI, envio Teams ou migração real.

## Por que 184, em vez dos 187 anteriores

O inventário encontrado tinha 180 testes de lógica: menu 23, identidade 21, SDK 10, consulta 16, serviço de consulta 10, detalhes 20, conversa 10, operações de resposta 11 e notificações 59. A correção visual acrescentou quatro: **180 + 4 = 184**.

O AGENTS.md anterior registrava 30 testes no menu. A diferença é exatamente sete nessa suíte: **187 − 7 + 4 = 184**. `tests/` está ignorado pelo Git, não existe manifesto histórico dos 187 IDs nem cópia recuperada dos sete casos ausentes. Portanto, não é possível identificar seus nomes originais, atribuir sua ausência a um commit ou afirmar que o conjunto antigo foi recuperado integralmente.

Foram acrescentados sete casos explícitos a partir dos requisitos documentados: payload inválido não avança formulário; confirmação antiga não cancela; botão de cancelamento sem confirmação pendente preserva formulário; menu em canal não apresenta cartão pessoal; continuar reapresenta confirmação sem perder respostas; callback do menu não faz busca legada e envia uma vez; descrição de formulário exige autorização legada. São **novos testes de regressão**, não uma cópia alegada dos antigos. O inventário atual tem 30 no menu e **191 no total**. Nenhum teste encontrado foi removido e nenhuma asserção de segurança foi relaxada.

## Causas e correções

O commit `e0579b0c1b887ac99afd5976bc162be874f6abe8` retirou de `main.py` e `bot/dialogs.py` código presente em `5c1bcb1`:

- O roteamento para `notification_actions.handle` e `ticket_consult.handle`, com prioridade dos formulários e preservação do texto de resposta.
- `needs_legacy_authorization`, a composição do adapter/provider/IdentityIngress compartilhados e o resolver limitado ao callback autenticado.
- Validação estrita de payloads e confirmação aleatória de interrupção; tratamento dos comandos em canais.
- Tratamento de erro sensível sem expor rascunho/exceção e interceptação da consulta antes dos logs legados de texto.

Sem o primeiro roteamento, escolher consulta devolve o cartão de negação temporária do menu, não inicializa TicketQueryState e nunca chega aos serviços mockados. Daí `KeyError: 'version'`, `NoneType is not subscriptable` em rascunhos e notificações, seleções interpretadas como abertura e dezenas de asserções de conteúdo/autorização em cascata. `AttributeError` de `needs_legacy_authorization` é uma evidência direta da remoção. Não eram erros no sanitizador ou no armazenamento SQL.

O commit `18ab4af2a4f508dd1d05f999529f4030e9dc534a` também retirou quatro campos de Settings: NOTIFICATIONS_ENABLED/SUPPORT_IDS/INTEGRATION_IDS/INTERVAL. A fixture de notificações fornecia uma configuração própria e não detectava essa ausência. Os quatro campos foram restaurados com os mesmos padrões seguros (desabilitado/listas vazias/60 segundos); o teste existente passou a conferir os defaults reais do modelo, sem ler credenciais.

`main.py`, `bot/dialogs.py` e `config.py` estão byte a byte iguais aos de `5c1bcb1` (hashes no JSON). A correção restaura a integração e proteções anteriores; não muda IDs/YAML/formulários/status/regras de negócio nem implementa uma etapa nova. Os quatro arquivos da correção visual permanecem alterados como na entrega anterior.

## Fixtures e isolamento

A suíte antiga do menu substituía somente os dois accessors de dialogs. Com a consulta novamente roteada, isso permitiria alcançar BotState real com contexto simplificado. Agora usa `install_state_mocks`, substituindo todas as referências de módulo consumidoras, compartilhando NavState entre dialogs e consulta, com estado novo por teste e `addCleanup` para restauração.

Três expectativas residuais de “consulta em preparação” foram substituídas pela negação segura quando não há resolver autenticado; botões válidos de confirmação nos testes existentes agora incluem o token realmente emitido. A retomada e o cancelamento continuam sendo verificados. O novo teste de confirmação antiga verifica a rejeição do token anterior.

A fixture AST do handler de erro não fornecia `traceback` e `send_error_message`. Na revisão defeituosa, isso produzia NameError artificial antes da asserção pretendida. Agora os globais estão definidos e o teste também exige que o remetente legado não seja chamado no caminho sensível. O erro real passa a ser uma asserção de proteção sensível, não uma ausência de import na fixture. Os callbacks AST do menu/cartões também receberam traceback para não mascarar exceções de diagnóstico.

O runner audita por identidade de objeto os accessors, serviços, funções de Requests/socket/aiohttp e TeamsInfo; verifica patches ativos e accessors de classe após cada teste, depois dos cleanups, e após a suíte. Também compara referências antes/depois de carregar os testes. Ambas as ordens terminaram sem vazamentos e sem importar `tests.test_menu` paralelamente ao `test_menu` do discovery. A ordem inversa contém exatamente os mesmos 191 IDs invertidos.

## Comparação controlada de fontes

Foram criadas cópias temporárias dos arquivos Python/YAML rastreados nas duas revisões, com cópias idênticas dos testes atuais. O JSON registra versões, hashes, IDs, exceções e tracebacks. Os quatro testes novos de cartão são executados nas suítes completas atuais; somente na comparação histórica de lógica são separados, pois exigem deliberadamente a correção visual ainda inexistente nessas revisões. Não foram excluídos da verificação final.

| Fontes | Casos | Falhas | Erros | Skips | Patches restaurados |
| --- | ---: | ---: | ---: | ---: | --- |
| 5c1bcb1, testes atuais de lógica | 187 | 0 | 0 | 0 | Sim |
| e0579b0, os mesmos testes/hashes | 187 | 33 | 20 | 0 | Sim |
| Workspace corrigido, todos | 191 | 0 | 0 | 0 | Sim |
| Workspace corrigido, todos em ordem inversa | 191 | 0 | 0 | 0 | Sim |

Os 187 atuais da comparação contêm os sete casos reconstruídos; esta execução não se apresenta como reprodução dos IDs históricos desconhecidos.

Além dos totais, comparei o log preservado da execução anterior de 184 casos/31 falhas/16 erros com o snapshot de e0579b0: **43 dos 47 registros** repetem ID, classe da exceção, mensagem e função/linha de código do último frame. Três registros deixam de falhar porque suas expectativas temporárias estavam obsoletas; o quarto, do handler sensível, passa de NameError artificial a AssertionError graças à fixture completa. O JSON identifica todos esses casos.

Os novos totais do snapshot são explicáveis: 31 falhas − 3 expectativas obsoletas + 4 falhas dos novos testes + 1 erro convertido em falha = 33; 16 erros + 2 testes existentes que agora exigem token de confirmação + 2 novos testes de confirmação + 1 verificação nova dos campos Settings − 1 erro convertido em falha = 20. Não se usou igualdade de totais como prova de equivalência.

Conclusão: os problemas antecediam a correção dos cartões na revisão e0579b0, mas **não** estavam presentes nas fontes de referência 5c1bcb1 sob o mesmo venv e os mesmos testes atuais de lógica. O diagnóstico anterior de “preexistente” era incompleto sem essa distinção.

## Reprodução e arquivos

```bash
venv/bin/python tests/run_suite_audit.py --report /tmp/suite-fixed.json
venv/bin/python tests/run_suite_audit.py --reverse --report /tmp/suite-reverse.json
venv/bin/python tests/run_suite_audit.py --revision 5c1bcb1 --exclude-cards --report /tmp/suite-reference.json
venv/bin/python tests/run_suite_audit.py --revision e0579b0 --exclude-cards --report /tmp/suite-regressed.json
venv/bin/python -m unittest discover -s tests -q
venv/bin/python -m pip check
```

O snapshot defeituoso retorna exit code 1, como esperado. Compilação Python e `git diff --check` aprovados.

Alterados nesta investigação: main.py, bot/dialogs.py, config.py, tests/test_menu.py, tests/test_notifications.py, tests/test_ticket_detail.py e tests/test_cards_sdk.py. Acrescentados tests/run_suite_audit.py e este relatório/JSON; AGENTS.md atualizado. tests/ e AGENTS.md continuam ignorados pela configuração Git existente, sem alteração de política ou staging automático. Preservar esses artefatos locais para que a suíte não volte a depender de arquivos fora do histórico.
