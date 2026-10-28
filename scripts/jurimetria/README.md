# Jurimetria do TJRJ (DJEN + DataJud)

Mede, num tipo de caso, quanto o TJRJ dá e quanto dá cada juízo, e quantas sentenças de um juiz
o 2º grau reformou. Usa só duas fontes públicas, gratuitas e sem login:

- **DJEN** ([comunicaapi.pje.jus.br](https://comunicaapi.pje.jus.br)): a sentença publicada, com o
  dispositivo, o valor e, quando o sistema publica, a assinatura do juiz.
- **DataJud** ([api-publica.datajud.cnj.jus.br](https://datajud-wiki.cnj.jus.br/api-publica/)): só
  metadados (movimentos da TPU), mas sobre centenas de milhares de processos. A chave pública que
  está no script é a que o CNJ divulga na wiki.

Requer Python 3.10+ e `requests`. A base é um SQLite ao lado do script.

> ⚠️ O número é régua, não previsão. Diga sempre o n e os limites abaixo ao usar um resultado.

## Uso

```bash
python jurimetria.py coletar --de 2025-10-01          # carga inicial do tema (sem datas: continua de onde parou)
python jurimetria.py datajud                          # procedência por vara no DataJud
python jurimetria.py antes  --comarca Capital --segmento vara
python jurimetria.py depois --orgao "2ª Vara Cível da Regional de Bangu"
python jurimetria.py reforma --juiz "NOME COMPLETO DO JUIZ" --de 2025-01-01
python jurimetria.py exportar                         # CSV para Excel
python jurimetria.py rotina                           # o que a tarefa diária roda
```

- **`antes`**, antes da distribuição: o estado contra a comarca e a faixa entre os juízos dela. Na
  Comarca da Capital a vara é sorteada, então serve para precificar o risco do sorteio, não para
  escolher.
- **`depois`**, depois da distribuição: o juízo sorteado contra a comarca e o estado, e por juiz.
- **`reforma`**: a taxa de reforma **do juiz**, e não da vara (ver abaixo).

O tema que vem pronto é **negativação indevida**. Para outro tema, acrescente uma entrada em `TEMAS`:
os termos de busca no DJEN, a regex que confirma o tema, a regex "forte" (o caso é sobre o tema, e
não só o menciona) e os assuntos do DataJud. Depois rode `coletar --de ...`.

## Taxa de reforma por juiz

O histórico de uma vara mistura juízes: o titular de hoje pode ter chegado há um ano. O `reforma`
faz o recorte pelo juiz:

1. busca no DJEN, mês a mês, as sentenças com o nome dele (cache em `relatorios/`; `--refazer` baixa de novo);
2. puxa no DataJud o 1º grau (tipo de sentença: 219 procedente, 220 improcedente, 221 parcial) e o
   2º grau de cada processo, em lotes de 50;
3. pega a **primeira decisão do 2º grau posterior à sentença dele**. O processo pode ter subido
   antes, contra a sentença de outro juiz, e esse acórdão não conta;
4. classifica: **provida** (237, 972), **em parte** (238), **anulada** (11373), **mantida** (239, 242,
   901), e põe fora da conta **não conhecida** (235, 230), **acordo** (466) e **pendente**. Os embargos de
   declaração (198, 200, 871) não entram;
5. gera a tabela por tipo de sentença e por órgão, com intervalo de confiança de Wilson, e o CSV
   processo a processo.

**Como ler:**
- **O número que decide é a reforma no todo.** "Alguma reforma" inclui o provimento em parte, que
  no TJRJ costuma ser ajuste de juros, honorários ou valor, sem mudar quem venceu. Em um teste real, 39%
  das sentenças de um juiz tiveram "alguma reforma", mas só 9% das improcedências dele viraram procedência.
- Só entra o que foi apelado, e quem apela acha que vai ganhar (viés de seleção).
- O DataJud não diz quem apelou. Na improcedência é, em regra, o autor.
- Com n < 10 o relatório marca ⚠️.

## Limites

- O DJEN só tem o que foi publicado (de 2023/2024 em diante). Sentença de processo sem advogado
  constituído pode não sair.
- O eproc publica muitas vezes só o dispositivo, sem assinatura. Nesses casos o juiz fica vazio em
  `coletar`, e a busca por nome no `reforma` não acha a sentença.
- O valor do dano moral é extraído por regra. Confiança "baixa" quer dizer que achou um R$ na
  condenação sem a palavra "moral" por perto. Confira uma amostra antes de usar o número em peça.
- Juizados: o DataJud quase não mostra o movimento de sentença do JEC.
- O IPv6 do DJEN não responde, e o script força IPv4. O DataJud dá 429 e 504 em rajadas, e o script
  espera e insiste até 12 vezes.
- Publicar número de jurimetria com nome de juiz ou de processo em rede social esbarra nas regras de
  publicidade da OAB (Provimento 205/2021).
