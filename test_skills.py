import sys
import os

from skills.browser_agent import pesquisar_na_web
from skills.project_manager import criar_projeto, escrever_documento, ler_documento, listar_projetos

def main():
    print("Testando pesquisar_na_web...")
    res = pesquisar_na_web("quando lançou o playstation 5")
    print(res)
    print("-" * 40)
    
    print("Testando criar_projeto...")
    res2 = criar_projeto("Test Project JARVIS", "A test project")
    print(res2)
    print("-" * 40)
    
    print("Testando escrever_documento...")
    res3 = escrever_documento("Test Project JARVIS", "test.txt", "Hello world this is a test.")
    print(res3)
    print("-" * 40)
    
    print("Testando ler_documento...")
    res4 = ler_documento("Test Project JARVIS", "test.txt")
    print(res4)
    print("-" * 40)
    
    print("Testando listar_projetos...")
    res5 = listar_projetos()
    print(res5)
    print("-" * 40)

if __name__ == "__main__":
    main()
