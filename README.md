# GW2Controller

Transforma um **controle Xbox** em teclado e mouse para **Guild Wars 2**. Ideal se você quer jogar com controle sem abrir mão das skills e atalhos do teclado.

Inclui:

- Funções **ao apertar**, **ao soltar** e **curto / longo**
- **Modificadoras** (ex.: LB muda o que A/B/X fazem)
- **Menu radial** no analógico direito
- **Sobreposição** transparente com o nome dos botões sobre as skills
- Camadas automáticas via **MumbleLink** (mapa, chat, montaria)

Repositório: [paulpolidoro/gw2controller](https://github.com/paulpolidoro/gw2controller)

## Requisitos

- Windows 10/11
- Python 3.11 ou superior
- Controle Xbox / XInput
- Guild Wars 2 em **janela** ou **sem bordas** (a sobreposição não aparece em tela cheia exclusiva)

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

## Contexto do jogo (MumbleLink)

O app lê o sinal do GW2 e troca funções sozinho:

| Situação | O que acontece |
|----------|----------------|
| Mapa do mundo aberto (M) | Usa a aba **Mapa aberto** |
| Chat / campo de texto ativo | Usa a aba **Chat** |
| Personagem em montaria | Usa a aba **Montaria** |
| Jogo sem foco | Não envia teclas (evita digitar fora do jogo) |

Ordem de prioridade: **modificadora** → **mapa** → **chat** → **montaria** → **função normal**.  
Nas abas de contexto, deixe em branco para manter a função normal do botão.

## Como usar

1. Conecte o controle e abra o GW2 (janela ou sem bordas).
2. Na aba **Botões**, defina o que cada botão faz.
3. Se quiser, configure **Mapa aberto**, **Chat** e **Montaria**.
4. Na aba **Sobreposição**, marque mostrar, escolha a tela e pressione **F8** para posicionar os nomes sobre as skills.
5. **F9** mostra ou oculta a sobreposição.

Fechar a janela minimiza para a bandeja. Use **Arquivo → Sair** para encerrar de verdade.

## Perfis

Os perfis ficam em `profiles/*.json`. Use **Salvar** ou **Salvar como…** na barra superior.

## Observações

- Respeite as regras do Guild Wars 2 quanto a macros e automação.
- Alguns anti-cheats podem ignorar teclas injetadas.
