# Gestion des Commentaires - Module incus_cli

## Modifications Appliquées

### Problème Initial
Les commentaires contenus dans les templates ou les commandes n'étaient pas supprimés avant l'exécution, causant des erreurs lors de l'appel aux commandes Incus.

### Solution Implémentée

#### 1. **Suppression des Commentaires Inline** (`_execute_command()`)
- Ajout d'une fonction `_remove_comments()` qui supprime intelligemment les commentaires en respectant les guillemets
- Les commentaires inline (ex: `incus list  # Display containers`) sont supprimés avant l'exécution

#### 2. **Suppression des Commentaires Standalone** (`run()`)
- Filtrage des lignes qui commencent par `#` dans le traitement des commandes
- Ces lignes sont complètement ignorées et ne sont pas exécutées

#### 3. **Traçabilité Conservée**
- Les commentaires restent visibles dans `rendered_commands` pour le debugging
- Seul l'exécution supprime les commentaires

## Fichiers Modifiés

### `library/incus_cli.py`

#### Nouvelle fonction `_remove_comments()`
```python
def _remove_comments(self, line):
    """Remove comments from a command line (# and everything after)"""
    # Respects single and double quotes
    # Returns the line without the comment portion
```

**Caractéristiques:**
- Supprime tout ce qui suit `#`
- Respecte les guillemets simples et doubles
- Ignore les `#` à l'intérieur des chaînes de caractères

#### Modification de `_execute_command()`
- Appelle `_remove_comments()` avant d'exécuter
- Ignore silencieusement les commandes vides après suppression des commentaires
- Retourne un résultat neutre (rc=0, stderr='') pour les commandes vides

#### Modification de `run()`
```python
# Filter out comment-only lines
commands_to_execute = [cmd for cmd in commands_to_execute if not cmd.startswith('#')]
```

## Comportement

### Avant Modification
```yaml
Template: "incus launch {{ image }} {{ container }}  # Start container"
Résultat: Erreur - le shell ne reconnaît pas la syntaxe
```

### Après Modification
```yaml
Template: "incus launch {{ image }} {{ container }}  # Start container"
Résultat: ✓ Exécute uniquement "incus launch images:debian/13 c3"
Trace: Les commentaires restent visibles dans debug_info pour traçabilité
```

## Cas de Gestion

| Type | Exemple | Résultat |
|------|---------|----------|
| **Commentaires Standalone** | `# Show containers` | Ligne complètement ignorée |
| **Commentaires Inline** | `incus list  # Display all` | `incus list` exécuté seul |
| **Guillemets Simples** | `echo '# test'` | Guillemets préservés, `#` interne conservé |
| **Guillemets Doubles** | `echo "# test"` | Guillemets préservés, `#` interne conservé |
| **Commandes Vides** | Après suppression des commentaires | Silencieusement ignorées (rc=0) |

## Tests

### Playbooks de Test Créés

1. **test_comments.yml** - Test des commentaires inline simples
2. **test_template_comments.yml** - Test d'un template avec commentaires mixtes
3. **test_comments_clean.yml** - Test avec template complet
4. **test_final_comments.yml** - Test final de validation ✓

### Résultats

```
✓ Commentaires inline supprimés correctement
✓ Commentaires standalone filtrés correctement
✓ Variables substituées malgré les commentaires
✓ Traçabilité maintenue dans debug_info
✓ Commandes exécutées avec succès
```

## Impact

- ✅ Templates et commandes peuvent maintenant contenir des commentaires
- ✅ Meilleure lisibilité et maintenabilité des playbooks
- ✅ Pas de régression fonctionnelle
- ✅ Debug facilité par conservation des commentaires dans la sortie
