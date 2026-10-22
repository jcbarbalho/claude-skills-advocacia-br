---
name: markitdown
description: Converte qualquer documento (PDF, DOCX, XLSX, PPTX, HTML, CSV, EPUB, ZIP, imagem, áudio) em Markdown legível, preservando tabelas e estrutura. Use quando precisar LER o conteúdo de um arquivo do acervo — peça, contrato, planilha, cópia de autos, anexo de e-mail — em vez de escrever código de extração para cada formato.
---

# markitdown — ler qualquer documento como Markdown

Ferramenta da Microsoft (https://github.com/microsoft/markitdown). Resolve o problema de
sempre: para ler um `.docx` era `python-docx`, para `.xlsx` era `openpyxl`, para `.pptx` era
`python-pptx`, cada um com um script diferente. Aqui é um comando só.

## Como chamar

```bash
markitdown "caminho/arquivo.docx" -o "saida.md"
```

⚠️ **Sempre usar `-o` e depois ler o arquivo.** Jogar a saída direto no terminal corrompe os
acentos (o console do Windows não está em UTF-8). Com `-o`, o arquivo sai em UTF-8 correto.

Para um arquivo grande, gravar no scratchpad da sessão e ler de lá em pedaços.

## O que ele cobre

| Formato | Resultado |
|---|---|
| `.docx` | texto com negrito, títulos e **tabelas em Markdown** |
| `.xlsx` / `.xls` / `.csv` | cada aba vira uma tabela Markdown com cabeçalho |
| `.pptx` | um bloco por slide, com notas do apresentador |
| `.pdf` | texto corrido (via pdfminer) |
| `.html`, `.epub`, `.json`, `.xml`, `.zip` | texto estruturado |
| imagem | metadados EXIF (OCR só com endpoint externo configurado) |
| áudio | transcrição (precisa de serviço de fala configurado) |

## Quando NÃO usar

- **PDF escaneado.** O markitdown não faz OCR local. Para isso continua valendo o
  `piece_gen/digestao_noturna.py`, que detecta a falta de camada de texto e chama o Tesseract.
- **PDF de autos com marcação de páginas.** A digestão noturna grava `===== PÁG n =====`, que é o
  que permite citar folha. O markitdown entrega texto corrido, sem paginação.
- **Extrair estilos de parágrafo** (conferir se a peça está no padrão do escritório). Isso é o
  `piece_gen/revisar_peca.py`; o markitdown descarta os nomes de estilo.

Em resumo: **markitdown para LER depressa; os scripts do escritório para OCR, paginação e
conferência de formatação.**

## Onde está instalado

Instalado com `uv` num ambiente isolado em Python 3.13, **fora do venv do escritório**:

```bash
uv tool install --python 3.13 "markitdown[all]"
```

O executável fica em `~/.local/bin/markitdown` (no Windows, `%USERPROFILE%\.local\bin\markitdown.exe`).

⚠️ **Por que isolado:** o markitdown 0.1.x depende do `magika`, que exige Python `<3.14`. No 3.14
o pip só resolve a versão **0.0.2**, de 2024, que quase não converte nada. O venv do escritório
foi recriado em 3.12 em 19/10/2026, mas continua valendo manter o
markitdown fora dele: assim um upgrade de Python no venv não o derruba sem aviso.

## Para atualizar

```bash
uv tool upgrade markitdown
```
