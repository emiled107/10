import streamlit as st
from streamlit.components.v1 import html
import json
import altair as alt
import pandas as pd

QUESTIONS = [
    "Quel est le délai dans lequel le prestataire doit mettre à disposition des données de consommation et de facturation, selon les dispositions du contrat ?",
    "Quels sont les éléments nécessaires pour que le Délégataire réclame les autorisations et arrêtés dont il a eu connaissance de l'existence, mais dont il n'a pas déjà copie ?",
    "Quelle est la reference du marché pour le Marché public pour la fourniture et l'acheminement en Gaz naturel et services associés ?",
    "Quels sont les principaux documents à prendre en compte lors de la définition des besoins et de la passation d'un marché public pour un membre du groupement ?",
    "Quels sont les formalités à respecter pour informer les sous-traitants des obligations de confidentialité et/ou des mesures de sécurité dans le cadre du marché ?",
    "Quelles sont les conditions selon lesquelles le Délégataire peut se porter candidat aux consultations lancées par l'Autorité Délégante ?",
    "Quelle est la périodicité de la révision des prix dans le cadre d'un marché où les prix sont révisés à chaque anniversaire de la date de notification du marché ?",
]

def calculate_f1(scores, threshold=3):
    true_positives = sum(1 for score in scores if score >= threshold)
    false_negatives = sum(1 for score in scores if score < threshold)
    total = len(scores)
    
    precision = true_positives / total if total > 0 else 0
    recall = true_positives / (true_positives + false_negatives) if (true_positives + false_negatives) > 0 else 0
    
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
    return f1

def load_data():
    with open('no_rag_results.json', 'r') as f:
        no_rag_results = json.load(f)
    with open('rag_results.json', 'r') as f:
        rag_results = json.load(f)
    
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
    
    return result_map

def main():
    st.set_page_config(page_title="Dashboard Comparaison RAG", layout="wide")
    st.title("Comparaison Réponses SANS RAG vs. AVEC RAG")

    if 'no_rag_scores' not in st.session_state:
        st.session_state.no_rag_scores = [3] * len(QUESTIONS)
    if 'rag_scores' not in st.session_state:
        st.session_state.rag_scores = [4] * len(QUESTIONS)

    st.sidebar.title("Méthodologie")
    st.sidebar.markdown("""
    **RAG (Retrieval-Augmented Generation)** combine un mécanisme de récupération d'informations pertinentes avec un modèle de langage génératif.
    
    - **Sans RAG** : Le modèle génère une réponse uniquement à partir de ses connaissances internes.
    - **Avec RAG** : Le modèle utilise des informations récupérées (chunks) pour enrichir ses réponses.
    
    Ce tableau de bord compare ces deux approches sur un ensemble fixe de questions.
    """)

    result_map = load_data()

    for i, q in enumerate(QUESTIONS):
        pair = result_map.get(q)
        if not pair:
            continue
        st.subheader(f"Question : {q}")
        
        col1, col2 = st.columns(2)

        with col1:
            st.write("### Sans RAG")
            st.write(pair["no_rag_answer"])
            st.session_state.no_rag_scores[i] = st.slider(f"Notez cette réponse sans RAG (0-5)", 0, 5, st.session_state.no_rag_scores[i], key=f"no_rag_{i}")

        with col2:
            st.write("### Avec RAG")
            st.write(pair["rag_answer"])
            st.session_state.rag_scores[i] = st.slider(f"Notez cette réponse avec RAG (0-5)", 0, 5, st.session_state.rag_scores[i], key=f"rag_{i}")
            
            st.write("Chunks retrouvés :")
            for j, chunk_text in enumerate(pair["rag_chunks"]):
                st.markdown(f"**Chunk {j+1}:**")
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
    
    # Graphique F1 avec Altair
    f1_chart_container = st.empty()

    def update_f1_chart():
        no_rag_f1 = calculate_f1(st.session_state.no_rag_scores)
        rag_f1 = calculate_f1(st.session_state.rag_scores)
        
        f1_data = pd.DataFrame({
            "Méthode": ["Sans RAG", "Avec RAG"],
            "Score F1": [no_rag_f1, rag_f1]
        })

        f1_chart = alt.Chart(f1_data).mark_bar().encode(
            x=alt.X("Méthode:N", axis=alt.Axis(labelAngle=0)),
            y=alt.Y("Score F1:Q", scale=alt.Scale(domain=[0, 1])),
            color=alt.Color("Méthode:N", scale=alt.Scale(domain=["Sans RAG", "Avec RAG"], range=["#1f77b4", "#ff7f0e"])),
            tooltip=["Méthode", "Score F1"]
        ).properties(width=600, height=400, title="Comparaison des Scores F1")

        f1_chart_container.altair_chart(f1_chart, use_container_width=True)

    update_f1_chart()

    # Composant JavaScript pour mise à jour en temps réel
    html_content = """
    <script>
    function updateF1Scores() {
        const noRagScores = %s;
        const ragScores = %s;
        
        function calculateF1(scores) {
            const truePositives = scores.filter(score => score >= 3).length;
            const falseNegatives = scores.filter(score => score < 3).length;
            const total = scores.length;
            
            const precision = total > 0 ? truePositives / total : 0;
            const recall = (truePositives + falseNegatives) > 0 ? truePositives / (truePositives + falseNegatives) : 0;
            
            return (precision + recall) > 0 ? 2 * (precision * recall) / (precision + recall) : 0;
        }
        
        const noRagF1 = calculateF1(noRagScores);
        const ragF1 = calculateF1(ragScores);
        
        Streamlit.setComponentValue({
            noRagF1: noRagF1,
            ragF1: ragF1
        });
    }
    
    // Mettre à jour les scores toutes les 100ms
    setInterval(updateF1Scores, 100);
    </script>
    """ % (json.dumps(st.session_state.no_rag_scores), json.dumps(st.session_state.rag_scores))

    html(html_content, height=0)

    # Callback pour mettre à jour le graphique
    if st.session_state.get('noRagF1') is not None and st.session_state.get('ragF1') is not None:
        update_f1_chart()

if __name__ == "__main__":
    main()
