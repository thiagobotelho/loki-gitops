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
