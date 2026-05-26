import { writeFile } from "fs/promises";

async function createFile(path: string, content: string): Promise<void> {
    try {
        await writeFile(path, content, "utf-8")
    } catch (error) {
        console.error("Erro ao criar arquivo", error)
    }
}

export default createFile