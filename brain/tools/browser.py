"""
JARVIS BRAIN - Ferramentas de Browser
Controla o navegador via Playwright, lendo o DOM real da página (não
adivinhando posição por screenshot). Sessão fica viva entre chamadas
(não abre/fecha navegador a cada ação) pra manter o estado da página.
"""

_playwright = None
_browser = None
_page = None

# Padrão: usa o mouse real do PC pra clicar (visível, você vê acontecendo).
# Só desliga quando o usuário pedir explicitamente naquele comando.
_usar_mouse_real = True


def definir_modo_mouse(usar_mouse: bool):
    global _usar_mouse_real
    _usar_mouse_real = usar_mouse


def _garantir_pagina():
    """Garante que existe um navegador+página abertos, abrindo se precisar."""
    global _playwright, _browser, _page

    if _page is not None:
        try:
            _page.title()  # só pra checar se a página ainda está viva
            return _page
        except Exception:
            pass  # página morreu, recria abaixo

    from playwright.sync_api import sync_playwright

    _playwright = sync_playwright().start()
    _browser = _playwright.chromium.launch(headless=False)  # visível de propósito
    _page = _browser.new_page()
    return _page


def navegar(url: str) -> dict:
    try:
        pagina = _garantir_pagina()
        if not url.startswith("http"):
            url = "https://" + url
        pagina.goto(url, wait_until="domcontentloaded", timeout=15000)
        return {"sucesso": True, "titulo": pagina.title(), "url": pagina.url}
    except Exception as e:
        return {"sucesso": False, "mensagem": f"Falha ao navegar pra '{url}': {e}"}


def ler_elementos_visiveis() -> dict:
    """
    'Snapshot' da página: pega os elementos interativos visíveis (botões,
    campos de texto, links) com um texto identificador cada. É isso que
    o agente usa pra decidir ONDE clicar/digitar - por elemento, não por
    coordenada.
    """
    try:
        pagina = _garantir_pagina()
        elementos = pagina.eval_on_selector_all(
            "button, a, input, textarea, [role=button], [role=textbox]",
            """els => els
                .filter(e => e.offsetParent !== null)
                .slice(0, 40)
                .map((e, i) => ({
                    indice: i,
                    tag: e.tagName.toLowerCase(),
                    texto: (e.innerText || e.placeholder || e.value || e.ariaLabel || '').slice(0, 60).trim()
                }))
                .filter(e => e.texto.length > 0)
            """
        )
        return {"sucesso": True, "elementos": elementos}
    except Exception as e:
        return {"sucesso": False, "mensagem": f"Falha ao ler a página: {e}"}


def _centro_na_tela(pagina, elemento):
    """
    Converte a posição do elemento (relativa à página) pra coordenada
    real de tela, somando a posição da janela do navegador + a moldura
    dela (barra de endereço etc). É o que permite mover o mouse de
    verdade até o elemento, em vez de só clicar no DOM.
    Retorna (x, y) em coordenada de tela, ou None se não der pra calcular.
    """
    caixa = elemento.bounding_box()
    if not caixa:
        return None

    janela = pagina.evaluate("""() => ({
        x: window.screenX,
        y: window.screenY,
        chromeH: window.outerHeight - window.innerHeight,
        chromeW: window.outerWidth - window.innerWidth
    })""")

    centro_x = janela["x"] + janela["chromeW"] / 2 + caixa["x"] + caixa["width"] / 2
    centro_y = janela["y"] + janela["chromeH"] + caixa["y"] + caixa["height"] / 2
    return (centro_x, centro_y)


def clicar_elemento(texto_do_elemento: str) -> dict:
    """Clica no primeiro elemento visível cujo texto bate com o pedido.
    Se o modo mouse real estiver ligado, move o cursor de verdade até lá
    e clica (visível na tela) - senão, clique sintético direto no DOM."""
    try:
        pagina = _garantir_pagina()
        elemento = pagina.get_by_text(texto_do_elemento, exact=False).first
        elemento.scroll_into_view_if_needed(timeout=5000)

        if _usar_mouse_real:
            coordenada = _centro_na_tela(pagina, elemento)
            if coordenada:
                import pyautogui
                pyautogui.moveTo(coordenada[0], coordenada[1], duration=0.3)
                pyautogui.click()
                return {"sucesso": True, "mensagem": f"Cliquei (mouse real) em '{texto_do_elemento}'."}
            # não conseguiu calcular a coordenada de tela - cai pro clique sintético abaixo

        try:
            elemento.click(timeout=5000)
        except Exception:
            elemento.click(timeout=5000, force=True)
        return {"sucesso": True, "mensagem": f"Cliquei em '{texto_do_elemento}'."}
    except Exception as e:
        return {"sucesso": False, "mensagem": f"Não achei/cliquei em '{texto_do_elemento}': {e}"}


def digitar_no_elemento(texto_do_elemento: str, texto_a_digitar: str) -> dict:
    """
    Digita texto num campo, tentando várias formas de achar o elemento
    (nem todo campo tem placeholder de verdade - às vezes é aria-label,
    às vezes é uma textarea/textbox genérica). Usa os localizadores
    prontos do Playwright em vez de um só método fixo.
    """
    pagina = _garantir_pagina()
    estrategias = [
        lambda: pagina.get_by_placeholder(texto_do_elemento, exact=False).first,
        lambda: pagina.get_by_label(texto_do_elemento, exact=False).first,
        lambda: pagina.get_by_role("textbox", name=texto_do_elemento).first,
        lambda: pagina.locator("textarea").first,  # último recurso: primeira textarea visível
    ]

    ultimo_erro = None
    for estrategia in estrategias:
        try:
            campo = estrategia()
            campo.fill(texto_a_digitar, timeout=4000)
            return {"sucesso": True, "mensagem": f"Texto inserido em '{texto_do_elemento}'."}
        except Exception as e:
            ultimo_erro = e
            continue

    return {"sucesso": False, "mensagem": f"Falha ao digitar em '{texto_do_elemento}' (tentei várias formas): {ultimo_erro}"}
