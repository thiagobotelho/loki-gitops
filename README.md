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
oc apply -k kustomize/overlays/crc
