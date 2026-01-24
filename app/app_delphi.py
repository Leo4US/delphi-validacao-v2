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

    # ordena colunas (mais legível e compatível com consolidação)
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
        consent = st.checkbox(
            "Li e concordo com o uso dos dados exclusivamente para reforço metodológico interno (fase piloto).",
            value=False
        )

    # Critérios Delphi (termos do print)
    st.info("Instruções claras sobre os critérios de avaliação e prazos de resposta.", icon="ℹ️")
    with st.expander("Critérios de avaliação (Delphi) - clique para abrir/fechar", expanded=False):
        st.markdown("""
Cada item será avaliado segundo os seguintes critérios:

**Grau de relevância**  
Avaliado por escala Likert de 5 pontos (1 = nada relevante; 5 = muito relevante).

**Aplicabilidade nacional**  
Resposta dicotômica: Sim / Não, considerando a realidade nacional da pesca artesanal.

**Aceitação do item**  
Resposta dicotômica: Sim / Não.

**Campo aberto para comentários e sugestões**  
Espaço para sugestões de ajustes, exclusão ou inclusão de itens.

**Critérios de consenso**  
Será adotado como critério de consenso:  
80% ou mais de concordância dos especialistas para:  
- Relevância (pontuação 4 ou 5);  
- Aplicabilidade (Sim);  
- Aceitação do item (Sim).

Itens que atingirem o consenso na primeira rodada serão considerados validados e seguirão para a rodada seguinte.
""")

    st.divider()
    st.subheader(f"Itens do {bloco_id}")
    st.write("Para cada item: primeiro leia o trecho do instrumento; depois avalie conforme os critérios Delphi e registre comentários quando necessário.")

    respostas = []
    problemas = []

    for _, row in itens.iterrows():
        secao = row["secao"]
        codigo = row["codigo"]
        tematica = row["tematica"]
        pergunta = row["pergunta"]
        resp_txt = row.get("respostas", "")

        st.markdown(f"### {codigo}  |  Seção: {secao}  |  Temática: {tematica}")

        # 1) Instrumento
        with st.container(border=True):
            st.markdown("**1) Instrumento de pesquisa (pergunta e respostas)**")
            st.markdown(f"**Pergunta:** {pergunta}")
            if resp_txt.strip():
                st.markdown("**Respostas:**")
                st.write(resp_txt)

        # 2) Avaliação Delphi (critérios do print)
        with st.container(border=True):
            st.markdown("**2) Avaliação Delphi (critérios)**")

            grau_relevancia = st.radio(
                "Grau de relevância (1 = nada relevante; 5 = muito relevante).",
                options=[1, 2, 3, 4, 5],
                horizontal=True,
                key=f"grau_relevancia_{codigo}"
            )

            aplicabilidade_nacional = st.radio(
                "Aplicabilidade nacional (Sim / Não), considerando a realidade nacional da pesca artesanal.",
                options=["Sim", "Não"],
                horizontal=True,
                key=f"aplicabilidade_nacional_{codigo}"
            )

            aceitacao_item = st.radio(
                "Aceitação do item (Sim / Não).",
                options=["Sim", "Não"],
                horizontal=True,
                key=f"aceitacao_item_{codigo}"
            )

            comentarios_sugestoes = st.text_area(
                "Campo aberto para comentários e sugestões (ajustes, exclusão ou inclusão de itens).",
                value="",
                key=f"comentarios_sugestoes_{codigo}",
                height=110
            )

            # Regra recomendada: comentário obrigatório quando há discordância
            # (Aceitação = Não) ou (Aplicabilidade = Não) ou (Relevância baixa 1–2).
            if (aceitacao_item == "Não" or aplicabilidade_nacional == "Não" or grau_relevancia in [1, 2]) and not comentarios_sugestoes.strip():
                problemas.append(codigo)
                st.warning("Comentário obrigatório quando Aceitação = Não, Aplicabilidade = Não, ou Relevância = 1–2.")

        respostas.append({
            "secao": secao,
            "codigo": codigo,
            "tematica": tematica,
            "pergunta": pergunta,
            "respostas": resp_txt,
            "grau_relevancia": int(grau_relevancia),
            "aplicabilidade_nacional": aplicabilidade_nacional,
            "aceitacao_item": aceitacao_item,
            "comentarios_sugestoes": comentarios_sugestoes.strip(),
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
            problemas_unicos = list(dict.fromkeys(problemas))
            st.error(f"Há itens que exigem comentário e estão sem preenchimento: {', '.join(problemas_unicos)}")
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