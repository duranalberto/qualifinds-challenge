FROM node:22-slim

ENV NEXT_TELEMETRY_DISABLED=1

WORKDIR /app

COPY package.json ./
RUN npm install

COPY . .

EXPOSE 3100

CMD ["npm", "run", "dev", "--", "--hostname", "0.0.0.0"]
