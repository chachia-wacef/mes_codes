import pandas as pd
import numpy as np

# 1. Joindre df_klife avec df_RIB
# On utilise how='left' pour garder toutes les lignes de klife
df_result = pd.merge(
    df_klife, 
    df_RIB[['IBAN_COD', 'BANQ_COMPTE_NUM', 'NB_CHANGES']], 
    left_on='IBAN', 
    right_on='IBAN_COD', 
    how='left'
)

# 2. Joindre avec df_compte
# On utilise des suffixes pour différencier les NUM_PERS des deux tables
df_result = pd.merge(
    df_result, 
    df_compte[['BANQ_COMPTE_NUM', 'NUM_PERS']], 
    on='BANQ_COMPTE_NUM', 
    how='left', 
    suffixes=('', '_compte')
)

# 3. Définition des conditions de suspicion
# Condition A : L'IBAN n'existe pas dans df_RIB
cond_a = df_result['IBAN_COD'].isna()

# Condition B : Le compte n'existe pas dans df_compte
cond_b = df_result['NUM_PERS_compte'].isna()

# Condition C : Le NUM_PERS ne match pas entre klife et compte
cond_c = df_result['NUM_PERS'] != df_result['NUM_PERS_compte']

# Condition D : NB_CHANGES n'est pas égal à 0
cond_d = df_result['NB_CHANGES'] != 0

# 4. Marquage final
# Une ligne est suspecte si A est vrai OR (si non A, alors B ou C ou D)
# En fait, selon ta logique, c'est un simple OR de toutes les erreurs possibles
df_result['IS_SUSPECT'] = cond_a | cond_b | cond_c | cond_d

# Optionnel : On peut même préciser la raison pour faciliter ton audit
df_result['RAISON'] = np.select(
    [cond_a, cond_b, cond_c, cond_d],
    ['IBAN absent RIB', 'Compte absent table compte', 'NUM_PERS mismatch', 'NB_CHANGES > 0'],
    default='OK'
)