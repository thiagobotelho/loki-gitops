# Ambientes

Este repositório usa `base/` e `overlays/{desenvolvimento,aceite,producao}`.

- `desenvolvimento`: LokiStack `1x.demo` com MinIO local para CRC.
- `aceite`: ponto de partida para homologação; ajuste retenção, limites e storage.
- `producao`: entrypoint declarativo; substitua MinIO local por object storage suportado, políticas de retenção e sizing adequados.

Validação:

```bash
oc kustomize overlays/desenvolvimento >/tmp/loki-dev.yaml
oc kustomize overlays/aceite >/tmp/loki-aceite.yaml
oc kustomize overlays/producao >/tmp/loki-prod.yaml
oc apply --dry-run=client -k overlays/desenvolvimento
```

Secrets obrigatórios:

- `openshift-logging/minio-credentials`: `root-user`, `root-password`.
- `openshift-logging/loki-s3`: `access_key_id`, `access_key_secret`, `bucketnames`, `endpoint`, `region`.

Decisões:

- `storageClassName` não é fixado na base; use a default do cluster ou patch por overlay.
- O datasource Grafana deve apontar para o gateway Loki com token de ServiceAccount.
- O `UIPlugin/logging` habilita `Observe > Logs` no Console do OpenShift e
  aponta para `openshift-logging/loki`.
- Network Observability não reutiliza esse LokiStack; flows usam LokiStack
  dedicado com `tenants.mode: openshift-network`.

## Classe de armazenamento

LokiStack exige storageClassName. O overlay desenvolvimento seleciona a classe do OpenShift Local crc-csi-hostpath-provisioner. Confira sua existência antes de aplicar; caso a distribuição use outro provisionador, altere o patch. Em aceite e produção, substitua classe-rwo-exemplo por uma StorageClass RWO existente, com capacidade e recuperação definidas. A classe de dados de ingesters/queriers não substitui o backend S3 dos blocos.

## Bootstrap de imagens no desenvolvimento

Somente o perfil CRC inclui o hook Sync `crc-minio-images`. Consulte
[imagens automáticas](../README.md#imagens-automáticas-no-crc) para ordem,
permissões, diagnóstico e atualização de versões. A sincronização completa
pelo Argo CD é o caminho de instalação desse perfil; aplicar Kustomize
diretamente não reproduz a execução dos hooks.
