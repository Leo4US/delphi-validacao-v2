import os
import re
from datetime import datetime
import pandas as pd
import streamlit as st

BASE_DIR = "base"
OUTPUT_DIR = "outputs"

def listar_blocos():
    if not os.path.isdir(BASE_DIR):
        return []
    arquivos = sorted([f for f in os.listdir(BASE_DIR) if re.match(r"bloco\d+_itens\.csv$", f)])
    return arquivos

def carregar_itens(caminho_csv: str) -> pd.DataFrame:
    df = pd.read_csv(caminho_csv, dtype=str).fillna("")
    df.columns = [c.strip().lower() for c in df.columns]

    if "pergunta" not in df.columns and "texto" in df.columns:
        df["pergunta"] = df["texto"]

    obrig = ["secao", "codigo", "tematica", "pergunta"]
    faltando = [c for c in obrig if c not in df.columns]
    if faltando:
        raise ValueError(f"CSV sem colunas obrigatórias: {faltando}")

    if "respostas" not in df.columns:
        df["respostas"] = ""

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

    col_order = [
        "bloco", "secao", "codigo", "tematica",
        "pergunta", "respostas",
        "grau_relevancia", "aplicabilidade_nacional", "aceitacao_item",
        "comentarios_sugestoes",
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
    st.write("Protótipo interno para teste de layout, fluxo de avaliação e armazenamento das respostas.")

    blocos = listar_blocos()
    if not blocos:
        st.error("Nenhum arquivo encontrado em base/ no padrão blocoX_itens.csv.")
        st.stop()

    bloco_arquivo = st.sidebar.selectbox("Escolha o bloco", blocos, index=0)
    caminho_csv = os.path.join(BASE_DIR, bloco_arquivo)

    itens = carregar_itens(caminho_csv)
    bloco_id = bloco_arquivo.replace("_itens.csv", "")

    with st.expander("Identificação", expanded=True):
        nome = st.text_input("Nome")
        email = st.text_input("E-mail")
        cpf = st.text_input("CPF (opcional)")
        consent = st.checkbox("Li e concordo com o uso dos dados exclusivamente para reforço metodológico interno.")

    st.info("Instruções claras sobre os critérios de avaliação e prazos de resposta.", icon="ℹ️")

    respostas = []
    problemas = []

    for i, row in itens.reset_index(drop=True).iterrows():
        secao = row["secao"]
        codigo = row["codigo"]
        tematica = row["tematica"]
        pergunta = row["pergunta"]
        resp_txt = row.get("respostas", "")
        item_uid = f"{bloco_id}__{codigo}__{i}"

        st.markdown(f"### {codigo} | Seção: {secao} | Temática: {tematica}")

        with st.container(border=True):
            st.markdown("**1) Instrumento**")
            st.markdown(f"**Pergunta:** {pergunta}")
            if resp_txt.strip():
                st.write(resp_txt)

        with st.container(border=True):
            st.markdown("**2) Avaliação Delphi**")

            grau_relevancia = st.radio(
                "Grau de relevância",
                options=[3, 4, 5],
                horizontal=True,
                key=f"grau_{item_uid}",
            )

            aplicabilidade_nacional = st.radio(
                "Aplicabilidade nacional",
                options=["Sim", "Não"],
                index=0,
                horizontal=True,
                key=f"aplic_{item_uid}",
            )

            aceitacao_item = st.radio(
                "Aceitação do item",
                options=["Sim", "Não"],
                index=0,
                horizontal=True,
                key=f"aceita_{item_uid}",
            )

            comentarios_sugestoes = st.text_area(
                "Comentários e sugestões",
                key=f"coment_{item_uid}",
                height=100
            )

            if (aceitacao_item == "Não" or aplicabilidade_nacional == "Não") and not comentarios_sugestoes.strip():
                problemas.append(codigo)

        respostas.append({
            "secao": secao,
            "codigo": codigo,
            "tematica": tematica,
            "pergunta": pergunta,
            "respostas": resp_txt,
            "grau_relevancia": grau_relevancia,
            "aplicabilidade_nacional": aplicabilidade_nacional,
            "aceitacao_item": aceitacao_item,
            "comentarios_sugestoes": comentarios_sugestoes.strip(),
        })

    if st.button("Salvar submissão"):
        if not consent or not nome or not email:
            st.error("Identificação e consentimento são obrigatórios.")
            st.stop()
        if problemas:
            st.error(f"Itens sem comentário obrigatório: {', '.join(sorted(set(problemas)))}")
            st.stop()

        registro = {
            "bloco": bloco_id,
            "nome": nome.strip(),
            "email": email.strip(),
            "cpf": cpf.strip(),
            "consentimento": "sim",
            "timestamp": datetime.now().isoformat(timespec="seconds"),
        }

        path = salvar_respostas(registro, respostas)
        st.success(f"Submissão salva: {path}")

if __name__ == "__main__":
    main()