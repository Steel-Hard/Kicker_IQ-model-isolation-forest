import { Client } from "pg"
import dotenv from "dotenv"
import { types } from "pg"

types.setTypeParser(1700, (val) => parseFloat(val)) // NUMERIC
types.setTypeParser(701,  (val) => parseFloat(val)) // FLOAT8
types.setTypeParser(700,  (val) => parseFloat(val)) // FLOAT4

dotenv.config()

const db = new Client({
    connectionString: process.env.POSTGRESQL_URL
})

db.connect()
    .then(() => console.log("🟢 Conectado ao PostgreSQL com sucesso!"))
    .catch((err: unknown) => console.error("🔴 Erro ao conectar:", err))

export default db