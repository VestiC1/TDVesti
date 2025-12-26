import pygame
import pytmx
import os
import time

# Initialisation
pygame.init()

LARGEUR = 1280  # 20 tuiles × 64px
HAUTEUR = 960   # 15 tuiles × 64px

ecran = pygame.display.set_mode((LARGEUR, HAUTEUR))
pygame.display.set_caption("Mon Tower Defense")
horloge = pygame.time.Clock()

# Charger la carte Tiled
carte_tmx = pytmx.load_pygame("assets/maps/niveau1.tmx")    

# Dictionnaire pour stocker tous les sprites
sprites = {}

def charger_sprite(nom_fichier, taille=None):
    """
    Charge une image et la redimensionne si nécessaire
    
    nom_fichier: le nom du fichier dans assets/sprites/
    taille: tuple (largeur, hauteur) ou None pour garder la taille originale
    """
    chemin = os.path.join("assets", "sprites", nom_fichier)
    try:
        image = pygame.image.load(chemin).convert_alpha()
        if taille:
            image = pygame.transform.scale(image, taille)
        return image
    except FileNotFoundError:
        print(f"⚠️ Fichier introuvable : {chemin}")
        # Créer une image de remplacement rouge
        image = pygame.Surface((64, 64))
        image.fill((255, 0, 0))
        return image

# Charger les sprites des tours
sprites['tour_canon'] = charger_sprite("tank_blue.png", (64, 64))
sprites['tour_laser'] = charger_sprite("tank_red.png", (64, 64))

# Charger les sprites des monstres
sprites['monstre_1'] = charger_sprite("towerDefense_tile245.png", (48, 48))
sprites['monstre_2'] = charger_sprite("towerDefense_tile246.png", (48, 48))

# Charger les projectiles
sprites['projectile'] = charger_sprite("bulletBlue1.png", (16, 16))

# Effet d'explosion (pour plus tard)
sprites['explosion'] = charger_sprite("explosion1.png", (64, 64))

print("✅ Sprites chargés :")
for nom, sprite in sprites.items():
    print(f"  - {nom}: {sprite.get_size()}")

# Fonction pour dessiner la carte
def dessiner_carte():
    # Parcourir toutes les couches visibles
    for couche in carte_tmx.visible_layers:
        # Vérifier que c'est une couche de tuiles
        if isinstance(couche, pytmx.TiledTileLayer):
            # Parcourir chaque tuile de la couche
            for x, y, image in couche.tiles():
                # Calculer la position en pixels
                pos_x = x * carte_tmx.tilewidth
                pos_y = y * carte_tmx.tileheight
                # Dessiner la tuile à l'écran
                ecran.blit(image, (pos_x, pos_y))

# Fonction pour récupérer les points d'entrée/sortie
def obtenir_points_speciaux():
    points = {}
    for obj in carte_tmx.objects:
        # Utilise 'point_type' au lieu de 'type'
        if hasattr(obj, 'properties') and 'point_type' in obj.properties:
            if obj.properties['point_type'] == "entree":
                points['entree'] = (obj.x, obj.y)
            elif obj.properties['point_type'] == "sortie":
                points['sortie'] = (obj.x, obj.y)
    return points

# Récupérer les points
points = obtenir_points_speciaux()
print("Points spéciaux trouvés :", points)

def creer_chemin_manuel():
    """
    Définit le chemin manuellement
    Tu devras ajuster ces coordonnées selon TON chemin dans Tiled
    """
    # Récupère le point d'entrée et de sortie
    points = obtenir_points_speciaux()
    
    # Crée un chemin simple pour tester
    # Format : liste de tuples (x, y) en pixels
    chemin = [
        points['entree'],
        (250, 190),  # Droite
        (520, 190),  # Droite
        (650, 280),  # Bas
        (650, 500),  # Bas
        (650, 700),  # Droite
        (750, 760),
        (980, 760),
        (1110, 760),
        points['sortie']
    ]
    
    return chemin

# Créer le chemin
chemin_monstres = creer_chemin_manuel()
print(f"✅ Chemin créé : {len(chemin_monstres)} points")

class Monstre:
    """Classe représentant un monstre ennemi"""
    
    def __init__(self, chemin, sprite, vitesse=2, vie=100):
        """
        chemin: liste de points (x, y) à suivre
        sprite: image du monstre
        vitesse: pixels par frame
        vie: points de vie
        """
        self.chemin = chemin
        self.sprite = sprite
        self.vitesse = vitesse
        self.vie_max = vie
        self.vie = vie
        
        # Position actuelle
        self.x, self.y = chemin[0]
        
        # Index du prochain point à atteindre
        self.index_chemin = 1
        
        # État
        self.actif = True
        self.arrive = False
    
    def deplacer(self):
        """Déplace le monstre vers le prochain point du chemin"""
        if not self.actif or self.arrive:
            return
        
        # Vérifier qu'il reste des points à atteindre
        if self.index_chemin >= len(self.chemin):
            self.arrive = True
            self.actif = False
            return
        
        # Récupérer le prochain point cible
        cible_x, cible_y = self.chemin[self.index_chemin]
        
        # Calculer la direction vers la cible
        dx = cible_x - self.x
        dy = cible_y - self.y
        
        # Calculer la distance
        distance = (dx**2 + dy**2)**0.5
        
        # Si on est proche du point, passer au suivant
        if distance < self.vitesse:
            self.x = cible_x
            self.y = cible_y
            self.index_chemin += 1
        else:
            # Normaliser la direction et avancer
            self.x += (dx / distance) * self.vitesse
            self.y += (dy / distance) * self.vitesse
    
    def dessiner(self, ecran):
        """Affiche le monstre à l'écran"""
        if not self.actif:
            return
        
        # Centrer le sprite sur la position
        rect = self.sprite.get_rect(center=(int(self.x), int(self.y)))
        ecran.blit(self.sprite, rect)
        
        # Dessiner la barre de vie
        self.dessiner_barre_vie(ecran)
    
    def dessiner_barre_vie(self, ecran):
        """Affiche une barre de vie au-dessus du monstre"""
        largeur_barre = 40
        hauteur_barre = 5
        
        # Position de la barre (au-dessus du monstre)
        barre_x = int(self.x - largeur_barre // 2)
        barre_y = int(self.y - 30)
        
        # Barre rouge (fond)
        pygame.draw.rect(ecran, (255, 0, 0), 
                        (barre_x, barre_y, largeur_barre, hauteur_barre))
        
        # Barre verte (vie actuelle)
        vie_largeur = int((self.vie / self.vie_max) * largeur_barre)
        pygame.draw.rect(ecran, (0, 255, 0), 
                        (barre_x, barre_y, vie_largeur, hauteur_barre))
    
    def prendre_degats(self, degats):
        """Inflige des dégâts au monstre"""
        self.vie -= degats
        if self.vie <= 0:
            self.vie = 0
            self.actif = False

# Créer une liste pour stocker tous les monstres
liste_monstres = []

# Créer un premier monstre de test
monstre_test = Monstre(chemin_monstres, sprites['monstre_1'], vitesse=3, vie=100)
liste_monstres.append(monstre_test)

# Gestion des vagues
vague_actuelle = 1
monstres_par_vague = 5
delai_entre_monstres = max(0.5, 2.0 - (vague_actuelle * 0.1))  # Plus rapide à chaque vague
derniere_apparition = 0
monstres_envoyes = 0
vague_en_cours = False

def demarrer_vague():
    """Démarre une nouvelle vague"""
    global vague_en_cours, monstres_envoyes, derniere_apparition
    vague_en_cours = True
    monstres_envoyes = 0
    derniere_apparition = time.time()
    print(f"🌊 Vague {vague_actuelle} démarre ! ({monstres_par_vague} monstres)")

def generer_monstre():
    global monstres_envoyes, derniere_apparition
    
    temps_actuel = time.time()
    
    if temps_actuel - derniere_apparition >= delai_entre_monstres:
        # Vagues 1-2 : Seulement monstre_1
        if vague_actuelle <= 2:
            sprite = sprites['monstre_1']
            vitesse = 2
            vie = 100
        # Vagues 3+ : Mélange de monstres plus forts
        else:
            if monstres_envoyes % 3 == 0:
                sprite = sprites['monstre_2']
                vitesse = 4  # Très rapide !
                vie = 150    # Plus de vie
            else:
                sprite = sprites['monstre_1']
                vitesse = 2
                vie = 100 + (vague_actuelle * 10)  # Vie augmente avec les vagues
        
        nouveau_monstre = Monstre(chemin_monstres, sprite, vitesse, vie)
        liste_monstres.append(nouveau_monstre)
        
        monstres_envoyes += 1
        derniere_apparition = temps_actuel

def verifier_fin_vague():
    """Vérifie si la vague est terminée"""
    global vague_en_cours, vague_actuelle, monstres_par_vague
    
    # Si tous les monstres sont envoyés
    if monstres_envoyes >= monstres_par_vague:
        # Si tous les monstres sont morts ou arrivés
        monstres_actifs = [m for m in liste_monstres if m.actif or not m.arrive]
        if len(monstres_actifs) == 0:
            vague_en_cours = False
            vague_actuelle += 1
            monstres_par_vague += 2  # Plus de monstres à chaque vague
            print(f"✅ Vague terminée ! Prochaine vague : {vague_actuelle}")
            return True
    return False

# Démarrer la première vague automatiquement
demarrer_vague()

# Boucle principale
en_cours = True
while en_cours:
    # Gestion des événements
    for evenement in pygame.event.get():
        if evenement.type == pygame.QUIT:
            en_cours = False
        
        # NOUVEAU : Touche ESPACE pour démarrer une vague manuellement
        if evenement.type == pygame.KEYDOWN:
            if evenement.key == pygame.K_SPACE and not vague_en_cours:
                demarrer_vague()
    
    # Dessiner la carte
    dessiner_carte()
    
    # ========== NOUVEAU : Gestion des vagues ==========
    if vague_en_cours:
        # Générer un monstre si nécessaire
        if monstres_envoyes < monstres_par_vague:
            generer_monstre()
        
        # Vérifier si la vague est terminée
        verifier_fin_vague()
    # ==================================================
    
    # Déplacer tous les monstres
    for monstre in liste_monstres:
        monstre.deplacer()
    
    # Nettoyer les monstres inactifs (morts ou arrivés)
    liste_monstres = [m for m in liste_monstres if m.actif or not m.arrive]
    
    # Dessiner tous les monstres
    for monstre in liste_monstres:
        monstre.dessiner(ecran)
    
    # Dessiner les cercles sur les points d'entrée/sortie
    if 'entree' in points:
        pygame.draw.circle(ecran, (0, 255, 0), 
                         (int(points['entree'][0]), int(points['entree'][1])), 5)
    if 'sortie' in points:
        pygame.draw.circle(ecran, (255, 0, 0), 
                         (int(points['sortie'][0]), int(points['sortie'][1])), 5)
    
    # ========== NOUVEAU : Affichage des infos ==========
    fonte = pygame.font.Font(None, 36)
    
    # Afficher le numéro de vague
    texte_vague = fonte.render(f"Vague: {vague_actuelle}", True, (255, 255, 255))
    ecran.blit(texte_vague, (10, 10))
    
    # Afficher le nombre de monstres
    texte_monstres = fonte.render(f"Monstres: {len(liste_monstres)}", True, (255, 255, 255))
    ecran.blit(texte_monstres, (10, 50))
    
    # Si vague terminée, afficher un message
    if not vague_en_cours:
        texte_attente = fonte.render("Appuie sur ESPACE pour la prochaine vague", True, (255, 255, 0))
        ecran.blit(texte_attente, (LARGEUR // 2 - 300, HAUTEUR // 2))
    # ===================================================
    
    pygame.display.flip()
    horloge.tick(60)

pygame.quit()