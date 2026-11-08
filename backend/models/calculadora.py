"""Índice de riesgo por distrito y alertas por aumento, sobre datos oficiales."""
import pandas as pd


class CalculadoraRiesgo:
    NIVELES = ["Bajo", "Medio", "Alto"]

    def __init__(self, pesos: dict | None = None, excluir: set | None = None):
        # Pesos por gravedad: criterio propio, debe justificarse en el informe.
        self.pesos = dict(pesos or {"HOMICIDIO": 10, "ROBO": 3, "HURTO": 1})
        self.excluir = set(excluir or ())

    def indice(self, oficial: pd.DataFrame, periodo: str = "2025") -> pd.DataFrame:
        datos = oficial[
            (oficial["periodo"] == periodo) & (~oficial["distrito"].isin(self.excluir))
        ]
        if datos.empty:
            return pd.DataFrame()
        tabla = datos.pivot_table(
            index="distrito", columns="delito", values="cantidad",
            aggfunc="sum", fill_value=0,
        )
        puntaje = pd.Series(0.0, index=tabla.index)
        for delito, peso in self.pesos.items():
            if delito not in tabla.columns:
                tabla[delito] = 0
            puntaje += tabla[delito] * peso
        posicion = puntaje.rank(pct=True)
        tabla["puntaje"] = puntaje
        tabla["indice"] = (posicion * 100).round(1)
        tabla["nivel"] = pd.cut(
            posicion, bins=[0, 1 / 3, 2 / 3, 1], labels=self.NIVELES, include_lowest=True
        )
        return tabla.sort_values("puntaje", ascending=False).reset_index()

    def alertas(self, oficial: pd.DataFrame, umbral: float = 1.2, minimo: int = 10) -> pd.DataFrame:
        """Distritos y delitos donde enero 2026 supera al promedio mensual de 2025."""
        datos = oficial[~oficial["distrito"].isin(self.excluir)]
        tabla = datos.pivot_table(
            index=["distrito", "delito"], columns="periodo", values="cantidad", aggfunc="sum"
        )
        if not {"2025", "2026-01"}.issubset(tabla.columns):
            return pd.DataFrame()
        tabla = tabla.dropna(subset=["2025", "2026-01"])
        tabla = tabla[tabla["2025"] > 0]
        tabla["prom_mensual_2025"] = (tabla["2025"] / 12).round(1)
        tabla["razon"] = (tabla["2026-01"] / tabla["prom_mensual_2025"]).round(2)
        alertas = tabla[(tabla["razon"] >= umbral) & (tabla["2026-01"] >= minimo)]
        return (
            alertas[["2026-01", "prom_mensual_2025", "razon"]]
            .rename(columns={"2026-01": "ene_2026"})
            .sort_values("razon", ascending=False)
            .reset_index()
        )
