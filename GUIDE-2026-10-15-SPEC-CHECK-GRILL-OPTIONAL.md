# spec-check і grill — зробити необов'язковими (v2)

**Для кого:** робочий документ для Миколи, для перенесення в окреме репо v2 по одному блоку.
**Дата:** 2026-10-15. **База:** `develop-2.0-init` на `11d32f3`.
**Статус:** не виконано ніде.

---

## Як користуватися

- **Рядки** вказані на `11d32f3`. У твоїй копії вони можуть зсунутись, тому в кожному пункті є **якір**: рядок, за яким місце шукається через grep.
- **Видаляти в одному файлі знизу вгору**: тоді номери рядків вище за текстом лишаються правильними.
- **Блок — одиниця перенесення.** Після кожного блоку система цілісна. Блоки 1 і 2 змінюють код, тест і текст команди **разом**: якщо прибрати verb, а текст команди лишити, команда викличе verb, якого вже немає.
- **Тексти для заміни** подано англійською, бо це байти файлів. Пояснення — українською.
- Біля кожного пункту стоїть `- [ ]`, щоб відмічати зроблене.

## Що робимо і чого не робимо

**Робимо:**
- `/devforge:plan` більше не вимагає свіжого `spec-check.md`;
- `/devforge:breakdown` більше не вимагає, щоб відпрацював grill.

**Лишається як є:**
- обидві команди можна запускати вручну або погодитись, коли модель запропонує;
- seeds повернення назад (`grill-seed.json`, `spec-check-seed.json`) і всі їхні споживачі;
- людське затвердження breakdown;
- підказка `stakes-hint` у `/plan`. Вона знову стає звичайною порадою, як була до плану 85, і тепер це єдине місце, де конвеєр згадує grill.

**Не робимо тут:**
- повне видалення команд. Це частина 2 в кінці документа, і її варто робити лише після заміру гейтів в oak.

## Чому

| | spec-check | grill |
|---|---|---|
| Вартість на фічу (бенчмарк) | ≈ 26 хв (14 LLM + 12 агент) | ≈ 65 хв (31 LLM + 34 агент) |
| Клієнтська інсталяція, один прогін | 15–17 хв LLM + 14–19 хв агент | 52–75 хв LLM + 58–101 хв агент |
| Доказ користі | на дефектній spec відповів CONSISTENT | двічі RE-ENTER-UPSTREAM → два зайві проходи specify→spec-check→plan; чи покращили вони план, ніхто не міряв |

Джерело: `RESEARCH-2026-09-27-V2-COST-DIAGNOSIS.md`, F5 і F10.

**Історія:**
- Обов'язковість spec-check з'явилась у плані 82 (коміт `24256c5`).
- Обов'язковість grill — у плані 85 (коміт `1b6b27a`, текст підказки — `4c08908`).
- Тексти «до» в цьому документі взяті з тих комітів. Подивитись оригінал: `git show <коміт>^:<файл>`.
- План 129 (`129-GRILL-GATE-TO-SIGNAL-RECOMMENDATION-PLAN.md`) пропонує те саме для grill, але його Phase 0 відкрита. Цей документ ширший, бо охоплює й spec-check.

---

## Блок 1 — прибрати гейт spec-check у `/plan`

### 1.1 `src/devforge/lib/plan_helper.py`

- [ ] **Реєстрація verb.** Якір: `# verify-spec-check` усередині `build_parser`.
  - Видалити рядки **2917–2940**: порожній рядок, коментар і весь блок до `sp.set_defaults(func=cmd_verify_spec_check)` включно.
  - Перед `return parser` має лишитися один порожній рядок.
- [ ] **Сам гейт.** Якір: `# Subcommand: verify-spec-check`.
  - Видалити рядки **2533–2738**: від лінії `# ----` над заголовком до `return 0` функції `cmd_verify_spec_check` разом із двома порожніми рядками після неї.
  - Наступне, що лишиться, — `# ---` / `# CLI wiring.`.
  - У діапазоні: `_parse_spec_hash`, `_z3_available`, копія `_Z3_INSTALL_MESSAGE`, `_render_blocked_spec_check`, `cmd_verify_spec_check`. Поза діапазоном жодна з цих функцій не використовується.
- [ ] **Імпорт.** Видалити `import hashlib` (рядок **198**): його використовував тільки гейт. `re` і `Optional` лишаються, бо використовуються в інших місцях.
- [ ] **Docstring модуля.** Якір: `  verify-spec-check --spec <spec-path>`.
  - Видалити рядки **152–183**: порожній рядок перед записом і весь запис до `the one-time install message to the BLOCKED text.`.
  - Перед `Exit codes:` має лишитися один порожній рядок.

### 1.2 `tests/lib/test_plan_helper.py`

- [ ] **Тести гейта.** Якір: `# Tests: verify-spec-check (Plan 82 Phase 5)`.
  - Видалити рядки **4244–4588**.
  - Це класи `ParseSpecHashTests`, `Z3AvailableTests`, `Z3InstallMessageDriftTests`, `VerifySpecCheckTests`, `VerifySpecCheckZ3Tests`.
  - Перед `if __name__ == "__main__":` мають лишитися два порожні рядки.
- [ ] **Фікстура.** Якір: `def _write_real_spec_check_report`. Видалити рядки **217–252** (функція і два порожні рядки після неї). Її викликають лише видалені тести.
- [ ] **Імпорти.** Якір: `# Producer imports for the verify-spec-check tests`. Видалити рядки **110–128**: коментар, чотири імпорти `_spec_check`, коментар та імпорт `Z3_INSTALL_MESSAGE` і порожній рядок.
- [ ] **`import hashlib`** (рядок **25**) видалити: його використовувала тільки фікстура.
- **Бонус:** `test_plan_helper.py` більше не потребує встановленого `z3`.

### 1.3 `src/commands/plan/main.md`

- [ ] **Секція гейта.** Якір: `## PHASE 0a.8: Spec-check gate (mandatory)`. Видалити рядки **152–172**, від заголовка до порожнього рядка перед `## PHASE 0b: Status flip`.
- [ ] **Посилання на 0a.8, гілка «seed не знайдено».** Рядок **150** (кінець 0a.7). Замінити:
  - `proceed normally to Phase 0a.8 with the resolved path`
  - → `proceed normally to Phase 0b with the resolved path`
- [ ] **Посилання на 0a.8, гілка «seed знайдено».** Рядок **146**, кінець абзацу. Замінити:
  - `Proceed to Phase 0a.8 with the resolved path.`
  - → `Proceed to Phase 0b with the resolved path.`
- [ ] **Оглядовий абзац.** Рядок **9**, якір: `and Phase 0a.8 additionally hard-gates`. У реченні про Phase 0 прибрати хвіст:
  - `…has completed before any plan work fires, and Phase 0a.8 additionally hard-gates on a fresh \`/devforge:spec-check\` report for the resolved spec.`
  - → `…has completed before any plan work fires.`
- [ ] **Абзац-передумова.** Рядок **32**, якір: `A fresh \`/devforge:spec-check\` report for the resolved spec is a precondition`. Видалити абзац разом із порожнім рядком після нього.

### Перевірка блоку 1

```bash
git grep -n -e 'verify-spec-check' -e 'verify_spec_check' -e '0a\.8' -- src tests
# лишаються тільки src/CLAUDE.md:93 (це блок 8) і коментарі в breakdown_helper.py (зникнуть у блоці 2)
python3 -m pytest tests/lib/test_plan_helper.py -q
```

---

## Блок 2 — прибрати гейт grill у `/breakdown`

### 2.1 `src/devforge/lib/breakdown_helper.py`

- [ ] **Реєстрація verb.** Якір: `# verify-grill-ran` усередині `build_parser`. Видалити рядки **4066–4098**: від коментаря до `sp.set_defaults(func=cmd_verify_grill_ran)` і порожнього рядка після нього. Наступним має йти `# finalize-handoff`.
- [ ] **Сам гейт.** Якір: `# Subcommand: verify-grill-ran`.
  - Видалити рядки **2675–2870**: від лінії `# ----` над заголовком до `return 0` функції `cmd_verify_grill_ran` і двох порожніх рядків.
  - Наступним лишиться `# --- Phase 4 — task-file parsing helpers`.
  - У діапазоні: `_render_blocked_grill_ran` і `cmd_verify_grill_ran`. Імпорт `_grill._state` у функції лінивий, тож верхніх імпортів чіпати не треба.

### 2.2 `tests/lib/test_breakdown_helper.py`

- [ ] Якір: `# Tests: verify-grill-ran`. Видалити рядки **7748–8120**.
  - Це фікстури `_write_grill_report`, `_write_grill_state_real`, `_write_pre_change_grill_state`, `_write_array_grill_state` і клас `VerifyGrillRanTests`. Поза цим діапазоном фікстури не використовуються.
  - Базовий клас `_CwdIsolationBH` (рядок 793) **лишається**: ним користуються інші тести.

### 2.3 `src/commands/breakdown/main.md`

- [ ] **Секція гейта.** Якір: `## PHASE 0a.6: Grill gate (MANDATORY)`.
  - Видалити рядки **80–102**, від заголовка до порожнього рядка перед `## PHASE 0b: Status flip + gates`.
  - Разом з нею йде абзац `Sub-phase numbers are per-command: the \`0a.6\` label…`: він існував лише для того, щоб цей номер не плутали з 0a.6 у `/plan`.
- [ ] **Два посилання з 0a.5.** Рядки **71** і **72**. В обох замінити:
  - `proceed to Phase 0a.6 with the resolved path`
  - → `proceed to Phase 0b with the resolved path`
- [ ] **Рядок підсумку.** Рядок **628**, якір: `**Grill**: [recommended disposition]`. Замінити на:
  ```
  **Grill**: [not run | [recommended disposition]; [clean — no question was asked | not clean]; [`grill-seed.json` present | no `grill-seed.json`]]
  ```
- [ ] **Пояснення до рядка.** Рядок **642**, якір: `The \`**Grill**:\` line is always present — Phase 0a.6 lets a run reach this point`. Замінити речення до першого `;` на:
  ```
  The `**Grill**:` line is always present and states only what files record. When `<feature_dir>/grill.md` does not exist it reads `not run` — grill is optional, so a breakdown without one is a normal run, not a defect. When the report exists, the line states:
  ```
  Решту абзацу лишити без змін: про disposition, clean, `grill-seed.json` і "Never state what the user picked…".

### 2.4 Відкрите рішення: `adversary_ran()`

- `_grill/_state.py:174` `adversary_ran()` втрачає свого єдиного виклику в робочому коді. Лишаються тільки тести: `tests/lib/_grill/test_state.py` ≈330–375 і `tests/lib/_grill/test_cli_phase1_wiring.py` ≈380–410.
- [ ] **Рекомендую лишити до частини 2.** Якщо grill видалиш повністю, функція піде разом із ним. Якщо видаляти зараз, доведеться переписувати два тести, а швидшим від цього нічого не стане.

### Перевірка блоку 2

```bash
git grep -n -e 'verify-grill-ran' -e 'verify_grill_ran' -e '_render_blocked_grill_ran' -- src tests
# має бути порожньо
git grep -n '0a\.6' -- src/commands/breakdown
# має бути порожньо (0a.6 у /plan — це інша фаза, Spec drift check, її не чіпаємо)
python3 -m pytest tests/lib/test_breakdown_helper.py -q
```

---

## Блок 3 — `stakes-hint` знову звичайна порада

### 3.1 `src/devforge/lib/_plan/_stakes.py`

- [ ] Якір: `/devforge:grill is required before /devforge:breakdown will decompose`. Блок `return (` … `).format(reason_str, plan_path)` (рядки **298–305**) замінити текстом, який був до плану 85 (`git show 4c08908^:src/devforge/lib/_plan/_stakes.py`):
  ```python
      return (
          "**High-stakes plan detected**: {0}.\n"
          "Consider running /devforge:grill for a design-level adversarial review "
          "before /devforge:breakdown decomposes this plan into tasks (optional, not "
          "a gate).\n"
          "\n"
          "/devforge:grill {1}\n"
      ).format(reason_str, plan_path)
  ```

### 3.2 `tests/lib/test_plan_stakes_hint.py`

- [ ] Якір: `def test_hint_names_grill_as_required_not_optional` (рядки **727–755**; два порожні рядки перед `if __name__` лишаються). Цей тест прямо забороняє слова "Consider running" і "optional, not". Замінити його на:
  ```python
      def test_hint_is_advisory_not_required(self):
          """Grill is optional: /devforge:breakdown has no grill entry gate. The
          hint suggests grill for a high-stakes plan and must not claim it is
          required."""
          signals = {"large_blast_radius": True, "file_count": 9}
          text = render_hint(signals, "specs/001-x/plan.md")

          self.assertIn("/devforge:grill", text)
          self.assertIn("/devforge:breakdown", text)
          self.assertIn("optional", text)
          self.assertNotIn("required", text)
  ```
- Два тести на останній рядок (`/devforge:grill specs/001-x/plan.md`) лишаються, вони й далі проходять.

### 3.3 `src/commands/plan/main.md`

- [ ] Рядок **723**, якір: `This hint is ADVISORY and NON-BLOCKING`. Весь абзац замінити (основа — текст до плану 85, `git show 1b6b27a^:src/commands/plan/main.md`):
  ```
  This hint is ADVISORY and NON-BLOCKING: it never blocks the approve flow, never gates `/devforge:breakdown`, and the user is free to ignore it. `/devforge:grill` is optional — the user chooses whether to run it, and this hint is the only place the pipeline suggests it. Like the other PHASE 4 helper calls, this step is best-effort; because `stakes-hint` always exits 0, there is no non-zero exit to handle here.
  ```

### Перевірка блоку 3

```bash
python3 -m pytest tests/lib/test_plan_stakes_hint.py -q
```

---

## Блок 4 — повідомлення про Z3

### 4.1 `src/devforge/lib/_spec_check/_preflight.py`

- [ ] Рядки **61–68**, якір: `Z3_INSTALL_MESSAGE = (`. Повідомлення зараз каже "/devforge:plan requires a fresh spec-check report". Замінити на:
  ```python
  Z3_INSTALL_MESSAGE = (
      "/devforge:spec-check requires the Z3 SMT solver. Install it once with:\n"
      "\n"
      "    pip install z3-solver\n"
      "\n"
      "(optional dependency -- not installed by default, since /devforge:spec-check "
      "is optional.)"
  )
  ```
- До плану 82 тут стояло слово `opt-in`. Я пропоную `optional`, бо після плану 93 spec-check модель може запропонувати сама, тож «opt-in» звучить неточно.
- Копія цього повідомлення в `plan_helper.py` і тест на її синхронність уже зникли в блоці 1.

### 4.2 `tests/lib/_spec_check/test_preflight.py`

- [ ] Якір: `def test_install_message_does_not_call_spec_check_opt_in` (рядки **117–125**). Замінити на:
  ```python
      def test_install_message_says_spec_check_is_optional(self):
          """/devforge:spec-check is optional: /devforge:plan does not require
          it, so the message must not claim that it does."""
          self.assertIn("not installed by default", Z3_INSTALL_MESSAGE)
          self.assertIn("optional", Z3_INSTALL_MESSAGE)
          self.assertNotIn("/devforge:plan requires", Z3_INSTALL_MESSAGE)
  ```

### Перевірка блоку 4

```bash
python3 -m pytest tests/lib/_spec_check/test_preflight.py -q
```

---

## Блок 5 — тексти самих команд spec-check і grill

### 5.1 `src/commands/spec-check/main.md`

- [ ] Рядок **21**, якір: `**Run on the user's say-so, and a fresh report is REQUIRED before \`/devforge:plan\` (D14, as amended).**`. Весь абзац замінити на (речення про high-stakes повернуто з тексту до плану 82):
  ```
  **Optional, run on the user's say-so (D14).** `/devforge:spec-check` runs because the user typed it or agreed to run it when it was offered (like `/devforge:grill`) — no command starts it on its own initiative, no `/devforge:specify` run chains into it, and `/devforge:plan` does not require it. Run it for high-stakes specs — those with many interacting numeric/threshold, state/enum, or conditional-permission acceptance criteria over shared quantities, where a hidden contradiction is most likely and most costly to discover only after `/devforge:plan` has designed against it. Its verdict never gates anything: blocking belongs to the deterministic forcing-functions family, never to a recommendation derived from a stochastic formalization.
  ```
- [ ] Рядок **316**, правило 1, якір: `1. **Run on the user's say-so, never self-initiated — and a fresh report is required before`. Замінити на:
  ```
  1. **Optional, run on the user's say-so, never self-initiated** — `/devforge:spec-check` runs only when the user types it or agrees to an offer to run it (like `/devforge:grill`); no command starts it on its own initiative, no `/devforge:specify` run chains into it, and `/devforge:plan` does not require it. The verdict never gates: verdict-blocking belongs to the deterministic forcing-functions family, never to a recommendation derived from a stochastic formalization.
  ```
- Рядки 307–312 (наступний крок після прогону) лишаються як є: вони вже ведуть до `/devforge:plan`.

### 5.2 `src/commands/grill/main.md`

- [ ] Рядок **9**: замінити `is a standalone, required pipeline stage` → `is a standalone, optional pipeline stage`.
- [ ] Рядок **17**, якір: `**Mandatory to RUN, never binding in its VERDICT.**`. Весь абзац замінити на (основа — текст до плану 85, з урахуванням плану 93):
  ```
  **Optional, run on the user's say-so, never binding in its VERDICT.** `/devforge:grill` runs only when the user types it or agrees to an offer to run it — no command starts it on its own initiative, and `/devforge:breakdown` does not require it. `/devforge:plan` emits a NON-BLOCKING advisory hint when the finished plan looks high-stakes (wide file impact / new data model / new dependency / security-relevant / risk-laden with 4+ risks); that hint neither runs `/devforge:grill` nor gates anything. Run it for high-stakes plans (new architecture / new dependency / new external integration / new data model / security-relevant) and skip it for mechanical ones. Skipping `/devforge:grill` leaves the `/devforge:plan → /devforge:breakdown` chain unchanged.
  ```
- [ ] Рядок **19**, якір: `**What being mandatory did NOT change.**`. Замінити на (інваріанти ті самі, без згадки про обов'язковість):
  ```
  **The disposition stays the user's.** The USER owns every non-clean verdict at the PHASE-7 human gate. All FOUR dispositions survive, KILL included. The cross-pick and re-entry arms are untouched. `/devforge:grill` never modifies `plan.md` or `spec.md`.
  ```

### Перевірка блоку 5

```bash
git grep -n -i -e 'required before' -e 'mandatory to run' -e 'being mandatory' -e 'required pipeline stage' -- src/commands/spec-check src/commands/grill
# має бути порожньо
```

---

## Блок 6 — `/fix`

У ланцюжках необов'язкові кроки беру в квадратні дужки, як було в `src/CLAUDE.md` до плану 82: `[/devforge:spec-check]`, `[/devforge:grill]`.

### 6.1 `src/commands/fix/main.md`

- [ ] Рядок **131**, якір: `tell the user there is no feature to remediate (run`. Ланцюжок:
  - `/devforge:specify` → `/devforge:spec-check` → `/devforge:plan` → `/devforge:grill` → `/devforge:breakdown` → …
  - → `/devforge:specify` → `[/devforge:spec-check]` → `/devforge:plan` → `[/devforge:grill]` → `/devforge:breakdown` → …
- [ ] Рядок **241**, якір: `so it belongs in a fresh`. Та сама заміна ланцюжка.
- [ ] Рядок **251**, якір: `` `/devforge:spec-check` sits inside that recommended cycle because ``. Абзац пояснює, що обидві команди потрібні, бо `/plan` і `/breakdown` блокують. Замінити на:
  ```
  `/devforge:spec-check` and `/devforge:grill` are optional steps of that cycle — spec-check before `/devforge:plan`, grill before `/devforge:breakdown`. Name them as options the user may run; never run them from here — `/devforge:fix` ends the turn and the user starts the cycle.
  ```
- [ ] Рядок **295**, якір: `that the recommended next cycle is`. Та сама заміна ланцюжка.

### 6.2 `src/commands/fix/references/triage.md`

- [ ] Рядок **54**, рядок таблиці **FEATURE**. Та сама заміна ланцюжка.

---

## Блок 7 — ланцюжки в інших командах

- [ ] `src/commands/plan/main.md:27`: `→ /devforge:spec-check → /devforge:plan → /devforge:grill →` → `→ [/devforge:spec-check] → /devforge:plan → [/devforge:grill] →`.
- [ ] `src/commands/breakdown/main.md:27` і `src/commands/implement/main.md:45`: тут spec-check у ланцюжку **взагалі немає** (це давня розбіжність). Привести до того самого вигляду:
  ```
  /devforge:research OR /devforge:discover → /devforge:specify → [/devforge:spec-check] → /devforge:plan → [/devforge:grill] → /devforge:breakdown → /devforge:implement → …
  ```
- **Помітив, але це поза цим документом:** у тих самих двох рядках стоїть `/devforge:research (optional)`, хоча `/devforge:specify` без intake-handoff не стартує. Якщо виправлятимеш ланцюжки, варто прибрати й це `(optional)`.

---

## Блок 8 — `src/CLAUDE.md` (потрапляє в кожну інсталяцію)

- [ ] **:44** — ланцюжок: `→ /devforge:spec-check →` → `→ [/devforge:spec-check] →`, `→ /devforge:grill →` → `→ [/devforge:grill] →`.
- [ ] **:47** — речення `That includes the two required adversarial checks and \`/devforge:fix\`: when \`/devforge:plan\` or \`/devforge:breakdown\` blocks on a missing \`spec-check.md\` / \`grill.md\`, offer to run the named command now and end the turn;` замінити на:
  ```
  That includes the two optional adversarial checks `/devforge:spec-check` and `/devforge:grill`, and `/devforge:fix`: offer the command and end the turn;
  ```
  Решту речення (`on agreement run that one command, …`) лишити.
- [ ] **:51** — весь абзац замінити на:
  ```
  `[/devforge:spec-check]` is **optional** — a spec-tier consistency check run between `/devforge:specify` and `/devforge:plan` that formalizes the acceptance criteria and proves whether they contradict each other; run it for high-stakes specs before planning. It is never self-initiated: the user types it or agrees to an offer to run it, and `/devforge:plan` does not require it. The human keeps every disposition it raises. A clean result is accepted without a question; anything else asks. It is a consistency prover, not a mind-reader — it checks whether the ACs contradict EACH OTHER, not whether they are what you meant.
  ```
- [ ] **:58** — замінити на:
  ```
  - `/devforge:spec-check` — **Optional, run on the user's say-so** spec-tier SMT consistency check of the acceptance criteria → `specs/[feature]/spec-check.md` (run between `/devforge:specify` and `/devforge:plan` for high-stakes specs; a consistency prover, not a mind-reader — checks whether the ACs contradict each other, not whether they are what you meant); WIP-commits its report + any re-entry seed as it writes them (folds into `/devforge:finalize`'s squash)
  ```
- [ ] **:60** — замінити на:
  ```
  - `/devforge:grill` — **Optional, run on the user's say-so** design-time adversarial review of the completed `plan.md` → `specs/[feature]/grill.md` (run between `/devforge:plan` and `/devforge:breakdown` for high-stakes plans; `/devforge:plan`'s stakes hint suggests it; the human keeps every call); WIP-commits its report + any re-entry seed as it writes them (folds into `/devforge:finalize`'s squash)
  ```
- [ ] **:90** — замінити на:
  ```
  **Optional**: spec-tier consistency proof of the acceptance criteria (Z3 over a 2-pass-quorum formalization) → `specs/[feature]/spec-check.md` with CONSISTENT / REVISE-SPEC / DISMISS; a matching REVISE-SPEC pick also writes `spec-check-seed.json` for `/devforge:specify`. Run it for high-stakes specs before `/devforge:plan`.
  ```
- [ ] **:93** — видалити перше речення `**Requires a fresh \`/devforge:spec-check\` report … once the user agrees).**`, лишити `**Requires approval before \`/devforge:breakdown\`.**`.
- [ ] **:99** — замінити на:
  ```
  **Optional**: adversarial review of the finished `plan.md` (two devils-advocate passes + architect-excluded refutation) → `specs/[feature]/grill.md` with a 4-way disposition the USER owns; a matching REVISE-PLAN / RE-ENTER-UPSTREAM pick also writes `grill-seed.json`. Run it for high-stakes plans before `/devforge:breakdown`.
  ```
- [ ] **:160** і **:162** — видалити обидва рядки з `### Hard Gates (block until approved)`: про свіжий spec-check перед plan і про grill перед breakdown.

---

## Блок 9 — документація репо

- [ ] **`README.md:49–50`** — ланцюжок у дужках: `/devforge:specify → [/devforge:spec-check]` і `→ /devforge:plan → [/devforge:grill] → /devforge:breakdown`.
- [ ] **`README.md:59`** — два речення від `` `/devforge:spec-check` is required before `` до `…you still own every call it raises.` (про grill, включно) замінити на:
  ```
  `[/devforge:spec-check]` and `[/devforge:grill]` are optional — Claude may offer them for a high-stakes spec or plan and runs one only once you agree, one agreement per command; nothing requires them, and you own every call they raise.
  ```
  Речення про `/devforge:fix` лишити.
- [ ] **`README.md:75`**:
  - `*(required before \`/devforge:plan\`; offered and run on your agreement)*` → `*(optional; offered and run on your agreement)*`;
  - речення `` `/devforge:plan` blocks until this report exists and still matches the spec — presence and freshness only, never the verdict. `` видалити.
- [ ] **`README.md:77`**:
  - `*(required before \`/devforge:breakdown\`; …)*` → `*(optional; offered and run on your agreement)*`;
  - два останні речення (`` `/devforge:breakdown` blocks until … `` і `What is mandatory is that the grill RAN…`) замінити на `` `/devforge:plan` suggests it when the finished plan looks high-stakes. ``
- [ ] **`CLAUDE.md:46`** (кореневий, для мейнтейнера) — `The USER owns the verdict at the \`/breakdown\` gate: the RUN is required before \`/breakdown\`, the verdict never binding.` → `Optional: runs on the user's say-so, \`/devforge:plan\`'s stakes hint suggests it for high-stakes plans, and its verdict is never binding.`
- [ ] **`DEVELOPMENT-STATUS.md`**:
  - **:17**: `**Run on the user's agreement, and REQUIRED before \`/devforge:plan\`**` → `**Optional, run on the user's agreement**`. Речення `` `/devforge:plan` PHASE 0a.8 (`plan_helper verify-spec-check`) fails closed until … (plan 62 D14 amended in place 2026-08-19). `` видалити. `both commands fail closed with the same message` → `/devforge:spec-check fails closed with that message`.
  - **:18**: фрагмент `PHASE 0a.8 is its first fail-closed mechanical preflight — … and it runs BEFORE the Draft→Approved status flip;` видалити.
  - **:42**: `, and \`/devforge:breakdown\` requires that it ran` і `, and \`/devforge:plan\` requires a fresh report from it` видалити. Номери планів лишити.
- [ ] **`CHANGELOG.md`** — у `## [Unreleased]` → `### Changed`:
  ```
  - feat(plan,breakdown,spec-check,grill): `/devforge:spec-check` and `/devforge:grill` are optional again — `/devforge:plan` no longer requires a fresh spec-check report and `/devforge:breakdown` no longer requires a grill run. Both commands stay available, run on the user's say-so, and keep their re-entry seeds; `/devforge:plan`'s high-stakes hint suggests grill. Reverses the run-mandatory gates of plans 82 and 85.
  ```
  Старі записи CHANGELOG (рядки 68 і 72) не чіпати: це історія.

---

## Фінальна перевірка (після всіх блоків)

```bash
# 1. Жодної згадки про обов'язковість
git grep -n -i -e 'verify-spec-check' -e 'verify-grill-ran' -e 'required before `/devforge:plan`' \
  -e 'required before `/devforge:breakdown`' -e 'refuses to decompose' -e 'required adversarial' \
  -e 'Mandatory to RUN' -e 'grill is required' -e 'plan requires a fresh' -- src README.md
# очікування: порожньо

# 2. Тести, яких торкались
python3 -m pytest tests/lib/test_plan_helper.py tests/lib/test_breakdown_helper.py \
  tests/lib/test_plan_stakes_hint.py tests/lib/_spec_check/test_preflight.py tests/lib/_grill -q

# 3. Гейти мейнтейнера (змінювались тексти команд)
python3 -m pytest tests/lib/test_agent_reachability.py tests/lib/test_memory_lane.py -q
```

**Живий прогін на тестовій інсталяції:**
- [ ] `/devforge:plan` на spec без `spec-check.md` іде далі без блокування.
- [ ] `/devforge:breakdown` на plan без `grill.md` іде далі, а в підсумку стоїть `**Grill**: not run`.
- [ ] На high-stakes plan `/devforge:plan` показує підказку "Consider running /devforge:grill … (optional, not a gate)".
- [ ] `/devforge:spec-check` і `/devforge:grill`, запущені вручну, працюють як раніше, включно із seeds повернення назад.

---

## Частина 2 (пізніше): повне видалення — тільки після заміру гейтів у oak

Робити, лише якщо гейти oak (spec-gate, plan-gate, breakdown-gate) покажуть, що окупаються, або якщо вирішиш жити без LLM-гейтів між артефактами.

**Перед видаленням:** скласти таблицю того, що перевіряють grill і spec-check, але чого немає в чеклистах oak:
- у grill: категорії атак `devils-advocate`, `src/commands/grill/references/design-attack-checklist.md`;
- у spec-check: зіставлення суб'єкта кожного AC з кодом і пошук протиріч між AC.

Цінне перенести в чеклисти.

**Що видаляється:**
- **Команди:** `src/commands/grill/` і `src/commands/spec-check/` разом із `references/`.
- **Код:** `grill_helper` і `spec_check_helper` разом із лаунчерами; `src/devforge/lib/_grill/` (≈ 4.0 тис. рядків) і `src/devforge/lib/_spec_check/` (≈ 4.6 тис. рядків); тести `tests/lib/_grill/` і `tests/lib/_spec_check/`.
- **Агенти:** `src/agents/devils-advocate.md` і `src/agents/spec-formalizer.md`. Інакше впаде `verify-agent-reachability`.
- **Емітер:** `_PROMOTED` у `scripts/emitters/claude.py`.
- **Seeds:** `SEED_SOURCES` у `src/devforge/lib/_shared/seed_schema.py` (прибрати `grill` і `spec-check`); Phase 0.6 у research і discover; Phase 0.5 у specify; у plan Phase 0a.7 стане мертвою, бо `grill` REVISE-PLAN — єдине джерело з `target_stage == "plan"`.
- **Підказка:** `_plan/_stakes.py`, verb `stakes-hint`, `tests/lib/test_plan_stakes_hint.py` і абзац про підказку в plan Phase 4. Вони існують лише для того, щоб радити grill.
- **Breakdown:** рядок `**Grill**:` у підсумку.
- **Моделі:** `src/commands/configure/main.md:448` і `references/q11-tiers.md` (grill стоїть на рівні `think`).
- **Документація:** `src/CLAUDE.md`, README, кореневий `CLAUDE.md` (рядок роутера `/grill`), `DEVELOPMENT-STATUS.md`.
- **Залежність Z3** зникає повністю.

**Що лишається:** спільний рушій спростування в `src/devforge/lib/_shared/`. Ним користується `/devforge:audit`.
