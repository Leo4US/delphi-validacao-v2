# Base do Questionário (Instrumento)

Esta pasta contém o **instrumento oficial de pesquisa** utilizado no projeto de validação Delphi.

Ela é o **ponto de partida obrigatório** para todo o fluxo do projeto:
- construção do formulário
- validação metodológica
- ajustes
- aplicação futura do questionário

Nenhuma etapa posterior deve ser realizada sem que o instrumento esteja corretamente organizado aqui.

---

## Documento fonte (Word)

O arquivo em formato **.docx** presente nesta pasta corresponde ao **instrumento original de coleta de dados**.

Ele é considerado:
- a **fonte primária**
- a **referência metodológica**
- o registro do questionário em sua forma narrativa original

Todos os arquivos CSV e formulários digitais **derivam diretamente** deste documento.

---

## Arquivos CSV por bloco

Cada bloco/seção do questionário deve ser convertido em um **arquivo CSV independente**, mantendo fidelidade total ao conteúdo do Word.

Esses CSVs são utilizados diretamente pela aplicação de validação Delphi.

---

## Formato oficial dos CSVs (padrão v2.0)

Cada arquivo CSV deve conter as seguintes colunas, nesta ordem:


### Descrição das colunas

| Coluna | Obrigatória | Descrição |
|------|------------|----------|
| `codigo` | sim | Identificador único do item (ex: 1.1, 2.4, 3.12) |
| `secao` | sim | Nome da seção conforme o questionário |
| `tematica` | sim | Área temática padronizada |
| `pergunta` | sim | Enunciado da pergunta (texto principal) |
| `respostas` | não | Alternativas de resposta, separadas por `;` |

- Perguntas abertas devem manter o campo `respostas` vazio.
- Perguntas fechadas devem listar **todas as alternativas** em texto corrido.

---

## Separação conceitual importante

Este padrão **separa explicitamente**:

1. **Pergunta**  
   → conteúdo do instrumento de pesquisa  
2. **Respostas**  
   → alternativas propostas pelo pesquisador  

Essa separação facilita:
- leitura pelos avaliadores
- reorganização futura
- adaptação para diferentes plataformas (Streamlit, Kobo, Google Forms etc.)

---

## Valores padronizados para `tematica`

Utilizar **exatamente** um dos valores abaixo (sem acentos):

- Sociodemografico  
- Organizacao do trabalho  
- Saude e seguranca  
- Meio ambiente  
- Politicas publicas genero e cultura  

A padronização garante consistência na validação, análise e consolidação dos dados.

---

## Observação metodológica

Os arquivos desta pasta representam o **instrumento**, não os dados coletados.

- Não incluir respostas de participantes aqui
- Não versionar dados sensíveis
- Alterações no CSV representam **alterações no instrumento**

---

## Fluxo resumido

Word (instrumento original)
↓
CSV por bloco (base/)
↓
Formulário Delphi (app/)
↓
Decisões e ajustes
↓
Versão final do questionário
