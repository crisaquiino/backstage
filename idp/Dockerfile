# Dockerfile para Backstage.io
# Este Dockerfile assume que você já tem um projeto Backstage configurado
# Se não tiver, você precisará criar um projeto Backstage primeiro usando:
# npx @backstage/create-app

FROM node:18-bullseye

WORKDIR /app

# Copia arquivos de configuração do Backstage
COPY package.json yarn.lock* package-lock.json* ./

# Instala dependências
RUN if [ -f yarn.lock ]; then yarn install --frozen-lockfile; \
    elif [ -f package-lock.json ]; then npm ci; \
    else echo "Lockfile not found." && exit 1; \
    fi

# Copia o resto dos arquivos
COPY . .

# Build do Backstage
RUN yarn build --config app-config.production.yaml || npm run build

# Expõe portas
EXPOSE 3000 7007

# Comando para iniciar o Backstage
CMD ["yarn", "start", "--config", "app-config.production.yaml"] || ["npm", "start", "--", "--config", "app-config.production.yaml"]
