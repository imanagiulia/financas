from datetime import date
from typing import Optional, Dict, Any


def round_brl(value: float) -> float:
    """Arredonda valor financeiro para 2 casas decimais."""
    return round(float(value), 2)


# Tabela regressiva oficial de IOF para aplicacoes de renda fixa (Decreto 6.306/2007)
# Indices 0 a 29 correspondem aos dias 1 a 30. A partir do dia 30, o IOF e 0%.
IOF_RATES = [
    96, 93, 90, 86, 83, 80, 76, 73, 70, 66,
    63, 60, 56, 53, 50, 46, 43, 40, 36, 33,
    30, 26, 23, 20, 16, 13, 10,  6,  3,  0
]

# Investimentos isentos de IR e IOF para pessoas fisicas no Brasil
EXEMPT_TYPES = {
    "lci", "lca", "cri", "cra", "poupanca", "poupança"
}


def is_tax_exempt(inv_type: Optional[str]) -> bool:
    """Verifica se o tipo de investimento e isento de IR/IOF para pessoa fisica."""
    if not inv_type:
        return False
    return inv_type.strip().lower() in EXEMPT_TYPES


def get_iof_rate(days: int, inv_type: Optional[str] = None) -> float:
    """
    Retorna a aliquota de IOF percentual aplicavel para a quantidade de dias corridos.
    Isento a partir do 30º dia ou se o tipo for isento por lei.
    """
    if is_tax_exempt(inv_type):
        return 0.0
    if days <= 0:
        return 0.0
    if 1 <= days <= 29:
        return float(IOF_RATES[days - 1])
    return 0.0


def get_ir_rate(days: int, inv_type: Optional[str] = None) -> float:
    """
    Retorna a aliquota regressiva de Imposto de Renda (IR) para renda fixa (Lei 11.033/2004):
    - Ate 180 dias: 22,5%
    - De 181 a 360 dias: 20,0%
    - De 361 a 720 dias: 17,5%
    - Acima de 720 dias: 15,0%
    - Isento para LCI, LCA, CRI, CRA, Poupanca
    """
    if is_tax_exempt(inv_type):
        return 0.0
    if days <= 180:
        return 22.5
    elif days <= 360:
        return 20.0
    elif days <= 720:
        return 17.5
    else:
        return 15.0


def calculate_tax(gross_gain: float, days: int, inv_type: Optional[str] = None) -> Dict[str, Any]:
    """
    Calcula o desconto de IOF e IR sobre o rendimento bruto de renda fixa.
    
    Regra legal brasileira:
    1. O IOF incide primeiro sobre o ganho bruto caso resgatado em menos de 30 dias.
    2. O IR incide sobre a base tributavel apos desconto do IOF: max(Ganho Bruto - IOF, 0).
    """
    exempt = is_tax_exempt(inv_type)
    if gross_gain <= 0 or exempt:
        return {
            "is_exempt": exempt,
            "iof_rate": 0.0,
            "iof_amount": 0.0,
            "ir_rate": 0.0 if exempt else get_ir_rate(days, inv_type),
            "ir_amount": 0.0,
            "total_tax": 0.0,
        }

    iof_rate = get_iof_rate(days, inv_type)
    iof_amount = gross_gain * (iof_rate / 100.0)

    taxable_gain = max(gross_gain - iof_amount, 0.0)
    ir_rate = get_ir_rate(days, inv_type)
    ir_amount = taxable_gain * (ir_rate / 100.0)

    total_tax = iof_amount + ir_amount

    return {
        "is_exempt": False,
        "iof_rate": iof_rate,
        "iof_amount": round_brl(iof_amount),
        "ir_rate": ir_rate,
        "ir_amount": round_brl(ir_amount),
        "total_tax": round_brl(total_tax),
    }


def calculate_yield(
    invested_amount: float,
    rate: float,
    rate_type: str,
    start_date: date,
    end_date: Optional[date] = None,
    cdi_rate: float = 10.5,
    ipca_rate: float = 4.5,
    selic_rate: float = 13.75,
    reference_date: Optional[date] = None,
    inv_type: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Calcula valor acumulado bruto, descontos tributarios (IOF e IR),
    valor liquido, ganho liquido e percentuais de rentabilidade.
    
    Regra pura de negocio, sem dependencia de banco de dados ou framework HTTP.
    - rate: taxa informada no investimento (ex: 12.0 para 12% a.a., 110 para 110% do CDI, ou 0.15 para SELIC + 0.15% a.a.)
    - cdi_rate: taxa anual do CDI (ex: 10.5 para 10.5% a.a.)
    - ipca_rate: taxa anual do IPCA (ex: 4.5 para 4.5% a.a.)
    - selic_rate: taxa anual da Selic (ex: 13.75 para 13.75% a.a.)
    - inv_type: tipo do investimento (CDB, Tesouro Selic, Tesouro IPCA, LCI, etc.)
    """
    ref_date = reference_date or date.today()
    
    # Se ja venceu antes da data de referencia, o calculo trava na data de vencimento
    end = end_date if (end_date and ref_date > end_date) else ref_date
    days = max((end - start_date).days, 0)
    years = days / 365.0

    rate_dec = rate / 100.0
    cdi_dec = cdi_rate / 100.0
    ipca_dec = ipca_rate / 100.0
    selic_dec = selic_rate / 100.0

    if rate_type == "prefixado":
        current = invested_amount * ((1 + rate_dec) ** years)
    elif rate_type == "cdi":
        effective = cdi_dec * rate_dec
        current = invested_amount * ((1 + effective) ** years)
    elif rate_type == "ipca":
        # IPCA + spread: (1 + ipca) * (1 + spread) - 1
        effective = (1 + ipca_dec) * (1 + rate_dec) - 1
        current = invested_amount * ((1 + effective) ** years)
    elif rate_type in ["selic", "selic_plus"]:
        # SELIC + taxa adicional: (1 + selic) * (1 + taxa) - 1
        effective = (1 + selic_dec) * (1 + rate_dec) - 1
        current = invested_amount * ((1 + effective) ** years)
    else:
        current = invested_amount

    gross_gain = current - invested_amount
    gross_gain_pct = (gross_gain / invested_amount * 100.0) if invested_amount > 0 else 0.0

    # Calculo dos descontos tributarios (IOF e IR)
    tax_info = calculate_tax(gross_gain, days, inv_type)
    total_tax = tax_info["total_tax"]
    net_gain = max(gross_gain - total_tax, 0.0) if gross_gain > 0 else gross_gain
    net_value = invested_amount + net_gain
    net_gain_pct = (net_gain / invested_amount * 100.0) if invested_amount > 0 else 0.0

    return {
        "current_value": round_brl(current),
        "gain": round_brl(gross_gain),
        "gain_pct": round(gross_gain_pct, 2),
        "days_elapsed": days,
        "is_exempt": tax_info["is_exempt"],
        "iof_rate": tax_info["iof_rate"],
        "iof_amount": tax_info["iof_amount"],
        "ir_rate": tax_info["ir_rate"],
        "ir_amount": tax_info["ir_amount"],
        "total_tax": tax_info["total_tax"],
        "net_gain": round_brl(net_gain),
        "net_value": round_brl(net_value),
        "net_gain_pct": round(net_gain_pct, 2),
    }
