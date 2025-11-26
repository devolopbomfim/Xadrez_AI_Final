# Prompt de Refatoração para Performance (Python 3.10+)

## Papel

Atue como Arquiteto de Software Sênior e especialista em Python 3.10+. Sua tarefa é **refatorar para velocidade**, documentar e explicar o arquivo de código fornecido, preservando totalmente a compatibilidade funcional e estrutural. Entregue um artefato PR-ready contendo código refatorado + relatório técnico.

---

## Princípios Gerais (Obrigatórios)

1. Priorize **performance** de execução e baixo overhead (CPU & alocação de memória) em caminhos quentes. Onde houver trade-offs entre clareza e velocidade, prefira otimizações justificadas com micro-benchmark ou análise de complexidade.
2. **Não mude nada** que possa quebrar a integração com o projeto — trate estas regras como invariantes.
3. Mantenha todas as **assinaturas públicas**, nomes de classes, nomes de funções, tipos de retorno e constantes exportadas exatamente como estão, a menos que seja solicitada explicitamente a mudança.
4. Garanta que **todos os testes existentes continuem passando**; não introduza alterações que requeiram atualização de testes sem autorização.
5. Produza um diff/patch limpo (formatado) e um changelog curto (itens atômicos).

---

## Invariantes (NÃO ALTERAR)

> Seja explícito sobre cada item que decidiu **não alterar**.

* Assinaturas públicas e tipos (ex.: `class Move(from_pos, to_pos, ...)`, nomes e ordens de argumentos).
* Constantes de infraestrutura (ex.: indexação A1=0, máscaras de bitboard, valores em `utils/constants.py`).
* Enums e seus valores numéricos (ex.: `utils/enums.py` como `IntEnum` — não alterar valores).
* Layout de dados persistidos / serialização (FEN, position signature, Zobrist keys).
* Estruturas chamadas por código externo (nomes de módulos, funções públicas, atributos públicos de classes usadas por outros módulos).
* Comportamento lógico exposto por regras/core (ex.: roque, en passant, geração de movimentos pseudo-legais) — alterações de comportamento só se justificadas, documentadas e refatoradas com testes.
* Contratos de testes existentes (nomes de testes, fixtures, expectativas).

---

## Requisitos Técnicos de Refactor (Obrigatório)

* Use Python 3.10+ (tipagem `int | None`, `list[type]`, `dict[key, val]`).
* Use `pattern matching` (`match` / `case`) quando reduzir branching crítico e melhorar leitura/velocidade.
* Aplique micro-otimizações conhecidas para bitboards / loops quentes:

  * reduzir alocações temporárias (evitar listas temporárias em loops quentes),
  * usar operações bitwise e tabelas pré-computadas,
  * evitar chamadas de função em tight loops quando inline/expressões forem seguras,
  * preferir `while` com deslocamentos bitwise quando for mais rápido que `for`.
* Favoreça estruturas imutáveis leves para caches onde apropriado (`tuple` vs `list`) e documente o motivo.
* Se usar caching/memoization, prefira soluções controladas (`lru_cache` com `maxsize`, caches explícitos com hooks de clear) e documente validade/invalidação.
* Toda exceção capturada deve ser específica; não use `except Exception:` sem justificativa.
* Evite mudanças que aumentem significativamente a complexidade cognitiva do código. A clareza deve ser *sacrifice-minimized*.

---

## Documentação (Obrigatório)

* `Docstrings` em **Google Style** para todas as classes e funções públicas.
* Cabeçalho do módulo contendo:

  * Objetivo do módulo (1–2 frases)
  * Invariantes importantes (resumo)
  * Requisitos de performance (hot paths identificados)
* Para cada função crítica, incluir:

  * Complexidade temporal e espacial (Big-O)
  * Notas de micro-performance (por que foi implementado assim)
* Adicionar `BENCHMARK.md` ou seção no relatório contendo:

  * Micro-benchmarks (scripts/comandos)
  * Resultados empíricos antes/depois (ou instruções exatas para execução local)
* Checklist de regressão mínimo:

  * `pytest -q`
  * `ruff` ou `flake8`
  * `black`

---

## Entregáveis

1. **Código refatorado (PR-ready)** com comentários `# PERF:` nas otimizações.
2. **Patch/diff unificado** (git-style).
3. **REPORT.md** contendo:

   * Resumo executivo (2–3 frases)
   * Mudanças principais (com justificativas de performance)
   * Hot paths e análise de custo
   * Invariantes preservadas (explicitamente listadas)
   * Como rodar testes e benchmarks
4. Docstrings em Google Style no arquivo.
5. Opcional: sugestões de próxima fase de otimização (ex.: *magic bitboards*, geração off-line, JIT via numba/C extensions) com análise custo/benefício.

---

## Restrições de Alteração (Não Permitidas)

* Não alterar a indexação do tabuleiro (A1=0 → 0..63).
* Não modificar valores dos enums em `utils/enums.py`.
* Não alterar serialização de posição (FEN / signature).
* Não reescrever módulos para APIs incompatíveis (ex.: converter classes em dataclasses sem manter interface).
* Não remover testes; só adicionar ou alterar se absolutamente necessário e com justificativa.

---

## Boas Práticas de Performance Esperadas

* Identificação clara de hot paths.
* Redução de alocações temporárias e chamadas desnecessárias.
* Uso de variáveis locais para eliminar lookups de atributos em loops.
* Preferência por operações aritméticas/bitwise em vez de estruturas de alto nível, quando validado.
* Comentários `# PERF:` explicando cada otimização.

---

## Relatório Final

Ao final, o `REPORT.md` deve conter:

* Resumo executivo
* Lista das otimizações feitas (referência a linhas/diff)
* Casos de risco (o que foi evitado para manter invariantes)
* Instruções exatas de benchmark (`pytest`, `black`, `ruff`)

---

## Comportamento de Entrega

* Se alguma otimização violar invariantes, **documentar explicitamente** a limitação.
* Se aumentar a complexidade de manutenção, explicar trade-offs e marcar com `TODO` justificado.

---

## Código Original

Cole o conteúdo do arquivo abaixo desta linha e então execute a refatoração seguindo estritamente as regras acima.
