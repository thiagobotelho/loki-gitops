# loki-gitops

Repositório GitOps responsável pela instalação do **Loki Operator (Red Hat)** e
provisionamento do **LokiStack** em ambiente OpenShift 4.x.

Este projeto segue modelo declarativo com Kustomize e integração nativa com
Argo CD/OpenShift GitOps.


## Arquitetura

```mermaid
flowchart LR
    Pods[Pods/OpenShift logs] --> CLF[ClusterLogForwarder]
    CLF --> Loki[LokiStack]
    Loki --> MinIO[(MinIO/S3 local)]
    Console[OpenShift Console] --> UI[UIPlugin logging]
    UI --> Loki
    Grafana[Grafana] --> Loki
    Tempo[Tempo] -. trace_id .-> Loki
```

O Loki recebe logs do OpenShift, armazena em backend S3 compatível no laboratório
e é consultado pelo Grafana para logs e correlação logs-traces. O recurso
`UIPlugin/logging` habilita o menu `Observe > Logs` no Console do OpenShift.

Este LokiStack é para logs de aplicação/infra/audit. Fluxos de rede do Network
Observability usam um LokiStack dedicado no repositório
`network-observability-gitops`, com tenant `openshift-network`.

## Objetivo

Provisionar:

- Loki Operator (via OLM)
- LokiStack
- OpenShift Logging Operator e `ClusterLogForwarder`
- `UIPlugin/logging` para o menu `Observe > Logs`
- Estrutura base para regras de alerta e gravação

## Estrutura

```text
loki-gitops/
├── base/
├── overlays/
│   ├── desenvolvimento/
│   ├── aceite/
│   └── producao/
├── docs/
└── README.md
```

## Operadores

- Package: loki-operator
- Source: redhat-operators
- Channel: stable-6.4
- Namespace obrigatório: openshift-operators-redhat

---

## Deploy

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

oc apply -k overlays/desenvolvimento
```

Os Secrets não são versionados. Para ambientes compartilhados, prefira
External Secrets ou Sealed Secrets e rotacione qualquer credencial que já
tenha sido publicada no histórico Git.


## Imagens automáticas no CRC

Ao sincronizar a aplicação `loki` no Argo CD, o overlay `desenvolvimento`
prepara as imagens do MinIO e do cliente `mc` no registro integrado.
Não é necessário executar `oc start-build` durante a instalação pelo Argo.
O registro integrado, os controladores de build e o acesso aos repositórios
Git e registros de imagens precisam estar disponíveis.

A ordem declarada evita iniciar o MinIO antes de publicar suas imagens:

| Wave | Recursos e objetivo |
| --- | --- |
| 4 | ImageStreams, BuildConfigs e identidade restrita para o Job |
| 5 | Hook Sync `crc-minio-images`: servidor MinIO e depois cliente mc |
| 6 | PVC e Deployment MinIO, juntos para atender `WaitForFirstConsumer` |
| 7–8 | Serviço e criação do bucket |
| 20 | LokiStack |

O hook consulta cada tag: se já existe, reutiliza a imagem. Se falta, acompanha
o último build ativo ou inicia um build e aguarda sua conclusão e publicação.
Uma falha interrompe o hook; o segundo build só começa após a primeira imagem.
As BuildConfigs não possuem trigger automático: o hook é responsável pelo
início, inclusive quando as BuildConfigs já existiam antes da atualização.

A ServiceAccount pode consultar somente as tags indicadas, as duas
BuildConfigs e builds do namespace, e instanciar essas duas BuildConfigs.
Não recebe acesso a Secrets nem permissões para remover recursos.
O Job tem prazo global de 35 minutos e não repete automaticamente após falhar.

### Acompanhar e recuperar

```bash
oc -n openshift-logging get job crc-minio-images
oc -n openshift-logging logs job/crc-minio-images
oc -n openshift-logging get builds
oc -n openshift-logging get imagestreamtag minio-crc:RELEASE.2025-09-07T16-13-09Z
oc -n openshift-logging get imagestreamtag mc-crc:RELEASE.2025-08-13T08-35-41Z
oc -n openshift-logging rollout status deployment/minio --timeout=10m
```

Espere o Job concluir antes de aguardar o rollout. Se o hook falhar, consulte
seus logs e depois os logs do build pelo nome mostrado em `get builds`:
`oc -n openshift-logging logs build/NOME_DO_BUILD`. Verifique também
`oc get clusteroperator image-registry` e eventos do namespace.
Corrija a causa e execute uma nova sincronização **completa** de `loki` no
Argo CD. O hook anterior é substituído no novo Sync, preservando as imagens e
o PVC; builds ainda ativos são reaproveitados. Um Refresh isolado não inicia
uma nova operação e sync seletivo de recursos não executa hooks.

Essa automação depende do Argo CD: `oc apply -k` isolado não executa sua
semântica de waves e hooks. Os perfis `aceite` e `producao` não incluem o hook
nem as BuildConfigs locais.

### Atualizar versões

A existência da tag é uma verificação de disponibilidade, sem comprovar a
origem de imagens já presentes. Para atualizar a versão, revise o commit Git
e os digests do Dockerfile nas BuildConfigs, use novas tags de saída e
atualize as referências do Deployment, do Job de bucket e do hook/RBAC.
Não reutilize uma tag antiga esperando que um novo Sync reconstrua a imagem.

Após a sincronização, valide o plugin de logs:

```bash
oc get uiplugin logging
oc get consoleplugin | grep logging
oc get consoles.operator.openshift.io cluster -o jsonpath='{.spec.plugins}{"\n"}'
```

No Console do OpenShift, faça refresh ou logout/login e acesse
`Observe > Logs`.

## Diagnóstico do menu Observe > Logs

O plugin do Console carrega um `plugin-manifest.json` e uma configuração JSON.
Se o navegador receber HTML nesses endpoints, a UI pode exibir erro de parsing
JSON. Valide primeiro os objetos do cluster:

```bash
oc get uiplugin logging
oc get consoleplugin logging-view-plugin
oc get consoles.operator.openshift.io cluster -o jsonpath='{.spec.plugins}{"\n"}'
```

Depois valide o Loki gateway usado pela UI. Use um token válido no shell, sem
registrá-lo em arquivo:

```bash
TOKEN="$(oc whoami --show-token)"
oc -n openshift-logging run loki-labels-check --rm -i --restart=Never \
  --image=curlimages/curl:8.10.1 -- \
  curl -ksS -H "Authorization: Bearer ${TOKEN}" \
  https://loki-gateway-http.openshift-logging.svc.cluster.local:8080/api/logs/v1/application/loki/api/v1/labels
```

Se os objetos e o gateway estiverem saudáveis, faça hard refresh no navegador.
Quando o Console mantiver bundle antigo em cache, reinicie apenas o Console:

```bash
oc -n openshift-console rollout restart deployment/console
oc -n openshift-console rollout status deployment/console --timeout=5m
```

## Ambientes e validação

```bash
oc kustomize overlays/desenvolvimento >/tmp/loki-dev.yaml
oc kustomize overlays/aceite >/tmp/loki-aceite.yaml
oc kustomize overlays/producao >/tmp/loki-prod.yaml
oc apply --dry-run=client -k overlays/desenvolvimento
```

A estrutura primária é `base/` e `overlays/{desenvolvimento,aceite,producao}`.
`storageClassName` não é fixado na base; o overlay `desenvolvimento` mantém a
classe definida para desenvolvimento; revise compatibilidade e migração antes de alterar PVCs existentes. Veja
`docs/AMBIENTES.md`.

## Manual de operação

Consulte [docs/OPERACAO.md](docs/OPERACAO.md) para os procedimentos de configuração, verificação e manutenção.

## Aprender a configuração

Consulte o [guia comentado](docs/APRENDIZADO.md) para entender componentes, escolhas, testes positivos/negativos e reversão.

## Auditoria Allow/Drop

Consulte o [guia de auditoria OVN](docs/AUDITORIA-OVN.md) para verificar decisões na interface do Console.
