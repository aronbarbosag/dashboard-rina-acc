# Dashboard RINA ACC

Dashboard em Streamlit para buscar, transformar e visualizar dados de auditorias do RINA ACC.

## Configuracao das credenciais

Para usar a aplicacao e atualizar os dados, e necessario configurar variaveis de ambiente com as credenciais de uma pessoa que tenha acesso ao RINA ACC.

Crie um arquivo `.env` na raiz do projeto usando o modelo abaixo:

```env
USERNAME=seu_usuario
PASSWORD=sua_senha
API_URL=https://api.rinaacc.com.br
```

Voce tambem pode usar o arquivo `.env-example` como referencia.




## Rodando com Docker

```bash
docker compose up --build
```

Depois acesse:

```text
http://localhost:8501
```
