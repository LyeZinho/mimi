# Ferramentas (Tools) do Mimi

Este documento descreve as ferramentas registradas em `agent/tools/registry.py` e mostra exemplos de como usá-las programaticamente.

## Ferramentas disponíveis

- `search` — Busca via DuckDuckGo. Entrada: texto da consulta. Retorna título e resumo dos resultados.
- `weather` — Previsão do tempo (usa Open-Meteo). Entrada: nome da cidade.
- `time` — Retorna data/hora atual. Entrada: `"utc"` para hora UTC, vazio para hora local.
- `calculator` — Avalia expressões aritméticas simples (safe eval via AST). Entrada: expressão (ex: `"(2+3)*4"`).
- `notes` — Gerencia notas simples em memória. Comandos:
 - `http` — Busca conteúdo via HTTP(S) (GET). Útil para capturar páginas públicas ou APIs simples.
 - `github` — Obtém metadados de repositórios públicos no GitHub (stars, forks, issues, última release).
 - `crypto` — Consulta preços via CoinGecko (ex: `btc` -> `bitcoin`).
 - `minecraft` — Verifica status de servidores Minecraft (via mcsrvstat API).
  - `add: texto` — adiciona nota
  - `list` — lista notas
  - `get:idx` — obtém nota pelo índice
  - `clear` — remove todas as notas

## Registro das ferramentas

As ferramentas são instanciadas e registradas automaticamente em `agent/tools/registry.py` no método `_register_defaults()`.

Exemplo simplificado de como obter e executar uma ferramenta:

```python
from agent.tools.registry import ToolRegistry

registry = ToolRegistry()
tool = registry.get_tool("calculator")
if tool is not None:
    result = await tool.execute("(10 - 3) * 2")
    print("Resultado:", result)
```

## Integração com `ActionRouter`

O `ActionRouter` (em `agent/output/actions.py`) tem um método de conveniência `execute_tool(tool_name, tool_input, registry)` que invoca a ferramenta registrada e retorna o resultado como string. Exemplo:

```python
from agent.tools.registry import ToolRegistry
from agent.output.actions import ActionRouter

registry = ToolRegistry()
router = ActionRouter()

# Executar ferramenta 'time' em UTC
res = await router.execute_tool("time", "utc", registry)
print(res)

# Executar calculadora
res2 = await router.execute_tool("calculator", "3**2 + 1", registry)
print(res2)
```

## Boas práticas

- Use `calculator` apenas para expressões numéricas simples — o avaliador é seguro, mas não é um interpretador completo.
- `notes` armazena notas em memória durante a execução; para persistência adapte para gravar em arquivo ou DB.
- `search` e `weather` dependem de bibliotecas externas/serviços; verifique conectividade ao usá-las.

## Testes

Os testes automatizados cobrem os comportamentos básicos dessas ferramentas. Para rodar a suíte:

```bash
source /e/git/Mimi/.venv/Scripts/activate  # Git Bash
pip install -r /e/git/Mimi/requirements.txt
python -m pytest -q
```
