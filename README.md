# loki-gitops

Repositório GitOps responsável pela instalação do **Loki Operator (Red Hat)** e provisionamento do **LokiStack** em ambiente OpenShift 4.x.

Este projeto segue modelo declarativo utilizando Kustomize, permitindo integração nativa com Argo CD / OpenShift GitOps.

---

## 🎯 Objetivo

Provisionar:

- Loki Operator (via OLM)
- LokiStack
- Estrutura base para regras de alerta e gravação

---

## 🏗 Estrutura

```bash
loki-gitops/
└── kustomize/
├── base/
│ ├── operatorgroup.yaml
│ ├── subscription.yaml
│ ├── lokistack.yaml
│ └── kustomization.yaml
└── overlays/
└── crc/
└── kustomization.yaml
```

---

## 📦 Operador Utilizado

- Package: loki-operator
- Source: redhat-operators
- Channel: stable-6.4
- Namespace obrigatório: openshift-operators-redhat

---

## 🚀 Deploy Manual

```bash
export MINIO_ROOT_USER=minio
export MINIO_ROOT_PASSWORD='use-a-random-password'

oc -n openshift-logging create secret generic minio-credentials \
  --from-literal=root-user="$MINIO_ROOT_USER" \
  --from-literal=root-password="$MINIO_ROOT_PASSWORD"

oc -n openshift-logging create secret generic loki-s3 \
  --from-literal=access_key_id="$MINIO_ROOT_USER" \
  --from-literal=access_key_secret="$MINIO_ROOT_PASSWORD" \
  --from-literal=bucketnames=loki \
  --from-literal=endpoint=http://minio.openshift-logging.svc:9000 \
  --from-literal=region=us-east-1

oc apply -k kustomize/overlays/crc
```

Os Secrets não são versionados. Para ambientes compartilhados, prefira
External Secrets ou Sealed Secrets e rotacione qualquer credencial que já
tenha sido publicada no histórico Git.
