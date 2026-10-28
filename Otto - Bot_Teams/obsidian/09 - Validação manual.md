# Validação manual

## Roteiro curto
1. Abrir chamado por cada formulário.
2. Consultar chamados próprios.
3. Ver detalhes e conversa pública.
4. Responder e confirmar envio.
5. Verificar notificação de resposta de técnico.

## Isolamento
- Usuário A não acessa chamados do usuário B.
- Testar IDs manipulados, botões antigos e contexto diferente.

## Reinício e persistência
- Reiniciar serviço e verificar perda de sessão/navegação.
- Verificar persistência de vínculos e operações no SQLite.
- Verificar concorrência e parada do serviço.

## Conferência visual no Teams
- Cartões, botões, paginação, seleção/desmarcação, anexos.
- Testar desktop e móvel.
- Validar textos sem duplicação entre Activity.text e cartão.

## Referências
- [[01 - Funcionamento]], [[08 - Formulários GLPI]], [[07 - Diagnóstico de problemas]]
