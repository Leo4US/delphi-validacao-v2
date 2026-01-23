import glob
import os
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUTPUTS = ROOT / "outputs"


def main() -> None:
    OUTPUTS.mkdir(parents=True, exist_ok=True)

    files = sorted(glob.glob(str(OUTPUTS / "respostas_bloco1_*.csv")))
    if not files:
        print("Nenhum arquivo encontrado em outputs/ com padrão respostas_bloco1_*.csv")
        return

    dfs = []
    for fp in files:
        try:
            dfs.append(pd.read_csv(fp))
        except Exception as e:
            print(f"Falha ao ler {fp}: {e}")

    if not dfs:
        print("Nenhum arquivo pôde ser lido.")
        return

    df = pd.concat(dfs, ignore_index=True)

    # Consolidação detalhada
    consolidado_csv = OUTPUTS / "consolidado_respostas.csv"
    df.to_csv(consolidado_csv, index=False)

    # Resumo de contagens por voto (total)
    resumo_total = (
        df.groupby(["voto_delphi"])
        .size()
        .reset_index(name="n")
        .sort_values("n", ascending=False)
    )
    total = resumo_total["n"].sum()
    resumo_total["percentual"] = (resumo_total["n"] / total * 100).round(2)

    # Resumo por temática x voto
    resumo_tematica = (
        df.groupby(["tematica", "voto_delphi"])
        .size()
        .reset_index(name="n")
        .sort_values(["tematica", "n"], ascending=[True, False])
    )

    # Resumo por item (codigo) x voto
    resumo_item = (
        df.groupby(["codigo", "voto_delphi"])
        .size()
        .reset_index(name="n")
        .sort_values(["codigo", "n"], ascending=[True, False])
    )

    resumo_csv = OUTPUTS / "resumo_contagens.csv"
    with pd.ExcelWriter(OUTPUTS / "consolidado_respostas.xlsx") as xw:
        df.to_excel(xw, sheet_name="respostas", index=False)
        resumo_total.to_excel(xw, sheet_name="resumo_total", index=False)
        resumo_tematica.to_excel(xw, sheet_name="resumo_tematica", index=False)
        resumo_item.to_excel(xw, sheet_name="resumo_por_item", index=False)

    # Também salvar os resumos em CSV
    resumo_total.to_csv(OUTPUTS / "resumo_total.csv", index=False)
    resumo_tematica.to_csv(OUTPUTS / "resumo_tematica.csv", index=False)
    resumo_item.to_csv(OUTPUTS / "resumo_por_item.csv", index=False)

    print(f"OK. Arquivos gerados em {OUTPUTS}")
    print(f"- {consolidado_csv.name}")
    print(f"- consolidado_respostas.xlsx")
    print(f"- resumo_total.csv / resumo_tematica.csv / resumo_por_item.csv")


if __name__ == "__main__":
    main()
