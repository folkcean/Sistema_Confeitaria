import os

from app import create_app
from app.config import Config, ConfigProducao

# APP_ENV=producao (definido no docker-compose) liga a configuração de produção.
# Sem a variável, cai no padrão de desenvolvimento
if os.getenv("APP_ENV") == "producao":
    configuracao = ConfigProducao
else:
    configuracao = Config

app = create_app(configuracao)
