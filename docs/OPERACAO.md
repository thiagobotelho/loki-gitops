# Operação do armazenamento de logs

## Preparar imagens de armazenamento

O overlay desenvolvimento utiliza ImageStreams e BuildConfigs sem triggers automáticos para as imagens MinIO/MC. Confira versões de fonte, disponibilidade das imagens base e capacidade de build antes de instalar.

Aplique primeiro os recursos de build definidos no overlay, inicie cada BuildConfig e aguarde sua conclusão antes de reconciliar os workloads dependentes:

```bash
oc -n openshift-logging start-build mc-crc --wait
oc -n openshift-logging start-build minio-crc --wait
oc -n openshift-logging get builds,imagestreams
```

O registry interno não substitui backup de imagens. Planeje atualização de versões e correções de segurança conforme o ciclo de vida das fontes.

## Configurar S3

Crie os Secrets exigidos pelo README com credenciais do armazenamento escolhido. Preserve PVCs e buckets ao atualizar os workloads. Confira endpoint, bucket, tenant e permissões antes de testar ingestão ou consultar logs.
