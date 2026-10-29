# storage — abstraction de object storage

Interface única para guardar os arquivos enviados; `FileService` só conhece a
interface `Storage`, não o provedor.

## Arquivos

- `minio.py` — implementação `MinioStorage` (MinIO local / S3 na AWS, via
  boto3 provider chain — sem credenciais em texto).
- `inmemory.py` — implementação em memória p/ testes.

## Uso

`get_storage()` retorna o storage configurado (MinIO por padrão; fake nos
testes via `set_storage`). URLs persistidas no formato `s3://<bucket>/<key>`
(`parse_s3_url`).
