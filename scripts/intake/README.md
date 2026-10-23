# Intake: a ficha viva do caso

Os dois scripts que a skill [`/intake`](../../skills/intake/SKILL.md) usa. Só biblioteca padrão do
Python 3.10+.

| Script | O que faz |
|---|---|
| `criar_intake.py` | cria o `intake.md` na pasta do caso: frontmatter de vault do Obsidian, `completo: false`, Dados cadastrais, Fatos-âncora, Verbas, Pendências, Observações. Não sobrescreve ficha existente. |
| `checar_intake.py` | só leitura: diz se a ficha pode ser lida como a ficha do caso (🔴 casca, 🟡 incompleta ou velha, ✅ ok) e lista as fichas das outras matérias do mesmo cliente. |

```bash
python criar_intake.py --pasta "Cliente/Caso" --cliente "Cliente" --adversario "Banco X" \
       --processo "0000000-00.0000.0.00.0000" --area Consumidor --papel autor --resumo "uma linha"
python checar_intake.py "Cliente/Caso" --raiz "<acervo>"
python checar_intake.py "Nome do Cliente" --raiz "<acervo>"
python checar_intake.py --cnj 0000000-00.0000.0.00.0000 --raiz "<acervo>" --json
```

A raiz do acervo também pode vir da variável `INTAKE_ROOT` (padrão: a pasta atual). O acervo
esperado é `<raiz>/<Cliente>/[<Caso>/]intake.md`. Pastas da raiz que começam com dígito e ponto
(`00. Inbox`, `02. Modelos`) ou com `_` não são clientes.

## Por que o checador existe

Uma ficha vazia que **parece** documentação é pior do que ficha nenhuma: ela tem frontmatter e data
recente, aparece no painel do vault, e quem a lê não estranha a ausência de dados. Num caso real, uma
ficha de 764 bytes criada por uma rotina automática foi lida assim, e a peça saiu com o argumento
fraco. Por isso toda ficha nasce com `completo: false` e só passa a `completo: true` quando os Dados
cadastrais estão preenchidos pela fonte. Até lá, o checador manda reconstruir pelos autos antes de
minutar.
