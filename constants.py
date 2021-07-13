from dotenv import dotenv_values

env_vars = dotenv_values('.env')
locals().update(env_vars)

ALLOWED_IDS = [int(el) for el in EXTRA_ALLOWED_IDS.split(',') + [ADMIN_ID, LOGGER_CHAT_ID, FAMILY_BUDGET_CHAT_ID]]
