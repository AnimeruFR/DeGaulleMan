# DeGaulleMan

Un jeu de labyrinthe original, façon arcade des années 80, aux couleurs de la France.

Pierrot, coiffé de son béret, doit manger toutes les pastilles du labyrinthe en échappant aux **Paperasses**, quatre feuilles administratives très en colère.

## Lancer le jeu

Double-clique sur **`DeGaulleMan.exe`**. Rien d'autre à installer.

Depuis les sources :

```bash
py -m pip install pygame
py degaulleman.py
```

## Commandes

| Touche | Action |
|---|---|
| Flèches / ZQSD / WASD | Se déplacer |
| Entrée / Espace | Commencer |
| P / Échap | Pause |
| M | Couper le son |
| F11 | Plein écran |

## Règles

- Pastille : 10 pts. **Cocarde tricolore** : 50 pts, et les Paperasses prennent peur.
- Paperasse attrapée pendant la peur : 200, 400, 800 puis 1600 pts. Elle repart au bureau en avion de papier.
- Bonus qui apparaissent deux fois par niveau : baguette, croissant, camembert, macaron, éclair, tour Eiffel, coq, médaille (100 à 5000 pts).
- Une vie en plus à 10 000 pts. Le record est sauvegardé.
- Les niveaux accélèrent et la peur dure de moins en moins longtemps. Il y a des entractes après les niveaux 2, 5 et 9.

### Les Paperasses

| Nom | Comportement |
|---|---|
| CERFA « le Tenace » | Te fonce droit dessus, et accélère quand il reste peu de pastilles |
| TAMPON « le Fourbe » | Vise quelques cases devant toi pour te couper la route |
| DOSSIER « l'Imprévisible » | Te prend en tenaille avec Cerfa |
| CIRCULAIRE « la Timide » | Te poursuit de loin, mais se sauve quand elle s'approche |

## Easter egg

<details>
<summary>Spoiler</summary>

Tape **GAULLE** au clavier (ou le code Konami : ↑ ↑ ↓ ↓ ← → ← → B A), à n'importe quel moment.

Pierrot est alors remplacé par la tête du **Général de Gaulle**, avec képi deux étoiles. Le titre devient DEGAULLEMAN, et l'activation joue les premières notes de La Marseillaise (domaine public). Refais le code pour revenir à Pierrot.
</details>

## Reconstruire l'exécutable

```bash
build.bat
```

Tous les graphismes et les sons sont générés par le code : il n'y a aucun fichier externe.
