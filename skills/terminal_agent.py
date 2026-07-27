import subprocess
import os

class SystemController:
    """
    JARVIS SKILL: OS Controller (Terminal Agent)
    Engine: PowerShell/CMD orchestration.
    Capability: Execution of system commands and process control.
    """
    def execute_command(self, command: str) -> str:
        """
        Executes a shell command and returns the output or error.
        """
        print(f"[Terminal] Executando comando: {command}")
        try:
            # Usa PowerShell por padrão no Windows para maior poder
            result = subprocess.run(
                ["powershell", "-Command", command],
                capture_output=True,
                text=True,
                timeout=30,
                encoding='cp850' # Encoding comum do terminal Windows
            )
            
            output = result.stdout.strip()
            error = result.stderr.strip()
            
            if result.returncode == 0:
                return output if output else "Comando executado com sucesso (sem saída)."
            else:
                return f"Erro ({result.returncode}): {error}"
                
        except subprocess.TimeoutExpired:
            return "Erro: O comando excedeu o tempo limite de 30 segundos."
        except Exception as e:
            return f"Erro inesperado: {str(e)}"

# Interface para o JARVIS
def executar_terminal(comando: str) -> str:
    controller = SystemController()
    return controller.execute_command(comando)
