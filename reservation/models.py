from django.db import models
from django.contrib.auth.models import AbstractUser
from datetime import datetime
# Create your models here

#--------TABLE UTILISATEUR-------------
class User(AbstractUser):
    is_cooperative = models.BooleanField(default=False)
    is_administrateur = models.BooleanField(default=False)
    is_utilisateur = models.BooleanField(default=True)

class Utilisateur(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    nom = models.CharField(max_length=100)
    prenom = models.CharField(max_length=100)
    adresse = models.CharField(max_length=100)
    email = models.EmailField()
    telephone = models.CharField(max_length=10)
    cin = models.CharField(max_length=100)
    date_naissance = models.DateField()
    lieux_naissance = models.CharField(max_length=50)

    def __str__(self):
        return self.nom

#--------------TABLE COOPERATIVE-----------

class Cooperative(models.Model):
    utilisateur = models.OneToOneField(User, on_delete=models.CASCADE)
    nom = models.CharField(max_length=100)
    adresse = models.CharField(max_length=255)
    telephone = models.CharField(max_length=10)
    email = models.EmailField()
    photo = models.ImageField(upload_to='media/', null=True, blank=True)


    def __str__(self):
        return self.nom

#-----------------TABLE CATEGORIE------------------------
class Categorie(models.Model):
    nom = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.nom
    
#----------------TABLE VOITURE-----------------------
class Voiture(models.Model):
    cooperative = models.ForeignKey(Cooperative, on_delete=models.CASCADE)
    categorie = models.ForeignKey(
    Categorie,
    related_name='voitures',
    on_delete=models.CASCADE,
    null=True, blank=True,
)
    marque = models.CharField(max_length=100)
    place = models.IntegerField()
    matricule = models.CharField(max_length=50, unique=True)
    photo = models.ImageField(upload_to='images/', null=True, blank=True)
    

    def __str__(self):
        return f"{self.marque} {self.place} ({self.matricule})"

#--------------------TABLE CHAUFFEUR---------------------------

class Chauffeur(models.Model):
    voiture = models.ForeignKey(Voiture, on_delete=models.CASCADE, related_name='chauffeurs')
    cooperative = models.ForeignKey(Cooperative, on_delete=models.CASCADE, related_name='chauffeurs')
    nom = models.CharField(max_length=100)
    prenom = models.CharField(max_length=100)
    telephone = models.CharField(max_length=20)
    email = models.EmailField()
    cin = models.CharField(max_length=100)
    date_naissance = models.DateField()
    lieu_naissance = models.CharField(max_length=50)
    photo = models.ImageField(upload_to='images/', null=True, blank=True, default="default.png")

    def __str__(self):
        return f"{self.prenom} {self.nom}"

#-------------------TABLE TRAJET------------------------------
class Trajet(models.Model):
    voiture = models.ForeignKey(Voiture, on_delete=models.CASCADE)
    cooperative = models.ForeignKey(Cooperative, on_delete=models.CASCADE, related_name='trajets')
    date_depart = models.DateField()
    heure_depart = models.TimeField()
    lieu_depart = models.CharField(max_length=100)
    lieu_destination = models.CharField(max_length=100)
    frais = models.DecimalField(max_digits=10, decimal_places=2)


    def __str__(self):
        return f"{self.voiture} - {self.lieu_depart} vers {self.lieu_destination} le {self.date_depart}" 
    
    @property
    def datetime_depart(self):
        return datetime.combine(self.date_depart, self.heure_depart)
    
    @staticmethod
    def dernier_trajet_voiture(voiture):
        return Trajet.objects.filter(voiture=voiture).order_by("-date_depart", "-heure_depart").first()
    
#------------------TABLE RESERVATION----------------
class Reservation(models.Model):
    utilisateur = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    trajet = models.ForeignKey(Trajet, on_delete=models.CASCADE)
    nb_place_reserve = models.PositiveBigIntegerField()
    date_reservation = models.DateTimeField(auto_now_add=True)
    places_json = models.TextField(default='[]')
    montant_total = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    # Champs pour réservation "sur place"
    nom_client = models.CharField(max_length=100, null=True, blank=True)
    prenom_client = models.CharField(max_length=100, null=True, blank=True)
    telephone_client = models.CharField(max_length=15, null=True, blank=True)

    def __str__(self):
        if self.utilisateur:
            return f"Réservation par {self.utilisateur.username} pour {self.trajet}"
        return f"Réservation sur place ({self.nom_client}) pour {self.trajet}"

#--------TABLE MANIFOLD--------------

class Manifold(models.Model):
    trajet = models.OneToOneField(Trajet, on_delete=models.CASCADE)  # un trajet = un manifold
    date_creation = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Manifold pour {self.trajet}"

#----------TABLE PASSAGER-----------------

class Passager(models.Model):
    manifold = models.ForeignKey(Manifold, on_delete=models.CASCADE, related_name="passagers")
    nom = models.CharField(max_length=100)
    prenom = models.CharField(max_length=100)
    date_naissance = models.DateField(null=True, blank=True)
    cin = models.CharField(max_length=50, null=True, blank=True)
    numero_famille = models.CharField(max_length=15, null=True, blank=True)
    numero_utilisateur = models.CharField(max_length=15, null=True, blank=True)
    numero_places = models.PositiveIntegerField(default=1)  # nombre de places réservées par ce passager

    def __str__(self):
        return f"{self.nom} {self.prenom} - {self.manifold.trajet}"
