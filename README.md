# delphi-validacao

Ferramenta experimental para validação interna de questionários por meio do método Delphi, com marcação estruturada de votos, espaço para comentários qualitativos e consolidação de resultados em formatos tabulares (CSV/XLSX).

Este repositório foi desenvolvido no âmbito do Programa Trabalho Saudável e Seguro na Pesca Artesanal (Fundacentro), com a finalidade de apoiar processos metodológicos internos de revisão e reorganização de instrumentos de pesquisa.

## Objetivo

Oferecer um ambiente controlado para:
- validação interna de questionários extensos;
- aplicação de rodadas Delphi entre pesquisadores e pesquisadoras;
- registro explícito de decisões metodológicas (Manter, Ajustar, Retirar, Coletivo);
- coleta de comentários qualitativos associados a cada item;
- consolidação posterior das respostas para análise, documentação e tomada de decisão.

Este repositório não se destina à coleta de dados junto aos participantes finais da pesquisa, mas exclusivamente à etapa metodológica de validação do instrumento.

## Categorias (legenda Delphi)

- Manter: a pergunta deve permanecer sem alterações;
- Ajustar: sugere-se revisão do enunciado e/ou das alternativas de resposta;
- Retirar: a pergunta deve ser excluída do instrumento;
- Coletivo: a pergunta não será aplicada ao respondente individual, devendo ser considerada para outro nível de coleta.

## Estrutura do repositório

delphi-validacao/
- app/ (aplicações de validação)
- base/ (bases de itens do questionário por bloco/seção)
- docs/ (documentação, governança e termos)
- scripts/ (consolidação e utilitários)
- outputs/ (saídas locais geradas pelo app; não versionar respostas)

## Execução local (para teste interno)

Requisitos:
- Python 3.10+ recomendado
- Dependências em app/requirements.txt

Passos:
1. Instalar dependências:
   pip install -r app/requirements.txt
2. Rodar o app do Bloco 1:
   streamlit run app/app_bloco1.py

O app lê a base em base/bloco1_itens.csv e salva as respostas em outputs/ (um arquivo por submissão).

## Consolidação

Após coletar arquivos em outputs/, execute:
python scripts/consolidar_respostas.py

A consolidação gera:
- outputs/consolidado_respostas.csv
- outputs/resumo_contagens.csv
- outputs/consolidado_respostas.xlsx

## Documentos de referência

- docs/plano_trabalho_validacao_delphi.md
- docs/bloco1_escopo.md
- docs/lgpd_etica_governanca.md

## Licença

Creative Commons Attribution–NonCommercial–NoDerivatives 4.0 International (CC BY-NC-ND 4.0).
