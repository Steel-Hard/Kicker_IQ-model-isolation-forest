# EstÃ¡gio de construÃ§Ã£o
FROM node:20-slim AS builder
# Instala dependÃªncias de compilaÃ§Ã£o necessÃ¡rias para mÃ³dulos nativos
RUN apt-get update && apt-get install -y python3 make g++ && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY package*.json tsconfig.json ./
RUN npm install
COPY src ./src
RUN npm run build

# EstÃ¡gio de produÃ§Ã£o
FROM node:20-slim AS production
# Instala libgomp1 (necessÃ¡ria para o ONNX Runtime no Linux)
RUN apt-get update && apt-get install -y libgomp1 && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY --from=builder /app/out ./out
COPY --from=builder /app/node_modules ./node_modules
COPY package*.json ./
COPY model ./model

EXPOSE 3000
CMD ["node", "out/index.js"]

