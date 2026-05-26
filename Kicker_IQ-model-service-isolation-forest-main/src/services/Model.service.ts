import * as ort from 'onnxruntime-node'
import * as fs from 'fs'
import * as path from 'path'
import ScalerParams from '../types/ScalerParams'
import SessionMetrics from '../types/SessionMetrics'
import AnomalyResult from '../types/AnomalyResult'

class ModelService {
    /**
     * Diretório raiz onde ficam os modelos por atleta.
     * Estrutura esperada:
     *   model/
     *   └── <athleteId>/
     *       ├── isolation_forest.onnx
     *       └── scaler_params.json
     */
    private modelBaseDir: string = './model'

    /**
     * Cache de sessões ONNX por atleta para evitar recarregamento a cada chamada.
     */
    private sessionCache: Map<number, ort.InferenceSession> = new Map()

    /**
     * Cache de scalers por atleta.
     */
    private scalerCache: Map<number, ScalerParams> = new Map()

    // ── Caminhos por atleta ──────────────────────────────────────────────────

    private modelPath(athleteId: number): string {
        return path.resolve(this.modelBaseDir, String(athleteId), 'isolation_forest.onnx')
    }

    private scalerPath(athleteId: number): string {
        return path.resolve(this.modelBaseDir, String(athleteId), 'scaler_params.json')
    }

    // ── Modelo disponível? ───────────────────────────────────────────────────

    public hasModel(athleteId: number): boolean {
        return fs.existsSync(this.modelPath(athleteId)) &&
               fs.existsSync(this.scalerPath(athleteId))
    }

    // ── Session ONNX (com cache) ─────────────────────────────────────────────

    private async getSession(athleteId: number): Promise<ort.InferenceSession> {
        if (!this.sessionCache.has(athleteId)) {
            const session = await ort.InferenceSession.create(this.modelPath(athleteId))
            this.sessionCache.set(athleteId, session)
        }
        return this.sessionCache.get(athleteId)!
    }

    // ── Scaler (com cache) ───────────────────────────────────────────────────

    private getScaler(athleteId: number): ScalerParams {
        if (!this.scalerCache.has(athleteId)) {
            const raw = fs.readFileSync(this.scalerPath(athleteId), 'utf-8')
            this.scalerCache.set(athleteId, JSON.parse(raw) as ScalerParams)
        }
        return this.scalerCache.get(athleteId)!
    }

    // ── Normalização (RobustScaler: (x - center) / scale) ───────────────────

    private normalize(values: number[], scaler: ScalerParams): number[] {
        return values.map((v, i) => (v - scaler.center[i]) / scaler.scale[i])
    }

    // ── Features brutas na mesma ordem do treinamento ───────────────────────

    private extractRawValues(session: SessionMetrics): number[] {
        return [
            session.distanceM,
            session.highIntensityRunningM,
            session.highIntensityEvents,
            session.sprintDistanceM,
            session.numberOfSprints,
            session.topSpeedKph,
            session.avgSpeedKph,
            session.accelerations,
            session.decelerations,
        ]
    }

    // ── Predição ─────────────────────────────────────────────────────────────

    /**
     * Executa o Isolation Forest para uma única sessão de um atleta.
     *
     * O modelo retorna dois tensores:
     *   - `label`  → Int64, valor -1 (anomalia) ou 1 (normal)
     *   - `scores` → Float32, anomaly score (mais negativo = mais anômalo)
     */
    public async predict(athleteId: number, sessionMetrics: SessionMetrics): Promise<AnomalyResult> {
        const scaler  = this.getScaler(athleteId)
        const session = await this.getSession(athleteId)

        const rawValues        = this.extractRawValues(sessionMetrics)
        const normalizedValues = this.normalize(rawValues, scaler)

        const input  = new Float32Array(normalizedValues)
        const tensor = new ort.Tensor('float32', input, [1, normalizedValues.length])
        const output = await session.run({ float_input: tensor })

        return this.interpretResult(output, sessionMetrics)
    }

    // ── Interpretação do resultado ───────────────────────────────────────────

    /**
     * Interpreta os tensores de saída do Isolation Forest.
     *
     * - `label`  : -1 = anomalia, 1 = normal
     * - `scores` : anomaly score contínuo (negativo = anômalo)
     * - `atypicalDirection`: determinado pela comparação com os limites históricos
     *   do próprio atleta. Como o ONNX não carrega contexto histórico, usamos
     *   a magnitude do score como proxy:
     *     score < -0.05  → "Abaixo do padrão"  (queda de desempenho)
     *     score > 0.05   → "Acima do padrão"   (pico atípico)
     */
    private interpretResult(
        output: Record<string, ort.Tensor>,
        sessionMetrics: SessionMetrics
    ): AnomalyResult {
        const label        = Number((output.label.data as BigInt64Array)[0])
        const anomalyScore = (output.scores.data as Float32Array)[0]
        const isAnomaly    = label === -1

        let atypicalDirection: AnomalyResult['atypicalDirection'] = null
        let anomalyLabel = 'Sessão Normal'

        if (isAnomaly) {
            // Heurística de direção baseada na velocidade média como feature representativa
            // O modelo de treino já captura a tendência central; aqui inferimos a direção
            // comparando o score com o limiar zero (threshold do Isolation Forest).
            atypicalDirection = anomalyScore < 0
                ? 'Abaixo do padrão'
                : 'Acima do padrão'
            anomalyLabel = `Sessão Atípica (${atypicalDirection})`
        }

        return {
            isAnomaly,
            anomalyScore,
            anomalyLabel,
            atypicalDirection,
        }
    }

    // ── Predição em lote (todas as sessões de um atleta) ────────────────────

    /**
     * Executa o modelo para uma lista de sessões de um atleta e retorna
     * um resumo agregado com a taxa de anomalias detectadas.
     */
    public async predictBatch(
        athleteId: number,
        sessions: SessionMetrics[]
    ): Promise<{
        totalSessions: number
        anomalies: number
        anomalyRate: string
        results: AnomalyResult[]
    }> {
        const results: AnomalyResult[] = []

        for (const session of sessions) {
            const result = await this.predict(athleteId, session)
            results.push(result)
        }

        const anomalies = results.filter(r => r.isAnomaly).length

        return {
            totalSessions: sessions.length,
            anomalies,
            anomalyRate: `${((anomalies / sessions.length) * 100).toFixed(1)}%`,
            results,
        }
    }
}

export default ModelService
