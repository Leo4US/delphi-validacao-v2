import os
import re
import logging
from datetime import datetime
from pathlib import Path
import tempfile
import shutil
import subprocess
import pandas as pd
import streamlit as st

# ============================================================
# CONFIGURAÇÃO (parâmetros fixos do app)
# ============================================================

BASE_DIR = "base"
OUTPUT_DIR = "outputs"

PRIVATE_REPO = "Leo4US/delphi-validacao-respostas"
PRIVATE_BRANCH = "main"

INSTRUCOES_DELPHI = """
### Instruções da Rodada Delphi [versão 2]

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

# ============================================================
# CAMADA: INFRA / LOGGING
# ============================================================

def setup_logging(log_dir: str = OUTPUT_DIR) -> logging.Logger:
    """
    Função: setup_logging

    Objetivo:
        Configurar logging técnico do app (console + arquivo), sem duplicar handlers
        a cada rerun do Streamlit.

    Entradas:
        log_dir (str): diretório base onde o arquivo de log será criado.

    Saídas:
        logging.Logger: logger configurado para uso no app.

    Efeitos colaterais:
        - cria diretório {log_dir}/logs se não existir
        - escreve logs em {log_dir}/logs/app.log
    """
    logger = logging.getLogger("delphi_app")
    logger.setLevel(logging.INFO)

    # Evita duplicar handlers em cada rerun
    if logger.handlers:
        return logger

    logs_path = Path(log_dir) / "logs"
    logs_path.mkdir(parents=True, exist_ok=True)
    file_path = logs_path / "app.log"

    fmt = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")

    # Console (útil em deploy/streamlit cloud)
    sh = logging.StreamHandler()
    sh.setLevel(logging.INFO)
    sh.setFormatter(fmt)
    logger.addHandler(sh)

    # Arquivo (rastreabilidade local)
    fh = logging.FileHandler(file_path, encoding="utf-8")
    fh.setLevel(logging.INFO)
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    logger.info("Logging inicializado")
    return logger

# ============================================================
# CAMADA: DOMÍNIO / DADOS (entrada, validação, persistência)
# ============================================================

def listar_blocos(base_dir: str = BASE_DIR) -> list[str]:
    """
    Função: listar_blocos

    Objetivo:
        Descobrir arquivos de blocos disponíveis no diretório base, seguindo
        o padrão: blocoX_itens.csv

    Entradas:
        base_dir (str): diretório onde os blocos ficam armazenados.

    Saídas:
        list[str]: lista ordenada de nomes de arquivo.
    """
    if not os.path.isdir(base_dir):
        return []
    arquivos = sorted(
        [f for f in os.listdir(base_dir) if re.match(r"bloco\d+_itens\.csv$", f)]
    )
    return arquivos

def carregar_itens(caminho_csv: str) -> pd.DataFrame:
    """
    Função: carregar_itens

    Objetivo:
        Carregar e normalizar o CSV de itens do bloco, garantindo colunas mínimas
        para o formulário.

    Entradas:
        caminho_csv (str): caminho completo do arquivo CSV do bloco.

    Saídas:
        pd.DataFrame: itens normalizados, prontos para renderização.

    Regras/validações:
        - colunas obrigatórias: secao, codigo, tematica, pergunta
        - se existir 'texto' e não existir 'pergunta', cria pergunta=text
        - se não existir 'respostas', cria coluna vazia
    """
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

def salvar_respostas(registro: dict, respostas: list[dict], output_dir: str = OUTPUT_DIR) -> str:
    """
    Função: salvar_respostas

    Objetivo:
        Persistir a submissão localmente em CSV, anexando metadados do registro
        em todas as linhas.

    Entradas:
        registro (dict): metadados do avaliador e da submissão.
        respostas (list[dict]): respostas item-a-item.
        output_dir (str): diretório de saída.

    Saídas:
        str: caminho completo do CSV gerado.
    """
    os.makedirs(output_dir, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_nome = re.sub(r"[^a-zA-Z0-9_-]+", "_", registro["nome"].strip())[:50] or "anon"
    fname = f"delphi_{registro['bloco']}_{safe_nome}_{ts}.csv"
    out_path = os.path.join(output_dir, fname)

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


# ============================================================
# CAMADA: INFRA / BACKUP (GitHub privado via git CLI)
# ============================================================

def backup_para_repo_privado(csv_path: str, bloco_id: str) -> str:
    """
    Função: backup_para_repo_privado

    Objetivo:
        Versionar e armazenar a submissão em repositório privado no GitHub,
        usando clone -> copy -> add -> commit -> push.

    Entradas:
        csv_path (str): caminho do arquivo CSV gerado localmente.
        bloco_id (str): identificador do bloco (ex.: bloco1).

    Saídas:
        str: caminho relativo no repositório (dest_rel).

    Dependências:
        - GITHUB_TOKEN em st.secrets ou variável de ambiente
        - git disponível no ambiente de execução
    """
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


# ============================================================
# CAMADA: UI (Streamlit) – funções de render e controle de fluxo
# ============================================================

def init_session_state() -> None:
    """
    Função: init_session_state

    Objetivo:
        Inicializar flags e variáveis de sessão necessárias ao fluxo.

    Regras:
        - delphi_ok é o flag definitivo da concordância com instruções
    """
    if "delphi_ok" not in st.session_state:
        st.session_state["delphi_ok"] = False


def render_header() -> None:
    """
    Função: render_header

    Objetivo:
        Renderizar cabeçalho institucional do app.
    """
    st.title("VALIDAÇÃO DO QUESTIONÁRIO")
    st.title("1º Rodada Delphi EQN + Especialistas Externos")
    st.write("Projeto de Pesquisa - Trabalho Saudável e Seguro na Pesca Artesanal")
    st.write("Protótipo para fluxo de validação e armazenamento das respostas dos especialistas.")
    st.write("Informações da Plataforma Brasil: 94837225.1.0000.5450 (CAAE) e 8.137.001 (Parecer)")


def gate_instrucoes_delphi() -> None:
    """
    Função: gate_instrucoes_delphi

    Objetivo:
        Impedir acesso ao questionário antes de leitura + concordância
        das instruções Delphi, usando flag persistente em session_state.

    Efeitos colaterais:
        - st.stop() quando não há concordância
        - st.rerun() após concordância para limpar a seção
    """
    if st.session_state["delphi_ok"]:
        return

    instr_box = st.empty()
    with instr_box.expander("Instruções e concordância (leitura obrigatória)", expanded=True):
        st.markdown(INSTRUCOES_DELPHI)

        concordou = st.checkbox(
            "Li, compreendi e concordo com as instruções do Método Delphi.",
            key="delphi_ok_checkbox"
        )

        if concordou:
            st.session_state["delphi_ok"] = True
            instr_box.empty()
            st.rerun()

    st.warning("Para acessar o questionário, é necessário ler e concordar com as instruções acima.")
    st.stop()


def select_and_load_block(logger: logging.Logger) -> tuple[str, str, pd.DataFrame]:
    """
    Função: select_and_load_block

    Objetivo:
        Selecionar o bloco via sidebar e carregar itens do CSV correspondente,
        com tratamento de erro para interromper o fluxo de forma controlada.

    Saídas:
        bloco_arquivo (str): nome do arquivo CSV selecionado
        bloco_id (str): identificador lógico do bloco (sem sufixo)
        itens (pd.DataFrame): itens carregados e normalizados
    """
    blocos = listar_blocos()
    if not blocos:
        st.error("Nenhum arquivo encontrado em base/ no padrão blocoX_itens.csv.")
        logger.error("Nenhum bloco encontrado em BASE_DIR=%s", BASE_DIR)
        st.stop()

    bloco_arquivo = st.sidebar.selectbox("Escolha o bloco", blocos, index=0)
    caminho_csv = os.path.join(BASE_DIR, bloco_arquivo)
    bloco_id = bloco_arquivo.replace("_itens.csv", "")

    try:
        itens = carregar_itens(caminho_csv)
        logger.info("Bloco carregado: %s | itens=%s", bloco_arquivo, len(itens))
    except Exception as e:
        st.error("Erro ao carregar o CSV do bloco.")
        st.text(str(e))
        logger.exception("Falha ao carregar bloco: %s", caminho_csv)
        st.stop()

    return bloco_arquivo, bloco_id, itens


def render_identification(logger: logging.Logger) -> tuple[str, str, str, bool]:
    """
    Função: render_identification

    Objetivo:
        Coletar identificação e consentimento. Usa session_state para
        reaproveitar valores ao trocar blocos.

    Saídas:
        nome (str), email (str), cpf (str), consent (bool)
    """
    with st.expander("Identificação", expanded=True):
        nome = st.text_input("Nome", key="nome")
        email = st.text_input("E-mail", key="email")
        cpf = st.text_input("CPF (opcional)", key="cpf")
        consent = st.checkbox(
            "Li e concordo com o uso dos dados exclusivamente uso metodológico.",
            key="consent"
        )

    logger.info("Identificação (parcial): nome_preenchido=%s email_preenchido=%s consent=%s",
                bool(nome.strip()), bool(email.strip()), bool(consent))

    st.info(
        "Instruções validadas. Você pode preencher este bloco e, se necessário, trocar para outro bloco sem reler as instruções.",
        icon="ℹ️"
    )

    return nome, email, cpf, consent


def render_items_form(itens: pd.DataFrame, bloco_id: str) -> tuple[list[dict], list[str]]:
    """
    Função: render_items_form

    Objetivo:
        Renderizar itens e capturar respostas Delphi para cada item.

    Entradas:
        itens (pd.DataFrame): itens normalizados
        bloco_id (str): identificador do bloco

    Saídas:
        respostas (list[dict]): respostas estruturadas
        problemas (list[str]): códigos com falta de comentário obrigatório
    """
    respostas: list[dict] = []
    problemas: list[str] = []

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

            # Regra: comentário obrigatório quando Aceitação=Não OU Aplicabilidade=Não
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

    return respostas, problemas


def render_submit(
    logger: logging.Logger,
    bloco_id: str,
    nome: str,
    email: str,
    cpf: str,
    consent: bool,
    respostas: list[dict],
    problemas: list[str],
) -> None:
    """
    Função: render_submit

    Objetivo:
        Validar pré-condições de submissão e executar:
        - persistência local
        - backup no repo privado

    Efeitos colaterais:
        - salva CSV no OUTPUT_DIR
        - tenta executar backup Git
        - exibe mensagens de status
    """
    st.divider()
    st.subheader("Enviar respostas")

    if st.button("Salvar submissão"):
        logger.info("Clique em 'Salvar submissão'")

        # Pré-condição: concordância Delphi
        if not st.session_state.get("delphi_ok", False):
            st.error("Você precisa concordar com as instruções do Método Delphi para enviar.")
            logger.warning("Submissão bloqueada: delphi_ok=False")
            st.stop()

        # Pré-condição: identificação e consentimento
        if not consent or not nome.strip() or not email.strip():
            st.error("Identificação (nome e e-mail) e consentimento são obrigatórios.")
            logger.warning("Submissão bloqueada: identificação/consentimento incompletos")
            st.stop()

        # Pré-condição: comentários obrigatórios
        if problemas:
            faltantes = ", ".join(sorted(set(problemas)))
            st.error(f"Itens sem comentário obrigatório: {faltantes}")
            logger.warning("Submissão bloqueada: comentários obrigatórios faltantes: %s", faltantes)
            st.stop()

        # Registro de submissão
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
        logger.info("Submissão salva localmente: %s", out_path)

        # Backup externo
        try:
            dest_rel = backup_para_repo_privado(out_path, bloco_id)
            st.success("Submissão salva e backup registrado.")
            logger.info("Backup OK: %s", dest_rel)
        except Exception as e:
            st.warning("Submissão salva localmente, mas o backup no repositório privado falhou.")
            st.text(str(e))
            logger.exception("Backup falhou: %s", str(e))


# ============================================================
# ORQUESTRAÇÃO (pipeline do app)
# ============================================================

def run_app() -> None:
    """
    Função: run_app

    Objetivo:
        Orquestrar a execução do app, mantendo fluxo previsível e rastreável:
        1) logging
        2) sessão
        3) gate de instruções
        4) seleção e carga do bloco
        5) identificação
        6) formulário de itens
        7) submissão
    """
    st.set_page_config(page_title="Validação Delphi", layout="wide")
    logger = setup_logging(OUTPUT_DIR)

    init_session_state()
    render_header()
    gate_instrucoes_delphi()

    _, bloco_id, itens = select_and_load_block(logger)
    nome, email, cpf, consent = render_identification(logger)

    respostas, problemas = render_items_form(itens, bloco_id)

    logger.info("Itens renderizados: total=%s | problemas=%s", len(respostas), len(set(problemas)))
    render_submit(logger, bloco_id, nome, email, cpf, consent, respostas, problemas)


def main() -> None:
    """
    Função: main

    Objetivo:
        Entry point do script.
    """
    run_app()


if __name__ == "__main__":
    main()
