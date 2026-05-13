# Dashboard RINA ACC

Dashboard em Streamlit para buscar, transformar e visualizar dados de auditorias do RINA ACC.

## Configuracao das credenciais

Para usar a aplicacao e atualizar os dados, e necessario configurar variaveis de ambiente com as credenciais de uma pessoa que tenha acesso ao RINA ACC.

Crie um arquivo `.env` na raiz do projeto usando o modelo abaixo:

```env
USERNAME=seu_usuario
PASSWORD=sua_senha
API_URL=https://api.rinaacc.com.br
DASHBOARD_USERNAME=seu_usuario
DASHBOARD_PASSWORD=sua_senha
AUTH_CACHE_TTL_SECONDS=43200
```

Voce tambem pode usar o arquivo `.env-example` como referencia.

## Acesso ao dashboard

A aplicacao possui uma tela de login para restringir o acesso aos dados.


Para trocar o usuario e senha, configure `DASHBOARD_USERNAME` e `DASHBOARD_PASSWORD`
no arquivo `.env`.

O login do dashboard fica em cache por 12 horas por padrao. Para alterar esse
tempo, ajuste `AUTH_CACHE_TTL_SECONDS` no `.env`.



## Rodando com Docker

```bash
docker compose up --build
```

Depois acesse:

```text
http://localhost:8501
```
