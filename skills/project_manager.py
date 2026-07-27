import os
import json

BASE_PROJECTS_DIR = os.path.join(os.path.expanduser("~"), "Documents", "Jarvis_Projetos")

def get_project_dir(nome_projeto):
    """Retorna o diretório do projeto, substituindo espaços por underscores."""
    nome_limpo = str(nome_projeto).replace(" ", "_")
    return os.path.join(BASE_PROJECTS_DIR, nome_limpo)

def criar_projeto(nome_projeto: str, resumo: str = "Projeto inicializado.") -> str:
    """
    Cria a estrutura de um novo projeto.
    
    Args:
        nome_projeto: O nome desejado para o projeto (ex: 'Braço Robótico').
        resumo: Um breve parágrafo descrevendo o objetivo do projeto.
    """
    try:
        project_dir = get_project_dir(nome_projeto)
        if os.path.exists(project_dir):
            return f"O projeto '{nome_projeto}' já existe."
        
        os.makedirs(project_dir)
        
        readme_path = os.path.join(project_dir, "README.md")
        with open(readme_path, "w", encoding="utf-8") as f:
            f.write(f"# Projeto: {nome_projeto}\n\n## Resumo\n{resumo}\n")
            
        return f"Projeto '{nome_projeto}' criado com sucesso em {project_dir}."
    except Exception as e:
        return f"Erro ao criar o projeto '{nome_projeto}': {str(e)}"

def escrever_documento(nome_projeto: str, nome_arquivo: str, conteudo: str) -> str:
    """
    Escreve ou sobrescreve conteúdo em um arquivo dentro do escopo de um projeto.
    
    Args:
        nome_projeto: O nome do projeto onde o arquivo será salvo.
        nome_arquivo: O nome do arquivo (ex: 'ideias.txt' ou 'planejamento.md').
        conteudo: O texto completo a ser escrito no arquivo.
    """
    try:
        project_dir = get_project_dir(nome_projeto)
        if not os.path.exists(project_dir):
            # Tenta criar se não existir
            os.makedirs(project_dir)
            
        file_path = os.path.join(project_dir, nome_arquivo)
        
        # Garante que não fuja do diretório do projeto (path traversal basic protection)
        if not os.path.abspath(file_path).startswith(os.path.abspath(project_dir)):
             return "Acesso negado: Tentativa de saída do diretório do projeto."

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(conteudo)
            
        return f"Arquivo '{nome_arquivo}' salvo com sucesso no projeto '{nome_projeto}'."
    except Exception as e:
        return f"Erro ao escrever o arquivo '{nome_arquivo}': {str(e)}"

def ler_documento(nome_projeto: str, nome_arquivo: str) -> str:
    """
    Lê todo o conteúdo de um arquivo dentro de um projeto.
    
    Args:
        nome_projeto: Nome do projeto.
        nome_arquivo: Nome do arquivo a ser lido.
    """
    try:
        project_dir = get_project_dir(nome_projeto)
        file_path = os.path.join(project_dir, nome_arquivo)
        
        if not os.path.exists(file_path):
            return f"O arquivo '{nome_arquivo}' não foi encontrado no projeto '{nome_projeto}'."
            
        with open(file_path, "r", encoding="utf-8") as f:
            conteudo = f.read()
            
        return conteudo
    except Exception as e:
        return f"Erro ao ler o arquivo '{nome_arquivo}': {str(e)}"

def listar_projetos(*args, **kwargs) -> str:
    """Lista todos os projetos existentes gerenciados pelo Jarvis."""
    try:
        if not os.path.exists(BASE_PROJECTS_DIR):
             return "Nenhum projeto encontrado."
        
        projetos = [d for d in os.listdir(BASE_PROJECTS_DIR) if os.path.isdir(os.path.join(BASE_PROJECTS_DIR, d))]
        if not projetos:
            return "Nenhum projeto encontrado."
            
        return f"Projetos atuais: {', '.join(projetos)}."
    except Exception as e:
         return f"Erro ao listar os projetos: {str(e)}"
