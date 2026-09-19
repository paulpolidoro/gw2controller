# GW2Controller

Mapeador de **controle Xbox** para teclado e mouse, pensado para **Guild Wars 2**. Inclui camadas de modificador, short/long press, release, radial no stick direito, overlay transparente e integração com **MumbleLink**.

Repositório: [paulpolidoro/gw2controller](https://github.com/paulpolidoro/gw2controller)

## Requisitos

- Windows 10/11
- Python 3.11 ou superior
- Controle Xbox / XInput
- Guild Wars 2 em **janela** ou **borderless** (o overlay não aparece em tela cheia exclusiva)

## Instalação

```powershell
git clone git@github.com:paulpolidoro/gw2controller.git
cd gw2controller
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Como abrir

Duplo clique em `run.bat`, ou:

```powershell
python run.py
```

## MumbleLink (contexto do jogo)

O app lê a shared memory `MumbleLink` do GW2:

| Fonte | Efeito |
|-------|--------|
| Bit 1 — Map open | Overrides da aba **Map open** |
| Bit 4 — Game focus | Sem foco no jogo → não envia input |
| Bit 6 — Textbox focus | Overrides da aba **Chat** |
| `mountIndex ≠ 0` | Overrides da aba **Mounted** |

Prioridade: **modificador** → **Map open** → **Chat** → **Mounted** → **base**.  
Nas abas de contexto, botão vazio = mantém a função base.

## Como usar

1. Conecte o controle e abra o GW2 (janela/borderless).
2. Ajuste o mapeamento na aba **Botões**.
3. Configure overrides de mapa e montaria nas abas **Map open** e **Mounted**.
4. **F8** edita o overlay; **F9** mostra/oculta.

Fechar a janela minimiza para a bandeja. **Arquivo → Sair** encerra.

## Perfis

Perfis em `profiles/*.json` (**Salvar** / **Salvar como**).

## Observações

- Respeite as regras do Guild Wars 2 quanto a macros e automação.
- Alguns anti-cheats podem ignorar teclas injetadas.
