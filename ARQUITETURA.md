# Arquitetura — Xadrez_AI_Final

Este documento define a arquitetura **final, congelada e não-negociável** do motor de xadrez `Xadrez_AI_Final`.

Ele existe para eliminar ambiguidades, prevenir regressões arquiteturais e garantir evolução controlada e consistente.

---

## 1. Princípios Arquiteturais Fixos

### 1.1 Indexação das Casas

* Todas as casas do tabuleiro são representadas por um inteiro de `0` a `63`.
* Sistema linear (flat indexing).

```
square = rank * 8 + file
file   = square % 8
rank   = square // 8
```

**Convenções:**

* `A1 = 0`, `H8 = 63`
* `rank`: 0–7 (rank 0 = lado das brancas)
* `file`: 0–7 (file 0 = coluna 'a')

---

### 1.2 Representação Interna

Toda a engine é baseada em bitboards, com ataques deslizantes implementados via **Magic Bitboards**.


A estrutura base:

```
bitboards[12]    # 6 tipos × 2 cores
occupancy[2]     # Branco / Preto
occupancy_all    # OR dos dois
```

**Decisões arquiteturais:**

* Não existem arrays de peças no core.
* Não existem raios ou offsets em runtime.
* Todo ataque deslizante é resolvido via *Magic Bitboards* (lookup O(1)).

* Não existem arrays de peças no core (mailbox, piece-lists, etc.).
* Toda a representação do tabuleiro é feita exclusivamente via bitboards.
* Offsets e raios não existem em runtime (somente em pré-processamento).
* Todo ataque deslizante é resolvido via Magic Bitboards (lookup O(1)).
* Nenhuma lógica de movimento depende de iteração de casas.
* Nada fora de bitboards é permitido no core.

---

### 1.3 Neutralidade de Cor

O motor é totalmente neutro:

* Nenhuma função assume perspectiva das brancas.
* Toda lógica usa apenas `side_to_move`.
* O código deve funcionar simetricamente para qualquer cor.

---

### 1.4 Hash: Zobrist

Utilizamos **Zobrist hashing incremental**, nunca recalculado do zero.

Usado para:

* Repetição tripla
* Histórico de posições
* Base para transposition table (fase futura)

O hash é atualizado somente via XOR nas transições de estado.

---

### 1.5 FEN (Input / Output)

FEN é **exclusivamente I/O**.

Responsabilidades do módulo:

* Parser de FEN para estado interno
* Exportação de estado interno para FEN
* Validação rigorosa da entrada

O FEN **nunca entra no core lógico**.

Core só trabalha com bitboards e estado já validado.

---

### 1.6 Tabelas de Ataque

Todas as tabelas são **pré-computadas no carregamento**:

* Knight attacks
* King attacks
* Pawn attacks
* Sliding attacks via Magic Bitboards

Não existe cálculo pesado de ataque em runtime.

---

## 2. Estrutura de Diretórios

```
Xadrez_AI_Final/
├── ARCHITECTURE.md
├── README.md
│
├── utils/
│   ├── enums.py
│   └── constants.py
│
├── core/
│   ├── hash/
│   │   └── zobrist.py
│   │
│   ├── board/
│   │   └── board.py
│   │
│   ├── moves/
│   │   ├── magic_bitboards.py
│   │   ├── attack_tables.py
│   │   ├── move_encoding.py
│   │   └── move_generator.py
│   │
│   ├── rules/
│   │   └── rules.py
│   │
│   └── io/
│       └── fen.py
│
└── tests/
    ├── test_enums.py
    ├── test_constants.py
    ├── test_magic_bitboards.py
    ├── test_attack_tables.py
    ├── test_zobrist.py
    ├── test_board.py
    ├── test_fen.py
    ├── test_move_encoding.py
    ├── test_move_generator.py
    └── test_rules.py
```

---

## 3. Ordem Obrigatória de Implementação

| Fase | Arquivo                       | Responsabilidade                  |
| ---- | ----------------------------- | --------------------------------- |
| 1    | utils/enums.py                | Enums fundamentais                |
| 2    | utils/constants.py            | Constantes e máscaras estruturais |
| 3    | core/hash/zobrist.py          | Hashing incremental               |
| 4    | core/moves/magic_bitboards.py | Magic Bitboards                   |
| 5    | core/moves/attack_tables.py   | Ataques (usando Magic)            |
| 6    | core/board/board.py           | Representação do estado           |
| 7    | core/io/fen.py                | Entrada/saída FEN                 |
| 8    | core/moves/move_encoding.py   | Estrutura congelada de Move       |
| 9    | core/moves/move_generator.py  | Gerador de movimentos             |
| 10   | core/rules/rules.py           | Regras do jogo                    |
| 11   | Otimizações                   | Profiling + performance           |

---

## 4. Definições Congeladas

### 4.1 Estrutura de Move

Definida em `move_encoding.py`.

Após estabilização: **não pode mais ser alterada**.

Campos mínimos:

* origem
* destino
* flags (promoção, roque, en passant, captura, etc.)

Isso garante:

* Compatibilidade futura
* Estabilidade do histórico
* Base sólida para busca e TT

---

### 4.2 Board

Responsabilidades estritas:

* Manter Magic Bitboards
* Manter occupancy e occupancy_all
* Atualizar hash Zobrist incremental
* Aplicar e desfazer movimentos
* Expor API minimalista

❌ Sem regras
❌ Sem validações de legalidade
❌ Sem lógica de xeque

O board é puramente mecânico.

---

## 5. Regras de Desenvolvimento

### 5.1 Gatekeeping

Nenhum passo avança sem:

* Validação conceitual
* Testes
* Aprovação

Sem testes passando = sem avanço.

---

### 5.2 TDD Estrutural

Todos os módulos devem:

* Ter testes próprios
* Validar invariantes bitwise
* Evitar regressões silenciosas

---

## 6. Fora de Escopo

Ainda não entram:

* Algoritmos de busca
* Avaliação
* UCI
* GUI

Isso é uma fase posterior ao core completo.

---

## 7. Fase de Performance

Como Magic Bitboards já entram desde o início, a fase de performance fica:

1. Profiling real (py-spy, perf, etc.)
2. Otimização de hot paths
3. Uso de instruções específicas (POPCNT, PEXT)
4. Preparação para Transposition Tables

Nada de substituição de raios — isso já nasce eliminado.
