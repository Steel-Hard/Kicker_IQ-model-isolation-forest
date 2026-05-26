import { Router } from "express"
import MatchController from "../controllers/Match.controller"

class MatchRoutes {
    private matchController: MatchController = new MatchController()
    private router: Router = Router()

    private url: string = "/match"

    constructor() {
        this.router.post(
            this.url + "/predict",
            this.matchController.matchPredict.bind(this.matchController)
        )
    }

    public getRouter() {
        return this.router
    }
}

const matchRoutes = new MatchRoutes().getRouter()
export default matchRoutes