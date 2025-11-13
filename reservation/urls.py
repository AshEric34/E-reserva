from django.urls import path
from .views import *
from .forms import CustomPasswordResetForm, CustomSetPasswordForm 
from django.contrib.auth import views as auth_views


urlpatterns = [
    path('',accueil, name='accueil'),
    path('utilisateur/', homeUtilisateurs, name='utilisateurs'),
    path('enregistrerUsers/', register, name="register"),
    path('connexion/', connexion, name='connexion'),
    path('administrateur_login/', login_admin, name='administrateur'),
    path('logout/', deconnexion, name='logout'),
    path('administrateur/', homeAdministrateur, name='administrateur'),
    path('administrateur/download-ticket/', download_cooperative_ticket, name='download_ticket'),

    path('administrateur/ajouter-cooperative/', ajouter_cooperative, name='ajouter_cooperative'),
    path('administrateur/cooperative/<int:pk>/modifier/', modifier_cooperative, name='modifier_cooperative'),
    path('administrateur/cooperative/<int:pk>/supprimer/', supprimer_cooperative, name='supprimer_cooperative'),
    path('administrateur/utilisateurs/', liste_utilisateurs, name='liste_utilisateurs'),
    path('administrateur/cooperatives/', liste_cooperatives, name='liste_cooperatives'),
    path('administrateur/chauffeurs/', liste_chauffeurs, name='liste_chauffeurs'),
    path('administrateur/voitures/', liste_voitures, name='liste_voitures'),
    path('koperative/', homeCooperative, name='koperative'),
    path('koperative/gestion_voiture/', gestionVoiture, name='gestion_voiture'),
    path('koperative/gestion_chauffeur/', gestionChauffeur, name='gestion_chauffeur'),
    path('koperative/gestion_trajet/', gestionTrajet, name='gestion_trajet'),
    path('koperative/historique_reservation/', historiqueReservation, name='historique_reservation'),
    path("manifold_detail/<int:trajet_id>/", manifold_detail, name="manifold_detail"),
    path("creer_manifold/<int:trajet_id>/create/", creer_manifold, name="creer_manifold"),
    path('ajouter_voiture/', ajouter_voiture, name='ajouter_voiture'), 
    path('modifier_voiture/<int:pk>/', modifier_voiture, name='modifier_voiture'),
    path('supprimer_voiture/<int:id>/', supprimer_voiture, name='supprimer_voiture'),
    path('ajouter_chauffeur/', ajouter_chauffeur, name='ajouter_chauffeur'), 
    path('modifier_chauffeur/<int:pk>/', modifier_chauffeur, name='modifier_chauffeur'),
    path('supprimer_chauffeur/<int:id>/', supprimer_chauffeur, name='supprimer_chauffeur'),
    path('ajouter_trajet', ajouter_trajet, name="ajouter_trajet"),
    path('modifier_trajet/<int:pk>/', modifier_trajet, name='modifier_trajet'),
    path('supprimer_trajet/<int:id>/', supprimer_trajet, name='supprimer_trajet'),
    
    path('reserver/<int:trajet_id>/', reserver_trajet, name='reserver'),
    path('ajouter_categorie', ajouter_categorie, name="ajouter_categorie"),
    path('supprimer_reservation/<int:id>/', supprimer_reservation, name="supprimer_reservation"),
    path('users/historique_reservation', historique_reservation, name="historique"),
    path("confirmation_paiement/", confirmation_paiement, name="confirmation_paiement"),
    path("confirmation_telechargement/<int:reservation_id>/", confirmation_telechargement, name="confirmation_telechargement"),
    path('users/success', paiement_success, name='paiement_success'),
    path("ticket/<int:reservation_id>/", ticket_pdf, name="ticket_pdf"),
    path('paiement/cancel/', paiement_cancel, name='paiement_cancel'),
    path("recherche/", recherche_trajets, name="recherche_trajets"),
    path('recherche-cooperative/', recherche_trajets_cooperative, name='recherche_cooperative'),
        # MOT DE PASSE OUBLIÉ
    path('password-reset/', 
         auth_views.PasswordResetView.as_view(
             template_name='compte/password_reset_form.html',
             email_template_name='compte/password_reset_email.html',
             subject_template_name='compte/password_reset_subject.txt',
             form_class=CustomPasswordResetForm,
             success_url='/password-reset/done/'
         ), 
         name='password_reset'),
    
    path('password-reset/done/', 
         auth_views.PasswordResetDoneView.as_view(
             template_name='compte/password_reset_done.html'
         ), 
         name='password_reset_done'),
    
    path('password-reset-confirm/<uidb64>/<token>/', 
         auth_views.PasswordResetConfirmView.as_view(
             template_name='compte/password_reset_confirm.html',
             form_class=CustomSetPasswordForm,
             success_url='/password-reset-complete/'
         ), 
         name='password_reset_confirm'),
    
    path('password-reset-complete/', 
         auth_views.PasswordResetCompleteView.as_view(
             template_name='compte/password_reset_complete.html'
         ), 
         name='password_reset_complete'),

]