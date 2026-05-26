import AthleteRepository from "../repositories/Athlete.repository"
import ModelService from "./Model.service"

class AthleteService {
    private athleteRepository: AthleteRepository = new AthleteRepository()
    private modelService: ModelService = new ModelService()

    public async getAthleteExists(athleteId: number): Promise<boolean> {
        const athlete = await this.athleteRepository.selectAthlete(athleteId)
        return !!athlete
    }

    /**
     * Analisa o histórico completo de sessões de um atleta e retorna
     * a taxa de anomalias detectadas ao longo do tempo.
     */
    public async analyzeAthlete(athleteId: number) {
        const sessions = await this.athleteRepository.selectSessionsPerAthlete(athleteId)

        if (sessions.length === 0) {
            return { error: 'Nenhuma sessão encontrada para este atleta.' }
        }

        return await this.modelService.predictBatch(athleteId, sessions)
    }

    /**
     * Analisa apenas a última sessão de um atleta.
     * Útil para alertas em tempo real após uma nova sessão ser registrada.
     */
    public async analyzeLastSession(athleteId: number) {
        const lastSession = await this.athleteRepository.selectLastSession(athleteId)

        if (!lastSession) {
            return { error: 'Nenhuma sessão encontrada para este atleta.' }
        }

        return await this.modelService.predict(athleteId, lastSession)
    }
}

export default AthleteService
