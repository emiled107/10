import streamlit as st
import subprocess
import json
import altair as alt
import pandas as pd
import os

# On retrouve les mêmes 10 questions (pour info ou vérif).
QUESTIONS = [
    "Quel est le délai dans lequel le prestataire doit mettre à disposition des données de consommation et de facturation, selon les dispositions du contrat ?",
    "Quels sont les éléments nécessaires pour que le Délégataire réclame les autorisations et arrêtés dont il a eu connaissance de l'existence, mais dont il n'a pas déjà copie ?",
    "Quelle est la reference du marché pour le Marché public pour la fourniture et l’acheminement en Gaz naturel et services associés ?",
    "Quels sont les principaux documents à prendre en compte lors de la définition des besoins et de la passation d'un marché public pour un membre du groupement ?",
    "Quels sont les formalités à respecter pour informer les sous-traitants des obligations de confidentialité et/ou des mesures de sécurité dans le cadre du marché ?",
    "Quelles sont les conditions selon lesquelles le Délégataire peut se porter candidat aux consultations lancées par l’Autorité Délégante ?",
    "Quelle est la périodicité de la révision des prix dans le cadre d'un marché où les prix sont révisés à chaque anniversaire de la date de notification du marché ?",
]

def main():
    st.set_page_config(page_title="Dashboard Comparaison RAG", layout="wide")
    st.title("Comparaison Réponses SANS RAG vs. AVEC RAG")

    # Section méthodologique
    st.sidebar.title("Méthodologie")
    st.sidebar.markdown("""
    **RAG (Retrieval-Augmented Generation)** combine un mécanisme de récupération d'informations pertinentes avec un modèle de langage génératif.
    
    - **Sans RAG** : Le modèle génère une réponse uniquement à partir de ses connaissances internes.
    - **Avec RAG** : Le modèle utilise des informations récupérées (chunks) pour enrichir ses réponses.
    
    Ce tableau de bord compare ces deux approches sur un ensemble fixe de questions.
    """)

    if st.button("Lancer l'évaluation sur les questions"):
        with st.spinner("Exécution des scripts ou chargement des résultats..."):
            no_rag_results = []
            rag_results = []

            # Vérifier si les scripts existent
            no_rag_script_exists = os.path.exists('no_rag_test.py')
            rag_script_exists = os.path.exists('rag_test.py')

            # Vérifier si les fichiers JSON existent
            no_rag_json_exists = os.path.exists('no_rag_results.json')
            rag_json_exists = os.path.exists('rag_results.json')

            # Traitement pour no_rag
            if no_rag_script_exists:
                no_rag_proc = subprocess.run(
                    ["python", "no_rag_test.py"],
                    capture_output=True, text=True
                )
                if no_rag_proc.returncode == 0:
                    no_rag_results = json.loads(no_rag_proc.stdout)
                else:
                    st.error(f"Erreur dans no_rag_test.py : {no_rag_proc.stderr}")
            elif no_rag_json_exists:
                with open('no_rag_results.json', 'r') as f:
                    no_rag_results = json.load(f)
            else:
                st.error("Ni le script no_rag_test.py ni le fichier no_rag_results.json n'ont été trouvés.")

            # Traitement pour rag
            if rag_script_exists:
                rag_proc = subprocess.run(
                    ["python", "rag_test.py"],
                    capture_output=True, text=True
                )
                if rag_proc.returncode == 0:
                    rag_results = json.loads(rag_proc.stdout)
                else:
                    st.error(f"Erreur dans rag_test.py : {rag_proc.stderr}")
            elif rag_json_exists:
                with open('rag_results.json', 'r') as f:
                    rag_results = json.load(f)
            else:
                st.error("Ni le script rag_test.py ni le fichier rag_results.json n'ont été trouvés.")

        # 4) Construire un dict question -> (réponse_sans_rag, réponse_avec_rag, rag_chunks)
        result_map = {}
        for item in no_rag_results:
            q = item["question"]
            ans = item["answer"]
            result_map[q] = {
                "no_rag_answer": ans,
                "rag_answer": None,
                "rag_chunks": []
            }

        for item in rag_results:
            q = item["question"]
            ans = item["answer"]
            cks = item.get("chunks", [])
            if q not in result_map:
                result_map[q] = {
                    "no_rag_answer": None,
                    "rag_answer": ans,
                    "rag_chunks": cks
                }
            else:
                result_map[q]["rag_answer"] = ans
                result_map[q]["rag_chunks"] = cks

        # 5) Affichage comparatif avec évaluation qualitative
        st.subheader("Comparaison des réponses")
        for q in QUESTIONS:
            pair = result_map.get(q)
            if not pair:
                continue
            st.subheader(f"Question : {q}")
            
            col1, col2 = st.columns(2)

            with col1:
                st.write("### Sans RAG")
                st.write(pair["no_rag_answer"])
                note_no_rag = st.slider(f"Notez cette réponse sans RAG (0-5) pour '{q}'", 0, 5, 3)

            with col2:
                st.write("### Avec RAG")
                st.write(pair["rag_answer"])
                note_rag = st.slider(f"Notez cette réponse avec RAG (0-5) pour '{q}'", 0, 5, 4)
                
                # On affiche les chunks retrouvés
                st.write("Chunks retrouvés :")
                for i, chunk_text in enumerate(pair["rag_chunks"]):
                    st.markdown(f"**Chunk {i+1}:**")
                    st.write(chunk_text)

            st.markdown("---")

        # 6) Calcul d'une métrique simple (par exemple la longueur de la réponse)
        question_labels = []
        len_no_rag = []
        len_rag = []

        for q in QUESTIONS:
            if q in result_map:
                ans_no_rag = result_map[q].get("no_rag_answer") or ""
                ans_rag = result_map[q].get("rag_answer") or ""
                question_labels.append(q[:30] + "...")  # tronque pour affichage
                len_no_rag.append(len(ans_no_rag))
                len_rag.append(len(ans_rag))

        # Préparer les données pour Altair
        data = pd.DataFrame({
            "Question": question_labels,
            "Longueur Sans RAG": len_no_rag,
            "Longueur Avec RAG": len_rag
        }).melt("Question", var_name="Type", value_name="Longueur")

        # Graphique interactif avec Altair
        st.subheader("Comparaison sur la longueur des réponses")
        chart = alt.Chart(data).mark_bar().encode(
            x=alt.X("Question:N", sort=None, axis=alt.Axis(labelAngle=-45)),
            y="Longueur:Q",
            color="Type:N",
            tooltip=["Question", "Type", "Longueur"]
        ).properties(width=800, height=400)

        st.altair_chart(chart, use_container_width=True)

        st.success("Évaluation terminée !")


if __name__ == "__main__":
    main()
