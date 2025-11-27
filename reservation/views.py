from .models import Voiture,Chauffeur,Trajet,Reservation,Cooperative,User,Utilisateur,Manifold
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.db.models import Q
import stripe
from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.urls import reverse
from reportlab.lib.utils import ImageReader
from django.db.models import Sum
from reportlab.lib.pagesizes import A6
import io
import json
from .forms import VoitureForm, UserForm, UtilisateurForm, CooperativeUserForm, CooperativeForm,CooperativeUserUpdateForm, ChauffeurForm, TrajetForm,CategorieForm,PassagerForm
from django.http import HttpResponse
from reportlab.pdfgen import canvas
from django.template.loader import render_to_string
from django.template.loader import get_template
from xhtml2pdf import pisa
import base64
import qrcode
from io import BytesIO
import qrcode
from django.utils import timezone
from datetime import datetime, timedelta


from django.contrib.auth import authenticate, login
from django.shortcuts import render, redirect
from django.contrib import messages



#--------------------------CONNEXION ET INSCRIPTION-----------------------------------
def accueil(request):
    return render(request, 'base.html')

def connexion(request):
    error = ''
    # Si l'utilisateur est déjà connecté, 
    if request.user.is_authenticated:
        if request.user.is_cooperative:
            return redirect('koperative')
        elif hasattr(request.user, 'is_administrateur') and request.user.is_administrateur:
            return redirect('administrateur')
        else:
            return redirect('utilisateurs')
    
    if request.method == "POST":
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        if username and password:  # Vérifier que les champs ne sont pas vides
            user = authenticate(request, username=username, password=password)
            
            if user is not None:
                # EMPÊCHER LES ADMINS DE SE CONNECTER ICI
                if hasattr(user, 'role') and user.role == 'admin':
                    error = 'Nom d\'utilisateur ou mot de passe invalide'
                elif hasattr(user, 'is_administrateur') and user.is_administrateur:
                    error = 'Nom d\'utilisateur ou mot de passe invalide'
                else:
                    login(request, user)

                    # Redirection vers la page demandée avant la connexion
                    next_url = request.GET.get('next')
                    if next_url:
                        return redirect(next_url)

                    # Sinon, redirection selon le type d'utilisateur
                    if user.is_cooperative:
                        return redirect('koperative')
                    else:
                        return redirect('utilisateurs')
            else:
                error = 'Nom d\'utilisateur ou mot de passe invalide'
        else:
            error = 'Veuillez remplir tous les champs'
    
    return render(request, 'connexion.html', {'error': error})
def login_admin(request):
    error = ''
    
    # Si l'admin est déjà connecté, rediriger
    if request.user.is_authenticated:
        if (hasattr(request.user, 'role') and request.user.role == 'admin') or \
           (hasattr(request.user, 'is_administrateur') and request.user.is_administrateur):
            return redirect('administrateur')
    
    if request.method == "POST":
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        if username and password:
            user = authenticate(request, username=username, password=password)
            
            if user is not None:
                # VÉRIFIER SI C'EST BIEN UN ADMIN
                if (hasattr(user, 'role') and user.role == 'admin') or \
                   (hasattr(user, 'is_administrateur') and user.is_administrateur):
                    login(request, user)
                    return redirect('administrateur')
                else:
                    error = "Accès refusé"
            else:
                error = "Nom d'utilisateur ou mot de passe invalide"
        else:
            error = 'Veuillez remplir tous les champs'
    
    return render(request, 'login_admin.html', {'error': error})

def register(request):
    if request.method == 'POST':
        user_form = UserForm(request.POST)
        utilisateur_form = UtilisateurForm(request.POST)
        
        if user_form.is_valid() and utilisateur_form.is_valid():
            # Sauvegarder l'utilisateur
            user = user_form.save()
            user.is_utilisateur = True
            user.save()
            
            # Sauvegarder le profil utilisateur sans committer pour l'instant
            utilisateur = utilisateur_form.save(commit=False)
            utilisateur.user = user
            utilisateur.save()
            
            # Connecter l'utilisateur
            login(request, user)

            messages.success(request, 'Votre inscription sur E-reserva est réussie !')
            
            # Rediriger vers la page de succès
            return redirect('accueil')
    else:
        user_form = UserForm()
        utilisateur_form = UtilisateurForm()
    
    return render(request, 'inscription.html', {
        'user_form': user_form,
        'utilisateur_form': utilisateur_form
    })

def deconnexion(request):
    logout(request)
    return redirect('accueil')

#----------------ACCUEIL DE CHAQUE PAGE------------------------
@login_required(login_url='/connexion/')
def homeAdministrateur(request):
    # Déterminer quelle section afficher
    active_section = request.GET.get('section', None)
    active_list = request.GET.get('list', None)
    
    # ========== TOUJOURS CHARGER LES STATISTIQUES ==========
    total_cooperatives = Cooperative.objects.count()
    new_cooperatives_this_week = Cooperative.objects.filter(
        utilisateur__date_joined__gte=timezone.now() - timedelta(days=7)
    ).count()

    total_users = User.objects.filter(is_utilisateur=True).count()
    new_users_this_week = User.objects.filter(
        date_joined__gte=timezone.now() - timedelta(days=7),
        is_utilisateur=True
    ).count()

    total_chauffeurs = Chauffeur.objects.count()
    new_chauffeurs_this_week = Chauffeur.objects.filter(
        id__in=Chauffeur.objects.filter(
            voiture__trajet__date_depart__gte=timezone.now().date() - timedelta(days=7)
        ).values('id')
    ).count()

    total_voitures = Voiture.objects.count()
    new_voitures_this_week = Voiture.objects.filter(
        id__in=Voiture.objects.filter(
            trajet__date_depart__gte=timezone.now().date() - timedelta(days=7)
        ).values('id')
    ).count()

    # Données pour les listes
    utilisateurs = None
    cooperatives = None
    chauffeurs = None
    voitures = None
    
    if active_list == 'users':
        utilisateurs = User.objects.filter(is_utilisateur=True).select_related('utilisateur')
    elif active_list == 'cooperatives':
        cooperatives = Cooperative.objects.all().select_related('utilisateur')
    elif active_list == 'chauffeurs':
        chauffeurs = Chauffeur.objects.all().select_related('cooperative', 'voiture')
    elif active_list == 'voitures':
        voitures = Voiture.objects.all().select_related('cooperative', 'categorie')

    # Activité récente (seulement si aucune liste active et pas de formulaire)
    recent_activity = None
    if not active_list and not active_section:
        recent_activity = Reservation.objects.select_related(
            'trajet', 'utilisateur'
        ).order_by('-date_reservation')[:5]

    # Initialiser le contexte avec TOUJOURS les statistiques
    context = {
        'coop_stats': {
            'total': total_cooperatives,
            'new_this_week': new_cooperatives_this_week,
        },
        'user_stats': {
            'total': total_users,
            'new_this_week': new_users_this_week,
        },
        'chauffeur_stats': {
            'total': total_chauffeurs,
            'new_this_week': new_chauffeurs_this_week,
        },
        'voiture_stats': {
            'total': total_voitures,
            'new_this_week': new_voitures_this_week,
        },
        'recent_activity': recent_activity,
        'active_section': active_section,
        'active_list': active_list,
        'utilisateurs': utilisateurs,
        'cooperatives': cooperatives,
        'chauffeurs': chauffeurs,
        'voitures': voitures,
    }
    
    # Si c'est une requête GET pour afficher le formulaire d'ajout
    if active_section == 'ajouter_cooperative' and request.method == 'GET':
        user_form = CooperativeUserForm(prefix='user')
        coop_form = CooperativeForm(prefix='coop')
        context.update({
            'user_form': user_form,
            'coop_form': coop_form,
            'action': 'ajouter',
            'cooperative': None
        })
    
    return render(request, 'administrateur/home.html', context)

@login_required(login_url='/connexion/')
def ajouter_cooperative(request):
    # Charger les statistiques pour le contexte
    total_cooperatives = Cooperative.objects.count()
    total_users = User.objects.filter(is_utilisateur=True).count()
    total_chauffeurs = Chauffeur.objects.count()
    total_voitures = Voiture.objects.count()
    
    if request.method == 'POST':
        user_form = CooperativeUserForm(request.POST, prefix='user')
        coop_form = CooperativeForm(request.POST, request.FILES, prefix='coop')
        
        print("=== DEBUG AJOUT COOPERATIVE ===")
        print("POST data:", dict(request.POST))
        print("FILES:", dict(request.FILES))
        print("User form valid:", user_form.is_valid())
        print("Coop form valid:", coop_form.is_valid())
        
        if user_form.is_valid():
            print("User form errors: Aucune")
        else:
            print("User form errors:", user_form.errors)
            
        if coop_form.is_valid():
            print("Coop form errors: Aucune")
        else:
            print("Coop form errors:", coop_form.errors)
        print("=== FIN DEBUG ===")
        
        if user_form.is_valid() and coop_form.is_valid():
            try:
                # Création de l'utilisateur
                user = user_form.save(commit=False)
                user.is_cooperative = True
                user.is_utilisateur = False
                user.email = coop_form.cleaned_data['email']
                user.save()
                
                # Création de la coopérative
                cooperative = coop_form.save(commit=False)
                cooperative.utilisateur = user
                cooperative.save()
                
                messages.success(request, f"Coopérative {cooperative.nom} ajoutée avec succès !")
                
                # Stocker les infos pour téléchargement
                request.session['download_ticket'] = {
                    'username': user.username,
                    'cooperative_name': cooperative.nom,
                    'password': user_form.cleaned_data['password1'],
                    'cooperative_id': cooperative.id
                }
                
                return redirect('administrateur')
                
            except Exception as e:
                messages.error(request, f"Erreur lors de la création: {str(e)}")
        else:
            messages.error(request, "Veuillez corriger les erreurs ci-dessous.")
    
    else:
        user_form = CooperativeUserForm(prefix='user')
        coop_form = CooperativeForm(prefix='coop')
    
    context = {
        'coop_stats': {'total': total_cooperatives, 'new_this_week': 0},
        'user_stats': {'total': total_users, 'new_this_week': 0},
        'chauffeur_stats': {'total': total_chauffeurs, 'new_this_week': 0},
        'voiture_stats': {'total': total_voitures, 'new_this_week': 0},
        'active_section': 'ajouter_cooperative',
        'user_form': user_form,
        'coop_form': coop_form,
        'action': 'ajouter',
        'active_list': None,
        'recent_activity': None,
        'utilisateurs': None,
        'cooperatives': None,
        'chauffeurs': None,
        'voitures': None,
    }
    
    return render(request, 'administrateur/home.html', context)

@login_required(login_url='/connexion/')
def modifier_cooperative(request, pk):
    """Modifier une coopérative existante"""
    cooperative = get_object_or_404(Cooperative, pk=pk)
    user = cooperative.utilisateur
    
    # Charger les statistiques
    total_cooperatives = Cooperative.objects.count()
    total_users = User.objects.filter(is_utilisateur=True).count()
    total_chauffeurs = Chauffeur.objects.count()
    total_voitures = Voiture.objects.count()
    
    if request.method == 'POST':
        # Utiliser un formulaire User personnalisé sans validation de username
        user_form = CooperativeUserUpdateForm(request.POST, instance=user, prefix='user')
        coop_form = CooperativeForm(request.POST, request.FILES, instance=cooperative, prefix='coop')
        
        if user_form.is_valid() and coop_form.is_valid():
            try:
                user = user_form.save(commit=False)
                user.email = coop_form.cleaned_data['email']
                user.save()
                
                cooperative = coop_form.save()
                
                messages.success(request, "Coopérative modifiée avec succès !")
                return redirect('administrateur')
            except Exception as e:
                messages.error(request, f"Erreur lors de la modification: {str(e)}")
        else:
            messages.error(request, "Veuillez corriger les erreurs ci-dessous.")
    else:
        # Pour GET, utiliser le formulaire de mise à jour
        user_form = CooperativeUserUpdateForm(instance=user, prefix='user')
        coop_form = CooperativeForm(instance=cooperative, prefix='coop')
        coop_form.fields['email'].initial = user.email

    context = {
        'coop_stats': {'total': total_cooperatives, 'new_this_week': 0},
        'user_stats': {'total': total_users, 'new_this_week': 0},
        'chauffeur_stats': {'total': total_chauffeurs, 'new_this_week': 0},
        'voiture_stats': {'total': total_voitures, 'new_this_week': 0},
        'active_section': 'modifier_cooperative',
        'user_form': user_form,
        'coop_form': coop_form,
        'cooperative': cooperative,
        'action': 'modifier',
        'active_list': None,
        'recent_activity': None,
        'utilisateurs': None,
        'cooperatives': None,
        'chauffeurs': None,
        'voitures': None,
    }
    
    return render(request, 'administrateur/home.html', context)

@login_required
def supprimer_cooperative(request, pk):
    """Supprimer une coopérative"""
    cooperative = get_object_or_404(Cooperative, pk=pk)
    
    if request.method == 'POST':
        # Récupérer l'utilisateur avant suppression
        user = cooperative.utilisateur
        
        # Supprimer la coopérative et l'utilisateur
        cooperative.delete()
        user.delete()
        
        messages.success(request, "Coopérative supprimée avec succès !")
        return redirect('administrateur') 
    
    # Si c'est une requête GET, on ne devrait pas arriver ici avec SweetAlert
    # Mais on redirige quand même vers la liste
    return redirect('administrateur') + '?list=cooperatives'

def generate_cooperative_ticket_pdf(user, cooperative, password):
    """Génère un mini-ticket PDF avec les identifiants de la coopérative"""
    
    # Créer le buffer PDF
    buffer = io.BytesIO()
    
    # Utiliser le format A6 pour un ticket petit (105mm x 148mm)
    p = canvas.Canvas(buffer, pagesize=A6)
    width, height = A6
    
    # Couleurs (RVB)
    primary_color = (52/255, 152/255, 219/255)   # #3498db - Bleu
    secondary_color = (44/255, 62/255, 80/255)   # #2c3e50 - Bleu foncé
    success_color = (46/255, 204/255, 113/255)   # #2ecc71 - Vert
    warning_color = (231/255, 76/255, 60/255)    # #e74c3c - Rouge
    dark_color = (52/255, 73/255, 94/255)        # #34495e - Gris foncé
    
    # === EN-TÊTE ===
    p.setFillColorRGB(*primary_color)
    p.rect(0, height-35, width, 35, fill=1, stroke=0)
    
    # Titre principal
    p.setFillColorRGB(1, 1, 1)  # Blanc
    p.setFont("Helvetica-Bold", 12)
    p.drawCentredString(width/2, height-20, "IDENTIFIANTS COOPÉRATIVE")
    
    # Sous-titre
    p.setFont("Helvetica", 8)
    p.drawCentredString(width/2, height-30, "Ticket de création de compte")
    
    # === INFORMATIONS COOPÉRATIVE ===
    y_position = height - 55
    
    p.setFillColorRGB(*secondary_color)
    p.setFont("Helvetica-Bold", 9)
    p.drawString(15, y_position, "INFORMATIONS COOPÉRATIVE")
    
    # Ligne séparatrice
    p.setStrokeColorRGB(*primary_color)
    p.setLineWidth(0.5)
    p.line(15, y_position-3, width-15, y_position-3)
    
    y_position -= 15
    
    # Nom de la coopérative
    p.setFillColorRGB(0, 0, 0)
    p.setFont("Helvetica-Bold", 8)
    p.drawString(15, y_position, "Nom: ")
    p.setFont("Helvetica", 8)
    p.drawString(40, y_position, cooperative.nom[:25])  # Limiter la longueur
    
    y_position -= 12
    
    # Email
    p.setFont("Helvetica-Bold", 8)
    p.drawString(15, y_position, "Email: ")
    p.setFont("Helvetica", 8)
    p.drawString(40, y_position, cooperative.email[:25])
    
    y_position -= 12
    
    # Téléphone
    p.setFont("Helvetica-Bold", 8)
    p.drawString(15, y_position, "Téléphone: ")
    p.setFont("Helvetica", 8)
    p.drawString(55, y_position, cooperative.telephone)
    
    y_position -= 12
    
    # Adresse (tronquée)
    p.setFont("Helvetica-Bold", 8)
    p.drawString(15, y_position, "Adresse: ")
    p.setFont("Helvetica", 7)
    address_lines = cooperative.adresse.split()[:6]  # Prendre les premiers mots
    truncated_address = ' '.join(address_lines)
    if len(cooperative.adresse) > len(truncated_address):
        truncated_address += "..."
    p.drawString(50, y_position, truncated_address)
    
    # === IDENTIFIANTS DE CONNEXION ===
    y_position -= 25
    
    p.setFillColorRGB(*success_color)
    p.setFont("Helvetica-Bold", 10)
    p.drawString(15, y_position, "IDENTIFIANTS DE CONNEXION")
    
    # Ligne séparatrice
    p.setStrokeColorRGB(*success_color)
    p.line(15, y_position-3, width-15, y_position-3)
    
    y_position -= 15
    
    # Nom d'utilisateur
    p.setFillColorRGB(0, 0, 0)
    p.setFont("Helvetica-Bold", 9)
    p.drawString(15, y_position, "Utilisateur: ")
    p.setFont("Helvetica", 9)
    p.drawString(60, y_position, user.username)
    
    y_position -= 15
    
    # Mot de passe
    p.setFont("Helvetica-Bold", 9)
    p.drawString(15, y_position, "Mot de passe: ")
    y_position -= 10  # Descendre pour le mot de passe
    p.setFont("Helvetica", 9)
    p.setFillColorRGB(*warning_color)

    max_password_length = 20
    if len(password) > max_password_length:
        displayed_password = password[:max_password_length] + "..."
    else:
        displayed_password = password
    
    p.drawString(15, y_position, displayed_password)  # Commencer depuis la gauche
    
    # Retour au noir pour la suite
    p.setFillColorRGB(0, 0, 0)
    
    y_position -= 15  # Espace supplémentaire après le mot de passe
    
    
    # URL de connexion
    p.setFont("Helvetica-Bold", 8)
    p.drawString(15, y_position, "URL de connexion:")
    p.setFont("Helvetica", 7)
    p.drawString(15, y_position-8, "http://127.0.0.1:8000/connexion/")
    
    # === MESSAGE IMPORTANT ===
    y_position -= 25
    
    p.setFillColorRGB(*warning_color)
    p.setFont("Helvetica-Bold", 7)
    p.drawString(15, y_position, "⚠️ IMPORTANT - À CONSERVER")
    
    p.setFillColorRGB(0.3, 0.3, 0.3)
    p.setFont("Helvetica", 6)
    p.drawString(15, y_position-8, "• Conservez ce ticket en lieu sûr")
    p.drawString(15, y_position-16, "• Les identifiants ne seront plus affichés")
    p.drawString(15, y_position-24, "• Changez le mot de passe après première connexion")
    
    # === INSTRUCTIONS ===
    y_position -= 35
    
    p.setFillColorRGB(*dark_color)
    p.setFont("Helvetica-Bold", 7)
    p.drawString(15, y_position, "INSTRUCTIONS:")
    
    p.setFont("Helvetica", 6)
    instructions = [
        "1. Allez sur la page de connexion",
        "2. Utilisez les identifiants ci-dessus", 
        "3. Accédez à votre tableau de bord",
        "4. Modifiez votre mot de passe"
    ]
    
    for i, instruction in enumerate(instructions):
        p.drawString(20, y_position-10-(i*8), instruction)
    
    # === PIED DE PAGE ===
    p.setFillColorRGB(0.5, 0.5, 0.5)  # Gris
    p.setFont("Helvetica", 5)
    
    # Date de génération
    current_time = timezone.now().strftime('%d/%m/%Y à %H:%M')
    p.drawString(15, 15, f"Généré le {current_time}")
    
    # ID de référence
    p.drawString(width-50, 15, f"REF: {cooperative.id:06d}")
    
    # Signature système
    p.drawCentredString(width/2, 8, "Système de Gestion eReserva")
    
    # Finaliser le PDF
    p.showPage()
    p.save()
    
    # Préparer la réponse
    buffer.seek(0)
    
    # Nom du fichier sans caractères spéciaux
    filename = f"identifiants_cooperative_{cooperative.nom.replace(' ', '_').replace('/', '_')}.pdf"
    
    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    return response

@login_required
def download_cooperative_ticket(request):
    """Télécharge le ticket après création"""
    ticket_data = request.session.pop('download_ticket', None)
    
    if ticket_data:
        user = User.objects.get(username=ticket_data['username'])
        cooperative = Cooperative.objects.get(id=ticket_data['cooperative_id'])
        
        return generate_cooperative_ticket_pdf(user, cooperative, ticket_data['password'])
    else:
        messages.error(request, "Aucun ticket à télécharger")
        return redirect('administrateur')

# Vues pour les listes détaillées
@login_required
def liste_utilisateurs(request):
    utilisateurs = User.objects.filter(is_utilisateur=True).select_related('utilisateur')
    return render(request, 'administrateur/listes/utilisateurs.html', {
        'utilisateurs': utilisateurs,
        'title': 'Liste des Utilisateurs'
    })

@login_required
def liste_cooperatives(request):
    cooperatives = Cooperative.objects.all().select_related('utilisateur')
    return render(request, 'administrateur/listes/cooperatives.html', {
        'cooperatives': cooperatives,
        'title': 'Liste des Coopératives'
    })

@login_required
def liste_chauffeurs(request):
    chauffeurs = Chauffeur.objects.all().select_related('cooperative', 'voiture')
    return render(request, 'administrateur/listes/chauffeurs.html', {
        'chauffeurs': chauffeurs,
        'title': 'Liste des Chauffeurs'
    })

@login_required
def liste_voitures(request):
    voitures = Voiture.objects.all().select_related('cooperative', 'categorie')
    return render(request, 'administrateur/listes/voitures.html', {
        'voitures': voitures,
        'title': 'Liste des Voitures'
    })

@login_required(login_url= '/connexion/')
def homeCooperative(request):
    cooperative = Cooperative.objects.get(utilisateur=request.user)
    trajets = Trajet.objects.filter(cooperative=cooperative)
    trajets_avec_infos = []
    for trajet in trajets:
        voiture = trajet.voiture  # relation ForeignKey
        chauffeur = voiture.chauffeurs.first()
        
        trajets_avec_infos.append({
            'trajet': trajet,
            'voiture': voiture,
            'chauffeur': chauffeur,
        })
    return render(request, 'koperative/index.html', {'trajets_infos': trajets_avec_infos})

@login_required(login_url= '/connexion/')
def homeUtilisateurs(request):
    # Récupérer tous les trajets 
    maintenant = timezone.now()
    trajets = Trajet.objects.filter(
        date_depart__gte=maintenant.date() - timedelta(days=1)  
    )
    
    trajets_avec_infos = []
    for trajet in trajets:
        voiture = trajet.voiture
        chauffeur = voiture.chauffeurs.first()
        
        # Chercher le dernier trajet pour cette voiture
        dernier_trajet = (
            Trajet.objects.filter(voiture=voiture)
            .exclude(id=trajet.id)
            .order_by("-date_depart", "-heure_depart")
            .first()
        )
        
        dernier_trajet_str = None
        if dernier_trajet:
            dernier_trajet_str = datetime.combine(
                dernier_trajet.date_depart, 
                dernier_trajet.heure_depart
            ).strftime("%d-%m-%Y %H:%M")
        
        trajets_avec_infos.append({
            'trajet': trajet,
            'voiture': voiture,
            'chauffeur': chauffeur,
            'dernier_trajet': dernier_trajet_str  # AJOUT IMPORTANT
        })
    
    return render(request, 'users/accueil.html', {'trajets_infos': trajets_avec_infos})

#------------------------GESTION RESERVATION--------------------------------
@login_required(login_url= '/connexion/')
def reserver_trajet(request, trajet_id):
    trajet = get_object_or_404(Trajet, id=trajet_id)
    trajet = get_object_or_404(Trajet, id=trajet_id)
    
    date_depart = datetime.combine(trajet.date_depart, trajet.heure_depart)

    date_depart = timezone.make_aware(date_depart)  

    maintenant = timezone.localtime() 
    
    if date_depart < maintenant:
        messages.error(request, "Ce trajet a déjà eu lieu et n'est plus disponible.")
        return redirect('utilisateurs')
    
    # Vérifier si des places sont disponibles
    reservations = Reservation.objects.filter(trajet=trajet)
    places_reservees = 0
    for r in reservations:
        places_reservees += r.nb_place_reserve
    
    if places_reservees >= trajet.voiture.place:
        messages.error(request, "Toutes les places de ce trajet sont déjà réservées.")
        return redirect('utilisateurs')


    voiture = trajet.voiture
    nb_places_total = voiture.place

    # Préparer les places déjà réservées
    reservations = Reservation.objects.filter(trajet=trajet)
    places_deja_reservees = []
    for r in reservations:
        if getattr(r, 'places_json', None):
            try:
                places_deja_reservees += json.loads(r.places_json)
            except (ValueError, TypeError):
                pass
    places_deja_reservees = [str(p).strip() for p in places_deja_reservees]

    if request.method == 'POST':
        places_selectionnees = request.POST.getlist('places[]')
        places_selectionnees = [str(p).strip() for p in places_selectionnees if str(p).strip() != '']

        if not places_selectionnees:
            messages.error(request, "Vous devez choisir au moins une place.")
            return redirect(request.path_info)

        # Vérifier les conflits de places
        reservations_existantes = Reservation.objects.filter(trajet=trajet)
        places_reservees_now = []
        for res in reservations_existantes:
            if getattr(res, 'places_json', None):
                try:
                    places_reservees_now += json.loads(res.places_json)
                except (ValueError, TypeError):
                    pass
        places_reservees_now = [str(p).strip() for p in places_reservees_now]

        conflit = set(places_selectionnees) & set(places_reservees_now)
        if conflit:
            messages.error(request, f"Places déjà réservées: {', '.join(sorted(conflit))}")
            return redirect(request.path_info)

        # Utilisateur classique -> Stripe
        if request.user.is_authenticated and getattr(request.user, "is_utilisateur", False):
            request.session['trajet_id'] = trajet.id
            request.session['places'] = places_selectionnees
            request.session['montant'] = len(places_selectionnees) * float(trajet.frais)
            return redirect('confirmation_paiement')

        # Coopérative -> réservation directe + génération ticket
        elif request.user.is_authenticated and getattr(request.user, "is_cooperative", False):
            nom = request.POST.get("nom")
            prenom = request.POST.get("prenom")
            telephone = request.POST.get("telephone")

            reservation = Reservation.objects.create(
                trajet=trajet,
                nb_place_reserve=len(places_selectionnees),
                places_json=json.dumps(places_selectionnees),
                montant_total=len(places_selectionnees) * float(trajet.frais),
                nom_client=nom,
                prenom_client=prenom,
                telephone_client=telephone,
            )

            # Rediriger vers la génération du ticket PDF
            return redirect('confirmation_telechargement', reservation_id=reservation.id)

        else:
            messages.error(request, "Vous devez être connecté pour réserver.")
            return redirect("connexion")

    # Préparer l'affichage (conversion en string pour cohérence avec template)
    places_avant = ['1', '2']
    places_arriere = [str(i) for i in range(3, nb_places_total + 1)]
    lignes = [places_arriere[i:i+4] for i in range(0, len(places_arriere), 4)]

    return render(request, 'users/schema_reservation.html', {
        'trajet': trajet,
        'nb_places_total': nb_places_total,
        'places_reservees': places_deja_reservees,
        'places_avant': places_avant,
        'lignes': lignes,
    })


# @login_required(login_url= '/connexion/')
# def homeAdministrateur(request):
#     return render(request, 'administrateur/home.html')


#------------AFFICHAGE VOITURE DISPONIBLE-----------------


#-----------GESTION VOITURE------------

def gestionVoiture(request):
    cooperative = Cooperative.objects.get(utilisateur=request.user)
    voitures = Voiture.objects.filter(cooperative=cooperative)
    return render(request, 'koperative/gestion_voiture.html', {'voitures':voitures})

@login_required
def ajouter_voiture(request):
    cooperative = Cooperative.objects.get(utilisateur=request.user)

    if request.method == 'POST':
        form = VoitureForm(request.POST, request.FILES, cooperative=cooperative)
        if form.is_valid():
            voiture = form.save(commit=False)
            voiture.cooperative = cooperative  # On force la coopérative
            voiture.save()
            messages.success(request, "Enregistrement réussi !")
            return redirect('gestion_voiture')
    else:
        form = VoitureForm(cooperative=cooperative)

    return render(request, 'koperative/form_voiture.html', {'form': form})

@login_required
def modifier_voiture(request, pk):
    voiture = get_object_or_404(Voiture, pk=pk, cooperative=request.user.cooperative)
    if request.method == "POST":
        form = VoitureForm(request.POST, request.FILES, instance=voiture)
        if form.is_valid():
            voiture = form.save(commit=False)
            voiture.cooperative = request.user.cooperative  # on sécurise
            voiture.save()
            messages.success(request, "Voiture modifiée avec succès !")
            return redirect('gestion_voiture')
    else:
        form = VoitureForm(instance=voiture)

    return render(request, "koperative/form_voiture.html", {"form": form})


def supprimer_voiture(request, id):
    voiture = get_object_or_404(Voiture, id=id)
    voiture.delete()
    return redirect('gestion_voiture')


#--------------------GESTION CHAUFFEUR-------------------------------

def gestionChauffeur(request):
    cooperative = Cooperative.objects.get(utilisateur=request.user)
    chauffeurs = Chauffeur.objects.filter(cooperative=cooperative)
    return render(request, 'koperative/gestion_chauffeur.html', {'chauffeurs':chauffeurs})

@login_required
def ajouter_chauffeur(request):
    cooperative = request.user.cooperative
    if request.method == 'POST':
        form = ChauffeurForm(request.POST, request.FILES, cooperative=cooperative)
        if form.is_valid():
            chauffeur = form.save(commit=False)
            chauffeur.cooperative = cooperative
            chauffeur.save()
            messages.success(request, "Chauffeur enregistré avec succès !")
            return redirect('gestion_chauffeur')
    else:
        form = ChauffeurForm(cooperative=cooperative)
    return render(request, 'koperative/form_chauffeur.html', {'form': form})


@login_required
def modifier_chauffeur(request, pk):
    chauffeur = get_object_or_404(Chauffeur, pk=pk, cooperative=request.user.cooperative)
    if request.method == 'POST':
        form = ChauffeurForm(request.POST, request.FILES, instance=chauffeur)
        if form.is_valid():
            chauffeur = form.save(commit=False)
            chauffeur.cooperative = request.user.cooperative
            chauffeur.save()
            messages.success(request, "Chauffeur modifié avec succès !")
            return redirect('gestion_chauffeur')
    else:
        form = ChauffeurForm(instance=chauffeur)
    return render(request, 'koperative/form_chauffeur.html', {'form': form})

def supprimer_chauffeur(request, id):
    chauffeur = get_object_or_404(Chauffeur, id=id)
    chauffeur.delete()
    return redirect('gestion_chauffeur')


#--------------------GESTION TRAJET--------------------------------

@login_required
def gestionTrajet(request):
    cooperative = Cooperative.objects.get(utilisateur=request.user)
    trajets = Trajet.objects.filter(cooperative=cooperative)
    trajets_avec_infos = []

    for trajet in trajets:
        voiture = trajet.voiture
        
        # Cherche le dernier trajet précédent pour cette voiture
        dernier = (
            Trajet.objects.filter(voiture=voiture, cooperative=cooperative)
            .exclude(id=trajet.id)
            .order_by("-date_depart", "-heure_depart")
            .first()
        )

        trajets_avec_infos.append({
            'trajet': trajet,
            'voiture': voiture,
            'chauffeur': voiture.chauffeurs.first(),
            'dernier_trajet': datetime.combine(dernier.date_depart, dernier.heure_depart).strftime("%d-%m-%Y %H:%M") if dernier else None
        })

    return render(request, 'koperative/gestion_trajet.html', {'trajets_infos': trajets_avec_infos})

@login_required
def ajouter_trajet(request):
    if request.method == 'POST':
        form = TrajetForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            trajet = form.save(commit=False)
            trajet.cooperative = Cooperative.objects.get(utilisateur=request.user)
            trajet.save()
            messages.success(request, "Trajet enregistré avec succès !")
            return redirect('gestion_trajet')
    else:
        form = TrajetForm(user=request.user)

    return render(request, 'koperative/form_trajet.html', {'form': form})


@login_required
def modifier_trajet(request, pk):
    trajet = get_object_or_404(Trajet, pk=pk, cooperative=request.user.cooperative)
    
    if request.method == 'POST':
        form = TrajetForm(request.POST, request.FILES, instance=trajet, user=request.user)
        if form.is_valid():
            trajet = form.save(commit=False)
            trajet.cooperative = Cooperative.objects.get(utilisateur=request.user)
            trajet.save()
            messages.success(request, "Trajet modifié avec succès !")
            return redirect('gestion_trajet')
    else:
        form = TrajetForm(instance=trajet, user=request.user)  # ici on envoie user=request.user
    
    return render(request, 'koperative/form_trajet.html', {'form': form})


def supprimer_trajet(request, id):
    trajet = get_object_or_404(Trajet, id=id)
    trajet.delete()
    return redirect('gestion_trajet')

#-------------------GESTION DE LA RESERVATION-------------------------------

def historiqueReservation(request):
    matricule = request.GET.get("matricule", None)
    date_depart = request.GET.get("date_depart", None)
    heure_depart = request.GET.get("heure_depart", None)
    
    trajet = None
    reservations = []
    total_places = 0
    total_frais = 0

    if matricule and date_depart and heure_depart:
        try:
            voiture = Voiture.objects.get(matricule=matricule)
            trajet = Trajet.objects.get(
                voiture=voiture,
                date_depart=date_depart,
                heure_depart=heure_depart
            )
            reservations = Reservation.objects.filter(trajet=trajet)

            # total des places réservées
            total_places = reservations.aggregate(Sum("nb_place_reserve"))["nb_place_reserve__sum"] or 0

            # total des frais payés
            total_frais = reservations.aggregate(Sum("montant_total"))["montant_total__sum"] or 0

        except (Voiture.DoesNotExist, Trajet.DoesNotExist):
            trajet = None

    return render(request, "koperative/historique_reservation.html", {
        "trajet": trajet,
        "reservations": reservations,
        "total_places": total_places,
        "total_frais": total_frais,
        "matricule": matricule,
        "date_depart": date_depart,
        "heure_depart": heure_depart,
    })

#-----------------------manifold---------------

def creer_manifold(request, trajet_id):
    trajet = get_object_or_404(Trajet, id=trajet_id)
    manifold, created = Manifold.objects.get_or_create(trajet=trajet)
    
    # Récupérer les numéros de places déjà attribués
    places_attribuees = list(manifold.passagers.values_list('numero_places', flat=True))
    places_disponibles = [i for i in range(1, trajet.voiture.place + 1) if i not in places_attribuees]

    if request.method == "POST":
        # Passer le trajet et le manifold au formulaire pour la validation
        form = PassagerForm(request.POST, trajet=trajet, manifold=manifold)
        if form.is_valid():
            passager = form.save(commit=False)
            passager.manifold = manifold
            passager.save()
            
            messages.success(request, f"Passager ajouté avec succès! Place numéro {passager.numero_places} attribuée.")
            return redirect("manifold_detail", trajet_id=trajet.id)
    else:
        form = PassagerForm(trajet=trajet, manifold=manifold)

    return render(request, "koperative/creer_manifold.html", {
        "trajet": trajet,
        "manifold": manifold,
        "passagers": manifold.passagers.all(),
        "form": form,
        "places_attribuees": places_attribuees,
        "places_disponibles": places_disponibles,
        "nombre_places_total": trajet.voiture.place
    })
def manifold_detail(request, trajet_id):
    trajet = get_object_or_404(Trajet, id=trajet_id)
    manifold = get_object_or_404(Manifold, trajet=trajet)
    passagers = manifold.passagers.all()
    
    # Récupérer le chauffeur associé à la voiture de ce trajet
    chauffeur = Chauffeur.objects.filter(voiture=trajet.voiture).first()
    
    return render(request, "koperative/manifold_detail.html", {
        "manifold": manifold,
        "passagers": passagers,
        "chauffeur": chauffeur  # Ajouter le chauffeur au contexte
    })
#-----------------------------------USERS------------------------------------------#
def historique_reservation(request):
    utilisateur = User.objects.get(username=request.user)
    reservations = Reservation.objects.filter(utilisateur=utilisateur)
    reservation_avec_info = []
    for reservation in reservations:
        trajet = reservation.trajet
        cooperative = trajet.cooperative
        voiture = trajet.voiture
        reservation_avec_info.append({
            'reservation': reservation,
            'trajet': trajet,
            'cooperative': cooperative,
            'voiture': voiture,
        })
    return render(request, 'users/historique_reservation.html', {'reservations_infos':reservation_avec_info})


def supprimer_reservation(request, id):
    reservation = get_object_or_404(Reservation, id=id)
    reservation.delete()
    return redirect('historique')


#---------------Ajouter cooperative (PARTIE ADMIN)----------------------------#

def is_admin(user):
    return user.is_superuser or user.is_administrateur


    #------------Gestion categorie------------

def ajouter_categorie(request):
    if request.method == 'POST':
        form = CategorieForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect('gestion_voiture')
    else:
        form = CategorieForm()
    return render(request, 'koperative/form_categorie.html', {'form': form})


#-------------------GESTION PAIEMENT---------------------#
@login_required
def paiement_success(request):
    trajet_id = request.session.get("trajet_id")
    places = request.session.get("places", [])
    montant = request.session.get("montant")

    if not trajet_id or not places:
        messages.error(request, "Aucune réservation trouvée.")
        return redirect("utilisateurs")

    trajet = Trajet.objects.get(id=trajet_id)

    # Créer la réservation dans la base
    reservation = Reservation.objects.create(
        trajet=trajet,
        nb_place_reserve=len(places),
        places_json=json.dumps(places),
        montant_total=montant,
        utilisateur=request.user,
    )

    # Vider la session
    request.session.pop("trajet_id", None)
    request.session.pop("places", None)
    request.session.pop("montant", None)

    # Au lieu de redirect('ticket_pdf', reservation_id=reservation.id)
    return redirect('confirmation_telechargement', reservation_id=reservation.id)

@login_required
def confirmation_paiement(request):
    trajet_id = request.session.get("trajet_id")
    places = request.session.get("places", [])
    montant = request.session.get("montant")

    if not trajet_id or not places:
        messages.error(request, "Session expirée. Veuillez recommencer la réservation.")
        return redirect("utilisateurs")

    trajet = Trajet.objects.get(id=trajet_id)

    stripe.api_key = settings.STRIPE_SECRET_KEY

    checkout_session = stripe.checkout.Session.create(
        payment_method_types=['card'],
        line_items=[{
            'price_data': {
                'currency': 'MGA',  
                'product_data': {
                    'name': f"Réservation {trajet.lieu_depart} → {trajet.lieu_destination}",
                },
                'unit_amount': int(montant * 1), 
            },
            'quantity': 1,
        }],
        mode='payment',
        success_url=request.build_absolute_uri(reverse("paiement_success")),
        cancel_url=request.build_absolute_uri(reverse("paiement_cancel")),
    )

    return redirect(checkout_session.url, code=303)


#----------ticketPDF-----------------
def generate_ticket_pdf(request, reservation_id):
    reservation = get_object_or_404(Reservation, id=reservation_id)
    
    try:
        places = json.loads(reservation.places_json) if reservation.places_json else []
    except:
        places = []

    # QR code
    qr_info = f"Réservation REF-{reservation.id:06d}\n"
    if reservation.utilisateur:
        qr_info += f"Passager: {reservation.utilisateur.get_full_name() or reservation.utilisateur.username}\n"
    else:
        qr_info += f"Passager: {reservation.nom_client} {reservation.prenom_client}\n"
    qr_info += f"Trajet: {reservation.trajet.lieu_depart} → {reservation.trajet.lieu_destination}\n"
    qr_info += f"Date: {reservation.trajet.date_depart.strftime('%d/%m/%Y')} {reservation.trajet.heure_depart.strftime('%H:%M')}\n"
    qr_info += f"Places: {', '.join(str(p) for p in places) if places else 'Aucune'}"

    qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=6, border=4)
    qr.add_data(qr_info)
    qr.make(fit=True)

    qr_img = qr.make_image(fill_color="black", back_color="white")
    qr_buffer = BytesIO()
    qr_img.save(qr_buffer, format="PNG")
    qr_code_data = base64.b64encode(qr_buffer.getvalue()).decode()
    qr_buffer.close()

    context = {
        "reservation": reservation,
        "places": places,
        "qr_code_data": qr_code_data,
    }

    template = get_template("ticket_template.html")
    html = template.render(context)

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="ticket_{reservation.id}.pdf"'
    
    # Créer le PDF
    pisa_status = pisa.CreatePDF(html, dest=response)
    
    if pisa_status.err:
        return HttpResponse("Erreur lors de la génération du PDF")
    return response


def ticket_pdf(request, reservation_id):
    try:
        reservation = get_object_or_404(Reservation, id=reservation_id)
        
        # Vérifier les permissions
        has_access = False
        
        if reservation.utilisateur and request.user == reservation.utilisateur:
            has_access = True
        elif (hasattr(request.user, 'cooperative') and 
              reservation.trajet.cooperative == request.user.cooperative):
            has_access = True
        elif request.user.is_superuser or getattr(request.user, 'is_administrateur', False):
            has_access = True
        
        if not has_access:
            messages.error(request, "Vous n'avez pas accès à ce ticket.")
            return redirect("accueil")
        
        # Créer la réponse PDF
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="ticket_{reservation.id}.pdf"'
        
        # Créer le PDF avec une petite taille (largeur de ticket de caisse)
        p = canvas.Canvas(response, pagesize=(200, 650))
        width, height = 200, 650
        
        # Style minimaliste
        p.setLineWidth(0.5)
        
        from django.utils import timezone
        import pytz
        
        # Forcer le fuseau horaire de Madagascar
        madagascar_tz = pytz.timezone('Indian/Antananarivo')
        date_reservation_local = reservation.date_reservation.astimezone(madagascar_tz)
        # date_reservation est un DateTimeField
        date_reservation_local = timezone.localtime(reservation.date_reservation)
        
        # date_depart est un DateField (objet date, pas datetime)
        date_depart_local = reservation.trajet.date_depart
        
        # heure_depart est un TimeField
        heure_depart_local = reservation.trajet.heure_depart
        
        # En-tête
        p.setFont("Helvetica-Bold", 10)
        p.drawString(10, height - 20, f"{reservation.trajet.cooperative.nom}")
        p.setFont("Helvetica", 8)
        p.drawString(10, height - 35, "Ticket de réservation")
        p.line(10, height - 40, 190, height - 40)
        
        # Informations essentielles
        y = height - 55
        p.setFont("Helvetica-Bold", 8)
        p.drawString(10, y, "REF:")
        p.setFont("Helvetica", 8)
        p.drawString(40, y, f"REF-{reservation.id:06d}")
        
        y -= 15
        p.setFont("Helvetica-Bold", 8)
        p.drawString(10, y, "Réservé le:")
        y -= 10  # Descendre pour la date
        p.setFont("Helvetica", 8)
        p.drawString(10, y, f"{date_reservation_local.strftime('%d/%m/%Y à %H:%M')}")
        
        # Ligne séparatrice
        y -= 10
        p.line(10, y, 190, y)
        y -= 15
        
        # Informations passager
        p.setFont("Helvetica-Bold", 9)
        p.drawString(10, y, "PASSAGER")
        y -= 12
        
        p.setFont("Helvetica", 8)
        if reservation.utilisateur:
            nom_complet = reservation.utilisateur.get_full_name() or reservation.utilisateur.username
            p.drawString(10, y, f"Nom: {nom_complet}")
        else:
            nom_complet = f"{reservation.nom_client} {reservation.prenom_client}"
            p.drawString(10, y, f"Nom: {nom_complet}")
        
        y -= 20
        p.line(10, y, 190, y)
        y -= 15
        
        # Informations trajet
        p.setFont("Helvetica-Bold", 9)
        p.drawString(10, y, "TRAJET")
        y -= 12
        
        p.setFont("Helvetica", 8)
        p.drawString(10, y, f"{reservation.trajet.lieu_depart} -> {reservation.trajet.lieu_destination}")
        y -= 12
        
        p.drawString(10, y, f"Le {date_depart_local.strftime('%d/%m/%Y')} à {heure_depart_local.strftime('%H:%M')}")
        
        y -= 20
        p.line(10, y, 190, y)
        y -= 15
        
        # Détails réservation
        p.setFont("Helvetica-Bold", 9)
        p.drawString(10, y, "DÉTAILS")
        y -= 12
        
        p.setFont("Helvetica", 8)
        p.drawString(10, y, f"Nombre des Place reserver: {reservation.nb_place_reserve}")
        
        # Afficher les numéros de place
        try:
            places = json.loads(reservation.places_json) if reservation.places_json else []
            if places:
                y -= 12
                p.drawString(10, y, f" Place N°: {', '.join(str(p) for p in places)}")
        except:
            pass
        
        y -= 12
        p.drawString(10, y, f"Montant: {reservation.montant_total} Ar")
        
        y -= 20
        p.line(10, y, 190, y)
        y -= 15
        
        # QR Code amélioré avec plus d'informations
        try:
            # Récupérer les informations de places
            places_list = []
            try:
                places_list = json.loads(reservation.places_json) if reservation.places_json else []
            except:
                pass
            
            qr_data = {
                "reference": f"REF-{reservation.id:06d}",
                "passager": nom_complet,
                "trajet": f"{reservation.trajet.lieu_depart} → {reservation.trajet.lieu_destination}",
                "date_depart": date_depart_local.strftime("%d/%m/%Y"),
                "heure_depart": heure_depart_local.strftime("%H:%M"),
                "places": ", ".join(str(p) for p in places_list) if places_list else str(reservation.nb_place_reserve),
                "montant": f"{reservation.montant_total} Ar",
                "cooperative": reservation.trajet.cooperative.nom,
                "date_reservation": date_reservation_local.strftime("%d/%m/%Y %H:%M")
            }
            
            # Formatage des données pour le QR code
            qr_info = f"""
RESERVEO - RÉSERVATION
══════════════════════
 RÉFÉRENCE: {qr_data['reference']}
 PASSAGER: {qr_data['passager']}
 TRAJET: {qr_data['trajet']}
 DATE: {qr_data['date_depart']}
 HEURE: {qr_data['heure_depart']}
 PLACES: {qr_data['places']}
 MONTANT: {qr_data['montant']}
 COOPÉRATIVE: {qr_data['cooperative']}
 RÉSERVÉ LE: {qr_data['date_reservation']}
            """.strip()

            qr = qrcode.QRCode(
                version=2,
                error_correction=qrcode.constants.ERROR_CORRECT_M,
                box_size=2,
                border=2
            )
            qr.add_data(qr_info)
            qr.make(fit=True)
            qr_img = qr.make_image(fill_color="black", back_color="white")
            
            buffer = BytesIO()
            qr_img.save(buffer, format="PNG")
            buffer.seek(0)
            
            # Dessiner un cadre autour du QR code
            p.setStrokeColorRGB(0.7, 0.7, 0.7)
            p.setLineWidth(0.5)
            p.rect(65, y - 70, 70, 85)
            
            # Dessiner le QR code centré
            p.drawImage(ImageReader(buffer), 70, y - 65, width=60, height=60)
            
            # Informations autour du QR code
            p.setFont("Helvetica-Bold", 7)
            p.drawString(75, y - 5, "TICKET ÉLECTRONIQUE")
            
            p.setFont("Helvetica", 6)
            p.drawString(75, y - 75, f"Réf: {qr_data['reference']}")
            
            y_after_qr = y - 100
            
        except Exception as qr_error:
            print(f"Erreur génération QR code: {qr_error}")
            # Fallback simple
            p.setFont("Helvetica", 7)
            p.drawString(70, y - 60, f"RÉF: REF-{reservation.id:06d}")
            p.drawString(70, y - 68, f"PLACES: {reservation.nb_place_reserve}")
            y_after_qr = y - 80
        
        # PIED DE PAGE APRÈS LE QR CODE
        y = y_after_qr
        
        # Ligne séparatrice avant le pied de page
        p.line(10, y, 190, y)
        y -= 12
        
        # Messages de pied de page
        p.setFont("Helvetica", 6)
        p.drawString(10, y, "Merci pour votre confiance!")
        y -= 8
        p.drawString(10, y, "Misaotra amin'ny fahatokisanao")
        y -= 8
        p.drawString(10, y, "Présentez ce ticket à l'embarquement")
        y -= 6
        p.drawString(10, y, "Ilaina ity tapakila ity rehefa hiditra ao anaty fiara")
        
        # Timestamp de génération
        now_local = timezone.localtime(timezone.now())
        y -= 10
        p.setFont("Helvetica", 5)
        p.drawString(10, y, f"Généré le {now_local.strftime('%d/%m/%Y %H:%M:%S')}")
        
        p.showPage()
        p.save()
        
        # Ajouter un en-tête pour rediriger après téléchargement
        response['Refresh'] = f'5; url={reverse("accueil")}'
        response['X-Redirect-After-Download'] = reverse("accueil")
        
        return response
        
    except Exception as e:
        messages.error(request, f"Erreur lors de la génération du ticket: {str(e)}")
        return redirect("accueil")
    
def confirmation_telechargement(request, reservation_id):
    reservation = get_object_or_404(Reservation, id=reservation_id)
    return render(request, 'users/confirmation_telechargement.html', {'reservation': reservation})

def telechargement_termine(request, reservation_id):
    messages.success(request, "Votre ticket a été téléchargé avec succès.")
    return redirect("utilisateurs")

def paiement_cancel(request):
    messages.error(request, " Paiement annulé, la réservation n'a pas été enregistrée.")
    return redirect("utilisateurs")


#-------------------RECHERCHE TRAJET---------------------#
def recherche_trajets(request):
    lieu_depart = request.GET.get("lieu_depart", "")
    lieu_destination = request.GET.get("lieu_destination", "")
    date_depart = request.GET.get("date_depart", "")

    # Obtenir la date et heure actuelles
    maintenant = timezone.now()
    
    trajets = Trajet.objects.select_related("voiture", "cooperative")

    # Filtrer les trajets dont la date et l'heure de départ sont dans le futur
    trajets = trajets.filter(
        Q(date_depart__gt=maintenant.date()) | 
        Q(date_depart=maintenant.date(), heure_depart__gt=maintenant.time())
    )

    if lieu_depart:
        trajets = trajets.filter(lieu_depart__icontains=lieu_depart)
    if lieu_destination:
        trajets = trajets.filter(lieu_destination__icontains=lieu_destination)
    if date_depart:
        trajets = trajets.filter(date_depart=date_depart)

    data = []
    for trajet in trajets:
        chauffeur = Chauffeur.objects.filter(voiture=trajet.voiture).first()
        
        # Vérifier si des places sont disponibles
        reservations = Reservation.objects.filter(trajet=trajet)
        places_reservees = 0
        for r in reservations:
            places_reservees += r.nb_place_reserve
        
        places_disponibles = trajet.voiture.place - places_reservees
        
        # Chercher le dernier trajet pour cette voiture
        dernier_trajet = (
            Trajet.objects.filter(voiture=trajet.voiture)
            .exclude(id=trajet.id)
            .order_by("-date_depart", "-heure_depart")
            .first()
        )
        
        dernier_trajet_str = None
        if dernier_trajet:
            dernier_trajet_str = datetime.combine(
                dernier_trajet.date_depart, 
                dernier_trajet.heure_depart
            ).strftime("%d-%m-%Y %H:%M")
        
        data.append({
            "id": trajet.id,
            "date_depart": trajet.date_depart.strftime("%d-%m-%Y"),
            "heure_depart": trajet.heure_depart.strftime("%H:%M"),
            "lieu_depart": trajet.lieu_depart,
            "lieu_destination": trajet.lieu_destination,
            "frais": str(trajet.frais),
            "places_disponibles": places_disponibles,
            "dernier_trajet": dernier_trajet_str,  # AJOUT IMPORTANT
            "voiture": {
                "marque": trajet.voiture.marque,
                "place": trajet.voiture.place,
                "matricule": trajet.voiture.matricule,
                "photo": trajet.voiture.photo.url if trajet.voiture.photo else "",
                "categorie": trajet.voiture.categorie.nom if trajet.voiture.categorie else "",
                "cooperative": trajet.voiture.cooperative.nom
            },
            "chauffeur": {
                "nom": chauffeur.nom if chauffeur else None,
                "prenom": chauffeur.prenom if chauffeur else None,
                "telephone": chauffeur.telephone if chauffeur else None
            } if chauffeur else None
        })

    return JsonResponse({"trajets": data})

@login_required
def recherche_trajets_cooperative(request):
    lieu_depart = request.GET.get("lieu_depart", "")
    lieu_destination = request.GET.get("lieu_destination", "")
    date_depart = request.GET.get("date_depart", "")

    # Obtenir la coopérative de l'utilisateur connecté
    cooperative = Cooperative.objects.get(utilisateur=request.user)
    
    # Obtenir la date et heure actuelles
    maintenant = timezone.now()
    
    # Filtrer les trajets de la coopérative
    trajets = Trajet.objects.filter(
        cooperative=cooperative,
        date_depart__gte=maintenant.date() - timedelta(days=1)  # Inclut les trajets d'hier
    )

    if lieu_depart:
        trajets = trajets.filter(lieu_depart__icontains=lieu_depart)
    if lieu_destination:
        trajets = trajets.filter(lieu_destination__icontains=lieu_destination)
    if date_depart:
        trajets = trajets.filter(date_depart=date_depart)

    data = []
    for trajet in trajets:
        # Vérifier si le trajet est encore disponible (moins d'1h après le départ)
        trajet_datetime = timezone.make_aware(
            datetime.combine(trajet.date_depart, trajet.heure_depart)
        )
        
        if trajet_datetime + timedelta(hours=1) < maintenant:
            continue  # Ne pas inclure les trajets non disponibles
            
        chauffeur = Chauffeur.objects.filter(voiture=trajet.voiture).first()
        
        # Vérifier si des places sont disponibles
        reservations = Reservation.objects.filter(trajet=trajet)
        places_reservees = 0
        for r in reservations:
            places_reservees += r.nb_place_reserve
        
        places_disponibles = trajet.voiture.place - places_reservees
        
        # Chercher le dernier trajet pour cette voiture
        dernier_trajet = (
            Trajet.objects.filter(voiture=trajet.voiture, cooperative=cooperative)
            .exclude(id=trajet.id)
            .order_by("-date_depart", "-heure_depart")
            .first()
        )
        
        dernier_trajet_str = None
        if dernier_trajet:
            dernier_trajet_str = datetime.combine(
                dernier_trajet.date_depart, 
                dernier_trajet.heure_depart
            ).strftime("%d-%m-%Y %H:%M")
        
        data.append({
            "id": trajet.id,
            "date_depart": trajet.date_depart.strftime("%d-%m-%Y"),
            "heure_depart": trajet.heure_depart.strftime("%H:%M"),
            "lieu_depart": trajet.lieu_depart,
            "lieu_destination": trajet.lieu_destination,
            "frais": str(trajet.frais),
            "places_disponibles": places_disponibles,
            "dernier_trajet": dernier_trajet_str,  # AJOUT IMPORTANT
            "voiture": {
                "marque": trajet.voiture.marque,
                "place": trajet.voiture.place,
                "matricule": trajet.voiture.matricule,
                "photo": trajet.voiture.photo.url if trajet.voiture.photo else "",
                "categorie": trajet.voiture.categorie.nom if trajet.voiture.categorie else "",
                "cooperative": trajet.voiture.cooperative.nom
            },
            "chauffeur": {
                "nom": chauffeur.nom if chauffeur else None,
                "prenom": chauffeur.prenom if chauffeur else None,
                "telephone": chauffeur.telephone if chauffeur else None
            } if chauffeur else None
        })

    return JsonResponse({"trajets": data})

