"""
Constantes utilizadas em todo o sistema.
"""

# Tipos de classes de ativos
ASSET_TYPES = ["FII", "Ações", "ETF", "Renda Fixa", "Fundos"]

# Tipos de tributação
TAX_TYPES = ["regressivo", "fixo_15", "isento", "come_cotas"]

# Alíquota única de IR para Renda Fixa (regra 2025)
# Nota: valor padrão; o valor efetivo vem de app_settings no banco
IR_ALIQUOTA_UNICA = 0.175  # 17,5%

# Tabela regressiva de IR (LEGADA — mantida para referência histórica)
IR_REGRESSIVO = [
    (180, 0.225),    # Até 180 dias: 22,5%
    (360, 0.20),     # 181 a 360 dias: 20%
    (720, 0.175),    # 361 a 720 dias: 17,5%
    (None, 0.15),    # Acima de 720 dias: 15%
]

# Alíquota fixa para ações e ETFs
TAX_RATE_ACOES_ETF = 0.15

# Isenção de IR para FII (dividendos)
TAX_RATE_FII_DIVIDENDOS = 0.0

# Come-cotas semestral (maio e novembro)
COME_COTAS_RATE_LONGO_PRAZO = 0.15
COME_COTAS_RATE_CURTO_PRAZO = 0.20
COME_COTAS_MONTHS = [5, 11]

# Benchmarks padrão (retornos anuais médios históricos para referência)
BENCHMARK_DEFAULTS = {
    "CDI": 13.65,
    "IPCA": 4.50,
    "SELIC": 13.75,
    "IBOV": 12.0,
    "IFIX": 10.0,
}

# Safe Withdrawal Rate padrão (Regra dos 4%)
DEFAULT_SWR = 4.0

# Meses por ano
MONTHS_PER_YEAR = 12

# Duração padrão da projeção (30 anos)
DEFAULT_PROJECTION_MONTHS = 360

# Configuração de autenticação
TWO_FACTOR_CODE_LENGTH = 6
TWO_FACTOR_EXPIRY_SECONDS = 300  # 5 minutos

# Formatação monetária
CURRENCY_SYMBOL = "R$"
CURRENCY_LOCALE = "pt_BR"
