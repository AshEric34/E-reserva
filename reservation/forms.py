from django import forms
from .models import Voiture,Utilisateur,Cooperative,Chauffeur,Trajet,Categorie,Manifold,Passager
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.forms import UserChangeForm
from django.contrib.auth.models import User
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
import datetime
import re
from django.contrib.auth.forms import PasswordResetForm, SetPasswordForm


User = get_user_model()


class UserForm(UserCreationForm):
    class Meta:
        model = User
        fields = [
            'username',
            'password1',
            'password2',
        ]

class UtilisateurForm(forms.ModelForm):
    class Meta:
        model = Utilisateur
        fields = [
            'nom',
            'prenom',
            'adresse',
            'email',
            'telephone',
            'cin',
            'date_naissance',
            'lieux_naissance'
        ]
        widgets = {
            'date_naissance': forms.DateInput(attrs={'type': 'date'}),
        }
    def clean_email(self):
        email = self.cleaned_data.get("email")
        if not email or "@" not in email:
            raise forms.ValidationError("Veuillez entrer un email valide.")
        return email

    def clean_cin(self):
        cin = self.cleaned_data.get("cin")

        if not cin.isdigit() or len(cin) != 12:
            raise forms.ValidationError("Le CIN doit contenir exactement 12 chiffres.")

        qs = Chauffeur.objects.filter(cin=cin)
        if self.instance.pk:  # si on est en modification
            qs = qs.exclude(pk=self.instance.pk)

        if qs.exists():
            raise forms.ValidationError("Ce CIN existe déjà.")
        
        return cin
    
    def clean_telephone(self):
        telephone = self.cleaned_data.get("telephone")

    # Vérifier que ce sont uniquement des chiffres
        if not telephone.isdigit():
            raise forms.ValidationError("Le numéro de téléphone doit contenir uniquement des chiffres.")

    # Vérifier la longueur
        if len(telephone) != 10:
            raise forms.ValidationError("Le numéro de téléphone doit contenir exactement 10 chiffres.")

    # Vérifier le préfixe autorisé
        if not (telephone.startswith("032") or 
                telephone.startswith("034") or 
                telephone.startswith("033") or 
                telephone.startswith("038") or 
                telephone.startswith("039")):
            raise forms.ValidationError("Le numéro doit commencer par 032, 034, 033, 038 ou 039.")

        return telephone

class CooperativeUserUpdateForm(UserChangeForm):
    """Formulaire pour modifier un utilisateur coopérative sans changer le mot de passe"""
    
    class Meta:
        model = User
        fields = ['username', 'email']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Rendre le champ username en lecture seule
        self.fields['username'].widget.attrs.update({
            'readonly': True,
            'class': 'form-control readonly'
        })
        self.fields['email'].widget.attrs.update({
            'class': 'form-control'
        })
        # Supprimer le champ password
        if 'password' in self.fields:
            del self.fields['password']


class CooperativeUserForm(UserCreationForm):
    class Meta:
        model = User
        fields = ['username', 'password1', 'password2']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Ajouter des classes CSS
        for field_name, field in self.fields.items():
            field.widget.attrs.update({
                'class': 'form-control',
                'placeholder': f'Entrez {field.label.lower()}'
            })

class CooperativeForm(forms.ModelForm):
    class Meta:
        model = Cooperative
        fields = ['nom', 'adresse', 'telephone', 'email', 'photo']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Ajouter des classes CSS
        for field_name, field in self.fields.items():
            field.widget.attrs.update({
                'class': 'form-control',
                'placeholder': f'Entrez {field.label.lower()}'
            })
class VoitureForm(forms.ModelForm):
    class Meta:
        model = Voiture
        fields = ["marque", "place", "matricule", "cooperative", "categorie", "photo"]

    def __init__(self, *args, **kwargs):
        cooperative = kwargs.pop('cooperative', None)
        super().__init__(*args, **kwargs)

        # Toujours désactiver le champ cooperative
        self.fields['cooperative'].disabled = True  

        # Si ajout (cooperative passée depuis la vue)
        if cooperative:
            self.fields['cooperative'].initial = cooperative

        # Si modification (instance existe déjà)
        elif self.instance and self.instance.pk:
            self.fields['cooperative'].initial = self.instance.cooperative

    def clean_numero_plaque(self):
        matricule = self.cleaned_data.get("matricule")
        qs = Voiture.objects.filter(matricule=matricule)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)

        if qs.exists():
            raise forms.ValidationError("Cette plaque d'immatriculation existe déjà.")
        return matricule


class ChauffeurForm(forms.ModelForm):
    class Meta:
        model = Chauffeur
        fields = ["nom", "prenom", "telephone", "email", "cin", "date_naissance", "lieu_naissance", "photo", "voiture", "cooperative"]
        widgets = {
            'date_naissance': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        cooperative = kwargs.pop('cooperative', None)
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

        # Toujours désactiver la coopérative
        self.fields['cooperative'].disabled = True  

        if user and hasattr(user, "cooperative"):
            # Récupérer la coopérative de l'utilisateur connecté
            cooperative_user = Cooperative.objects.get(utilisateur=user)
            
            # 1. Filtrer et définir la coopérative d'abord
            self.fields["cooperative"].queryset = Cooperative.objects.filter(pk=cooperative_user.pk)
            self.fields["cooperative"].initial = cooperative_user
            
            # 2. Ensuite filtrer les voitures de cette coopérative
            self.fields["voiture"].queryset = Voiture.objects.filter(cooperative=cooperative_user)

        # Si une coopérative est passée en paramètre (pour override)
        elif cooperative:
            self.fields['cooperative'].initial = cooperative
            # Filtrer aussi les voitures pour cette coopérative
            self.fields["voiture"].queryset = Voiture.objects.filter(cooperative=cooperative)

        # Si c'est une modification d'instance existante
        elif self.instance and self.instance.pk:
            self.fields['cooperative'].initial = self.instance.cooperative
            # Filtrer les voitures pour la coopérative de l'instance
            self.fields["voiture"].queryset = Voiture.objects.filter(cooperative=self.instance.cooperative)

    def clean_email(self):
        email = self.cleaned_data.get("email")
        if not email or "@" not in email:
            raise forms.ValidationError("Veuillez entrer un email valide.")
        return email

    def clean_cin(self):
        cin = self.cleaned_data.get("cin")

        if not cin.isdigit() or len(cin) != 12:
            raise forms.ValidationError("Le CIN doit contenir exactement 12 chiffres.")

        qs = Chauffeur.objects.filter(cin=cin)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)

        if qs.exists():
            raise forms.ValidationError("Ce CIN existe déjà.")

        return cin

class TrajetForm(forms.ModelForm):
    dernier_trajet = forms.CharField(
        required=False,
        disabled=True,
        label="Dernier trajet de cette voiture"
    )

    class Meta:
        model = Trajet
        fields = '__all__'
        widgets = {
            'date_depart': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

        if user and hasattr(user, "cooperative"):
            cooperative = Cooperative.objects.get(utilisateur=user)

            #  Filtrer uniquement les voitures de la coopérative connectée
            self.fields["voiture"].queryset = Voiture.objects.filter(cooperative=cooperative)

            #  Fixer la coopérative automatiquement (un seul choix possible)
            self.fields["cooperative"].queryset = Cooperative.objects.filter(pk=cooperative.pk)
            self.fields["cooperative"].initial = cooperative
            self.fields["cooperative"].disabled = True # empêche de modifier

        # Dernier trajet si voiture déjà choisie
        if "voiture" in self.data:
            try:
                voiture_id = int(self.data.get("voiture"))
                voiture = Voiture.objects.get(pk=voiture_id)
                dernier = Trajet.dernier_trajet_voiture(voiture)
                if dernier:
                    self.fields["dernier_trajet"].initial = f"{dernier.date_depart} {dernier.heure_depart}"
                else:
                    self.fields["dernier_trajet"].initial = "Aucun trajet trouvé"
            except:
                self.fields["dernier_trajet"].initial = ""
        elif self.instance.pk:
            dernier = Trajet.dernier_trajet_voiture(self.instance.voiture)
            if dernier:
                self.fields["dernier_trajet"].initial = f"{dernier.date_depart} {dernier.heure_depart}"


class CategorieForm(forms.ModelForm):
    class Meta:
        model = Categorie
        fields = ['nom']

class PassagerForm(forms.ModelForm):
    class Meta:
        model = Passager
        fields = ['nom', 'prenom', 'date_naissance', 'cin', 'numero_famille', 'numero_utilisateur', 'numero_places']
        widgets = {
            'date_naissance': forms.DateInput(attrs={'type': 'date'}),
            'numero_places': forms.NumberInput(attrs={'min': 1}),
        }
    
    cin = forms.CharField(required=False, label="CIN")
    
    def __init__(self, *args, **kwargs):
        self.trajet = kwargs.pop('trajet', None)
        self.manifold = kwargs.pop('manifold', None)
        super().__init__(*args, **kwargs)
    
    def clean_numero_places(self):
        numero_places = self.cleaned_data.get("numero_places")
        
        if not self.trajet:
            raise ValidationError("Erreur: trajet non spécifié.")
        
        # Vérification 1: Le numéro de place ne dépasse pas le nombre total de places
        if numero_places > self.trajet.voiture.place:
            raise ValidationError(
                f"Numéro de place invalide. Le véhicule a seulement {self.trajet.voiture.place} place(s)."
            )
        
        # Vérification 2: Le numéro de place n'est pas déjà attribué
        if self.manifold:
            place_deja_utilisee = self.manifold.passagers.filter(
                numero_places=numero_places
            ).exists()
            
            if place_deja_utilisee:
                raise ValidationError(
                    f"Le numéro de place {numero_places} est déjà attribué à un autre passager."
                )
        
        # Vérification 3: Le numéro de place doit être positif
        if numero_places <= 0:
            raise ValidationError("Le numéro de place doit être supérieur à 0.")
        
        return numero_places
    
    def clean_cin(self):
        cin = self.cleaned_data.get("cin")
        
        if cin:
            if not cin.isdigit() or len(cin) != 12:
                raise ValidationError("Le CIN doit contenir exactement 12 chiffres.")
        return cin
    
    def clean_telephone(self):
        telephone = self.cleaned_data.get("telephone")
        
        if telephone:
            # Vérifier que ce sont uniquement des chiffres
            if not telephone.isdigit():
                raise ValidationError("Le numéro de téléphone doit contenir uniquement des chiffres.")

            # Vérifier la longueur
            if len(telephone) != 10:
                raise ValidationError("Le numéro de téléphone doit contenir exactement 10 chiffres.")

            # Vérifier le préfixe autorisé
            if not (telephone.startswith("032") or 
                    telephone.startswith("034") or 
                    telephone.startswith("033") or 
                    telephone.startswith("038") or 
                    telephone.startswith("039")):
                raise ValidationError("Veuillez entrer un numéro de téléphone valide!")

        return telephone
class CustomPasswordResetForm(PasswordResetForm):
    email = forms.EmailField(
        label='Email',
        max_length=254,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Votre adresse email',
            'autocomplete': 'email'
        })
    )
    
    def clean_email(self):
        email = self.cleaned_data['email']
        if not User.objects.filter(email__iexact=email, is_active=True).exists():
            raise forms.ValidationError("Aucun utilisateur actif avec cette adresse email.")
        return email

class CustomSetPasswordForm(SetPasswordForm):
    new_password1 = forms.CharField(
        label="Nouveau mot de passe",
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'autocomplete': 'new-password'
        }),
        strip=False,
    )
    new_password2 = forms.CharField(
        label="Confirmation du mot de passe",
        strip=False,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'autocomplete': 'new-password'
        }),
    )