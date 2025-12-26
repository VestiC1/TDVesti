import pygame
import pytmx
import os
import time

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
        self.recompense_donnee = False  # NOUVEAU : éviter de donner plusieurs fois l'argent
    
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
    
    def mettre_a_jour(self, liste_monstres, liste_projectiles):
        """Met à jour la tour"""
        self.cible = self.trouver_cible(liste_monstres)
        if self.cible:
            self.tirer(liste_projectiles)
    
    def dessiner(self, ecran):
        """Affiche la tour et son rayon de portée"""
        rect = self.sprite.get_rect(center=(int(self.x), int(self.y)))
        ecran.blit(self.sprite, rect)
        
        surface_portee = pygame.Surface((self.portee * 2, self.portee * 2), pygame.SRCALPHA)
        pygame.draw.circle(surface_portee, (255, 255, 255, 30), 
                          (self.portee, self.portee), self.portee)
        ecran.blit(surface_portee, (self.x - self.portee, self.y - self.portee))

# ========================================
# VARIABLES GLOBALES DU JEU
# ========================================

# Listes des entités
liste_monstres = []
liste_tours = []
liste_projectiles = []

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

def generer_monstre():
    """Génère un nouveau monstre"""
    global monstres_envoyes, derniere_apparition
    
    temps_actuel = time.time()
    
    if temps_actuel - derniere_apparition >= delai_entre_monstres:
        if vague_actuelle <= 2:
            sprite = sprites['monstre_1']
            vitesse = 2
            vie = 100
        else:
            if monstres_envoyes % 3 == 0:
                sprite = sprites['monstre_2']
                vitesse = 4
                vie = 150
            else:
                sprite = sprites['monstre_1']
                vitesse = 2
                vie = 100 + (vague_actuelle * 10)
        
        nouveau_monstre = Monstre(chemin_monstres, sprite, vitesse, vie)
        liste_monstres.append(nouveau_monstre)
        
        monstres_envoyes += 1
        derniere_apparition = temps_actuel
        print(f"  Monstre {monstres_envoyes}/{monstres_par_vague} envoyé")

def verifier_fin_vague():
    """Vérifie si la vague est terminée"""
    global vague_en_cours, vague_actuelle, monstres_par_vague
    
    if monstres_envoyes >= monstres_par_vague:
        # Compter seulement les monstres encore en jeu
        monstres_actifs = [m for m in liste_monstres if m.actif and not m.arrive]
        if len(monstres_actifs) == 0:
            vague_en_cours = False
            vague_actuelle += 1
            monstres_par_vague += 2
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

# ========================================
# BOUCLE PRINCIPALE
# ========================================

print("🎮 Jeu prêt ! Appuie sur ESPACE pour lancer la première vague")

en_cours = True
while en_cours:
    # Gestion des événements
    for evenement in pygame.event.get():
        if evenement.type == pygame.QUIT:
            en_cours = False
        
        if evenement.type == pygame.KEYDOWN:
            # Démarrer une vague
            if evenement.key == pygame.K_SPACE and not vague_en_cours and not game_over:
                demarrer_vague()
            
            # Sélectionner une tour à placer
            elif evenement.key == pygame.K_1 and not game_over:
                mode_placement = True
                tour_a_placer = 'canon'
                print(f"Mode placement: Tour Canon (Prix: {PRIX_TOUR_CANON})")
            
            elif evenement.key == pygame.K_2 and not game_over:
                mode_placement = True
                tour_a_placer = 'laser'
                print(f"Mode placement: Tour Laser (Prix: {PRIX_TOUR_LASER})")
            
            # Annuler le placement
            elif evenement.key == pygame.K_ESCAPE:
                mode_placement = False
                tour_a_placer = None
                print("Placement annulé")
            
            # Redémarrer après Game Over
            elif evenement.key == pygame.K_r and game_over:
                # Réinitialiser tout
                liste_monstres.clear()
                liste_tours.clear()
                liste_projectiles.clear()
                argent = 200
                vie_base = 20
                vague_actuelle = 1
                monstres_par_vague = 5
                vague_en_cours = False
                game_over = False
                print("🔄 Jeu redémarré !")
        
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
    
    # Si le jeu n'est pas terminé
    if not game_over:
        # Gestion des vagues
        if vague_en_cours:
            if monstres_envoyes < monstres_par_vague:
                generer_monstre()
            verifier_fin_vague()
        
        # Déplacer les monstres
        for monstre in liste_monstres[:]:  # Copie de la liste pour itérer en sécurité
            monstre.deplacer()
            
            # Si le monstre arrive à la sortie
            if monstre.arrive and not monstre.recompense_donnee:
                vie_base -= 1
                monstre.recompense_donnee = True
                print(f"💔 Un monstre est passé ! Vie restante: {vie_base}")
            
            # Si le monstre meurt, donner l'argent UNE SEULE FOIS
            if not monstre.actif and monstre.vie <= 0 and not monstre.recompense_donnee:
                argent += 10
                monstre.recompense_donnee = True
                print(f"💰 +10$ (Total: {argent})")
        
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
        
        # Vérifier Game Over
        if vie_base <= 0:
            game_over = True
            print("💀 GAME OVER !")
    
    # Dessiner tous les éléments
    for monstre in liste_monstres:
        monstre.dessiner(ecran)
    
    for tour in liste_tours:
        tour.dessiner(ecran)
    
    for projectile in liste_projectiles:
        projectile.dessiner(ecran)
    
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
    
    # Informations de jeu
    texte_vague = fonte.render(f"Vague: {vague_actuelle}", True, (255, 255, 255))
    ecran.blit(texte_vague, (10, 10))
    
    texte_argent = fonte.render(f"Argent: {argent}$", True, (255, 215, 0))
    ecran.blit(texte_argent, (10, 50))
    
    texte_vie = fonte.render(f"Vie: {vie_base}", True, (255, 0, 0))
    ecran.blit(texte_vie, (10, 90))
    
    # Aide aux touches
    if not game_over:
        y_offset = HAUTEUR - 150
        texte_touches = fonte_petite.render("Touches:", True, (255, 255, 255))
        ecran.blit(texte_touches, (10, y_offset))
        
        texte_1 = fonte_petite.render(f"1 - Tour Canon ({PRIX_TOUR_CANON}$)", True, (150, 200, 255))
        ecran.blit(texte_1, (10, y_offset + 30))
        
        texte_2 = fonte_petite.render(f"2 - Tour Laser ({PRIX_TOUR_LASER}$)", True, (255, 150, 150))
        ecran.blit(texte_2, (10, y_offset + 60))
        
        texte_espace = fonte_petite.render("ESPACE - Nouvelle vague", True, (200, 200, 200))
        ecran.blit(texte_espace, (10, y_offset + 90))
    
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
        texte_attente = fonte.render("Appuie sur ESPACE pour la prochaine vague", True, (255, 255, 0))
        ecran.blit(texte_attente, (LARGEUR // 2 - 300, HAUTEUR // 2))
    
    # Écran Game Over
    if game_over:
        # Fond semi-transparent
        overlay = pygame.Surface((LARGEUR, HAUTEUR), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        ecran.blit(overlay, (0, 0))
        
        # Textes
        fonte_grande = pygame.font.Font(None, 72)
        texte_game_over = fonte_grande.render("GAME OVER", True, (255, 0, 0))
        ecran.blit(texte_game_over, (LARGEUR // 2 - 200, HAUTEUR // 2 - 50))
        
        texte_score = fonte.render(f"Tu as survécu jusqu'à la vague {vague_actuelle - 1}", True, (255, 255, 255))
        ecran.blit(texte_score, (LARGEUR // 2 - 250, HAUTEUR // 2 + 50))
        
        texte_rejouer = fonte.render("Appuie sur R pour rejouer", True, (255, 255, 0))
        ecran.blit(texte_rejouer, (LARGEUR // 2 - 200, HAUTEUR // 2 + 100))
    
    pygame.display.flip()
    horloge.tick(60)

pygame.quit()
print("👋 Merci d'avoir joué !")