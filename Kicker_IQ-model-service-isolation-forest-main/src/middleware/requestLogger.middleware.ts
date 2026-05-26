import { Request, Response, NextFunction } from "express";
import readFile from "../utils/readFile";
import createFile from "../utils/createFile";

async function createLogger(log: {date: string, method: string, url: string, status: number, duration: string}) {
    const path = "request.log"
    const content = readFile(path) + JSON.stringify(log) + "\n"
    createFile(path, content)
}

function requestLoggerMiddleware(req: Request, res: Response, next: NextFunction) {
    const start = Date.now();

    res.on("finish", () => {
        const duration = Date.now() - start;
        const now = new Date()
        const log = {
            date: now.toLocaleString("pt-br"),
            method: req.method,
            url: req.originalUrl,
            status: res.statusCode,
            duration: `${duration}ms`
        }
        createLogger(log)
    });

    next();
}

export default requestLoggerMiddleware