# Atualização e backup

[[obsidian/07 - Operacao/Indice|← Operação]] · [[obsidian/Inicio|Início]]

## Preservar dados persistentes

Arquivos de implantação podem incluir `.env`, `config/forms.yaml`, SQLite apontado por `IDENTITY_DB_PATH`, WAL/SHM, arquivo de lock e logs. Não substituir nem remover banco para contornar falha de caminho. Caminho congelado usa diretório do executável; valide antes de atualizar.

## Sequência segura

1. Confirmar ambiente, conta de serviço, versão do banco e política de grupos/vínculos.
2. Parar o serviço e fazer backup consistente do SQLite e configurações sem publicar segredos.
3. Construir artefato a partir de uma revisão de código conhecida no Windows.
4. Atualizar executável e, no spec atual onedir, diretório `_internal` como conjunto do mesmo build; não misturar builds.
5. Preservar os arquivos externos e ACLs; aplicar migração incremental somente no startup/CLI documentado após backup.
6. Iniciar instância única; verificar logs sem expor conteúdo/credenciais.
7. Executar roteiro de regressão homologado; reversão do executável/banco exige compatibilidade de schema.

O spec atual pode divergir da instalação real, que não foi inspecionada. Não faça alteração destrutiva nem reexecute POST incerto durante validação.

## Backup SQLite

Preferir bot/worker parados ou mecanismo oficial de backup SQLite. Considerar arquivo principal e WAL/SHM. Arquivo `.notifications.lock` é protegido por handle de sistema operacional e não deve ser apagado como forma de “parar” worker. Backups também contêm vínculo e dados de operação; controle acesso e prazo.

[[obsidian/07 - Operacao/Build PyInstaller|Build]] · [[obsidian/07 - Operacao/Serviço Windows NSSM|NSSM]] · [[obsidian/04 - Dados/Persistência e modelos|Persistência]]
