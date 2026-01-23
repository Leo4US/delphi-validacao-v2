import os
import re
from datetime import datetime
import pandas as pd
import streamlit as st

BASE_DIR = "base"
OUTPUT_DIR = "outputs"

VOTOS = ["Manter", "Ajustar", "Retirar", "Coletivo"]

def listar_blocos():
    if not os.path.isdir(BASE_DIR):
        return []
    arquivos = sorted([f for f in os.listdir(BASE_DIR) if re.match(r"bloco\d+_itens\.csv$", f)])
    return arquivos

def carregar_itens(caminho_csv: str) -> pd.DataFrame:
    df = pd.read_csv(caminho_csv, dtype=str).fillna("")
    df.columns = [c.strip().lower() for c in df.columns]

    # fallback: se ainda existir "texto", vira "pergunta"
    if "pergunta" not in df.columns and "texto" in df.columns:
        df["pergunta"] = df["texto"]

    # colunas mínimas
    obrig = ["secao", "codigo", "tematica", "pergunta"]
    faltando = [c for c in obrig if c not in df.columns]
    if faltando:
        raise ValueError(f"CSV sem colunas obrigatórias: {faltando}")

    # garante coluna respostas (opcional)
    if "respostas" not in df.columns:
        df["respostas"] = ""

    # limpeza básica
    for c in ["secao", "codigo", "tematica", "pergunta", "respostas"]:
        df[c] = df[c].astype(str).str.strip()

    return df

def salvar_respostas(registro: dict, respostas: list[dict]) -> str:
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_nome = re.sub(r"[^a-zA-Z0-9_-]+", "_", registro["nome"].strip())[:50] or "anon"
    fname = f"delphi_{registro['bloco']}_{safe_nome}_{ts}.csv"
    out_path = os.path.join(OUTPUT_DIR, fname)

    df = pd.DataFrame(respostas)
    for k, v in registro.items():
        df[k] = v

    # ordena colunas (mais legível)
    col_order = [
        "bloco", "secao", "codigo", "tematica",
        "pergunta", "respostas",
        "voto", "comentario",
        "nome", "email", "cpf",
        "consentimento", "timestamp",
    ]
    cols = [c for c in col_order if c in df.columns] + [c for c in df.columns if c not in col_order]
    df = df[cols]

    df.to_csv(out_path, index=False, encoding="utf-8")
    return out_path

def main():
    st.set_page_config(page_title="Validação Delphi", layout="wide")

    st.title("Validação Delphi (fase piloto)")
    st.write("Protótipo interno para teste de layout, fluxo de votação e armazenamento das respostas.")

    blocos = listar_blocos()
    if not blocos:
        st.error("Nenhum arquivo encontrado em base/ no padrão blocoX_itens.csv.")
        st.stop()

    bloco_arquivo = st.sidebar.selectbox("Escolha o bloco", blocos, index=0)
    caminho_csv = os.path.join(BASE_DIR, bloco_arquivo)

    try:
        itens = carregar_itens(caminho_csv)
    except Exception as e:
        st.error(f"Erro ao ler o CSV: {e}")
        st.stop()

    bloco_id = bloco_arquivo.replace("_itens.csv", "")

    with st.expander("Identificação", expanded=True):
        nome = st.text_input("Nome", "")
        email = st.text_input("E-mail", "")
        cpf = st.text_input("CPF (opcional, se o grupo decidir coletar)", "")
        consent = st.checkbox("Li e concordo com o uso dos dados exclusivamente para reforço metodológico interno (fase piloto).", value=False)

    st.divider()
    st.subheader(f"Itens do {bloco_id}")
    st.write("Para cada item: primeiro leia o trecho do instrumento; depois registre o voto Delphi e, quando necessário, o comentário.")

    respostas = []
    problemas = []

    for i, row in itens.iterrows():
        secao = row["secao"]
        codigo = row["codigo"]
        tematica = row["tematica"]
        pergunta = row["pergunta"]
        resp_txt = row.get("respostas", "")

        # Cabeçalho do item
        st.markdown(f"### {codigo}  |  Seção: {secao}  |  Temática: {tematica}")

        # Opção 2: dois blocos bem destacados
        st.markdown("**Instrumento (pergunta e respostas):**")
        st.markdown(f"> **Pergunta:** {pergunta}")

        if resp_txt.strip():
            st.markdown(f"> **Respostas:** {resp_txt}")

        st.markdown("---")
        st.markdown("**Delphi (decisão e comentário):**")

        col1, col2 = st.columns([1, 3])
        with col1:
            voto = st.radio(
                f"Voto (item {codigo})",
                VOTOS,
                key=f"voto_{codigo}",
                horizontal=False
            )
        with col2:
            comentario = st.text_area(
                f"Comentário (item {codigo})",
                value="",
                key=f"coment_{codigo}",
                height=90
            )

        if voto != "Manter" and not comentario.strip():
            problemas.append(codigo)

        respostas.append({
            "secao": secao,
            "codigo": codigo,
            "tematica": tematica,
            "pergunta": pergunta,
            "respostas": resp_txt,
            "voto": voto,
            "comentario": comentario.strip(),
        })

        st.divider()

    st.subheader("Enviar respostas")
    if st.button("Salvar submissão"):
        if not consent:
            st.error("Marque o consentimento para enviar.")
            st.stop()
        if not nome.strip() or not email.strip():
            st.error("Preencha Nome e E-mail para enviar.")
            st.stop()
        if problemas:
            st.error(f"Há itens com voto diferente de Manter sem comentário: {', '.join(problemas)}")
            st.stop()

        registro = {
            "bloco": bloco_id,
            "nome": nome.strip(),
            "email": email.strip(),
            "cpf": cpf.strip(),
            "consentimento": "sim",
            "timestamp": datetime.now().isoformat(timespec="seconds"),
        }

        out_path = salvar_respostas(registro, respostas)
        st.success(f"Submissão salva em: {out_path}")

if __name__ == "__main__":
    main()
