"""
Serviço de busca de indicadores econômicos.

Fonte: Banco Central do Brasil — Sistema Gerenciador de Séries Temporais (SGS).
API pública, gratuita e sem autenticação.
Documentação: https://dadosabertos.bcb.gov.br/
"""

import json
import logging
from datetime import datetime, timedelta
from urllib.request import urlopen, Request
from urllib.error import URLError

import streamlit as st

logger = logging.getLogger(__name__)

# Séries do BCB SGS
BCB_SERIES = {
    "selic_meta": 432,       # Taxa Selic Meta (% a.a.) — decidida pelo COPOM
    "cdi_diario": 12,        # Taxa CDI diária (% a.d.) — precisa anualizar
    "ipca_12m": 13522,       # IPCA acumulado 12 meses (% a.a.)
}

BCB_API_URL = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.{serie}/dados/ultimos/1?formato=json"

# Dias úteis por ano para anualização do CDI
BUSINESS_DAYS_PER_YEAR = 252

# Timeout para requests (segundos)
REQUEST_TIMEOUT = 10


def _fetch_bcb_serie(serie_id: int) -> float | None:
    """Busca o último valor de uma série do BCB SGS."""
    url = BCB_API_URL.format(serie=serie_id)
    try:
        req = Request(url, headers={"Accept": "application/json"})
        with urlopen(req, timeout=REQUEST_TIMEOUT) as response:
            data = json.loads(response.read().decode("utf-8"))
            if data and isinstance(data, list) and len(data) > 0:
                valor = data[-1].get("valor", "0")
                return float(valor.replace(",", "."))
    except (URLError, ValueError, KeyError, IndexError, TypeError) as e:
        logger.warning(f"Erro ao buscar série {serie_id} do BCB: {e}")
    return None


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_market_indicators() -> dict:
    """
    Busca os indicadores econômicos atuais do Banco Central.
    
    Retorna dict com:
        - selic: Taxa Selic Meta (% a.a.)
        - cdi: Taxa CDI (% a.a.)
        - ipca: IPCA acumulado 12 meses (% a.a.)
        - inflation: Mesma do IPCA (usado como inflação padrão)
        - source: Fonte dos dados
        - updated_at: Data/hora da busca
        - success: Se a busca foi bem-sucedida
    """
    results = {
        "selic": None,
        "cdi": None,
        "ipca": None,
        "inflation": None,
        "source": "Banco Central do Brasil (SGS)",
        "updated_at": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "success": False,
    }

    try:
        selic = _fetch_bcb_serie(BCB_SERIES["selic_meta"])
        cdi_diario = _fetch_bcb_serie(BCB_SERIES["cdi_diario"])
        ipca = _fetch_bcb_serie(BCB_SERIES["ipca_12m"])

        if selic is not None:
            results["selic"] = round(selic, 2)

        if cdi_diario is not None and cdi_diario > 0:
            # Série 12 retorna a taxa CDI DIÁRIA (ex: 0.055131 = 0.055131% ao dia)
            # Anualizar: ((1 + taxa/100)^252 - 1) * 100
            cdi_anual = ((1 + cdi_diario / 100) ** BUSINESS_DAYS_PER_YEAR - 1) * 100
            results["cdi"] = round(cdi_anual, 2)
        elif selic is not None:
            # Fallback: CDI ≈ Selic - 0.10 p.p.
            results["cdi"] = round(selic - 0.10, 2)

        if ipca is not None:
            results["ipca"] = round(ipca, 2)
            results["inflation"] = round(ipca, 2)

        # Considerar sucesso se pelo menos um indicador foi obtido
        results["success"] = any(
            results[k] is not None for k in ["selic", "cdi", "ipca"]
        )

    except Exception as e:
        logger.error(f"Erro geral ao buscar indicadores: {e}")

    return results


def get_indicators(force_refresh: bool = False) -> dict:
    """
    Retorna indicadores econômicos, usando cache ou buscando novos.
    
    Args:
        force_refresh: Se True, limpa o cache e busca dados novos.
    
    Returns:
        Dict com selic, cdi, ipca, inflation, source, updated_at, success.
    """
    if force_refresh:
        fetch_market_indicators.clear()

    return fetch_market_indicators()
