import pygame
import pytmx
import os
import time
import math
import random

# ========================================
# INITIALISATION
# ========================================

pygame.init()

LARGEUR = 1280
HAUTEUR = 960

ecran = pygame.display.set_mode((LARGEUR, HAUTEUR))
pygame.display.set_caption("Mon Tower Defense")
horloge = pygame.time.Clock()

# Charger la carte Tiled
carte_tmx = pytmx.load_pygame("assets/maps/niveau1.tmx")

# Initialiser le son
try:
    pygame.mixer.init()
    son_tir = pygame.mixer.Sound("assets/sounds/footstep_carpet_001.ogg")
    son_explosion = pygame.mixer.Sound("assets/sounds/impactMetal_medium_003.ogg")
    son_degats = pygame.mixer.Sound("assets/sounds/impactSoft_heavy_001.ogg")
    son_tir.set_volume(0.3)
    son_explosion.set_volume(0.5)
    son_degats.set_volume(0.4)
    sons_actives = True
    print("✅ Sons chargés")
except:
    sons_actives = False
    print("⚠️ Sons désactivés")

# ========================================
# CHARGEMENT DES SPRITES
# ========================================

sprites = {}

def charger_sprite(nom_fichier, taille=None):
    """Charge une image et la redimensionne si nécessaire"""
    chemin = os.path.join("assets", "sprites", nom_fichier)
    try:
        image = pygame.image.load(chemin).convert_alpha()
        if taille:
            image = pygame.transform.scale(image, taille)
        return image
    except FileNotFoundError:
        print(f"⚠️ Fichier introuvable : {chemin}")
        image = pygame.Surface((64, 64))
        image.fill((255, 0, 0))
        return image

# Charger tous les sprites
sprites['tour_canon'] = charger_sprite("tank_blue.png", (64, 64))
sprites['tour_laser'] = charger_sprite("tank_red.png", (64, 64))
sprites['monstre_1'] = charger_sprite("towerDefense_tile245.png", (48, 48))
sprites['monstre_2'] = charger_sprite("towerDefense_tile246.png", (48, 48))
sprites['projectile'] = charger_sprite("bulletBlue1.png", (16, 16))
sprites['explosion'] = charger_sprite("explosion1.png", (64, 64))
# Sprite du héros
sprites['hero'] = charger_sprite("towerDefense_tile271.png", (64, 64))

print("✅ Sprites chargés")

# ========================================
# FONCTIONS CARTE
# ========================================

def dessiner_carte():
    """Dessine toutes les couches de la carte"""
    for couche in carte_tmx.visible_layers:
        if isinstance(couche, pytmx.TiledTileLayer):
            for x, y, image in couche.tiles():
                pos_x = x * carte_tmx.tilewidth
                pos_y = y * carte_tmx.tileheight
                ecran.blit(image, (pos_x, pos_y))

def obtenir_points_speciaux():
    """Récupère les points d'entrée et de sortie"""
    points = {}
    for obj in carte_tmx.objects:
        if hasattr(obj, 'properties') and 'point_type' in obj.properties:
            if obj.properties['point_type'] == "entree":
                points['entree'] = (obj.x, obj.y)
            elif obj.properties['point_type'] == "sortie":
                points['sortie'] = (obj.x, obj.y)
    return points

points = obtenir_points_speciaux()

def creer_chemin_manuel():
    """Définit le chemin que suivront les monstres"""
    pts = obtenir_points_speciaux()
    chemin = [
        pts['entree'],
        (250, 190),
        (520, 190),
        (650, 280),
        (650, 500),
        (650, 700),
        (750, 760),
        (980, 760),
        (1110, 760),
        pts['sortie']
    ]
    return chemin

chemin_monstres = creer_chemin_manuel()
print(f"✅ Chemin créé : {len(chemin_monstres)} points")

# ========================================
# CLASSE MONSTRE
# ========================================

class Monstre:
    """Représente un monstre ennemi"""

    def __init__(self, chemin, sprite, vitesse=2, vie=100):
        self.chemin = chemin
        self.sprite = sprite
        self.vitesse = vitesse
        self.vie_max = vie
        self.vie = vie
        self.x, self.y = chemin[0]
        self.index_chemin = 1
        self.actif = True
        self.arrive = False
        self.recompense_donnee = False

    def deplacer(self):
        """Déplace le monstre le long du chemin"""
        if not self.actif or self.arrive:
            return

        if self.index_chemin >= len(self.chemin):
            self.arrive = True
            self.actif = False
            return

        cible_x, cible_y = self.chemin[self.index_chemin]
        dx = cible_x - self.x
        dy = cible_y - self.y
        distance = (dx**2 + dy**2)**0.5

        if distance < self.vitesse:
            self.x = cible_x
            self.y = cible_y
            self.index_chemin += 1
        else:
            self.x += (dx / distance) * self.vitesse
            self.y += (dy / distance) * self.vitesse

    def dessiner(self, ecran):
        """Affiche le monstre et sa barre de vie"""
        if not self.actif:
            return

        rect = self.sprite.get_rect(center=(int(self.x), int(self.y)))
        ecran.blit(self.sprite, rect)

        # Barre de vie
        largeur_barre = 40
        hauteur_barre = 5
        barre_x = int(self.x - largeur_barre // 2)
        barre_y = int(self.y - 30)

        pygame.draw.rect(ecran, (255, 0, 0),
                        (barre_x, barre_y, largeur_barre, hauteur_barre))

        vie_largeur = int((self.vie / self.vie_max) * largeur_barre)
        pygame.draw.rect(ecran, (0, 255, 0),
                        (barre_x, barre_y, vie_largeur, hauteur_barre))

    def prendre_degats(self, degats):
        """Inflige des dégâts au monstre"""
        self.vie -= degats
        if self.vie <= 0:
            self.vie = 0
            self.actif = False
        if sons_actives:
            son_degats.play()

    def attaquer_hero(self, hero):
        """Attaque le héros s'il est proche"""
        if not self.actif or not hero.actif:
            return False

        dx = hero.x - self.x
        dy = hero.y - self.y
        distance = (dx**2 + dy**2)**0.5

        # Si le héros est très proche
        if distance < 50:
            hero.prendre_degats(0.5)

            # Créer quelques particules rouges
            if random.random() < 0.1:  # 10% de chance par frame
                for _ in range(3):
                    particule = Particule(hero.x, hero.y)
                    # Forcer la couleur rouge pour le héros
                    particule.couleur = (255, 0, 0)
                    liste_particules.append(particule)

            return True
        return False

# ========================================
# CLASSE PROJECTILE
# ========================================

class Projectile:
    """Représente un projectile tiré par une tour"""

    def __init__(self, x, y, cible, sprite, degats, vitesse=8):
        self.x = x
        self.y = y
        self.cible = cible
        self.sprite = sprite
        self.degats = degats
        self.vitesse = vitesse
        self.actif = True

    def deplacer(self):
        """Déplace le projectile vers sa cible"""
        if not self.actif or not self.cible.actif:
            self.actif = False
            return

        dx = self.cible.x - self.x
        dy = self.cible.y - self.y
        distance = (dx**2 + dy**2)**0.5

        if distance < 10:
            # Créer un texte flottant pour les dégâts
            texte_degats = TexteFlottant(
                self.cible.x,
                self.cible.y - 20,
                f"-{self.degats}",
                (255, 100, 100)
            )
            liste_textes_flottants.append(texte_degats)

            # Créer quelques particules d'impact
            for _ in range(5):
                particule = Particule(self.cible.x, self.cible.y)
                liste_particules.append(particule)

            # Infliger les dégâts
            self.cible.prendre_degats(self.degats)
            self.actif = False
            return

        self.x += (dx / distance) * self.vitesse
        self.y += (dy / distance) * self.vitesse

    def dessiner(self, ecran):
        """Affiche le projectile"""
        if not self.actif:
            return
        rect = self.sprite.get_rect(center=(int(self.x), int(self.y)))
        ecran.blit(self.sprite, rect)

# ========================================
# CLASSE EFFET VISUEL
# ========================================

class Effet:
    """Représente un effet visuel temporaire (explosion, etc.)"""

    def __init__(self, x, y, sprite, duree=0.3):
        self.x = x
        self.y = y
        self.sprite = sprite
        self.duree = duree  # Durée en secondes
        self.temps_creation = time.time()
        self.actif = True
        self.alpha = 255  # Opacité

    def mettre_a_jour(self):
        """Met à jour l'effet (fade out)"""
        temps_ecoule = time.time() - self.temps_creation

        if temps_ecoule >= self.duree:
            self.actif = False
            return

        # Fade out progressif
        progression = temps_ecoule / self.duree
        self.alpha = int(255 * (1 - progression))

    def dessiner(self, ecran):
        """Affiche l'effet avec transparence"""
        if not self.actif:
            return

        sprite_alpha = self.sprite.copy()
        sprite_alpha.set_alpha(self.alpha)
        rect = sprite_alpha.get_rect(center=(int(self.x), int(self.y)))
        ecran.blit(sprite_alpha, rect)

# ========================================
# CLASSE PARTICULE
# ========================================

class Particule:
    """Représente une particule d'explosion"""

    def __init__(self, x, y):
        self.x = x
        self.y = y
        # Vitesse aléatoire dans toutes les directions
        import random
        angle = random.uniform(0, 6.28)  # 0 à 2π radians
        vitesse = random.uniform(1, 4)
        self.vx = vitesse * math.cos(angle)
        self.vy = vitesse * math.sin(angle)

        # Propriétés visuelles
        self.taille = random.randint(3, 8)
        self.couleur = random.choice([
            (255, 150, 0),   # Orange
            (255, 100, 0),   # Orange foncé
            (255, 200, 0),   # Jaune
            (200, 50, 0),    # Rouge-orange
            (255, 255, 100)  # Jaune clair
        ])

        # Durée de vie
        self.duree = random.uniform(0.3, 0.8)
        self.temps_creation = time.time()
        self.actif = True
        self.alpha = 255

    def mettre_a_jour(self):
        """Met à jour la position et l'opacité de la particule"""
        temps_ecoule = time.time() - self.temps_creation

        if temps_ecoule >= self.duree:
            self.actif = False
            return

        # Déplacement
        self.x += self.vx
        self.y += self.vy

        # Gravité légère
        self.vy += 0.2

        # Ralentissement
        self.vx *= 0.98
        self.vy *= 0.98

        # Fade out
        progression = temps_ecoule / self.duree
        self.alpha = int(255 * (1 - progression))

    def dessiner(self, ecran):
        """Affiche la particule"""
        if not self.actif:
            return

        # Créer une surface temporaire avec alpha
        surface = pygame.Surface((self.taille * 2, self.taille * 2), pygame.SRCALPHA)
        couleur_alpha = (*self.couleur, self.alpha)
        pygame.draw.circle(surface, couleur_alpha, (self.taille, self.taille), self.taille)
        ecran.blit(surface, (int(self.x - self.taille), int(self.y - self.taille)))

# ========================================
# CLASSE TEXTE FLOTTANT
# ========================================

class TexteFlottant:
    """Représente un texte qui monte et disparaît (dégâts, argent, etc.)"""

    def __init__(self, x, y, texte, couleur=(255, 0, 0)):
        self.x = x
        self.y = y
        self.texte = texte
        self.couleur = couleur
        self.vitesse_y = -2  # Monte vers le haut
        self.duree = 1.0  # 1 seconde
        self.temps_creation = time.time()
        self.actif = True
        self.alpha = 255

        # Créer la surface texte une seule fois
        fonte = pygame.font.Font(None, 28)
        self.surface_texte = fonte.render(texte, True, couleur)

    def mettre_a_jour(self):
        """Met à jour la position et l'opacité"""
        temps_ecoule = time.time() - self.temps_creation

        if temps_ecoule >= self.duree:
            self.actif = False
            return

        # Déplacement vers le haut
        self.y += self.vitesse_y

        # Fade out
        progression = temps_ecoule / self.duree
        self.alpha = int(255 * (1 - progression))

    def dessiner(self, ecran):
        """Affiche le texte avec transparence"""
        if not self.actif:
            return

        # Appliquer l'alpha
        surface_alpha = self.surface_texte.copy()
        surface_alpha.set_alpha(self.alpha)
        rect = surface_alpha.get_rect(center=(int(self.x), int(self.y)))
        ecran.blit(surface_alpha, rect)

# ========================================
# CLASSE TOUR
# ========================================

class Tour:
    """Représente une tour défensive"""

    def __init__(self, x, y, sprite, portee=150, degats=25, cadence=1.0):
        self.x = x
        self.y = y
        self.sprite = sprite
        self.portee = portee
        self.degats = degats
        self.cadence = cadence
        self.dernier_tir = 0
        self.cible = None

    def trouver_cible(self, liste_monstres):
        """Trouve le monstre le plus proche dans la portée"""
        meilleure_cible = None
        distance_min = self.portee

        for monstre in liste_monstres:
            if not monstre.actif:
                continue

            dx = monstre.x - self.x
            dy = monstre.y - self.y
            distance = (dx**2 + dy**2)**0.5

            if distance <= self.portee and distance < distance_min:
                meilleure_cible = monstre
                distance_min = distance

        return meilleure_cible

    def tirer(self, liste_projectiles):
        """Tire sur la cible si possible"""
        temps_actuel = time.time()

        if temps_actuel - self.dernier_tir >= self.cadence:
            if self.cible and self.cible.actif:
                projectile = Projectile(
                    self.x, self.y,
                    self.cible,
                    sprites['projectile'],
                    self.degats
                )
                liste_projectiles.append(projectile)
                self.dernier_tir = temps_actuel
                if sons_actives:
                    son_tir.play()

    def mettre_a_jour(self, liste_monstres, liste_projectiles):
        """Met à jour la tour"""
        self.cible = self.trouver_cible(liste_monstres)
        if self.cible:
            self.tirer(liste_projectiles)

    def dessiner(self, ecran):
        """Affiche la tour et son rayon de portée"""
        rect = self.sprite.get_rect(center=(int(self.x), int(self.y)))
        ecran.blit(self.sprite, rect)

        # Dessiner la portée seulement si activé
        if afficher_portees:
            surface_portee = pygame.Surface((self.portee * 2, self.portee * 2), pygame.SRCALPHA)
            pygame.draw.circle(surface_portee, (255, 255, 255, 30),
                              (self.portee, self.portee), self.portee)
            ecran.blit(surface_portee, (self.x - self.portee, self.y - self.portee))

# ========================================
# CLASSE HÉROS
# ========================================

class Hero:
    """Représente le héros contrôlable par le joueur"""

    def __init__(self, x, y, sprite):
        self.x = x
        self.y = y
        self.sprite = sprite
        self.vitesse = 4  # Vitesse de déplacement

        # Combat
        self.vie_max = 100
        self.vie = 100
        self.portee = 120  # Portée d'attaque
        self.degats = 20
        self.cadence = 0.8  # Temps entre chaque tir
        self.dernier_tir = 0
        self.cible = None

        # État
        self.actif = True

    def deplacer(self, touches):
        """Déplace le héros selon les touches pressées"""
        if not self.actif:
            return

        # ZQSD ou Flèches
        if touches[pygame.K_z] or touches[pygame.K_UP]:
            self.y -= self.vitesse
        if touches[pygame.K_s] or touches[pygame.K_DOWN]:
            self.y += self.vitesse
        if touches[pygame.K_q] or touches[pygame.K_LEFT]:
            self.x -= self.vitesse
        if touches[pygame.K_d] or touches[pygame.K_RIGHT]:
            self.x += self.vitesse

        # Limiter aux bords de l'écran
        self.x = max(32, min(LARGEUR - 32, self.x))
        self.y = max(32, min(HAUTEUR - 32, self.y))

    def trouver_cible(self, liste_monstres):
        """Trouve le monstre le plus proche dans la portée"""
        meilleure_cible = None
        distance_min = self.portee

        for monstre in liste_monstres:
            if not monstre.actif:
                continue

            dx = monstre.x - self.x
            dy = monstre.y - self.y
            distance = (dx**2 + dy**2)**0.5

            if distance <= self.portee and distance < distance_min:
                meilleure_cible = monstre
                distance_min = distance

        return meilleure_cible

    def attaquer(self, liste_projectiles):
        """Tire sur la cible si possible"""
        temps_actuel = time.time()

        if temps_actuel - self.dernier_tir >= self.cadence:
            if self.cible and self.cible.actif:
                # Créer un projectile spécial pour le héros
                projectile = Projectile(
                    self.x, self.y,
                    self.cible,
                    sprites['projectile'],
                    self.degats,
                    vitesse=10  # Plus rapide que les tours
                )
                liste_projectiles.append(projectile)
                self.dernier_tir = temps_actuel

    def mettre_a_jour(self, touches, liste_monstres, liste_projectiles):
        """Met à jour le héros (déplacement + attaque)"""
        if not self.actif:
            return

        self.deplacer(touches)
        self.cible = self.trouver_cible(liste_monstres)

        if self.cible:
            self.attaquer(liste_projectiles)

    def prendre_degats(self, degats):
        """Le héros prend des dégâts"""
        self.vie -= degats
        if self.vie <= 0:
            self.vie = 0
            self.actif = False

    def dessiner(self, ecran):
        """Affiche le héros et sa barre de vie"""
        if not self.actif:
            return

        # Dessiner le sprite
        rect = self.sprite.get_rect(center=(int(self.x), int(self.y)))
        ecran.blit(self.sprite, rect)

        # Dessiner le cercle de portée (transparent)
        surface_portee = pygame.Surface((self.portee * 2, self.portee * 2), pygame.SRCALPHA)
        pygame.draw.circle(surface_portee, (100, 200, 255, 50),
                          (self.portee, self.portee), self.portee)
        ecran.blit(surface_portee, (self.x - self.portee, self.y - self.portee))

        # Barre de vie
        largeur_barre = 60
        hauteur_barre = 8
        barre_x = int(self.x - largeur_barre // 2)
        barre_y = int(self.y - 40)

        # Fond rouge
        pygame.draw.rect(ecran, (255, 0, 0),
                        (barre_x, barre_y, largeur_barre, hauteur_barre))

        # Vie verte
        vie_largeur = int((self.vie / self.vie_max) * largeur_barre)
        pygame.draw.rect(ecran, (0, 255, 0),
                        (barre_x, barre_y, vie_largeur, hauteur_barre))

        # Contour blanc
        pygame.draw.rect(ecran, (255, 255, 255),
                        (barre_x, barre_y, largeur_barre, hauteur_barre), 2)

# ========================================
# VARIABLES GLOBALES DU JEU
# ========================================

# Listes des entités
liste_monstres = []
liste_tours = []
liste_projectiles = []
liste_effets = []  # Liste des effets visuels
liste_particules = []  # Liste des particules
liste_textes_flottants = []  # Liste des textes flottants

# Ressources du joueur
argent = 200
vie_base = 20

# Système de vagues
vague_actuelle = 1
monstres_par_vague = 5
delai_entre_monstres = 1.5
derniere_apparition = 0
monstres_envoyes = 0
vague_en_cours = False

# Placement de tours
mode_placement = False
tour_a_placer = None

# Prix des tours
PRIX_TOUR_CANON = 50
PRIX_TOUR_LASER = 100

# État du jeu
game_over = False
kills_total = 0  # Compteur de monstres tués
afficher_portees = False  # Toggle pour afficher les portées
en_menu = True  # Commence au menu

# Créer le héros au centre de la carte
hero = Hero(LARGEUR // 2, HAUTEUR // 2, sprites['hero'])

# ========================================
# FONCTIONS DU JEU
# ========================================

def demarrer_vague():
    """Démarre une nouvelle vague"""
    global vague_en_cours, monstres_envoyes, derniere_apparition
    vague_en_cours = True
    monstres_envoyes = 0
    derniere_apparition = time.time()
    print(f"🌊 Vague {vague_actuelle} démarre ! ({monstres_par_vague} monstres)")

    # Message visuel au centre de l'écran
    texte_vague_debut = TexteFlottant(
        LARGEUR // 2,
        HAUTEUR // 3,
        f"VAGUE {vague_actuelle}",
        (255, 255, 100)
    )
    # Rendre le texte plus gros et dure plus longtemps
    texte_vague_debut.duree = 2.0
    fonte_grande = pygame.font.Font(None, 64)
    texte_vague_debut.surface_texte = fonte_grande.render(f"VAGUE {vague_actuelle}", True, (255, 255, 100))
    liste_textes_flottants.append(texte_vague_debut)

def generer_monstre():
    """Génère un nouveau monstre"""
    global monstres_envoyes, derniere_apparition

    temps_actuel = time.time()

    if temps_actuel - derniere_apparition >= delai_entre_monstres:
        # Progression plus douce de la difficulté
        if vague_actuelle <= 3:
            # Vagues 1-3 : Faciles
            sprite = sprites['monstre_1']
            vitesse = 2
            vie = 80 + (vague_actuelle * 10)  # 90, 100, 110
        elif vague_actuelle <= 6:
            # Vagues 4-6 : Mélange
            if monstres_envoyes % 2 == 0:
                sprite = sprites['monstre_1']
                vitesse = 2.5
                vie = 100 + (vague_actuelle * 8)
            else:
                sprite = sprites['monstre_2']
                vitesse = 3.5
                vie = 80 + (vague_actuelle * 8)
        else:
            # Vagues 7+ : Difficiles
            if monstres_envoyes % 3 == 0:
                # Boss occasionnel
                sprite = sprites['monstre_2']
                vitesse = 3
                vie = 200 + (vague_actuelle * 15)
            else:
                sprite = sprites['monstre_1']
                vitesse = 2 + (vague_actuelle * 0.1)
                vie = 120 + (vague_actuelle * 10)

        nouveau_monstre = Monstre(chemin_monstres, sprite, vitesse, vie)
        liste_monstres.append(nouveau_monstre)

        monstres_envoyes += 1
        derniere_apparition = temps_actuel
        print(f"  Monstre {monstres_envoyes}/{monstres_par_vague} envoyé")

def verifier_fin_vague():
    """Vérifie si la vague est terminée"""
    global vague_en_cours, vague_actuelle, monstres_par_vague

    if monstres_envoyes >= monstres_par_vague:
        monstres_actifs = [m for m in liste_monstres if m.actif and not m.arrive]
        if len(monstres_actifs) == 0:
            vague_en_cours = False

            # Message de victoire
            texte_victoire = TexteFlottant(
                LARGEUR // 2,
                HAUTEUR // 3,
                "VAGUE TERMINÉE !",
                (100, 255, 100)
            )
            texte_victoire.duree = 2.0
            fonte_grande = pygame.font.Font(None, 56)
            texte_victoire.surface_texte = fonte_grande.render("VAGUE TERMINÉE !", True, (100, 255, 100))
            liste_textes_flottants.append(texte_victoire)

            vague_actuelle += 1

            if vague_actuelle <= 5:
                monstres_par_vague += 2
            else:
                monstres_par_vague += 1

            print(f"✅ Vague terminée ! Prochaine vague : {vague_actuelle}")
            return True
    return False

def placer_tour(x, y, type_tour):
    """Place une tour aux coordonnées données"""
    global argent

    prix = PRIX_TOUR_CANON if type_tour == 'canon' else PRIX_TOUR_LASER

    if argent < prix:
        print(f"❌ Pas assez d'argent ! (besoin: {prix}, disponible: {argent})")
        return False

    if type_tour == 'canon':
        sprite = sprites['tour_canon']
        portee = 150
        degats = 25
        cadence = 1.0
    else:
        sprite = sprites['tour_laser']
        portee = 200
        degats = 15
        cadence = 0.5

    nouvelle_tour = Tour(x, y, sprite, portee, degats, cadence)
    liste_tours.append(nouvelle_tour)

    argent -= prix
    print(f"✅ Tour {type_tour} placée ! Argent restant: {argent}")
    return True

def verifier_position_valide(x, y):
    """Vérifie si on peut placer une tour à cette position"""
    for point_x, point_y in chemin_monstres:
        distance = ((x - point_x)**2 + (y - point_y)**2)**0.5
        if distance < 40:
            return False

    for tour in liste_tours:
        distance = ((x - tour.x)**2 + (y - tour.y)**2)**0.5
        if distance < 60:
            return False

    return True

def dessiner_interface():
    """Dessine une interface horizontale en haut et en bas de l'écran"""
    fonte = pygame.font.Font(None, 32)
    fonte_petite = pygame.font.Font(None, 26)

    # ========================================
    # BANDEAU SUPÉRIEUR (informations du jeu)
    # ========================================

    # Fond du bandeau
    bandeau_haut = pygame.Surface((LARGEUR, 60), pygame.SRCALPHA)
    bandeau_haut.fill((0, 0, 0, 200))
    ecran.blit(bandeau_haut, (0, 0))

    # Ligne de séparation en bas du bandeau
    pygame.draw.line(ecran, (100, 100, 100), (0, 60), (LARGEUR, 60), 2)

    # Espacement entre les éléments
    x_pos = 20

    # 1. Vague
    texte_vague = fonte.render(f"Vague {vague_actuelle}", True, (255, 255, 255))
    ecran.blit(texte_vague, (x_pos, 15))
    x_pos += 150

    # Séparateur vertical
    pygame.draw.line(ecran, (100, 100, 100), (x_pos, 10), (x_pos, 50), 1)
    x_pos += 20

    # 2. Argent
    texte_argent = fonte.render(f"💰 {argent}$", True, (255, 215, 0))
    ecran.blit(texte_argent, (x_pos, 15))
    x_pos += 140

    # Séparateur vertical
    pygame.draw.line(ecran, (100, 100, 100), (x_pos, 10), (x_pos, 50), 1)
    x_pos += 20

    # 3. Vie de la base
    couleur_vie = (255, 0, 0) if vie_base <= 5 else (255, 100, 100)
    texte_vie_base = fonte.render(f"❤️ {vie_base}", True, couleur_vie)
    ecran.blit(texte_vie_base, (x_pos, 15))
    x_pos += 100

    # Séparateur vertical
    pygame.draw.line(ecran, (100, 100, 100), (x_pos, 10), (x_pos, 50), 1)
    x_pos += 20

    # 4. Kills
    texte_kills = fonte.render(f"💀 {kills_total}", True, (255, 150, 150))
    ecran.blit(texte_kills, (x_pos, 15))
    x_pos += 120

    # Compteur de monstres restants (pendant la vague)
    if vague_en_cours:
        # Séparateur vertical
        pygame.draw.line(ecran, (100, 100, 100), (x_pos, 10), (x_pos, 50), 1)
        x_pos += 20

        monstres_restants = monstres_par_vague - monstres_envoyes
        monstres_vivants = len([m for m in liste_monstres if m.actif])
        texte_restants = fonte_petite.render(f"Restants: {monstres_restants + monstres_vivants}", True, (200, 200, 200))
        ecran.blit(texte_restants, (x_pos, 18))
        x_pos += 150

    # Séparateur vertical (avant la barre héros)
    pygame.draw.line(ecran, (100, 100, 100), (x_pos, 10), (x_pos, 50), 1)
    x_pos += 30

    # 5. Barre de vie du héros (compacte, horizontale)
    texte_hero = fonte_petite.render("Héros:", True, (200, 200, 200))
    ecran.blit(texte_hero, (x_pos, 18))

    barre_x = x_pos + 80
    barre_y = 20
    barre_largeur = 200
    barre_hauteur = 20

    # Fond de la barre
    pygame.draw.rect(ecran, (100, 0, 0), (barre_x, barre_y, barre_largeur, barre_hauteur))

    # Vie actuelle
    vie_proportion = hero.vie / hero.vie_max
    couleur_vie_hero = (0, 255, 0) if vie_proportion > 0.5 else (255, 150, 0) if vie_proportion > 0.25 else (255, 0, 0)
    pygame.draw.rect(ecran, couleur_vie_hero,
                    (barre_x, barre_y, int(barre_largeur * vie_proportion), barre_hauteur))

    # Texte sur la barre
    texte_vie_hero = fonte_petite.render(f"{int(hero.vie)}/{int(hero.vie_max)}", True, (255, 255, 255))
    ecran.blit(texte_vie_hero, (barre_x + 65, barre_y + 2))

    # Bordure de la barre
    pygame.draw.rect(ecran, (255, 255, 255), (barre_x, barre_y, barre_largeur, barre_hauteur), 2)

    # ========================================
    # BANDEAU INFÉRIEUR (contrôles)
    # ========================================

    # Fond du bandeau
    bandeau_bas = pygame.Surface((LARGEUR, 50), pygame.SRCALPHA)
    bandeau_bas.fill((0, 0, 0, 200))
    ecran.blit(bandeau_bas, (0, HAUTEUR - 50))

    # Ligne de séparation en haut du bandeau
    pygame.draw.line(ecran, (100, 100, 100), (0, HAUTEUR - 50), (LARGEUR, HAUTEUR - 50), 2)

    # Contrôles en ligne
    x_ctrl = 20
    y_ctrl = HAUTEUR - 35

    # Icône de contrôles
    texte_ctrl = fonte_petite.render("⌨️", True, (200, 200, 200))
    ecran.blit(texte_ctrl, (x_ctrl, y_ctrl))
    x_ctrl += 40

    # ZQSD
    texte_zqsd = fonte_petite.render("ZQSD-Héros", True, (100, 200, 255))
    ecran.blit(texte_zqsd, (x_ctrl, y_ctrl))
    x_ctrl += 150

    # Séparateur
    texte_sep = fonte_petite.render("|", True, (100, 100, 100))
    ecran.blit(texte_sep, (x_ctrl, y_ctrl))
    x_ctrl += 20

    # Tour Canon
    couleur_canon = (150, 200, 255) if argent >= PRIX_TOUR_CANON else (100, 100, 100)
    texte_1 = fonte_petite.render(f"1-Canon ({PRIX_TOUR_CANON}$)", True, couleur_canon)
    ecran.blit(texte_1, (x_ctrl, y_ctrl))
    x_ctrl += 160

    # Séparateur
    ecran.blit(texte_sep, (x_ctrl, y_ctrl))
    x_ctrl += 20

    # Tour Laser
    couleur_laser = (255, 150, 150) if argent >= PRIX_TOUR_LASER else (100, 100, 100)
    texte_2 = fonte_petite.render(f"2-Laser ({PRIX_TOUR_LASER}$)", True, couleur_laser)
    ecran.blit(texte_2, (x_ctrl, y_ctrl))
    x_ctrl += 160

    # Séparateur
    ecran.blit(texte_sep, (x_ctrl, y_ctrl))
    x_ctrl += 20

    # Espace pour vague
    texte_espace = fonte_petite.render("ESPACE-Vague", True, (255, 255, 100))
    ecran.blit(texte_espace, (x_ctrl, y_ctrl))

def dessiner_menu():
    """Dessine l'écran de démarrage"""
    # Fond semi-transparent
    overlay = pygame.Surface((LARGEUR, HAUTEUR), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 220))
    ecran.blit(overlay, (0, 0))

    # Titre
    fonte_titre = pygame.font.Font(None, 96)
    texte_titre = fonte_titre.render("TOWER DEFENSE", True, (255, 215, 0))
    ecran.blit(texte_titre, (LARGEUR // 2 - 350, HAUTEUR // 3 - 50))

    # Sous-titre
    fonte = pygame.font.Font(None, 48)
    texte_start = fonte.render("Appuie sur ESPACE pour commencer", True, (255, 255, 255))
    ecran.blit(texte_start, (LARGEUR // 2 - 320, HAUTEUR // 2))

    # Instructions
    fonte_petite = pygame.font.Font(None, 32)
    instructions = [
        "ZQSD / Fleches - Contrôler le héros",
        "1 - Placer une tour Canon (50$)",
        "2 - Placer une tour Laser (100$)",
        "P - Afficher/Masquer les portées",
        "ESPACE - Démarrer la vague suivante"
    ]

    y_offset = HAUTEUR // 2 + 100
    for instruction in instructions:
        texte = fonte_petite.render(instruction, True, (200, 200, 200))
        ecran.blit(texte, (LARGEUR // 2 - 280, y_offset))
        y_offset += 40

    # Crédits
    texte_credits = fonte_petite.render("Créé avec Pygame | Bon jeu !", True, (150, 150, 150))
    ecran.blit(texte_credits, (LARGEUR // 2 - 180, HAUTEUR - 80))

# ========================================
# BOUCLE PRINCIPALE
# ========================================

# Boucle principale
print("🎮 Jeu prêt !")

en_cours = True
while en_cours:
    # Gestion des événements
    for evenement in pygame.event.get():
        if evenement.type == pygame.QUIT:
            en_cours = False

        if evenement.type == pygame.KEYDOWN:
            # Sortir du menu
            if en_menu and evenement.key == pygame.K_SPACE:
                en_menu = False
                print("🎮 C'est parti !")
                continue

            # Le reste des contrôles (seulement si pas dans le menu)
            if not en_menu:
                # Démarrer une vague
                if evenement.key == pygame.K_SPACE and not vague_en_cours and not game_over:
                    demarrer_vague()

                # Toggle affichage des portées
                if evenement.key == pygame.K_p and not game_over:
                    afficher_portees = not afficher_portees
                    print(f"Affichage des portées: {'ON' if afficher_portees else 'OFF'}")

                # Sélectionner une tour à placer
                if evenement.key == pygame.K_1 and not game_over:
                    mode_placement = True
                    tour_a_placer = 'canon'
                    print(f"Mode placement: Tour Canon (Prix: {PRIX_TOUR_CANON})")

                if evenement.key == pygame.K_2 and not game_over:
                    mode_placement = True
                    tour_a_placer = 'laser'
                    print(f"Mode placement: Tour Laser (Prix: {PRIX_TOUR_LASER})")

                # Annuler le placement
                if evenement.key == pygame.K_ESCAPE:
                    mode_placement = False
                    tour_a_placer = None
                    print("Placement annulé")

            # Redémarrer après Game Over
            if evenement.key == pygame.K_r and game_over:
                # Réinitialiser tout
                liste_monstres.clear()
                liste_tours.clear()
                liste_projectiles.clear()
                liste_effets.clear()
                liste_particules.clear()
                liste_textes_flottants.clear()
                argent = 200
                vie_base = 20
                vague_actuelle = 1
                monstres_par_vague = 5
                vague_en_cours = False
                game_over = False
                kills_total = 0
                en_menu = True  # Retour au menu

                hero.x = LARGEUR // 2
                hero.y = HAUTEUR // 2
                hero.vie = hero.vie_max
                hero.actif = True

                print("🔄 Retour au menu !")

        # Placer une tour avec la souris
        if evenement.type == pygame.MOUSEBUTTONDOWN and mode_placement and not game_over:
            souris_x, souris_y = pygame.mouse.get_pos()

            if verifier_position_valide(souris_x, souris_y):
                if placer_tour(souris_x, souris_y, tour_a_placer):
                    mode_placement = False
                    tour_a_placer = None
            else:
                print("❌ Position invalide !")

    # Dessiner la carte
    dessiner_carte()

    # Si on est dans le menu, afficher le menu et ignorer le reste
    if en_menu:
        dessiner_menu()
        pygame.display.flip()
        horloge.tick(60)
        continue  # Passer à l'itération suivante

    # Si le jeu n'est pas terminé
    if not game_over:
        # Gestion des vagues
        if vague_en_cours:
            if monstres_envoyes < monstres_par_vague:
                generer_monstre()
            verifier_fin_vague()

        # ========== Mettre à jour le héros ==========
        touches = pygame.key.get_pressed()
        hero.mettre_a_jour(touches, liste_monstres, liste_projectiles)
        # ======================================================

        # Déplacer les monstres
        for monstre in liste_monstres[:]:
            monstre.deplacer()

            # Attaquer le héros s'il est proche
            if hero.actif:
                monstre.attaquer_hero(hero)

            # Si le monstre arrive à la sortie
            if monstre.arrive and not monstre.recompense_donnee:
                vie_base -= 1
                monstre.recompense_donnee = True
                print(f"💔 Un monstre est passé ! Vie restante: {vie_base}")

            # Si le monstre meurt, donner l'argent ET créer une explosion
            if not monstre.actif and monstre.vie <= 0 and not monstre.recompense_donnee:
                # Récompense variable selon le monstre
                if monstre.sprite == sprites['monstre_2']:
                    recompense = 15  # Monstre rapide vaut plus
                else:
                    recompense = 10

                # Bonus si vague avancée
                if vague_actuelle > 5:
                    recompense += 5

                argent += recompense
                kills_total += 1
                monstre.recompense_donnee = True
                print(f"💰 +{recompense}$ (Total: {argent}) | Kills: {kills_total}")

                # Créer une explosion
                explosion = Effet(monstre.x, monstre.y, sprites['explosion'], duree=0.4)
                liste_effets.append(explosion)
                if sons_actives:
                    son_explosion.play()

                # Limite maximale de particules actives
                MAX_PARTICULES = 200

                # Dans la mort du monstre, vérifie avant d'ajouter
                if len(liste_particules) < MAX_PARTICULES:
                    for _ in range(random.randint(15, 25)):
                        particule = Particule(monstre.x, monstre.y)
                        liste_particules.append(particule)

                # Texte flottant avec la vraie récompense
                texte_argent = TexteFlottant(
                    monstre.x,
                    monstre.y,
                    f"+{recompense}$",
                    (255, 215, 0)
                )
                liste_textes_flottants.append(texte_argent)

        # Nettoyer les monstres qui ne sont plus utiles
        liste_monstres = [m for m in liste_monstres if m.actif or (not m.actif and not m.recompense_donnee)]

        # Mettre à jour les tours
        for tour in liste_tours:
            tour.mettre_a_jour(liste_monstres, liste_projectiles)

        # Déplacer les projectiles
        for projectile in liste_projectiles:
            projectile.deplacer()

        # Nettoyer les projectiles inactifs
        liste_projectiles = [p for p in liste_projectiles if p.actif]

        # Mettre à jour les effets visuels
        for effet in liste_effets:
            effet.mettre_a_jour()

        # Nettoyer les effets terminés
        liste_effets = [e for e in liste_effets if e.actif]

        # Mettre à jour les particules
        for particule in liste_particules:
            particule.mettre_a_jour()

        # Nettoyer les particules inactives
        liste_particules = [p for p in liste_particules if p.actif]

        # Mettre à jour les textes flottants
        for texte in liste_textes_flottants:
            texte.mettre_a_jour()

        # Nettoyer les textes terminés
        liste_textes_flottants = [t for t in liste_textes_flottants if t.actif]

        # Vérifier Game Over
        if vie_base <= 0 or not hero.actif:
            game_over = True
            if not hero.actif:
                print("💀 Le héros est mort !")
            else:
                print("💀 GAME OVER !")

    # Dessiner tous les éléments
    for monstre in liste_monstres:
        monstre.dessiner(ecran)

    for tour in liste_tours:
        tour.dessiner(ecran)

    for projectile in liste_projectiles:
        projectile.dessiner(ecran)

    # Dessiner les effets visuels
    for effet in liste_effets:
        effet.dessiner(ecran)

    # Dessiner les particules
    for particule in liste_particules:
        particule.dessiner(ecran)

    # Dessiner les textes flottants
    for texte in liste_textes_flottants:
        texte.dessiner(ecran)

    # Dessiner le héros
    hero.dessiner(ecran)

    # Points d'entrée/sortie
    if 'entree' in points:
        pygame.draw.circle(ecran, (0, 255, 0),
                         (int(points['entree'][0]), int(points['entree'][1])), 5)
    if 'sortie' in points:
        pygame.draw.circle(ecran, (255, 0, 0),
                         (int(points['sortie'][0]), int(points['sortie'][1])), 5)

    # ========================================
    # INTERFACE UTILISATEUR
    # ========================================

    fonte = pygame.font.Font(None, 36)
    fonte_petite = pygame.font.Font(None, 28)

    # Dessiner le panneau d'interface stylisé
    if not game_over:
        dessiner_interface()

    # Mode placement
    if mode_placement and not game_over:
        souris_x, souris_y = pygame.mouse.get_pos()

        apercu = sprites['tour_canon'] if tour_a_placer == 'canon' else sprites['tour_laser']
        valide = verifier_position_valide(souris_x, souris_y)
        couleur = (0, 255, 0, 100) if valide else (255, 0, 0, 100)

        apercu_surface = apercu.copy()
        apercu_surface.set_alpha(150)
        rect = apercu_surface.get_rect(center=(souris_x, souris_y))
        ecran.blit(apercu_surface, rect)

        portee = 150 if tour_a_placer == 'canon' else 200
        surface_portee = pygame.Surface((portee * 2, portee * 2), pygame.SRCALPHA)
        pygame.draw.circle(surface_portee, couleur, (portee, portee), portee, 2)
        ecran.blit(surface_portee, (souris_x - portee, souris_y - portee))

    # Message entre les vagues
    if not vague_en_cours and not game_over:
        # Panneau central
        panneau_vague = pygame.Surface((700, 120), pygame.SRCALPHA)
        panneau_vague.fill((0, 0, 0, 200))
        ecran.blit(panneau_vague, (LARGEUR // 2 - 350, HAUTEUR // 2 - 60))
        pygame.draw.rect(ecran, (255, 255, 100), (LARGEUR // 2 - 350, HAUTEUR // 2 - 60, 700, 120), 3)

        fonte_vague = pygame.font.Font(None, 48)
        texte_attente = fonte_vague.render("Prêt pour la prochaine vague ?", True, (255, 255, 0))
        ecran.blit(texte_attente, (LARGEUR // 2 - 280, HAUTEUR // 2 - 40))

        texte_espace = fonte.render("Appuie sur ESPACE", True, (200, 200, 200))
        ecran.blit(texte_espace, (LARGEUR // 2 - 150, HAUTEUR // 2 + 20))

    # Écran Game Over
    if game_over:
        # Fond semi-transparent
        overlay = pygame.Surface((LARGEUR, HAUTEUR), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        ecran.blit(overlay, (0, 0))

        # Textes
        fonte_grande = pygame.font.Font(None, 72)
        texte_game_over = fonte_grande.render("GAME OVER", True, (255, 0, 0))
        ecran.blit(texte_game_over, (LARGEUR // 2 - 200, HAUTEUR // 2 - 150))

        # Plus de statistiques
        fonte = pygame.font.Font(None, 36)

        texte_vague = fonte.render(f"Vague atteinte: {vague_actuelle - 1}", True, (255, 255, 255))
        ecran.blit(texte_vague, (LARGEUR // 2 - 180, HAUTEUR // 2 - 50))

        texte_kills = fonte.render(f"Monstres éliminés: {kills_total}", True, (255, 215, 0))
        ecran.blit(texte_kills, (LARGEUR // 2 - 180, HAUTEUR // 2))

        texte_tours = fonte.render(f"Tours construites: {len(liste_tours)}", True, (100, 200, 255))
        ecran.blit(texte_tours, (LARGEUR // 2 - 180, HAUTEUR // 2 + 50))

        # Score calculé
        score_final = (vague_actuelle - 1) * 100 + kills_total * 10 + len(liste_tours) * 5
        texte_score = fonte.render(f"Score final: {score_final}", True, (255, 150, 255))
        ecran.blit(texte_score, (LARGEUR // 2 - 180, HAUTEUR // 2 + 100))

        texte_rejouer = fonte.render("Appuie sur R pour rejouer", True, (255, 255, 0))
        ecran.blit(texte_rejouer, (LARGEUR // 2 - 200, HAUTEUR // 2 + 170))

    pygame.display.flip()
    horloge.tick(60)

pygame.quit()
print("👋 Merci d'avoir joué !")
