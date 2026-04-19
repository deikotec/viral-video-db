import sys
import os

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)

from mcp_server.server import db_search_refs, call_gemini_for_script, save_idea_to_db

def test():
    print("Testing db_search_refs...")
    refs = db_search_refs(empresa="Fisioterapia Madrid", nicho="salud", num_refs=3)
    print("Refs found:", len(refs))
    
    print("Testing call_gemini_for_script...")
    idea = call_gemini_for_script("Fisioterapia Madrid", "Atraer pacientes", "Instagram Reels", refs)
    print("Idea keys:", idea.keys() if isinstance(idea, dict) else idea)
    
    print("Testing save_idea_to_db...")
    idea_id = save_idea_to_db("Fisioterapia Madrid", "Atraer pacientes", "Instagram Reels", refs, idea)
    print("Saved idea ID:", idea_id)

if __name__ == "__main__":
    test()
