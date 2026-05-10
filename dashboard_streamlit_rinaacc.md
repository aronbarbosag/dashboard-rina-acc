# Dashboard Streamlit para API RINAACC

## Contexto

Este documento resume a abordagem sugerida para construir uma dashboard em Streamlit a partir da API RINAACC, com base na mini documentacao presente em `api.http`.

A API permite:

- Fazer login e obter um token.
- Buscar todas as aeronaves.
- Pesquisar auditorias por periodo, base, operadora, prefixo, tipo de auditoria e outros filtros.
- Buscar detalhes de uma auditoria pelo endpoint `/report/{audit_id}`.
- Buscar sub-relatorios relacionados, como dados de aeronave, opiniao, pesagem e itens especificos.

## Abordagem Recomendada

A ideia de primeiro puxar os dados da API, consolidar em arquivos locais e depois consumir esses dados no Streamlit e uma boa abordagem.

O ideal e separar o projeto em tres etapas:

1. Extracao dos dados da API.
2. Normalizacao e consolidacao dos dados.
3. Visualizacao e analise no Streamlit.

Fluxo sugerido:

```text
API RINAACC
   ↓
scripts/fetch_data.py
   ↓
data/raw/*.json
   ↓
scripts/build_dataset.py
   ↓
data/processed/*.csv ou *.parquet
   ↓
app_streamlit.py
```

## Por que nao chamar a API direto no Streamlit?

Evitar que o Streamlit chame a API diretamente em cada interacao e melhor porque:

- A dashboard fica mais rapida.
- Reduz o risco de sobrecarregar a API.
- Evita refazer chamadas desnecessarias.
- Facilita debugar dados inconsistentes.
- Permite manter historico local dos dados coletados.
- Separa responsabilidade de coleta, tratamento e visualizacao.

O Streamlit pode ter um botao de "Atualizar dados", mas esse botao deveria rodar o pipeline de ingestao, e nao misturar toda a logica da API diretamente nos graficos.

## Estrutura Inicial Sugerida

Uma primeira versao simples poderia ter:

```text
.
├── api.http
├── app_streamlit.py
├── scripts/
│   ├── fetch_audits.py
│   ├── fetch_reports.py
│   └── build_dataset.py
├── data/
│   ├── raw/
│   │   ├── audits.json
│   │   └── reports/
│   └── processed/
│       ├── audits.csv
│       ├── aircrafts.csv
│       ├── non_conformities.csv
│       └── operators.csv
└── .env
```

## Etapa 1: Extrair Dados

O primeiro script deve:

- Ler `USERNAME` e `PASSWORD` do `.env`.
- Fazer login no endpoint `/login`.
- Guardar o token retornado.
- Buscar auditorias pelo endpoint `/search`.
- Salvar a resposta bruta em `data/raw/audits.json`.

Campos importantes da busca de auditorias:

- Tipo de auditoria.
- Data realizada.
- Prefixo da aeronave.
- Nome do relatorio.
- Nao conformidades anteriores de manutencao.
- Nao conformidades anteriores operacionais.
- ID da auditoria.
- ATA, quando houver nao conformidade.

## Etapa 2: Buscar Detalhes dos Relatorios

Para cada `audit_id` retornado pela busca, o segundo script deve chamar:

```text
GET /report/{audit_id}
```

Esse endpoint retorna informacoes mais completas, como:

- Numero do contrato.
- Operadora.
- Base.
- Base abreviada.
- Modelo da aeronave.
- Tipo de auditoria.
- Prefixo.
- Nao conformidades atuais e anteriores.
- Itens de acompanhamento atuais e anteriores.
- URLs das fotos.

Tambem podem existir referencias para outros relatorios:

- `_auditing`
- `_aircraft`
- `_operator`
- `_powerChech`
- `_observationOpr`
- `_weighing`
- `_specificItems`
- `_observationMnt`
- `_opinion`
- `_notepad`

Essas referencias podem ser usadas depois para enriquecer a base.

## Etapa 3: Consolidar Dados

Para comecar, CSV e suficiente.

Arquivos uteis:

- `audits.csv`
- `aircrafts.csv`
- `non_conformities.csv`
- `operators.csv`
- `bases.csv`
- `contracts.csv`

Depois, se o volume crescer, vale considerar:

- Parquet, para arquivos analiticos mais eficientes.
- SQLite, se a estrutura ficar mais relacional.
- DuckDB, se a ideia for fazer analise local eficiente em cima de CSV ou Parquet.

Uma evolucao natural seria:

```text
CSV no MVP
↓
Parquet quando os dados crescerem
↓
DuckDB ou SQLite se houver muitas relacoes e consultas
```

## O que Mostrar na Dashboard

### KPIs Principais

- Total de auditorias no periodo.
- Total de nao conformidades.
- Percentual de auditorias com nao conformidade.
- Nao conformidades abertas versus resolvidas.
- Tempo medio de resolucao, caso a API traga data de resolucao.
- Auditorias por tipo: `ACCI`, `RMNR`, `ACCD`, `Extra`, `ACC`.

### Filtros

- Periodo da auditoria.
- Operadora.
- Base.
- Prefixo da aeronave.
- Modelo.
- Tipo de auditoria.
- Contrato.
- Status da nao conformidade, se disponivel.

### Graficos Uteis

- Auditorias por mes.
- Nao conformidades por mes.
- Nao conformidades por operadora.
- Nao conformidades por base.
- Ranking de aeronaves com mais ocorrencias.
- Auditorias por tipo.
- Heatmap de base por tipo de auditoria.
- Evolucao de nao conformidades abertas e resolvidas ao longo do tempo.

### Tabelas Importantes

Tabela de auditorias:

- Data.
- Tipo.
- Prefixo.
- Operadora.
- Base.
- Contrato.
- Quantidade de nao conformidades.
- Status.
- ID ou link do relatorio.

Tabela de nao conformidades:

- ID da auditoria.
- ATA.
- Area: manutencao ou operacional.
- Descricao ou resumo, se disponivel.
- Status.
- Data de abertura.
- Data de resolucao.

## MVP Recomendado

Para uma primeira versao, o objetivo deve ser simples:

1. Fazer login na API.
2. Buscar auditorias em um periodo configuravel.
3. Buscar detalhes de cada auditoria.
4. Salvar JSON bruto em `data/raw`.
5. Gerar um CSV consolidado em `data/processed/audits.csv`.
6. Criar uma dashboard Streamlit lendo esse CSV.
7. Mostrar KPIs, filtros basicos, graficos principais e uma tabela detalhada.

## Primeira Versao da Dashboard

A primeira tela poderia ter:

- Filtros no topo ou na sidebar:
  - Periodo.
  - Operadora.
  - Base.
  - Tipo de auditoria.
  - Prefixo.

- Linha de KPIs:
  - Total de auditorias.
  - Total de nao conformidades.
  - Percentual com nao conformidade.
  - Bases auditadas.
  - Aeronaves auditadas.

- Graficos:
  - Auditorias por mes.
  - Auditorias por tipo.
  - Nao conformidades por operadora.
  - Nao conformidades por base.
  - Ranking de aeronaves com mais nao conformidades.

- Tabela:
  - Lista detalhada de auditorias.

## Recomendacao Final

A melhor abordagem e consolidar primeiro e analisar depois.

O CSV e uma excelente escolha para validar a ideia rapidamente. O mais importante e preservar os JSONs brutos da API e separar bem:

- Extracao.
- Tratamento.
- Visualizacao.

Essa separacao deixa o projeto mais facil de manter, testar, depurar e evoluir.

