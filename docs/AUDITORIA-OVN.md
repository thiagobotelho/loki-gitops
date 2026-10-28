# Auditoria OVN do laboratório

O overlay de desenvolvimento adiciona input audit restrito à origem ovn,
preserva o pipeline application e encaminha somente mensagens com
`name="NP:mesh-lab:` ao Loki existente. Não coleta kubeAPI, openshiftAPI
ou auditd por esse input.

O collector recebe os papéis padrão collect-audit-logs e
cluster-logging-write-audit-logs em wave 4, antes do forwarder em wave 30.
A permissão collect é do tipo audit; a restrição à origem OVN é feita pela
configuração do input, não pelo RBAC.

Habilite allow/deny somente no namespace dos exercícios. Para visualização,
consultas e interpretação, siga o [guia do mesh-apps-lab](https://github.com/thiagobotelho/mesh-apps-lab/blob/main/docs/AUDITORIA-OVN.md).

## Conferir

```bash
oc -n openshift-logging get clusterlogforwarder instance
oc -n openshift-logging get clusterlogforwarder instance -o jsonpath='{.status.conditions}{"\n"}'
oc -n openshift-logging rollout status daemonset/instance --timeout=180s
```

Confira Authorized, Valid e Ready verdadeiros. Use Observe → Logs, tipo Audit:

```logql
{log_type="audit"} |= "NP:mesh-lab:" |= "verdict=drop"
```

Revise retenção, limite de auditoria OVN e volume de eventos. Audit contém
metadados de rede; preserve as permissões de leitura restritas.

## Reverter

1. Desative a anotação ACL do namespace para parar a geração.
2. Retire a referência ao patch ovn-audit-patch.yaml no overlay e sincronize.
3. Confirme que o collector continua Ready com o pipeline application.
4. Retire a referência ovn-audit-rbac.yaml e sincronize novamente.

Retirar as permissões antes do input pode interromper a coleta de todos os
logs desse forwarder. Não exclua Loki, PVCs nem a Application para reverter.

Referência: [Red Hat Logging 6.5](https://docs.redhat.com/en/documentation/red_hat_openshift_logging/6.5/html/configuring_logging/configuring-log-forwarding).
