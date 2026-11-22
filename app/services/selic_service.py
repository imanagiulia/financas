import json
import logging
import urllib.request
import urllib.error
from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session

from models import AppSettings

logger = logging.getLogger("selic_service")

# URLs oficiais do SGS (Sistema Gerenciador de Series Temporais) do Banco Central do Brasil
BCB_SERIES_432 = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.432/dados/ultimos/1?formato=json"
BCB_SERIES_1178 = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.1178/dados/ultimos/1?formato=json"


def fetch_current_selic(timeout_seconds: int = 6) -> Optional[Dict[str, Any]]:
    """
    Consulta a taxa Selic oficial direto da API do Banco Central do Brasil.
    Prioriza a Meta Selic do Copom (Serie 432) e usa a Selic acumulada diaria (Serie 1178) como contingencia.
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json",
    }
    candidates = [
        ("Meta Selic (Copom - Serie 432)", BCB_SERIES_432),
        ("Selic Diaria Anualizada (Serie 1178)", BCB_SERIES_1178),
    ]

    for name, url in candidates:
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=timeout_seconds) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode("utf-8"))
                    if data and isinstance(data, list) and len(data) > 0 and "valor" in data[0]:
                        rate = float(data[0]["valor"])
                        data_referencia = data[0].get("data", "")
                        logger.info(f"Taxa Selic obtida com sucesso via {name}: {rate}% (data ref: {data_referencia})")
                        return {
                            "rate": rate,
                            "date": data_referencia,
                            "source": name,
                        }
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, ValueError, Exception) as e:
            logger.warning(f"Falha ao consultar {name}: {e}")

    logger.error("Nao foi possivel obter a taxa Selic em nenhuma serie do BCB.")
    return None


def get_stored_selic_rate(db: Session, user_id: Optional[str] = None, fallback: float = 13.75) -> float:
    """Retorna a taxa Selic armazenada no banco para o usuario ou valor fallback."""
    q = db.query(AppSettings).filter(AppSettings.key == "selic_rate")
    if user_id is not None:
        q = q.filter(AppSettings.user_id == user_id)
    row = q.first()
    if row and row.value:
        try:
            return float(row.value)
        except ValueError:
            pass
    return fallback


def _upsert_user_selic(db: Session, user_id: str, rate: float, update_info: str) -> None:
    row_rate = (
        db.query(AppSettings)
        .filter(AppSettings.user_id == user_id, AppSettings.key == "selic_rate")
        .first()
    )
    if row_rate:
        row_rate.value = str(rate)
    else:
        db.add(AppSettings(user_id=user_id, key="selic_rate", value=str(rate)))

    row_update = (
        db.query(AppSettings)
        .filter(AppSettings.user_id == user_id, AppSettings.key == "selic_last_update")
        .first()
    )
    if row_update:
        row_update.value = update_info
    else:
        db.add(AppSettings(user_id=user_id, key="selic_last_update", value=update_info))


def sync_selic_rate(db: Session, user_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Sincroniza a taxa Selic oficial do Banco Central com as configuracoes do sistema.
    Se user_id for informado, atualiza apenas aquele usuario; caso contrario, atualiza todos os usuarios.
    """
    fetched = fetch_current_selic()
    now_str = datetime.now().strftime("%d/%m/%Y %H:%M")

    if fetched:
        rate = fetched["rate"]
        ref_date = fetched["date"]
        source = fetched["source"]
        update_info = f"{now_str} (Ref: {ref_date})"

        if user_id:
            target_users = [user_id]
        else:
            target_users = [
                str(r[0]) for r in db.query(AppSettings.user_id).distinct().all()
            ]

        for uid in target_users:
            _upsert_user_selic(db, uid, rate, update_info)

        db.commit()
        return {
            "success": True,
            "rate": rate,
            "ref_date": ref_date,
            "last_update": update_info,
            "source": source,
            "updated_users": len(target_users),
            "message": f"Taxa Selic atualizada com sucesso para {rate}% a.a. via Banco Central ({source}).",
        }
    else:
        current_rate = get_stored_selic_rate(db, user_id=user_id)
        return {
            "success": False,
            "rate": current_rate,
            "message": f"Nao foi possivel conectar ao Banco Central. Mantida a taxa atual de {current_rate}% a.a.",
        }
