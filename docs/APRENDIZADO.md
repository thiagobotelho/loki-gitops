# Logs e armazenamento

## O que observar

LokiStack usa armazenamento S3; retenção de logs e retenção do bucket precisam ser compatíveis. RBAC limita consultas por tenant. Renderizar YAML não valida credenciais S3, conectividade, capacidade ou recuperação de dados. Teste ingestão, consulta autorizada e negação entre tenants com logs sintéticos.

## Roteiro de leitura e validação

1. Leia o README e identifique o componente que recebe a configuração.
2. Confira namespaces, seletores, portas, identidades e dependências nos exemplos.
3. Ajuste apenas os campos necessários em um ambiente isolado; não use credenciais de produção.
4. Valide sintaxe e contratos locais antes de aplicar. Registre o resultado real separado deste guia.
5. Execute um caso permitido e um caso negado, conferindo a causa da resposta.
6. Defina reversão por recurso/arquivo e preserve dados persistentes antes de mudanças.

Os comentários dos manifests explicam escolhas; não comprovam disponibilidade do componente. Exemplos fora de entradas Kustomize não são implantados automaticamente.

## Entender e testar o bootstrap CRC

Leia `overlays/desenvolvimento/crc-image-builds.yaml` para identificar fontes,
digests, tags e limites dos builds. Em `crc-image-bootstrap.yaml`, acompanhe
a consulta da tag, a seleção do build e a interrupção em caso de erro.
A wave do PVC precisa acompanhar o Deployment quando o provisionador usa
`WaitForFirstConsumer`; aguardar o PVC antes de criar o consumidor bloqueia
a instalação.

`tests/test-crc-bootstrap.py` executa o script do hook com uma API simulada:
cluster vazio, imagens existentes, builds ativos, falhas, timeout e negação
de permissões. O CI também renderiza os três perfis e valida os schemas.
Esses testes não substituem admissão SCC/RBAC, compilação e publicação reais.

Em um cluster descartável, valide a instalação completa, um segundo Sync sem
novos builds e a recuperação após falha controlada de conectividade. Registre
os resultados separadamente. Não remova imagens ou PVCs de instalações com
dados para simular um cluster vazio. Reverter o hook não desfaz builds já
iniciados nem deve remover o armazenamento.
