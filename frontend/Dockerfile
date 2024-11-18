# build env
FROM node:21.7.1-alpine
WORKDIR /app
COPY package*.json ./
RUN npm ci --legacy-peer-deps
COPY . ./
ENV PUBLIC_URL=./
RUN npm run build
CMD cp -r build result_build
