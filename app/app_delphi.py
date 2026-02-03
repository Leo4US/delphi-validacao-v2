import os
import re
from datetime import datetime
import pandas as pd
import streamlit as st
import shutil
import subprocess
import tempfile
from pathlib import Path

BASE_DIR = "base"
OUTPUT_DIR = "outputs"

INSTRUCOES_DELPHI = """
### Instruções – Rodada Delphi

1) Leia o item do questionário (pergunta e respostas).
2) Avalie o item conforme os critérios:
- Grau de relevância: 1 (nada relevante) a 5 (muito relevante)
- Aplicabilidade nacional: Sim/Não
- Aceitação do item: Sim/Não
3) Comentários são obrigatórios quando:
- Aceitação = Não, ou
- Aplicabilidade = Não

Ao prosseguir, você confirma que leu e compreendeu estas instruções.
"""

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
        "concordancia_instr_delphi",
        "consentimento", "timestamp",
    ]
    cols = [c for c in col_order if c in df.columns] + [c for c in df.columns if c not in col_order]
    df = df[cols]

    df.to_csv(out_path, index=False, encoding="utf-8")
    return out_path

PRIVATE_REPO = "Leo4US/delphi-validacao-respostas"
PRIVATE_BRANCH = "main"

def backup_para_repo_privado(csv_path: str, bloco_id: str) -> str:
    token = (
        st.secrets.get("GITHUB_TOKEN", "").strip()
        or os.getenv("GITHUB_TOKEN", "").strip()
    )
    if not token:
        raise RuntimeError("GITHUB_TOKEN não encontrado (secrets/env).")

    git_user_email = (
        st.secrets.get("GIT_USER_EMAIL", "").strip()
        or os.getenv("GIT_USER_EMAIL", "").strip()
        or "noreply@example.com"
    )

    git_user_name = (
        st.secrets.get("GIT_USER_NAME", "").strip()
        or os.getenv("GIT_USER_NAME", "").strip()
        or "delphi-bot"
    )

    dest_rel = f"respostas/{bloco_id}/{os.path.basename(csv_path)}"

    with tempfile.TemporaryDirectory() as td:
        repo_dir = Path(td) / "repo_privado"
        repo_url = f"https://x-access-token:{token}@github.com/{PRIVATE_REPO}.git"

        subprocess.run(
            ["git", "clone", "--depth", "1", "--branch", PRIVATE_BRANCH, repo_url, str(repo_dir)],
            check=True,
            text=True,
        )

        (repo_dir / f"respostas/{bloco_id}").mkdir(parents=True, exist_ok=True)
        shutil.copy2(csv_path, repo_dir / dest_rel)

        subprocess.run(["git", "-C", str(repo_dir), "add", dest_rel], check=True)

        msg = f"Backup {bloco_id}: {os.path.basename(csv_path)}"
        subprocess.run(
            [
                "git", "-C", str(repo_dir),
                "-c", f"user.name={git_user_name}",
                "-c", f"user.email={git_user_email}",
                "commit", "-m", msg
            ],
            check=False,
            text=True,
        )

        subprocess.run(["git", "-C", str(repo_dir), "push", "origin", PRIVATE_BRANCH], check=True, text=True)

    return dest_rel

def main():
    st.set_page_config(page_title="Validação Delphi", layout="wide")

    st.title("Validação Rodada Delphi (v.beta)")
    st.write("Protótipo interno para teste de layout, fluxo de avaliação e armazenamento das respostas.")

    # =========================
    # Etapa 0) Instruções Delphi (leitura obrigatória)
    # =========================
    with st.expander("Instruções do Método Delphi (leitura obrigatória)", expanded=True):
        st.markdown(INSTRUCOES_DELPHI)

    li_instrucoes = st.checkbox("Li e compreendi as instruções do Método Delphi.", key="li_instr")

    # =========================
    # Etapa 1) Seleção de bloco
    # =========================
    blocos = listar_blocos()
    if not blocos:
        st.error("Nenhum arquivo encontrado em base/ no padrão blocoX_itens.csv.")
        st.stop()

    bloco_arquivo = st.sidebar.selectbox("Escolha o bloco", blocos, index=0)
    caminho_csv = os.path.join(BASE_DIR, bloco_arquivo)

    try:
        itens = carregar_itens(caminho_csv)
    except Exception as e:
        st.error("Erro ao carregar o CSV do bloco.")
        st.text(str(e))
        st.stop()

    bloco_id = bloco_arquivo.replace("_itens.csv", "")

    # =========================
    # Etapa 2) Identificação + consentimento
    # =========================
    with st.expander("Identificação", expanded=True):
        nome = st.text_input("Nome", key="nome")
        email = st.text_input("E-mail", key="email")
        cpf = st.text_input("CPF (opcional)", key="cpf")
        consent = st.checkbox(
            "Li e concordo com o uso dos dados exclusivamente para reforço metodológico interno.",
            key="consent"
        )

    # =========================
    # Etapa 3) Concordância (Delphi)
    # =========================
    with st.expander("Concordância (Método Delphi)", expanded=True):
        st.markdown(INSTRUCOES_DELPHI)
        concorda_instr = st.checkbox(
            "Li e compreendi as instruções acima e concordo em participar desta rodada.",
            value=False,
            key="concorda_instr"
        )

    if not concorda_instr:
        st.warning("Para acessar o questionário, é necessário ler e concordar com as instruções.")
        st.stop()

    st.info("Instruções claras sobre os critérios de avaliação e prazos de resposta.", icon="ℹ️")

    # =========================
    # Etapa 4) Loop de itens
    # =========================
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
                options=[1, 2, 3, 4, 5],
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

    # =========================
    # Etapa 5) Envio
    # =========================
    st.divider()
    st.subheader("Enviar respostas")

    # >>>> BOTÃO NO NÍVEL CORRETO (direto dentro de main) <<<<
    if st.button("Salvar submissão"):
        if not li_instrucoes:
            st.error("Você precisa confirmar a leitura das instruções do Método Delphi para enviar.")
            st.stop()

        if not consent or not nome.strip() or not email.strip():
            st.error("Identificação (nome e e-mail) e consentimento são obrigatórios.")
            st.stop()

        if problemas:
            st.error(f"Itens sem comentário obrigatório: {', '.join(sorted(set(problemas)))}")
            st.stop()

        registro = {
            "bloco": bloco_id,
            "nome": nome.strip(),
            "email": email.strip(),
            "cpf": cpf.strip(),
            "concordancia_instr_delphi": "sim",
            "consentimento": "sim",
            "timestamp": datetime.now().isoformat(timespec="seconds"),
        }

        out_path = salvar_respostas(registro, respostas)

        try:
            _dest = backup_para_repo_privado(out_path, bloco_id)
            st.success("Submissão salva e backup registrado.")
        except Exception as e:
            st.warning("Submissão salva localmente, mas o backup no repositório privado falhou.")
            st.text(str(e))

if __name__ == "__main__":
    main()