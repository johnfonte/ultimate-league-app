from django.db import models, transaction
from django.db.models import Count
from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist

from pybb.models import *

from datetime import date


class Field(models.Model):
	id = models.AutoField(primary_key=True)
	name = models.TextField()
	layout_link = models.TextField(blank=True)
	address = models.TextField(blank=True)
	driving_link = models.TextField(blank=True)
	note = models.TextField(blank=True)

	class Meta:
		db_table = u'field'
		ordering = ['name']

	def __unicode__(self):
		return self.name


class FieldNames(models.Model):
	id = models.AutoField(primary_key=True)
	name = models.TextField()
	field = models.ForeignKey('leagues.Field')
	class Meta:
		db_table = u'field_names'
		verbose_name_plural = 'field names'
		ordering = ['field__name', 'name']

	def __unicode__(self):
		return '%s %s' % (self.field.name, self.name)


class League(models.Model):
	LEAGUE_STATE_CHOICES = (
		('closed',	'Closed - visible to all, registration closed'),
		('hidden',	'Hidden - hidden to all, registration closed'),
		('open',	'Open - visible to all, registration conditionally open'),
		('preview',	'Preview - visible to admins, registration conditionally open only to admins'),
	)

	LEAGUE_GENDER_CHOICES = (
		('50/50',		'50/50 League'),
		('coed',		'Normal Co-Ed Gender Matched'),
		('competitive',	'Competitive League'),
		('event',		'Special Event'),
		('hat',			'Hat Tourney'),
		('open',		'Open, No Gender Match'),
		('showcase',	'Showcase League'),
		('women',		'Women Only'),
	)

	id = models.AutoField(primary_key=True)
	night = models.CharField(max_length=32, help_text='lower case, no special characters, e.g. "sunday", "tuesday and thursday", "end of season tournament"')
	season = models.CharField(max_length=32, help_text='lower case, no special characters, e.g. "late fall", "winter"')
	year = models.IntegerField(help_text='four digit year, e.g. 2013')
	gender = models.CharField(max_length=32, choices=LEAGUE_GENDER_CHOICES)
	gender_note = models.TextField(help_text='gender or other notes for league, e.g. 50/50 league, showcase league notes')
	baggage = models.IntegerField(help_text='max baggage group size')
	times = models.TextField(help_text='start to end time, e.g. 6:00-8:00pm')
	num_games_per_week = models.IntegerField(default=1, help_text='number of games per week, used to calculate number of games for a league')
	reg_start_date = models.DateField(help_text='date that registration process is open (not currently automated)')
	price_increase_start_date = models.DateField(help_text='date when cost increases for league')
	waitlist_start_date = models.DateField(help_text='date that waitlist is started (regardless of number of registrations)')
	league_start_date = models.DateField(help_text='date of first game')
	league_end_date = models.DateField(help_text='date of last game')
	checks_accepted = models.BooleanField(default=True)
	paypal_cost = models.IntegerField(help_text='base cost of league if paying by PayPal')
	check_cost_increase = models.IntegerField(help_text='amount to be added to paypal_cost if paying by check')
	late_cost_increase = models.IntegerField(help_text='amount to be added to paypal_cost if paying after price_increase_start_date')
	max_players = models.IntegerField(help_text='max players for league, extra registrations will be placed on waitlist')
	state = models.CharField(max_length=32, choices=LEAGUE_STATE_CHOICES, help_text='state of league, changes whether registration is open or league is visible')
	field = models.ManyToManyField(Field, db_table='field_league', help_text='Select the fields these games will be played at, use the green "+" icon if we\'re playing at a new field.')
	details = models.TextField(help_text='details page text, use HTML')
	league_email = models.CharField(max_length=64, blank=True, help_text='email address for entire season')
	league_captains_email = models.CharField(max_length=64, blank=True, help_text='email address for league captains')
	division_email = models.CharField(max_length=64, blank=True, help_text='email address for just this league')
	mail_check_address = models.TextField(help_text='treasurer mailing address')

	class Meta:
		db_table = u'league'

	@property
	def night_title(self):
		return ('%s' % (self.night)).replace('_', ' ')

	@property
	def season_title(self):
		return ('%s' % (self.season)).replace('_', ' ')

	@property
	def season_year(self):
		return ('%s %d' % (self.season, self.year)).replace('_', ' ')

	@property
	def gender_title(self):
		return ('%s' % (self.gender)).replace('_', ' ')

	@property
	def paypal_price(self):
		if date.today() >= self.price_increase_start_date:
			return self.paypal_cost + self.late_cost_increase

		return self.paypal_cost

	@property
	def check_price(self):
		if date.today() >= self.price_increase_start_date:
			return self.paypal_cost + self.check_cost_increase + self.late_cost_increase

		return self.paypal_cost + self.check_cost_increase

	def get_fields(self):
		return FieldLeague.objects.filter(league=self)

	def get_field_names(self):
		return FieldNames.objects.filter(field__fieldleague__league=self, game__league=self).distinct().order_by('field__name', 'name')

	def get_teams(self):
		return Team.objects.filter(league=self)

	def get_games(self):
		return Game.objects.filter(league=self).order_by('field_name__field__name', 'field_name__name', 'date')

	def get_user_games(self, user):
		return Game.objects.filter(league=self, gameteams__team__teammember__user=user).order_by('date')

	def get_num_game_events(self):
		diff = self.league_end_date - self.league_start_date
		num_weeks = (diff.days / 7) + 1

		if self.num_games_per_week > 1:
			num_games = num_weeks * self.num_games_per_week
		else:
			num_games = num_weeks

		return num_games

	def get_league_captains(self):
		return User.objects.filter(teammember__team__league=self, teammember__captain=1)

	def get_league_captains_teammember(self):
		return TeamMember.objects.filter(team__league=self, captain=1).order_by('team')

	def player_survey_complete_for_user(self, user):
		return bool(Team.objects.get(league=self, teammember__user=user).player_survey_complete(user))

	def get_registrations(self):
		return Registrations.objects.filter(league=self).order_by('registered')

	def get_registrations_for_user(self, user):
		return Registrations.objects.filter(league=self, user=user)

	def get_complete_registrations(self):
		registrations = Registrations.objects.filter(league=self).order_by('registered')
		return [r for r in registrations if r.is_complete() and not r.waitlist and not r.refunded]

	def get_waitlist_registrations(self):
		registrations = Registrations.objects.filter(league=self).order_by('registered')
		return [r for r in registrations if r.is_complete() and r.waitlist and not r.refunded]

	def get_incomplete_registrations(self):
		registrations = Registrations.objects.filter(league=self).order_by('registered')
		return [r for r in registrations if not r.is_complete() and not r.refunded]

	def get_refunded_registrations(self):
		registrations = Registrations.objects.filter(league=self).order_by('registered')
		return [r for r in registrations if r.is_complete() and r.refunded]

	def get_unassigned_registrations(self):
		team_member_users = [t.user for t in TeamMember.objects.filter(team__league=self)]
		registrations = Registrations.objects.filter(league=self).exclude(user__in=team_member_users)
		return [r for r in registrations if r.is_complete() and not r.refunded]

	def is_visible(self, user=None):
		if user and (user.is_superuser or user.groups.filter(name='junta').exists()):
			return self.state in ['closed', 'open', 'preview']

		return self.state in ['closed', 'open']

	def is_open(self, user=None):
		is_open = None
		if user and (user.is_superuser or user.groups.filter(name='junta').exists()):
			is_open = self.state in ['open', 'preview']
		else:
			is_open = self.state in ['open']

		return is_open and (date.today() >= self.reg_start_date) and (date.today() <= self.league_end_date)

	def is_waitlist(self, user=None):
		return self.is_open(user) and ((date.today() >= self.waitlist_start_date) or (len(self.get_complete_registrations()) >= self.max_players))

	def __unicode__(self):
		return ('%s %d %s' % (self.season, self.year, self.night)).replace('_', ' ')


class FieldLeague(models.Model):
	id = models.AutoField(primary_key=True)
	league = models.ForeignKey('leagues.League')
	field = models.ForeignKey('leagues.Field')

	class Meta:
		db_table = u'field_league'


class Player(PybbProfile):
	GENDER_CHOICES = (
		('M',	'Male'),
		('F',	'Female'),
	)

	user = models.ForeignKey(User, db_column='id')
	groups = models.TextField()
	nickname = models.CharField(max_length=90)
	phone = models.CharField(max_length=45)
	street_address = models.CharField(max_length=765)
	city = models.CharField(max_length=127)
	state = models.CharField(max_length=6)
	zipcode = models.CharField(max_length=15)
	gender = models.CharField(max_length=1, choices=GENDER_CHOICES)
	height_inches = models.IntegerField()
	highest_level = models.TextField()
	birthdate = models.DateField(help_text='e.g. ' + date.today().strftime('%Y-%m-%d'))
	jersey_size = models.CharField(max_length=45, help_text='XS, S, M, L, XL, XXL')

	class Meta:
		db_table = u'player'

	def get_spirit(self):
		return self.user.skills.exclude(spirit=0)

	def get_age(self, now=None):
		if not self.birthdate:
			return 0
		if now is None:
			now = date.today()
		return (now.year - self.birthdate.year) - int((now.month, now.day) < (self.birthdate.month, self.birthdate.day))


class Baggage(models.Model):
	id = models.AutoField(primary_key=True)

	class Meta:
		db_table = u'baggage'

	def get_registrations(self):
		return self.registrations_set.all()

	@property
	def num_registrations(self):
		return self.registrations_set.all().count()

	def __unicode__(self):
		return '%d' % (self.id)


class Registrations(models.Model):
	REGISTRATION_PAYMENT_CHOICES = (
		('check',	'Check'),
		('paypal',	'PayPal'),
	)

	REGISTRATION_CAPTAIN_CHOICES = (
		(0, u'I refuse to captain.'),
		(1, u'I will captain if absolutely necessary.'),
		(2, u'I am willing to captain.'),
		(3, u'I would like to captain.'),
		(4, u'I will be very sad if I don\'t get to captain.'),
	)

	id = models.AutoField(primary_key=True)
	user = models.ForeignKey(User)
	league = models.ForeignKey('leagues.League')
	baggage = models.ForeignKey('leagues.Baggage', null=True, blank=True)
	created = models.DateTimeField(auto_now_add=True)
	updated = models.DateTimeField(auto_now=True)
	registered = models.DateTimeField(null=True, blank=True)
	conduct_complete = models.BooleanField()
	waiver_complete = models.BooleanField()
	pay_type = models.CharField(choices=REGISTRATION_PAYMENT_CHOICES, max_length=6, null=True, blank=True)
	check_complete = models.BooleanField()
	paypal_invoice_id = models.CharField(max_length=127, null=True, blank=True)
	paypal_complete = models.BooleanField()
	refunded = models.BooleanField()
	waitlist = models.BooleanField()
	attendance = models.IntegerField(null=True, blank=True)
	captain = models.IntegerField(null=True, blank=True, choices=REGISTRATION_CAPTAIN_CHOICES)

	class Meta:
		db_table = u'registrations'
		verbose_name_plural = 'registrations'

	def get_status(self):
		status = 'New'
		if self.refunded:
			status = 'Refunded'
		elif self.conduct_complete:
			status = 'Conduct Completed'
			if self.waiver_complete:
				status = 'Waiver Completed'
				if self.attendance != None and self.captain != None:
					status = 'Attendance Completed'

					if self.league.check_price == 0 and self.league.paypal_price == 0:
						status = 'Registration Completed'

					else:
						if self.pay_type == 'check' and not self.check_complete:
							status = 'Waiting for Check'
						elif self.pay_type == 'check' and self.check_complete:
							status = 'Check Completed'
						elif self.pay_type == 'paypal' and not self.paypal_complete:
							status = 'Waiting for Paypal'
						elif self.pay_type == 'paypal' and self.paypal_complete:
							status = 'Paypal Completed'
		return status

	def get_progress(self):
		percentage = 0
		interval = 20

		if self.league.check_price == 0 and self.league.paypal_price == 0:
			interval = 25

		if self.conduct_complete:
			percentage += interval
			if self.waiver_complete:
				percentage += interval
				if self.attendance != None and self.captain != None:
					percentage += interval

					if self.league.check_price == 0 and self.league.paypal_price == 0:
						percentage += interval

					elif self.pay_type:
						percentage += interval
						if self.check_complete or self.paypal_complete:
							percentage += interval

		return percentage

	def is_complete(self):
		return bool(self.conduct_complete and \
			self.waiver_complete and \
			self.attendance != None and \
			self.captain != None and \
			((self.league.check_price == 0 and self.league.paypal_price == 0) or \
			(self.pay_type and 	(self.check_complete or self.paypal_complete))) and \
			not self.refunded)

	@property
	def baggage_size(self):
		if self.baggage:
			return self.baggage.num_registrations
		return 0

	@transaction.commit_on_success
	def add_to_baggage_group(self, email):
		if date.today() > self.league.waitlist_start_date:
			return 'You may not edit a baggage group after the group change deadline (' + self.league.waitlist_start_date.strftime('%Y-%m-%d') + ').'

		if self.user.email == email:
			return 'You cannot form a baggage group with yourself.'

		if not self.is_complete():
			return 'Your registration is currently incomplete and is ineligible to form baggage groups.'

		if self.waitlist:
			return 'You are currently on the waitlist and are ineligible to form baggage groups.'

		try:
			registration = Registrations.objects.get(user__email=email, league=self.league)
		except ObjectDoesNotExist:
			return 'No registration found for ' + email + '.'

		if not registration.is_complete():
			return email + ' has an incomplete registration and is ineligible to form baggage groups.'

		if registration.waitlist:
			return email + ' is currently on the waitlist and is ineligible to form baggage groups.'

		baggage_limit = self.league.baggage

		current_baggage = self.baggage
		current_baggage_registrations = current_baggage.get_registrations()

		target_baggage = registration.baggage

		if target_baggage == current_baggage:
			return email + ' is already part of your baggage group.'

		if (current_baggage_registrations.count() + target_baggage.num_registrations) > baggage_limit:
			return 'Baggage group with ' + email + ' exceeds limit.'

		for current_baggage_registration in current_baggage_registrations:
			current_baggage_registration.baggage = target_baggage
			current_baggage_registration.save()

		current_baggage.delete()

		return True


	@transaction.commit_manually
	def leave_baggage_group(self):
		if date.today() > self.league.waitlist_start_date:
			return 'You may not edit a baggage group after the group change deadline (' + self.league.waitlist_start_date.strftime('%Y-%m-%d') + ').'

		try:
			baggage = Baggage()
			baggage.save()

			if (self.baggage.get_registrations().count() <= 1):
				self.baggage.delete()

			self.baggage = baggage
			self.save()

		except:
			transaction.rollback()
			return False
		else:
			transaction.commit()

		return True


	def __unicode__(self):
		return '%d %s %s - %s %s' % (self.league.year, self.league.season, self.league.night, self.user, self.get_status())


class Team(models.Model):
	id = models.AutoField(primary_key=True)
	name = models.CharField(max_length=128)
	color = models.CharField(max_length=96)
	email = models.CharField(max_length=128)
	league = models.ForeignKey('leagues.League')

	class Meta:
		db_table = u'team'

	@property
	def size(self):
		return self.teammember_set.all().count()

	@property
	def css_background_color(self):
		if 'black' in self.color.lower():
			return '#2C3E50'
		if 'blue' in self.color.lower():
			return '#3498DB'
		if 'green' in self.color.lower():
			return '#2ECC71'
		if 'orange' in self.color.lower():
			return '#E67E22'
		if 'pink' in self.color.lower():
			return '#EE6FA0'
		if 'purple' in self.color.lower():
			return '#9B59B6'
		if 'red' in self.color.lower():
			return '#E74C3C'
		if 'white' in self.color.lower():
			return '#FFFFFF'
		if 'yellow' in self.color.lower():
			return '#F1C40F'
		return '#95A5A6'

	@property
	def css_text_color(self):
		if 'white' in self.color.lower():
			return '#2C3E50'
		return '#FFFFFF'

	def get_members(self):
		return self.teammember_set.all()

	def get_male_members(self):
		return self.get_members().filter(user__player__gender__iexact='M')

	def get_female_members(self):
		return self.get_members().filter(user__player__gender__iexact='F')

	def on_team(self, user):
		return bool(self.teammember_set.filter(user=user))

	def get_games(self):
		return Game.objects.filter(gameteams__team=self)

	def get_record_list(self):
		# return in format {wins, losses, ties, conflicts}
		team_record = {'wins': 0, 'losses': 0, 'ties': 0, 'conflicts': 0, 'blanks': 0, 'points_for': 0, 'points_against': 0}

		games = self.get_games()
		for game in games:

			team_reports = game.gamereport_set.filter(team=self)
			opponent_reports = game.gamereport_set.exclude(team=self)
			points_for = float(0)
			points_against = float(0)
			report_count = float(team_reports.count() + opponent_reports.count())

			team_result = 0
			for report in team_reports:
				team_score = report.gamereportscore_set.filter(team=self)[0].score
				opponent_score = report.gamereportscore_set.exclude(team=self)[0].score

				points_for += team_score
				points_against += opponent_score

				if team_score > opponent_score:
					# team win
					team_result = 1
				elif team_score < opponent_score:
					# team loss
					team_result = 2
				else:
					# tie
					team_result = 3

			opponent_result = 0
			for report in opponent_reports:
				team_score = report.gamereportscore_set.filter(team=self)[0].score
				opponent_score = report.gamereportscore_set.exclude(team=self)[0].score

				points_for += team_score
				points_against += opponent_score

				if team_score > opponent_score:
					# win
					opponent_result = 1
				elif team_score < opponent_score:
					# loss
					opponent_result = 2
				else:
					# tie
					opponent_result = 3

			if (team_result == 1 and opponent_result == 1) or \
				(team_result == 1 and opponent_result == 0) or \
				(opponent_result == 1 and team_result == 0):

				team_record['wins'] += 1

			elif (team_result == 2 and opponent_result == 2) or \
				(team_result == 2 and opponent_result == 0) or \
				(opponent_result == 2 and team_result == 0):

				team_record['losses'] += 1

			elif (team_result == 3 and opponent_result == 3) or \
				(team_result == 3 and opponent_result == 0) or \
				(opponent_result == 3 and team_result == 0):

				team_record['ties'] += 1

			elif team_result != opponent_result and \
				team_result != 0 and \
				opponent_result != 0:

				team_record['conflicts'] += 1

			else:

				team_record['blanks'] += 1

			if report_count > 1:
				points_for /= report_count
				points_against /= report_count

			team_record['points_for'] += points_for
			team_record['points_against'] += points_against

		return team_record


	def player_survey_complete(self, user):
		skill_reports = self.skillsreport_set.annotate(num_skills=Count('skills')).filter(submitted_by=user)
		# since you don't rate yourself, looking for a skill report and teamsize - 1 skill entries
		return bool(skill_reports.count() > 0) and \
			bool(skill_reports.filter(num_skills__gte=self.size - 1).count() > 0)

	def __unicode__(self):
		return '%s (%s)' % (self.name, self.color)


class TeamMember(models.Model):
	id = models.AutoField(primary_key=True)
	team = models.ForeignKey('leagues.Team')
	user = models.ForeignKey(User)
	captain = models.BooleanField()

	class Meta:
		db_table = u'team_member'
		ordering = ['-captain', 'user__last_name']

	def __unicode__(self):
		return '%s %s' % (self.user.first_name, self.user.last_name)


class Game(models.Model):
	id = models.AutoField(primary_key=True)
	date = models.DateField()
	field_name = models.ForeignKey('leagues.FieldNames')
	league = models.ForeignKey('leagues.league')

	class Meta:
		db_table = u'game'
		ordering = ['-date', 'field_name']

	def get_teams(self):
		return Team.objects.filter(gameteams__game=self).all()

	def get_user_team(self, user):
		return self.gameteams_set.filter(team__teammember__user=user)[0:1].get().team

	def get_user_opponent(self, user):
		try:
			return self.gameteams_set.exclude(team__teammember__user=user)[0:1].get().team
		except ObjectDoesNotExist:
			return None

	def get_reports(self):
		return self.gamereport_set.all()

	def get_report_for_team(self, team):
		return self.gamereport_set.filter(team=team)

	def report_complete_for_team(self, user):
		for report in self.gamereport_set.filter(team__teammember__user=user, team__teammember__captain=1):
			if (report.is_complete):
				return True
		return False

	def report_complete_for_user(self, user):
		for report in self.gamereport_set.filter(last_updated_by=user, team__teammember__user=user, team__teammember__captain=1):
			if (report.is_complete):
				return report.game.id
		return False

	def __unicode__(self):
		return '%s - %s' % (self.date, self.league)


class GameTeams(models.Model):
	id = models.AutoField(primary_key=True)
	game = models.ForeignKey('leagues.Game')
	team = models.ForeignKey('leagues.Team')

	class Meta:
		db_table = u'game_teams'


class SkillsType(models.Model):
	id = models.AutoField(primary_key=True)
	description = models.TextField()
	weight = models.FloatField()

	class Meta:
		db_table = u'skills_type'


class SkillsReport(models.Model):
	id = models.AutoField(primary_key=True)
	submitted_by = models.ForeignKey(User, related_name='skills_report_submitted_by_set')
	team = models.ForeignKey('leagues.Team')
	updated = models.DateTimeField()

	class Meta:
		db_table = u'skills_report'

	def __unicode__(self):
		return '%s, %s, %s' % (self.team, self.team.league, self.submitted_by)


class Skills(models.Model):
	id = models.AutoField(primary_key=True)
	skills_report = models.ForeignKey('leagues.SkillsReport')
	highest_level = models.TextField()
	athletic = models.PositiveIntegerField(default=0)
	experience = models.PositiveIntegerField(default=0)
	forehand = models.PositiveIntegerField(default=0)
	backhand = models.PositiveIntegerField(default=0)
	receive = models.PositiveIntegerField(default=0)
	strategy = models.PositiveIntegerField(default=0)
	skills_type = models.ForeignKey('leagues.SkillsType')
	user = models.ForeignKey(User)
	submitted_by = models.ForeignKey(User, related_name='skills_submitted_by_set')
	updated = models.DateField()
	spirit = models.PositiveIntegerField(default=0)
	not_sure = models.BooleanField()

	class Meta:
		db_table = u'skills'
		verbose_name_plural = 'skills'

	def __unicode__(self):
		return '%s %s <- %s' % (str(self.updated), self.user, self.submitted_by)
