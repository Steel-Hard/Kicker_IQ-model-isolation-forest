# Kicker_IQ-model-service-isolation-forest

API REST em TypeScript/Node.js que carrega modelos de **Isolation Forest** no formato ONNX (um por atleta) e expõe endpoints para detecção de sessões atípicas de performance.

- **Linguagem:** TypeScript (Node.js)
- **Runtime ONNX:** `onnxruntime-node`
- **Banco de dados:** PostgreSQL
- **Modelos:** gerados pelo repositório [`Kicker_IQ-model-isolation-forest`](../Kicker_IQ-model-isolation-forest)

---

## Endpoints

### `GET /api/athlete/anomaly?id=<athleteId>`

Analisa o **histórico completo** de sessões de um atleta e retorna a taxa de anomalias detectadas.

**Resposta de exemplo:**
```json
{
  "totalSessions": 42,
  "anomalies": 7,
  "anomalyRate": "16.7%",
  "results": [
    {
      "isAnomaly": false,
      "anomalyScore": 0.082,
      "anomalyLabel": "Sessão Normal",
      "atypicalDirection": null
    },
    {
      "isAnomaly": true,
      "anomalyScore": -0.143,
      "anomalyLabel": "Sessão Atípica (Abaixo do padrão)",
      "atypicalDirection": "Abaixo do padrão"
    }
  ]
}
```

---

### `GET /api/athlete/anomaly/last?id=<athleteId>`

Analisa apenas a **última sessão** registrada do atleta. Útil para alertas em tempo real após uma nova sessão ser cadastrada.

**Resposta de exemplo:**
```json
{
  "isAnomaly": true,
  "anomalyScore": -0.201,
  "anomalyLabel": "Sessão Atípica (Abaixo do padrão)",
  "atypicalDirection": "Abaixo do padrão"
}
```

---

## Estrutura do projeto

```
src/
├── app.ts
├── index.ts
├── db.ts
├── controllers/
│   ├── Athlete.controller.ts     ← Dois endpoints de anomalia
│   └── Match.controller.ts
├── services/
│   ├── Athlete.service.ts        ← Orquestra repositório + modelo
│   └── Model.service.ts          ← Carrega .onnx por atleta via ONNX Runtime
├── repositories/
│   └── Athlete.repository.ts     ← Queries ao PostgreSQL
├── routes/
│   ├── athlete.routes.ts         ← /api/athlete/anomaly e /api/athlete/anomaly/last
│   └── match.routes.ts
├── types/
│   ├── AnomalyResult.ts          ← Resultado de uma sessão analisada
│   ├── ScalerParams.ts           ← Parâmetros do RobustScaler (center + scale)
│   └── SessionMetrics.ts         ← Features de entrada do modelo
└── middleware/
    └── requestLogger.middleware.ts

model/                            ← Modelos ONNX (não versionados)
└── <athleteId>/
    ├── isolation_forest.onnx
    └── scaler_params.json
```

---

## Como usar

### Pré-requisitos
- Node.js 18+
- PostgreSQL com o schema populado (ver `Kicker_IQ-model-isolation-forest`)
- Modelos ONNX gerados em `model/<athleteId>/`

### 1. Instalar dependências

```bash
npm install
```

### 2. Configurar variáveis de ambiente

Crie um arquivo `.env`:

```env
DATABASE_URL=postgres://user:password@host:port/kicker_iq_model
PORT=3000
```

### 3. Copiar os modelos ONNX

Copie a pasta `model/` gerada pelo `Kicker_IQ-model-isolation-forest` para a raiz deste repositório:

```
model/
├── 679795059/
│   ├── isolation_forest.onnx
│   └── scaler_params.json
...
```

### 4. Rodar em desenvolvimento

```bash
npm run dev
```

### 5. Build + produção

```bash
npm start
```

### 6. Docker

```bash
npm run create-image
npm run create-container
```
