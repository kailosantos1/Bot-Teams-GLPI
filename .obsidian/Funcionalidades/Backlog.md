# Backlog e Melhorias

## Itens Pendentes (conforme documentação)

### Homologação Necessária
- [ ] **JWT/TeamsInfo em produção**: Validar resolução de identidade no ambiente real
- [ ] **Contrato GLPI implantado**: Conferir versão exata, permissões, entidades
- [ ] **Renderização no Teams**: Validar HeroCards em desktop/mobile
- [ ] **Permissões Group_User**: Confirmar visibilidade completa para classificação por grupos
- [ ] **IDs crescentes GLPI**: Validar premissa para notificações

### Melhorias Técnicas
- [ ] **Persistência de navegação**: NavState em memória se perde em reinício (atual intencional)
- [ ] **Suporte a múltiplas réplicas**: SQLite não suporta (atual limitação documentada)
- [ ] **Transações distribuídas**: Gap entre leitura e ação em notificações
- [ ] **Garantia exatamente-uma-vez**: Não garantida para respostas uncertain
- [ ] **Deduplicação persistente**: Atual apenas em memória (últimos 100)

### Funcionalidades Futuras
- [ ] **Anexos na consulta/resposta**: Fora do escopo atual
- [ ] **Novos gatilhos para notificações**: Fora do escopo
- [ ] **Histórico completo**: Apenas público implementado
- [ ] **Notificações por status**: Não implementadas
- [ ] **Suporte a canais/grupos**: Intencionalmente restrito a conversa pessoal

## Limitações Conhecidas

| Limitação           | Impacto                                 | Mitigação                           |
| ------------------- | --------------------------------------- | ----------------------------------- |
| MemoryStorage       | Perde estados em reinício               | Usuário precisa recomeçar fluxo     |
| SQLite local único  | Não funciona com réplicas               | Usar instância única                |
| Autorização legada  | Baseada em domínio/nome                 | Em transição para identidade segura |
| Anexos em memória   | Perdidos em reinício durante formulário | Aviso implícito no fluxo            |
| Notificações opt-in | Requer configuração manual              | Desabilitado por padrão             |

## Roadmap Sugerido

1. **Curto Prazo**: Homologação em ambiente real, ajuste fino de cartões
2. **Médio Prazo**: Migrar navegação para persistência se necessário, melhorar observabilidade
3. **Longo Prazo**: Considerar Redis para multi-instância, implementar anexos em consulta
