# Kicker_IQ-model-isolation-forest

Este é o ambiente de pesquisa e treinamento do modelo de detecção de anomalias.

- **Linguagem:** Python
- **Propósito:** Analisar dados históricos de GPS/rastreamento de atletas e treinar um modelo de detecção de sessões atípicas (Isolation Forest) por atleta, exportando-o no formato ONNX para ser consumido pelo `model-service`.
- **Arquivos Chave:**
  - `src/isolation-forest_model.ipynb`: Jupyter Notebook onde o modelo é desenvolvido, treinado e avaliado.
  - `src/export/export_onnx.py`: Script que treina os modelos e exporta um `.onnx` + `scaler_params.json` por atleta.
  - `scripts/importData.py`: Popula o banco de dados PostgreSQL com os dados da planilha.
  - `requirements.txt`: Dependências do projeto.
  - `data/`: Pasta para armazenar o dataset `.xlsx`.
  - `model/`: Pasta onde os arquivos de modelo gerados são salvos, organizados por atleta.

- **Fluxo:**
  1. A equipe usa o notebook para explorar os dados e validar o pipeline.
  2. Executa `export_onnx.py` para gerar, para cada atleta com sessões suficientes, um arquivo `model/<athlete_id>/isolation_forest.onnx` e um `model/<athlete_id>/scaler_params.json`.
  3. Os arquivos gerados são copiados para o `model-service`, que os utiliza em produção via ONNX Runtime.

---

## Sobre o Isolation Forest

O Isolation Forest é um algoritmo de detecção de anomalias que identifica sessões atípicas (muito acima ou muito abaixo do padrão histórico do atleta) sem precisar de dados rotulados.

**Destaques do pipeline:**
- **Split temporal 70/30 por atleta**: evita vazamento de dados do futuro para o passado.
- **Contamination adaptativo**: calculado com base no percentil 10 dos scores do treino de cada atleta.
- **Features sem leakage**: z-score e rolling calculados com `.shift(1)`, garantindo que a sessão atual nunca entra no próprio cálculo.
- **Um modelo por atleta**: cada atleta tem seu próprio `.onnx`, treinado exclusivamente com seu histórico.

---

## Como usar

### Pré-requisitos
- Python 3.11+
- PostgreSQL acessível

### 1. Instalar dependências

```bash
pip install -r requirements.txt
```

Ou via Makefile:

```bash
make install
```

### 2. Configurar variáveis de ambiente

Crie um arquivo `.env` na raiz:

```env
DATABASE_URL=postgres://user:password@host:port/kicker_iq_model
```

### 3. Popular o banco de dados

```bash
python scripts/importData.py
```

Ou via Makefile:

```bash
make import
```

### 4. Treinar e exportar os modelos ONNX

```bash
python src/export/export_onnx.py
```

Ou via Makefile:

```bash
make export
```

Os modelos serão gerados em `model/<athlete_id>/`:
```
model/
├── 679795059/
│   ├── isolation_forest.onnx
│   └── scaler_params.json
├── 123456789/
│   ├── isolation_forest.onnx
│   └── scaler_params.json
...
```

### 5. Explorar no notebook

```bash
make notebook
```

---

## Estrutura do projeto

```
Kicker_IQ-model-isolation-forest/
├── data/
│   └── players.xlsx              # Dataset de entrada
├── model/
│   └── <athlete_id>/
│       ├── isolation_forest.onnx # Modelo exportado por atleta
│       └── scaler_params.json    # Parâmetros do RobustScaler
├── scripts/
│   └── importData.py             # Popula o banco PostgreSQL
├── src/
│   ├── export/
│   │   └── export_onnx.py        # Treina e exporta os modelos
│   └── isolation-forest_model.ipynb
├── .env                          # Não versionado
├── .gitignore
├── Dockerfile
├── Makefile
├── requirements.txt
└── README.md
```
