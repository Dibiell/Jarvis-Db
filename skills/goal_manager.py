import json
import os
import datetime

class GoalManager:
    def __init__(self, goals_path="goals.json"):
        self.goals_path = goals_path
        self.goals = self.load_goals()

    def load_goals(self):
        if not os.path.exists(self.goals_path):
            return {"daily_goals": [], "okrs": [], "progress": {}}
        try:
            with open(self.goals_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {"daily_goals": [], "okrs": [], "progress": {}}

    def save_goals(self):
        try:
            with open(self.goals_path, "w", encoding="utf-8") as f:
                json.dump(self.goals, f, ensure_ascii=False, indent=4)
            return "Metas salvas com sucesso."
        except Exception as e:
            return f"Erro ao salvar metas: {e}"

    def adicionar_meta_diaria(self, meta):
        date_str = datetime.datetime.now().strftime("%Y-%m-%d")
        self.goals["daily_goals"].append({"date": date_str, "goal": meta, "completed": False})
        return self.save_goals()

    def completar_meta(self, index):
        try:
            self.goals["daily_goals"][index]["completed"] = True
            return self.save_goals()
        except:
            return "Índice de meta inválido."

    def obter_relatorio_manhã(self):
        daily = [g["goal"] for g in self.goals["daily_goals"] if not g["completed"]]
        if not daily:
            return "Senhor, você não tem metas pendentes para hoje. Vamos definir algumas?"
        return "Bom dia, senhor. Aqui estão suas metas pendentes: \n" + "\n".join([f"- {g}" for g in daily])

    def obter_relatorio_noite(self):
        pendentes = [g["goal"] for g in self.goals["daily_goals"] if not g["completed"]]
        concluidas = [g["goal"] for g in self.goals["daily_goals"] if g["completed"]]
        resumo = f"Senhor, fim do dia. \nConcluídas: {len(concluidas)} \nPendentes: {len(pendentes)}"
        if pendentes:
            resumo += "\nAmanhã focaremos em: " + ", ".join(pendentes[:3])
        return resumo

goal_manager = GoalManager()
