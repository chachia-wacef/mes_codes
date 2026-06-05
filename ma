import boto3

bedrock = boto3.client("bedrock-runtime", region_name="us-east-1")
MODEL_ID = "anthropic.claude-sonnet-4-6"


class VerificateurConformite:
    def __init__(self, transcription: str):
        self.transcription = transcription
        # Préfixe stable construit UNE FOIS - ne jamais le modifier
        self.system_blocks = [
            {"text": "Tu es un auditeur conformité. Tu reçois une transcription d'appel courtier/client. Pour chaque exigence, réponds en JSON: {verifiee: bool, citation: str, justification: str}."},
            {"text": f"<transcription>\n{transcription}\n</transcription>"},
            {"cachePoint": {"type": "default"}},
        ]

    def poser_question(self, question: str) -> tuple[str, dict]:
        response = bedrock.converse(
            modelId=MODEL_ID,
            system=self.system_blocks,  # ← exactement le même à chaque appel
            messages=[{
                "role": "user",
                "content": [{"text": question}],
            }],
            inferenceConfig={"maxTokens": 2000},
        )

        text = response["output"]["message"]["content"][0]["text"]
        usage = response["usage"]
        return text, usage


# Usage
transcript = open("appel.txt").read()
verif = VerificateurConformite(transcript)

questions = [
    "Le courtier a-t-il vérifié l'identité du client (nom, date de naissance, adresse) ?",
    "Le courtier a-t-il évalué la situation financière du client ?",
    "Le courtier a-t-il informé le client des risques associés au produit ?",
    "Le courtier a-t-il documenté le profil de risque du client ?",
]

for i, q in enumerate(questions, 1):
    reponse, usage = verif.poser_question(q)
    print(f"\n--- Question {i} ---")
    print(f"Cache write: {usage.get('cacheWriteInputTokens', 0):>6} tokens")
    print(f"Cache read:  {usage.get('cacheReadInputTokens', 0):>6} tokens")
    print(f"Input neuf:  {usage['inputTokens']:>6} tokens")
    print(f"Output:      {usage['outputTokens']:>6} tokens")
    print(f"Réponse: {reponse[:200]}...")
