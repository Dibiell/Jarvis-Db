import os
import shutil
import glob

def port_agents(src_dir, dest_dir):
    if not os.path.exists(dest_dir):
        os.makedirs(dest_dir)
        
    # Squads are top-level directories in src_dir (excluding .git, .next, etc.)
    squads = [d for d in os.listdir(src_dir) if os.path.isdir(os.path.join(src_dir, d)) and not d.startswith('.')]
    
    count = 0
    for squad in squads:
        agents_dir = os.path.join(src_dir, squad, 'agents')
        if not os.path.exists(agents_dir):
            # Try to find squads that might not have an agents folder but have md files
            continue
            
        agent_files = glob.glob(os.path.join(agents_dir, '*.md'))
        for agent_file in agent_files:
            # Clean filename: squad_agentname.md
            agent_base = os.path.basename(agent_file)
            new_filename = f"{squad.replace('-','_')}_{agent_base.replace('-','_')}"
            
            dest_path = os.path.join(dest_dir, new_filename)
            
            # Read 
            try:
                with open(agent_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                with open(dest_path, 'w', encoding='utf-8') as f:
                    # Add a small header for Jarvis to identify the source
                    f.write(f"# Agent: {new_filename.replace('.md', '').upper()} (from {squad})\n\n")
                    f.write(content)
                
                count += 1
                # print(f"Ported: {new_filename}")
            except Exception as e:
                print(f"Error porting {agent_file}: {e}")
            
    return count

if __name__ == "__main__":
    src = "xquads_tmp"
    dest = "skills"
    print(f"Starting porting from {src} to {dest}...")
    total = port_agents(src, dest)
    print(f"\nTotal agents ported successfully: {total}")
