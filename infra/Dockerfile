FROM node:22

ENV COREPACK_HOME=/home/node/.cache/corepack
RUN mkdir -p $COREPACK_HOME && chown -R node:node /home/node/.cache

RUN corepack enable && corepack prepare pnpm@10.17.1 --activate

USER node
WORKDIR /app

CMD ["bash"]