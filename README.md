# GW2Controller

Mapeador de **controle Xbox** para teclado e mouse, pensado para **Guild Wars 2** (e outros jogos sem suporte nativo a controle). Inclui camadas de modificador, short/long press, radial no stick direito e overlay transparente com ícones dos botões sobre a barra de skills.

Repositório: [paulpolidoro/gw2controller](https://github.com/paulpolidoro/gw2controller)

## Requisitos

- Windows 10/11
- Python 3.11 ou superior
- Controle Xbox / XInput (Xbox 360, One, Series ou clone compatível)
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

## Como usar

1. Conecte o controle Xbox.
2. Abra o jogo em **janela** ou **borderless**.
3. No app, ajuste o mapeamento na aba **Botões**.
4. **Press** segura a função enquanto o botão está apertado; a coluna **Release** dispara ao soltar.
5. **Short / Long**: soltar rápido dispara o curto; segurar dispara o longo.
6. **Modificadora** (ex.: LB/RB) abre uma aba de overrides — o que não for alterado mantém a função base.
7. **F8** edita o overlay (arraste os ícones; scroll muda o tamanho; botão direito remove).
8. **F9** mostra ou oculta o overlay.

Fechar a janela só minimiza para a bandeja. Use **Arquivo → Sair** para encerrar.

## Overlay

Na aba **Overlay**:

- Escolha a tela (importante com dois monitores)
- Tema escuro/claro só dos overlays (ícones e radial)
- Alpha do radial (transparência)

## Perfis

Os perfis ficam em `profiles/*.json`. Dá para salvar cópias pela interface (**Salvar como**).

## Observações

- Alguns jogos com anti-cheat podem ignorar teclas injetadas.
- Respeite as regras do Guild Wars 2 quanto a macros e automação.
