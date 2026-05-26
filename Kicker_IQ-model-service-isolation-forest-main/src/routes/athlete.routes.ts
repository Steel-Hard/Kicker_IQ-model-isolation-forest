import { Router } from "express"
import AthleteController from "../controllers/Athlete.controller"

class AthleteRoutes {
    private athleteController: AthleteController = new AthleteController()
    private router: Router = Router()

    private baseUrl: string = "/athlete"

    constructor() {
        /**
         * GET /api/athlete/anomaly?id=<athleteId>
         * Analisa o histórico completo de sessões de um atleta.
         */
        this.router.get(
            this.baseUrl + "/anomaly",
            this.athleteController.getAnomalyAnalysis.bind(this.athleteController)
        )

        /**
         * GET /api/athlete/anomaly/last?id=<athleteId>
         * Analisa apenas a última sessão registrada do atleta.
         */
        this.router.get(
            this.baseUrl + "/anomaly/last",
            this.athleteController.getLastSessionAnomaly.bind(this.athleteController)
        )
    }

    public getRouter() {
        return this.router
    }
}

const athleteRoutes = new AthleteRoutes().getRouter()
export default athleteRoutes
