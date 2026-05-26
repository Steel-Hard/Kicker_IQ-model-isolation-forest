import app from "./app"
import dontenv from "dotenv"

dontenv.config();

const {PORT} = process.env;

const port = PORT || 3002;

app.listen(port, () => {
    console.log(`✅ | Servidor rodando na porta http://0.0.0.0:${port}`)
})