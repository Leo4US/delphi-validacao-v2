cat << 'EOF' > README.md
# Sistema de Validação Delphi
## Projeto: Trabalho Saudável e Seguro na Pesca Artesanal

---

## 1. Finalidade do Sistema

Este sistema foi desenvolvido para operacionalizar a 2ª Rodada Delphi do processo de validação do instrumento de pesquisa do projeto:

Trabalho Saudável e Seguro na Pesca Artesanal

O sistema permite:

- Aplicação estruturada do questionário
- Registro padronizado das avaliações
- Validação automática de regras metodológicas
- Armazenamento rastreável das submissões
- Backup automático em repositório privado

---

## 2. Fundamentação Metodológica

O sistema implementa o Método Delphi estruturado, com:

- Avaliação item a item
- Escala ordinal de relevância (1–5)
- Julgamento binário de aplicabilidade nacional
- Julgamento binário de aceitação do item
- Comentário obrigatório quando houver rejeição ou restrição

Regra metodológica implementada:

Se Aplicabilidade = "Não" OU Aceitação = "Não" → Comentário obrigatório

Essa regra garante:

- Qualidade qualitativa das discordâncias
- Possibilidade de revisão fundamentada do instrumento
- Transparência na análise de dissensos

---

## 3. Arquitetura do Sistema

### 1. Camada de Interface (UI)

Responsável por:

- Renderização via Streamlit
- Controle de fluxo
- Captura de dados
- Controle de sessão

### 2. Camada de Domínio / Dados

Responsável por:

- Validação estrutural dos blocos CSV
- Normalização de colunas
- Consolidação das respostas
- Organização padronizada das colunas
- Geração do artefato final (CSV)

### 3. Camada de Infraestrutura

Responsável por:

- Logging técnico
- Persistência local
- Backup automatizado via Git
- Controle de autenticação segura via token

---

## 4. Estrutura de Diretórios

.
├── base/
│   ├── bloco1_itens.csv
│   ├── bloco2_itens.csv
│   └── ...
│
├── outputs/
│   ├── delphi_bloco1_nome_timestamp.csv
│   └── logs/
│       └── app.log
│
├── app.py
└── README.md

---

## 5. Estrutura do CSV de Blocos

Colunas obrigatórias:

- secao
- codigo
- tematica
- pergunta

Coluna opcional:

- respostas

Se a coluna "texto" existir e "pergunta" não existir, o sistema converte automaticamente.

---

## 6. Estrutura do CSV de Saída

Cada submissão gera um arquivo CSV com:

### Metadados

- bloco
- nome
- email
- cpf
- concordancia_instr_delphi
- consentimento
- timestamp

### Dados por item

- secao
- codigo
- tematica
- pergunta
- respostas
- grau_relevancia
- aplicabilidade_nacional
- aceitacao_item
- comentarios_sugestoes

A ordenação das colunas é padronizada para facilitar:

- Auditoria
- Consolidação estatística posterior
- Reprodutibilidade

---

## 7. Controle de Integridade Metodológica

O sistema impede submissão quando:

- Instruções Delphi não foram aceitas
- Nome ou e-mail não preenchidos
- Consentimento não marcado
- Itens obrigatórios sem comentário

Isso assegura conformidade metodológica da rodada.

---

## 8. Logging e Rastreabilidade

O sistema registra:

- Carregamento de bloco
- Número de itens
- Tentativas de submissão
- Bloqueios por validação
- Caminho do arquivo salvo
- Status do backup Git

Logs são armazenados em:

outputs/logs/app.log

Formato:

YYYY-MM-DD HH:MM:SS | LEVEL | mensagem

Isso permite:

- Auditoria técnica
- Reconstrução de eventos
- Evidência de governança de dados

---

## 9. Backup Automatizado

Após salvar localmente, o sistema:

1. Clona repositório privado
2. Copia arquivo
3. Executa git add
4. Executa git commit
5. Executa git push

Requisitos:

- GITHUB_TOKEN em secrets ou variável de ambiente
- git instalado no ambiente

Finalidade:

- Redundância
- Preservação institucional
- Segurança contra perda local

---

## 10. Segurança e Privacidade

- Token GitHub não é exposto no código
- Uso de st.secrets ou variável de ambiente
- CPF é opcional
- Dados não são publicados automaticamente
- Repositório privado para armazenamento seguro

---

## 11. Conformidade Ética

O sistema:

- Registra concordância metodológica
- Registra consentimento
- Permite rastreabilidade temporal
- Estrutura dados para análise posterior anonimizada

Informações institucionais incluídas:

- CAAE
- Número do parecer

---

## 12. Possibilidades Futuras

O sistema foi estruturado para permitir:

- Múltiplas rodadas Delphi
- Consolidação estatística automática
- Geração de relatórios
- Exportação para Power BI
- Integração com pipeline quantitativo
- Controle de versão de instrumento

---

## 13. Potencial de Publicação

Este sistema pode fundamentar:

- Artigo metodológico sobre validação Delphi digital
- Relato técnico de governança de dados em pesquisa participativa
- Estudo sobre integração entre extensão e infraestrutura digital
- Descrição de tecnologia social aplicada à pesquisa

---

## 14. Autoria Técnica

Sistema desenvolvido como infraestrutura metodológica para validação estruturada do instrumento de pesquisa no âmbito do Programa Trabalho Saudável e Seguro na Pesca Artesanal.

EOF
