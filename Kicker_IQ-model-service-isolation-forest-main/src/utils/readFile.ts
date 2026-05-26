import { readFileSync } from "fs";

function readFile(caminho: string): string {
    try {
        return readFileSync(caminho, "utf-8");
    } catch {
        return ""
    }
}

export default readFile