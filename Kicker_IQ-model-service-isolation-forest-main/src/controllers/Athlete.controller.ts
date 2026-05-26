import { Request, Response } from "express"
import AthleteService from "../services/Athlete.service"
import ModelService from "../services/Model.service"

class AthleteController {
    private athleteService: AthleteService = new AthleteService()
    private modelService: ModelService = new ModelService()

    /**
     * `GET /api/athlete/anomaly?id=<athleteId>`
     *
     * Analisa o histórico completo de sessões do atleta e retorna
     * a taxa de anomalias detectadas ao longo do tempo.
     *
     * Resposta:
     * {
     *   totalSessions: number,
     *   anomalies: number,
     *   anomalyRate: string,       // ex: "18.2%"
     *   results: AnomalyResult[]
     * }
     */
    public async getAnomalyAnalysis(req: Request, res: Response) {
        try {
            const { id } = req.query

            const validation = this.validateAthleteId(id, res)
            if (!validation) return

            const { athleteId } = validation

            if (!this.modelService.hasModel(athleteId)) {
                res.status(404).json({
                    error: `Modelo não encontrado para o atleta ${athleteId}. Execute o script de exportação ONNX primeiro.`
                })
                return
            }

            const athleteExists = await this.athleteService.getAthleteExists(athleteId)
            if (!athleteExists) {
                res.status(404).json({ error: 'Atleta não encontrado.' })
                return
            }

            const response = await this.athleteService.analyzeAthlete(athleteId)
            res.status(200).json(response)
        } catch (error: unknown) {
            console.error('Error on getAnomalyAnalysis:', error)
            res.sendStatus(500)
        }
    }

    /**
     * `GET /api/athlete/anomaly/last?id=<athleteId>`
     *
     * Analisa apenas a sessão mais recente do atleta.
     * Ideal para alertas em tempo real após uma nova sessão ser registrada.
     *
     * Resposta:
     * {
     *   isAnomaly: boolean,
     *   anomalyScore: number,
     *   anomalyLabel: string,
     *   atypicalDirection: 'Acima do padrão' | 'Abaixo do padrão' | null
     * }
     */
    public async getLastSessionAnomaly(req: Request, res: Response) {
        try {
            const { id } = req.query

            const validation = this.validateAthleteId(id, res)
            if (!validation) return

            const { athleteId } = validation

            if (!this.modelService.hasModel(athleteId)) {
                res.status(404).json({
                    error: `Modelo não encontrado para o atleta ${athleteId}. Execute o script de exportação ONNX primeiro.`
                })
                return
            }

            const athleteExists = await this.athleteService.getAthleteExists(athleteId)
            if (!athleteExists) {
                res.status(404).json({ error: 'Atleta não encontrado.' })
                return
            }

            const response = await this.athleteService.analyzeLastSession(athleteId)
            res.status(200).json(response)
        } catch (error: unknown) {
            console.error('Error on getLastSessionAnomaly:', error)
            res.sendStatus(500)
        }
    }

    // ── Helpers ──────────────────────────────────────────────────────────────

    private validateAthleteId(
        id: unknown,
        res: Response
    ): { athleteId: number } | null {
        if (!id) {
            res.status(400).json({ error: 'id is missing' })
            return null
        }
        if (isNaN(Number(id))) {
            res.status(400).json({ error: 'id must be a number' })
            return null
        }
        return { athleteId: Number(id) }
    }
}

export default AthleteController
