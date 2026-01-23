import csv
import os
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st


BASE_CSV = Path(__file__).resolve().parents[1] / "base" / "bloco1_itens.csv"
OUTPUTS_DIR = Path(__file__).resolve().parents[1] / "outputs"

VOTOS = ["Manter", "Ajustar", "Retirar", "Coletivo"]


def sanitize_filename(s: str) -> str:
    s = (s or "").strip().lower()
    safe = []
    for ch in s:
        if ch.isalnum() or ch in ["-", "_", "."]:
            safe.append(ch)
        elif ch in ["@", " "]:
            safe.append("_")
    out = "".join(safe)
    return out[:80] if out else "participante"


def load_itens(csv_path: Path) -> pd.DataFrame:
    if not csv_path.exists():
        raise FileNotFoundError(f"Base não encontrada: {csv_path}")
    df = pd.read_csv(csv_path)
    expected = {"secao", "codigo", "texto", "tematica"}
    missing = expected - set(df.columns)
    if missing:
        raise ValueError(f"Base CSV sem colunas obrigatórias: {sorted(missing)}")
    df = df.fillna("")
    return df


def main() -> None:
    st.set_page_config(page_title="Validação Delphi – Bloco 1 (piloto)", layout="wide")

    st.title("Validação Delphi – Bloco 1 (fase piloto)")
    st.write(
        "Este formulário é um protótipo interno para teste de layout, fluxo de votação e armazenamento das respostas. "
        "As decisões registradas aqui não possuem caráter definitivo."
    )

    with st.expander("Identificação", expanded=True):
        nome = st.text_input("Nome", value="")
        email = st.text_input("E-mail", value="")
        aceite = st.checkbox("Li e concordo com o uso dos dados exclusivamente para reforço metodológico interno (fase piloto).")

    if not aceite:
        st.info("Para continuar, marque o aceite acima.")
        st.stop()

    try:
        itens = load_itens(BASE_CSV)
    except Exception as e:
        st.error(str(e))
        st.stop()

    st.subheader("Itens do Bloco 1")
    st.write("Selecione um voto por item. Comentário é obrigatório quando o voto for diferente de Manter.")

    respostas = []
    for idx, row in itens.iterrows():
        codigo = str(row["codigo"]).strip()
        texto = str(row["texto"]).strip()
        tematica = str(row["tematica"]).strip()
        secao = str(row["secao"]).strip()

        st.markdown(f"**{codigo}** (Seção {secao} | Temática: {tematica})")
        st.write(texto)

        col1, col2 = st.columns([1, 2])
        with col1:
            voto = st.radio(
                label=f"Voto ({codigo})",
                options=VOTOS,
                index=0,
                key=f"voto_{codigo}_{idx}",
                horizontal=True,
            )
        with col2:
            comentario = st.text_area(
                label=f"Comentário ({codigo})",
                value="",
                key=f"coment_{codigo}_{idx}",
                height=80,
                placeholder="Escreva aqui. Obrigatório se o voto não for 'Manter'.",
            )

        if voto != "Manter" and not comentario.strip():
            st.warning(f"Comentário obrigatório para o item {codigo} quando o voto for {voto}.")
            st.stop()

        respostas.append(
            {
                "secao": secao,
                "codigo": codigo,
                "tematica": tematica,
                "texto": texto,
                "voto_delphi": voto,
                "comentario": comentario.strip(),
            }
        )

        st.divider()

    st.subheader("Enviar")
    if st.button("Enviar respostas", type="primary"):
        if not nome.strip() or not email.strip():
            st.error("Preencha Nome e E-mail.")
            st.stop()

        OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_email = sanitize_filename(email)
        out_path = OUTPUTS_DIR / f"respostas_bloco1_{ts}_{safe_email}.csv"

        header = [
            "timestamp",
            "nome",
            "email",
            "secao",
            "codigo",
            "tematica",
            "texto",
            "voto_delphi",
            "comentario",
        ]

        with out_path.open("w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=header)
            w.writeheader()
            for r in respostas:
                w.writerow(
                    {
                        "timestamp": datetime.now().isoformat(timespec="seconds"),
                        "nome": nome.strip(),
                        "email": email.strip(),
                        **r,
                    }
                )

        st.success(f"Respostas salvas em: {out_path}")
        st.write("Para consolidar, use: python scripts/consolidar_respostas.py")


if __name__ == "__main__":
    main()
