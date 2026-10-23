# -*- coding: utf-8 -*-
r"""
criar_intake.py — Cria o intake.md padrão na pasta de um caso (protocolo de caso novo).

Uso:
  python criar_intake.py --pasta "<caminho da pasta do caso>" --cliente "Nome" \
       [--adversario "Nome"] [--processo "0000000-00..."] [--area "Consumidor"] \
       [--resumo "..."] [--papel autor|reu]

Gera <pasta>\intake.md no padrão do escritório. Não sobrescreve intake existente
(salvo --force). Campos desconhecidos ficam em branco para preenchimento.

Modelo da skill /intake: frontmatter de vault do Obsidian, `completo: false` até a
ficha ser preenchida pelas fontes, e o bloco "Dados cadastrais" no topo
de cada ficha. Os rótulos `- **Rótulo:** valor` são lidos por outros scripts
(cálculo, minuta simples, cadastro); não renomear sem conferir neles.
"""
import os, re, sys, argparse, datetime

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

TEMPLATE = """---
tipo: intake
cliente: "{cliente}"
processos: [{processos}]
situacao: ativo
completo: false
atualizado: {hoje}
tags: [intake, incompleto]
---
# Intake — {titulo}

> [!warning] Ficha nova: `completo: false`
> Preencher os Dados cadastrais pela inicial, pela procuração e pelos autos, com a fonte de cada
> dado, e só então trocar para `completo: true` (e tirar `incompleto` das tags).
> Ausência de dado aqui NÃO é ausência no caso.

## Dados cadastrais
_Copiar como está no documento (nome sem acento inventado). Fonte no fim de cada linha: (inicial),
(procuração), (CNH), (autos, fls./id/ev.)._
- **Cliente:** {cliente}
- **Papel:** {papel}
- **CPF/CNPJ:**
- **Qualificação completa:**
- **Representado (menor/incapaz):**
- **Parte adversa:** {adversario}
- **Advogado da parte adversa:**
- **Processo:** {processo}
- **Vara:**
- **Comarca:**
- **Classe:**
- **Valor da causa:**
- **Data de distribuição:**
- **Segredo de justiça / gratuidade:**
- **Área:** {area}

## Fatos-âncora
- **Data do evento danoso:**
- **Citação (data e forma):**
- **Audiência:**
- **Data de publicação da sentença:**
- **Data de publicação do acórdão:**
- **Trânsito em julgado:**

## O caso
- **Resumo do caso:** {resumo}

## Decisões e estratégia (do advogado)
- **Dispositivo da sentença:**
- **Dispositivo/Ementa do acórdão:**

## Verbas deferidas em sentença
| Verba | Valor |
|---|---|
| (preencher após sentença) | |

## Verbas pedidas pelo autor / valor da causa
| Verba | Valor |
|---|---|
| | |

## Provas / Documentos
-

## Pendências
- [ ] Preencher os Dados cadastrais com a fonte e marcar `completo: true`

## Observações / Atualizações
- [{hoje}] — Intake criado (protocolo de caso novo).
"""

CNJ_RE = re.compile(r"\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pasta", required=True)
    ap.add_argument("--cliente", required=True)
    ap.add_argument("--adversario", default="")
    ap.add_argument("--processo", default="")
    ap.add_argument("--area", default="")
    ap.add_argument("--resumo", default="")
    ap.add_argument("--papel", default="", choices=["", "autor", "reu", "réu"])
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()

    if not os.path.isdir(a.pasta):
        raise SystemExit("Pasta do caso não existe: " + a.pasta)
    dest = os.path.join(a.pasta, "intake.md")
    if os.path.exists(dest) and not a.force:
        raise SystemExit("intake.md já existe (use --force para sobrescrever): " + dest)

    titulo = a.cliente + (f" x {a.adversario}" if a.adversario else "")
    cnj = CNJ_RE.search(a.processo or "")
    txt = TEMPLATE.format(
        titulo=titulo, cliente=a.cliente, papel=(a.papel or ""),
        adversario=a.adversario, processo=a.processo, area=a.area,
        resumo=a.resumo, hoje=datetime.date.today().isoformat(),
        processos=(f'"{cnj.group(0)}"' if cnj else ""),
    )
    open(dest, "w", encoding="utf-8").write(txt)
    print("OK ->", dest, "(completo: false até preencher os Dados cadastrais)")

if __name__ == "__main__":
    main()
