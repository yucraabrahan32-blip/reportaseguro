"""Análisis de los reportes ciudadanos: por tipo, hora, franja y distrito."""
import pandas as pd


class AnalizadorIncidentes:
    FRANJAS = [
        ("Madrugada (0-5 h)", 0, 5),
        ("Mañana (6-11 h)", 6, 11),
        ("Tarde (12-17 h)", 12, 17),
        ("Noche (18-23 h)", 18, 23),
    ]

    def __init__(self, incidentes: pd.DataFrame):
        self.df = incidentes.copy()
        horas = self.df["hora_hecho"].astype(str).str[:2]
        self.df["hora"] = pd.to_numeric(horas, errors="coerce")

    @classmethod
    def franja_de(cls, hora):
        if pd.isna(hora):
            return None
        for nombre, inicio, fin in cls.FRANJAS:
            if inicio <= hora <= fin:
                return nombre
        return None

    def filtrar(self, departamento: str | None = None, delito: str | None = None):
        df = self.df
        if departamento:
            df = df[df["departamento"] == departamento]
        if delito:
            df = df[df["delito"] == delito]
        return AnalizadorIncidentes(df)

    def por_tipo(self) -> pd.DataFrame:
        conteo = self.df.groupby("delito").size().rename("reportes").reset_index()
        return conteo.sort_values("reportes", ascending=False).reset_index(drop=True)

    def por_hora(self) -> pd.DataFrame:
        conteo = self.df["hora"].dropna().astype(int).value_counts()
        return pd.DataFrame({
            "hora": range(24),
            "reportes": [int(conteo.get(h, 0)) for h in range(24)],
        })

    def por_franja(self) -> pd.DataFrame:
        conteo = self.df["hora"].map(self.franja_de).value_counts()
        return pd.DataFrame({
            "franja": [f[0] for f in self.FRANJAS],
            "reportes": [int(conteo.get(f[0], 0)) for f in self.FRANJAS],
        })

    def por_distrito(self, limite: int = 10) -> pd.DataFrame:
        conteo = (
            self.df.groupby(["departamento", "provincia", "distrito"], dropna=False)
            .size().rename("reportes").reset_index()
        )
        return conteo.sort_values("reportes", ascending=False).head(limite).reset_index(drop=True)
