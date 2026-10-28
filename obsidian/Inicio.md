# Otto — Assistente GLPI

Vault de documentação do bot Microsoft Teams que abre chamados pelo Formcreator do GLPI e oferece consulta, resposta pública e notificações opcionais.

## Navegação

- [[obsidian/00 - Inicio/Mapa|Mapa do vault e registro de cobertura]]
- [[obsidian/00 - Inicio/Indice|Índice da pasta de início]]
- [[obsidian/01 - Arquitetura/Indice|Arquitetura]]
- [[obsidian/02 - Modulos/Indice|Módulos]]
- [[obsidian/03 - Fluxos/Indice|Fluxos]]
- [[obsidian/04 - Dados/Indice|Dados e formulários]]
- [[obsidian/05 - Interfaces e Integracoes/Indice|Interfaces e integrações]]
- [[obsidian/06 - Desenvolvimento/Indice|Desenvolvimento e testes]]
- [[obsidian/07 - Operacao/Indice|Operação]]
- [[obsidian/08 - Pendencias/Indice|Pendências e homologação]]

## Leitura rápida

- **Implementado no código:** API FastAPI/Bot Framework, navegação e formulários, vínculo de identidade, consulta e resposta condicionadas à autorização, e worker opt-in de notificações.
- **Não equivale a produção validada:** não foram verificados neste trabalho JWT/tenant reais, GLPI implantado, permissões, cliente Teams, Windows/NSSM ou banco de produção.
- [[obsidian/00 - Inicio/Mapa|Escopo examinado, limites da leitura e cobertura por pasta]]

O vault já existia no repositório, com configurações Obsidian em `.obsidian/`. Abra a pasta `Otto - Bot_Teams/` no Obsidian; as notas organizadas ficam em `obsidian/`.
