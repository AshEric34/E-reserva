# reservation/templatetags/custom_filters.py
from django import template
from django.utils import timezone
from datetime import datetime, timedelta

register = template.Library()

@register.filter
def subtract(value, arg):
    """Soustrait arg de value"""
    try:
        return int(value) - int(arg)
    except (ValueError, TypeError):
        return value

@register.filter
def is_trajet_disponible(trajet):
    """Vérifie si un trajet est encore disponible (moins d'1h après le départ)"""
    maintenant = timezone.now()
    trajet_datetime = timezone.make_aware(
        datetime.combine(trajet.date_depart, trajet.heure_depart)
    )
    return trajet_datetime + timedelta(hours=1) > maintenant

@register.filter
def places_reservees(trajet):
    """Calcule le nombre de places réservées pour un trajet"""
    reservations = trajet.reservation_set.all()
    return sum(r.nb_place_reserve for r in reservations)

@register.filter
def places_disponibles(trajet):
    """Calcule le nombre de places disponibles pour un trajet"""
    reservations = trajet.reservation_set.all()
    places_reservees = sum(r.nb_place_reserve for r in reservations)
    return trajet.voiture.place - places_reservees

@register.filter
def hours_since(value):
    """Calcule le nombre d'heures écoulées depuis une date donnée"""
    if not value:
        return 0
    
    maintenant = timezone.now()
    if isinstance(value, str):
        # Convertir la chaîne en objet datetime si nécessaire
        try:
            value = datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
            value = timezone.make_aware(value)
        except (ValueError, TypeError):
            return 0
    
    difference = maintenant - value
    return difference.total_seconds() / 3600  # Convertir en heures

@register.filter
def parse_datetime(value):
    try:
        # Adjust the format according to your date/time format
        return datetime.strptime(value, '%Y-%m-%d %H:%M:%S')
    except (ValueError, TypeError):
        return None