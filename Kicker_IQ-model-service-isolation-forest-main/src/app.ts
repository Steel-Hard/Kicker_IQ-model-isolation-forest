import express, { Request, Response } from 'express'
import cors from 'cors'
import requestLoggerMiddleware from './middleware/requestLogger.middleware'
import dotenv from "dotenv"
import matchRoutes from './routes/match.routes'
import athleteRoutes from './routes/athlete.routes'

dotenv.config()

const app = express()

app.use(cors())
app.use(express.json())
app.use(requestLoggerMiddleware)

app.use("/api", matchRoutes)
app.use("/api", athleteRoutes)
app.use("/", (_: Request, res: Response) => res.sendStatus(404))

export default app