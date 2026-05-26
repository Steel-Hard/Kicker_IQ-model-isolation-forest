import { Request, Response } from "express";
import ModelService from "../services/Model.service";
import PlayerMetricsInput from "../types/PlayerMetrics";

class MatchController {
    private modelService: ModelService = new ModelService()

    /**
     * `POST | http://0.0.0.0:0000/match/predict`
     */
    public async matchPredict(req: Request<{}, {}, PlayerMetricsInput>, res: Response): Promise<void> {
        try {
            const match = req.body

            const modelResult = await this.modelService.predict(match)
            const result = this.modelService.interpretResult(modelResult)

            res.status(200).json(result)
        } catch (error: unknown) {
            console.error("Error:", error)
            res.sendStatus(500)
        }
    }
}

export default MatchController