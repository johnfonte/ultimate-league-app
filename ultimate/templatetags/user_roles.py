from django import template
register = template.Library()

from ultimate.leagues.models import TeamMember

@register.filter
def in_group(user, groups):
	group_list = groups.split(',')
	return user.is_superuser or user.groups.filter(name__in=group_list).exists()

@register.filter
def is_captain(user):
	return TeamMember.objects.filter(user=user, captain=1).exists()
