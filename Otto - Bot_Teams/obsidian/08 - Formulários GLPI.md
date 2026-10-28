# Formulários GLPI

## Formulários atuais (config/forms.yaml)
- FlexSmart: ID 5, nome "Solicitações sistema FlexSmart".
- Manutenção: ID 1, nome "Solicitações de Manutenção".
- Cadastro de Novo Colaborador: ID 2, nome "Cadastro de Novo Colaborador".

## FlexSmart (ID 5)
Perguntas e condições conforme YAML:
- 106 tipo_atendimento (obrigatório): Liberação / Outro.
- 107 qual_liberacao (obrigatório, se tipo_atendimento=Liberação): Telas / Outros.
- 108 qual_tela (obrigatório, se qual_liberacao=Telas).
- 111 qual_liberacao_sistema (obrigatório, se qual_liberacao=Outros).
- 109 liberacao_para_usuario (obrigatório, se tipo_atendimento=Liberação): Usuario Atual / Outro Usuario.
- 110 nome_usuario (obrigatório, se liberacao_para_usuario=Outro Usuario).
- 42 descricao_problema (obrigatório).
- 73 canal_contato (obrigatório): Microsoft Teams / WhatsApp / OPA.
- 74 whatsapp (obrigatório, se canal_contato=WhatsApp).
- 75 email_teams (obrigatório, se canal_contato=Microsoft Teams).
- 112 urgencia (obrigatório): Baixa / Média / Alta.

## Manutenção (ID 1)
- 2 tipo_solicitacao (obrigatório): Manutenção de Equipamentos / Manutenção de Acessos.
- 26 equipamento (obrigatório): Computador/Hardware, Periféricos (Webcam/Impressora), Smartphone/Mobile, Sistemas/Softwares, Servidores/Pastas de Arquivos, Internet/Páginas da Web (NBSP canônico), Outros.
- 3 descricao_problema (obrigatório).
- 6 local_solicitacao (obrigatório): Filial / Matriz.
- 7 filial (obrigatório, se local_solicitacao=Filial): Maravilha, Lages, Videira, Concordia, Catanduvas.
- 70 canal_contato (obrigatório): WhatsApp / Microsoft Teams / OPA.
- 71 whatsapp (obrigatório, se canal_contato=WhatsApp).
- 72 email_teams (obrigatório, se canal_contato=Microsoft Teams).
- 4 urgencia (obrigatório): Baixa / Média / Alta.

## Cadastro de Novo Colaborador (ID 2)
- 8 nome_completo (obrigatório).
- 9 tipo_unidade (obrigatório): Matriz / Filial.
- 10 filial (obrigatório, se tipo_unidade=Filial): Maravilha, Lages, Videira, Concordia, Catanduvas.
- 11 setor (obrigatório): Comercial Peças, Comercial Implementos, Compras, Financeiro, Fiscal, Logística, Garantia, Almoxarifado, Qualidade, Recepção, Marketing, Desenvolvimento e Implantações, RH.
- 12 modelo_usuario (obrigatório).
- 13 acesso_vpn (obrigatório): Sim / Não.
- 14 licenca_m365 (obrigatório): Standard / Basic.
- 15 acesso_flex (obrigatório): Sim / Não.
- 16 possui_equipamento (obrigatório): Sim / Não.
- 17 tipo_equipamento_existente (obrigatório, se possui_equipamento=Sim): Desktop / Notebook.
- 102 ramal_corporativo (obrigatório): Sim / Não.
- 18 equipamento_necessario (obrigatório, múltipla escolha): Desktop, Notebook, Celular, Fone de ouvido com microfone.
- 19 precisa_programa (obrigatório): Sim / Não.
- 20 quais_programas (obrigatório, se precisa_programa=Sim).
- 22 assinatura_email (obrigatório): Sim / Não.
- 24 observacoes (opcional).
- 82 canal_contato (obrigatório): WhatsApp / Microsoft Teams / OPA.
- 83 whatsapp (obrigatório, se canal_contato=WhatsApp).
- 84 email_teams (obrigatório, se canal_contato=Microsoft Teams).

## Conferir alterações no Formcreator
- Validar IDs de perguntas/opções no GLPI real.
- Conferir dependências `depends_on` no YAML.
- Testar condicionais e múltipla escolha.

## Extração da descrição
- `services/ticket_content.py` extrai descrição a partir do HTML real do Formcreator.
- Formatos suportados: tabelas com rótulo marcado e blocos `<div>` com `<b>`/`<strong>`.
- Fallback sanitizado para HTML sem estrutura reconhecida.
- Se não for possível extrair com segurança: "Descrição não disponível nesta visualização."

## Status, atribuição e permissões
- Separar status do ticket, atribuição de técnico/grupo e permissões.
- Responder não comprova mudança automática de status; validar no ambiente.
- Anexos continuam fora do campo nativo de arquivo do Formcreator.

## Referências
- [[01 - Funcionamento]], [[09 - Validação manual]]
