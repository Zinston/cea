# -*- coding: utf-8 -*-
# !/usr/bin/env python

import webapp2
import jinja2
import os
import logging
import re
from google.appengine.ext import db
from google.appengine.api import memcache
from google.appengine.api import mail
from google.appengine.runtime import apiproxy_errors
import datetime
import time
import json
import unicodedata

##########
# GLOBAL #
##########

template_dir = os.path.join(os.path.dirname(__file__), 'templates')
jinja_env = jinja2.Environment(loader=jinja2.FileSystemLoader(template_dir),
                               autoescape=True)
PLAINTE_EN_COURS = None


def render_str(template, **params):
    t = jinja_env.get_template(template)
    return t.render(params)


# HANDLER
class Handler(webapp2.RequestHandler):
    def write(self, *a, **kw):
        self.response.out.write(*a, **kw)

    def render_str(self, template, **params):
        return render_str(template, **params)

    def render(self, template, **kw):
        self.write(self.render_str(template, **kw))

    def initialize(self, *a, **kw):
        webapp2.RequestHandler.initialize(self, *a, **kw)

    # Returns list of all Membres_du_CE db entries
    def membres_list(self):
        return list(m.prenom + " " + m.nom for m in cached_membres())

    def p_en_cours_from_num(self, num=None):
        """Takes Plainte.numero string (##-####)
           Stores (first) corresponding Plainte
           db entry in global variable PLAINTE_EN_COURS
           Returns boolean (True if success)"""
        global PLAINTE_EN_COURS
        plaintes = list(cached_plaintes())
        for p in plaintes:
            if p.numero == num:
                PLAINTE_EN_COURS = p
                key = str(PLAINTE_EN_COURS.key().id())
                return True

    def test_num_exists(self, num=None):
        """Takes a Plainte.numero string (##-####)
           Returns boolean (True if there is a
           corresponding Plainte db entry)"""
        plaintes = list(cached_plaintes())
        for p in plaintes:
            if p.numero == num:
                return True


###################
# CACHE FUNCTIONS #
###################

def latest_plaintes(update=False):
    """CACHE set & get for MAINPAGE"""
    key = 'latest'
    plaintes = memcache.get(key)
    if plaintes is None or update:
        logging.debug("DB QUERY : latest_plaintes")
        plaintes = db.GqlQuery("select * from Plainte "
                               "where date_de_classement > :1 "
                               "order by date_de_classement desc "
                               "limit 10 ",
                               None)
        memcache.set(key, plaintes)
    else:
        print("latest_plaintes retrieved from cache")
    return plaintes


def permalinked_plainte(key="", plainte=None, update=False):
    """CACHE set & get for PLAINTEPAGE (permalink)"""
    print("key = " + key)
    if plainte is None or update:
        logging.debug("DB QUERY : permalinked_plainte")
        if plainte is None:
            plainte = db.get(key)
        memcache.set(key, plainte)
    else:
        logging.debug("permalinked_plainte retrieved from cache")
    return plainte


def json_page(update=False):
    """CACHE set & get for JSONPAGE (RegleHandler)"""
    key = 'json'
    json = memcache.get(key)
    if json is None or update:
        logging.debug("DB QUERY : json_page")
        json = db.GqlQuery("select * from RegleJSON").get()
        memcache.set(key, json)
    else:
        logging.debug("json_page retrieved from cache")
    return json


def plaintes_en_cours(update=False):
    """CACHE set & get for ENCOURS"""
    key = 'encours'
    plaintes = memcache.get(key)
    if plaintes is None or update:
        logging.debug("DB QUERY : plaintes_en_cours")
        plaintes = db.GqlQuery("SELECT * from Plainte "
                               "WHERE date_de_classement = :1 "
                               "ORDER by numero desc ",
                               None)
        memcache.set(key, plaintes)
    else:
        logging.debug("plaintes_en_cours retrieved from cache")
    return plaintes


def cached_plaintes(update=False):
    """CACHE set & get for everything"""
    key = 'recherchenum'
    plaintes = memcache.get(key)
    if plaintes is None or update:
        logging.debug("DB QUERY : cached_plaintes")
        plaintes = Plainte.all().order('-numero')
        memcache.set(key, plaintes)
    else:
        logging.debug("cached_plaintes retrieved from cache")
    return plaintes


def cached_membres(update=False):
    """2- membres du CE"""
    key = 'recherchemembre'
    membres = memcache.get(key)
    if membres is None or update:
        logging.debug("DB QUERY : cached_membres")
        membres = Membres_du_CE.all().order('prenom')
        memcache.set(key, membres)
    else:
        logging.debug("cached_membres retrieved from cache")
    return membres


def cached_regles(update=False):
    """3- regles"""
    key = 'rechercheregle'
    regles = memcache.get(key)
    if regles is None or update:
        logging.debug("DB QUERY : cached_regles")
        regles = Regle.all().order('nrdec')
        memcache.set(key, regles)
    else:
        logging.debug("cached_regles retrieved from cache")
    return regles


##########
# MODELS #
##########

class JsonProperty(db.TextProperty):
    """CUSTOM DATA TYPE TO STORE JSON IN DATASTORE"""
    def validate(self, value):
        return value

    def get_value_for_datastore(self, model_instance):
        result = super(JsonProperty, self)
        result = result.get_value_for_datastore(model_instance)
        result = json.dumps(result)
        return db.Text(result)

    def make_value_from_datastore(self, value):
        try:
            value = json.loads(str(value))
        except:
            pass
        return super(JsonProperty, self).make_value_from_datastore(value)


class Membres_du_CE(db.Model):
    """NOMS DES MEMBRES DU CE"""
    nom = db.StringProperty(required=True)
    prenom = db.StringProperty(required=True)


class Regle(db.Model):
    """REGLES"""
    nr = db.StringProperty(required=True)
    nrdec = db.FloatProperty()
    titre = db.StringProperty()
    regletxt = db.TextProperty()
    date = db.DateTimeProperty()

    def render(self):
        self._render_regle = self.regletxt.replace('\n', '<br>')
        return render_str("regle.html", r=self)

    def to_dict(model):
        SIMPLE_TYPES = (int, long, float, bool, dict, basestring, list)
        output = {}

        for key, prop in model.properties().iteritems():
            value = getattr(model, key)
            if value is None or isinstance(value, SIMPLE_TYPES):
                output[key] = value
            elif isinstance(value, datetime.datetime):
                ms = time.mktime(value.utctimetuple()) * 1000
                ms += getattr(value, 'microseconds', 0) / 1000
                output[key] = int(ms)
            elif isinstance(value, db.GeoPt):
                output[key] = {'lat': value.lat, 'lon': value.lon}
            elif isinstance(value, db.Model):
                output[key] = to_dict(value)
            else:
                raise ValueError('cannot encode ' + repr(prop))

        return output


class RegleJSON(db.Model):
    """JSON STORE FOR REGLE"""
    json = JsonProperty()


class Plainte(db.Model):
    """PLAINTES"""
    numero = db.StringProperty(required=True)
    date_de_reception = db.DateTimeProperty()
    date_de_classement = db.DateTimeProperty()
    rapport = db.TextProperty()
    accuse = db.StringProperty()
    accusation = db.TextProperty()
    declaration = db.StringProperty()
    sanction = db.TextProperty()
    presente_au_ce = db.DateTimeProperty()

    def render(self, to_print=False, i=0, en_cours=False):
        self._render_rapport = self.rapport.replace('\n', '<br>')
        regles = Regle.all()
        regles.order("nrdec")
        return render_str("plainte.html",
                          p=self,
                          to_print=to_print,
                          i=i,
                          en_cours=en_cours,
                          regles=regles)


class PlainteSupprimee(db.Model):
    """IDENTICAL TO PLAINTE BUT FOR ARCHIVING THE DELETED ONES"""
    numero = db.StringProperty(required=True)
    date_de_reception = db.DateTimeProperty()
    date_de_classement = db.DateTimeProperty()
    rapport = db.TextProperty()
    accuse = db.StringProperty()
    accusation = db.TextProperty()
    declaration = db.StringProperty()
    sanction = db.TextProperty()
    presente_au_ce = db.DateTimeProperty()

    def render(self, to_print=False, i=0, en_cours=False):
        self._render_rapport = self.rapport.replace('\n', '<br>')
        regles = Regle.all()
        regles.order('nrdec')
        return render_str("plainte.html",
                          p=self,
                          to_print=to_print,
                          i=i,
                          en_cours=en_cours,
                          regles=regles)


#########
# PAGES #
#########

class RegleHandler(Handler):
    def get(self):
        jsonentity = json_page()
        self.response.out.write(jsonentity.json)


class NouveauMembre(Handler):
    """ADD A MEMBER"""
    def get(self):
        self.render("nouveaumembre.html")

    def post(self):
        nom = self.request.get("nom")
        prenom = self.request.get("prenom")
        if nom and prenom:
            self.add(nom, prenom)
            commu = prenom + " " + nom
            commu += u" a été ajouté(e) à la liste "
            commu += "des membres de l'Ecole Autonome."
            self.render("cea.html", commu=commu)
        else:
            error = u"Tous les champs doivent être complétés."
            self.render("nouveaumembre.html", commu=error, error=error)

    def add(self, nom, prenom):
        m = Membres_du_CE(nom=nom, prenom=prenom)
        m.put()
        cached_membres(update=True)


class NouvelleRegle(Handler):
    """ADD A REGLE"""
    def get(self):
        self.render("nouvelleregle.html")

    def post(self):
        nr = self.request.get("nr")
        titre = self.request.get("titre")
        regletxt = self.request.get("regletxt")

        if nr and titre and regletxt:
            r = self.add(nr, titre, regletxt)
            self.mkjson(r)
            commu = u"La règle " + r.nr
            commu += u" a bien été encodée dans la base de données."
            self.render("reglepage.html", r=r, commu=commu)
        else:
            error = u"Tous les champs doivent être complétés."
            self.render("nouvelleregle.html", commu=error, error=error)

    def add(self, nr, titre, regletxt):
        """Put the encoded rule in the db and update json version"""
        nrdec = 9999
        if self.is_number(nr):
            nrdec = float(nr)
            r = Regle(nr=nr,
                      titre=titre,
                      regletxt=regletxt,
                      date=datetime.datetime.now(),
                      nrdec=nrdec)
            self.mkjson(r)
            r.put()
            cached_regles(update=True)
            return r

    def mkjson(self, nregle=None):
        """Updates the json version, taking a Regle entry as a parameter."""
        old_json = None
        old_json = db.GqlQuery("select * from RegleJSON").get()

        regles = Regle.all()
        logging.debug("DB QUERY : mkjson")
        jsondict = [r.to_dict() for r in regles]
        jsondict.append(nregle.to_dict())
        jsonfile = json.dumps(jsondict)
        logging.debug(nregle.nr + " added to jsonfile")

        if old_json:
            old_json.json = jsonfile
            old_json.put()
            json_page(update=True)
        else:
            new_json = RegleJSON(json=jsonfile)
            new_json.put()
            json_page(update=True)

    def is_number(self, s):
        """Takes a variable
           Returns True if the variable is a number"""
        try:
            float(s)
            return True
        except ValueError:
            return False


class NouvellePlainte(Handler):
    """ADD A PLAINTE"""
    def get(self):
        global PLAINTE_EN_COURS
        PLAINTE_EN_COURS = None
        examen = None
        regles = Regle.all()
        logging.debug("DB QUERY : Regle.all() from NouvellePlainte")
        regles.order('nrdec')

        # To edit work in progress
        # ------------------------

        num = self.request.get('num')
        if num:
            a = self.p_en_cours_from_num(num=num)
            if not a:
                logging.error("Erreur : num n'est pas valide")
                self.redirect("/nouvelleplainte")

        if PLAINTE_EN_COURS:
            numero = PLAINTE_EN_COURS.numero
            rapport = PLAINTE_EN_COURS.rapport
            if PLAINTE_EN_COURS.accuse:
                accuse = PLAINTE_EN_COURS.accuse.split('|')
                accusation = PLAINTE_EN_COURS.accusation.split('|')
                declaration = PLAINTE_EN_COURS.declaration.split('|')
                sanction = PLAINTE_EN_COURS.sanction.split('|')
            else:
                accuse = None
                accusation = None
                declaration = None
                sanction = None

            self.render("nouvelleplainte.html",
                        regles=regles,
                        new=True,
                        examen=examen,
                        membres_lst=self.membres_list(),
                        numero=numero,
                        rapport=rapport,
                        accuse=accuse,
                        accusation=accusation,
                        declaration=declaration,
                        sanction=sanction)

        # To start working on a new complaint
        # -----------------------------------

        else:
            lastnumero = None
            p = cached_plaintes().get()
            if p:
                lastnumero = p.numero

            self.render("nouvelleplainte.html",
                        regles=regles,
                        new=True,
                        lastnumero=lastnumero,
                        membres_lst=self.membres_list())

    def post(self):
        """Retrieving data from form"""

        numero_int = self.request.get("numero")
        numero = str(datetime.datetime.now().strftime("%y"))
        numero += "-" + str(str(numero_int).zfill(4))
        rapport = self.request.get("rapport")
        regles = Regle.all()
        regles.order('nrdec')

        accuse = []
        accusation = []
        declaration = []
        sanction = []
        i = 0
        while self.request.get("accuse"+str(i)):
            accuse.append(self.request.get("accuse"+str(i)))

            accusation_params = self.request.params.getall("accusation"+str(i))
            accusation_to_append = u'£'.join(accusation_params)
            accusation.append(accusation_to_append)

            declaration.append(self.request.get("declaration"+str(i)))
            sanction.append(self.request.get("sanction"+str(i)))
            i = i+1
        if self.request.get("accuse"):
            accuse.append(self.request.get("accuse"))

            accusation_params = self.request.params.getall("accusation")
            accusation_to_append = u'£'.join(accusation_params)
            accusation.append(accusation_to_append)

            declaration.append(self.request.get("declaration"))
            sanction.append(self.request.get("sanction"))

        # Which button was pressed ?
        # --------------------------

        examen = self.request.get("examen")
        sauver = self.request.get("sauver")
        classer = self.request.get("classer")
        i = 0
        supprimer = None
        for a in accuse:
            if self.request.get("supprimer" + str(i)):
                supprimer = i
                i += 1
            if self.request.get("supprimernew"):
                supprimer = -1

        global PLAINTE_EN_COURS

        if sauver:
            if numero and numero != 0:
                key = self.sauver(numero=numero,
                                  rapport=rapport,
                                  accuse=accuse,
                                  accusation=accusation,
                                  declaration=declaration,
                                  sanction=sanction)
                self.redirect('/%s' % key)
            else:
                msg = u"Encodage incomplet, "
                msg += "le numéro de la plainte doit être encodé."
                self.render("nouvelleplainte.html",
                            regles=regles,
                            examen=examen,
                            membres_lst=self.membres_list(),
                            rapport=rapport,
                            accuse=accuse,
                            accusation=accusation,
                            declaration=declaration,
                            sanction=sanction,
                            commu=msg,
                            error=msg)
        elif examen:
            if numero and rapport:
                self.render("nouvelleplainte.html",
                            regles=regles,
                            num=numero,
                            examen=examen,
                            membres_lst=self.membres_list(),
                            numero=numero,
                            rapport=rapport,
                            accuse=accuse,
                            accusation=accusation,
                            declaration=declaration,
                            sanction=sanction)
            elif numero:
                examen = None
                msg = u"Encodage incomplet. "
                msg += "Il est interdit de mettre "
                msg += "une personne en examen sans rapport."
                self.render("nouvelleplainte.html",
                            regles=regles,
                            examen=examen,
                            membres_lst=self.membres_list(),
                            numero=numero,
                            rapport=rapport,
                            accuse=accuse,
                            accusation=accusation,
                            declaration=declaration,
                            sanction=sanction,
                            commu=msg,
                            error=msg)
            else:
                examen = None
                msg = u"Encodage incomplet. "
                msg += "Le numéro et le rapport sont "
                msg += "obligatoires avant mise en examen."
        elif classer:
            if numero and rapport:
                self.classer(numero=numero,
                             rapport=rapport,
                             accuse=accuse,
                             accusation=accusation,
                             declaration=declaration,
                             sanction=sanction)
            elif numero:
                msg = u"Encodage incomplet. "
                msg += "Il faut un rapport avant de classer une plainte."
                self.render("nouvelleplainte.html",
                            regles=regles,
                            examen=examen,
                            membres_lst=self.membres_list(),
                            numero=numero,
                            rapport=rapport,
                            accuse=accuse,
                            accusation=accusation,
                            declaration=declaration,
                            sanction=sanction,
                            commu=msg,
                            error=msg)
            else:
                msg = "Encodage incomplet. "
                msg += "Le numéro et le rapport sont "
                msg += "obligatoires avant de classer une plainte."
                self.render("nouvelleplainte.html",
                            regles=regles,
                            examen=examen,
                            membres_lst=self.membres_list(),
                            numero=numero,
                            rapport=rapport,
                            accuse=accuse,
                            accusation=accusation,
                            declaration=declaration,
                            sanction=sanction,
                            commu=msg,
                            error=msg)
        elif supprimer or supprimer == 0:
            del accuse[supprimer]
            del accusation[supprimer]
            del declaration[supprimer]
            del sanction[supprimer]
            self.render("nouvelleplainte.html",
                        regles=regles,
                        num=numero,
                        examen=examen,
                        membres_lst=self.membres_list(),
                        numero=numero,
                        rapport=rapport,
                        accuse=accuse,
                        accusation=accusation,
                        declaration=declaration,
                        sanction=sanction)
        else:
            msg = "Incapable d'identifier le bouton."
            self.render("nouvelleplainte.html",
                        regles=regles,
                        examen=examen,
                        membres_lst=self.membres_list(),
                        numero=numero,
                        rapport=rapport,
                        accuse=accuse,
                        accusation=accusation,
                        declaration=declaration,
                        sanction=sanction,
                        commu=msg,
                        error=msg)

    def sauver(self,
               classer=False,
               numero=None,
               rapport=None,
               accuse=None,
               accusation=None,
               declaration=None,
               sanction=None):
        global PLAINTE_EN_COURS
        date_de_reception = None
        date_de_classement = None

        # if not accuse then first "mise en examen"
        if accuse:
            accuse = '|'.join(accuse)
            accusation = '|'.join(accusation)
            declaration = '|'.join(declaration)
            sanction = '|'.join(sanction)
        else:
            accuse = None
            accusation = None
            declaration = None
            sanction = None

        if PLAINTE_EN_COURS:
            PLAINTE_EN_COURS.rapport = rapport
            PLAINTE_EN_COURS.accuse = accuse
            PLAINTE_EN_COURS.accusation = accusation
            PLAINTE_EN_COURS.declaration = declaration
            PLAINTE_EN_COURS.sanction = sanction
            if classer:
                PLAINTE_EN_COURS.date_de_classement = datetime.datetime.now()
        else:
            date_de_reception = datetime.datetime.now()
            if classer:
                date_de_classement = datetime.datetime.now()
            PLAINTE_EN_COURS = Plainte(numero=numero,
                                       rapport=rapport,
                                       accuse=accuse,
                                       accusation=accusation,
                                       declaration=declaration,
                                       sanction=sanction,
                                       date_de_reception=date_de_reception,
                                       date_de_classement=date_de_classement)

        PLAINTE_EN_COURS.put()
        key = str(PLAINTE_EN_COURS.key().id())
        plaintes_en_cours(update=True)
        cached_plaintes(update=True)
        permalinked_plainte(key=key, plainte=PLAINTE_EN_COURS, update=True)
        PLAINTE_EN_COURS = None
        return key

    def classer(self,
                numero=None,
                rapport=None,
                accuse=None,
                accusation=None,
                declaration=None,
                sanction=None):
        key = self.sauver(classer=True,
                          numero=numero,
                          rapport=rapport,
                          accuse=accuse,
                          accusation=accusation,
                          declaration=declaration,
                          sanction=sanction)
        latest_plaintes(update=True)
        self.redirect('/%s' % key)


# TRAVAIL EN COURS
class EnCours(Handler):
    def get(self):
        plaintes = plaintes_en_cours()
        if plaintes:
            plaintes_lst = list(plaintes)

        self.render('/encours.html',
                    plaintes_lst=plaintes_lst,
                    to_print=-1,
                    en_cours=True)

    def post(self):
        num = self.request.get("plaintenum")
        self.redirect('/nouvelleplainte?num=' + num)


class PlaintePage(Handler):
    def get(self, plainte_id):
        key = db.Key.from_path('Plainte', int(plainte_id))
        strkey = str(key)
        plainte = permalinked_plainte(strkey)
        if not plainte:
            self.error(404)
            return
        self.render("permalink.html", plainte=plainte, key=key)

    def post(self, plainte_id):
        key = db.Key.from_path('Plainte', int(plainte_id))
        plainte = db.get(key)

        if self.request.get("supprimer"):
            commu = u"La plainte #" + plainte.numero + u" a été supprimée."
            self.supprimer(plainte)
            self.render("cea.html", commu=commu)
        else:
            self.modifier(plainte)

    def modifier(self, plainte):
        self.redirect('/nouvelleplainte?num=' + plainte.numero)

    def supprimer(self, plainte):
        p = PlainteSupprimee(numero=plainte.numero,
                             date_de_reception=plainte.date_de_reception,
                             rapport=plainte.rapport,
                             accuse=plainte.accuse,
                             accusation=plainte.accusation,
                             declaration=plainte.declaration,
                             sanction=plainte.sanction,
                             date_de_classement=plainte.date_de_classement,
                             presente_au_ce=plainte.presente_au_ce)
        p.put()
        db.delete(plainte)

    def retablir(self, plainte_supprimee):
        p = Plainte(numero=plainte_supprimee.numero,
                    date_de_reception=plainte_supprimee.date_de_reception,
                    rapport=plainte_supprimee.rapport,
                    accuse=plainte_supprimee.accuse,
                    accusation=plainte_supprimee.accusation,
                    declaration=plainte_supprimee.declaration,
                    sanction=plainte_supprimee.sanction,
                    date_de_classement=plainte_supprimee.date_de_classement,
                    presente_au_ce=plainte_supprimee.presente_au_ce)
        p.put()
        db.delete(plainte_supprimee)


class RecherchePage(Handler):
    def get(self):
        num_lst = list(p.numero for p in cached_plaintes())
        membres_lst = list(m.prenom + " " + m.nom for m in cached_membres())
        regles = cached_regles()

        err_noselect = ""
        if self.request.get('err') == "noselect":
            err_noselect = u"Merci de sélectionner "
            err_noselect += "quelque chose si vous "
            err_noselect += "voulez faire une recherche..."

        self.render('recherche.html',
                    num_lst=num_lst,
                    membres_lst=membres_lst,
                    regles=regles,
                    commu=err_noselect)

    def post(self):
        num = self.request.get("numsearch")
        name = self.request.get("namesearch")
        rule = self.request.get("rulesearch")

        pres = self.request.get("presenter")
        to_print = self.request.get("toprint")

        if not num and not name and not rule and not pres:
            self.error_noselect()
        if num:
            return self.par_numero(num)
        if pres:
            return self.a_presenter(to_print)

        titre = ""
        plaintes = list(cached_plaintes())
        plaintes_lst = []

        if name:
            for p in plaintes:
                if p.accuse and name in p.accuse and p.date_de_classement:
                    plaintes_lst.append(p)
            plaintes = plaintes_lst
            titre = "Dossier de litiges de " + name

        r = None
        if rule != "":
            plaintes_lst = []
            num_accuse = 0
            for p in plaintes:
                if p.accusation and p.date_de_classement:
                    if name:
                        accuses = p.accuse.split(u'|')
                        i = 0
                        for accuse in accuses:
                            if accuse == name:
                                num_accuse = i
                            i += 1
                    accusationsindividuelles = p.accusation.split(u'|')
                    if name:
                        i = 0
                        for accusationi in accusationsindividuelles:
                            if i == num_accuse:
                                accusationsplit = accusationi.split(u'£')
                                for acc in accusationsplit:
                                    if acc == rule and p not in plaintes_lst:
                                        plaintes_lst.append(p)
                            i += 1
                    else:
                        for accusationi in accusationsindividuelles:
                            accusationsplit = accusationi.split(u'£')
                            for acc in accusationsplit:
                                if acc == rule and p not in plaintes_lst:
                                    plaintes_lst.append(p)
            regles = list(cached_regles())
            regle_lst = []
            for regle in regles:
                if regle.nr == rule:
                    regle_lst.append(regle)
            if name:
                titre = "Infractions de " + name + " "
            else:
                titre = "Infractions connues "
            titre = titre + u"à la règle " + rule
            r = regle_lst[0]
            if r:
                titre += "   " + r.titre

        return self.render('resultat-recherche.html',
                           plaintes_lst=plaintes_lst,
                           nom=name,
                           titre=titre,
                           r=r,
                           to_print=to_print)

    def error_noselect(self):
        self.redirect('/recherche?err=noselect')

    def par_numero(self, num):
        plaintes = list(cached_plaintes())
        key = ""
        for p in plaintes:
            if p.numero == num:
                key = str(p.key().id())
        self.redirect('/%s' % key)

    def a_presenter(self, to_print="-1"):
        self.redirect('/rapportpourlece?toprint=' + to_print)


class RapportPourLeCE(Handler):
    def get(self):
        to_print_str = self.request.get('toprint')
        if to_print_str.isdigit():
            to_print = int(to_print_str)
        else:
            to_print = -1

        q = db.GqlQuery("""select * from Plainte
                           where date_de_classement > :1
                           order by date_de_classement desc""", None)
        plaintes_lst = []
        for n in q.run():
            if not n.presente_au_ce:
                plaintes_lst.append(n)

        precent = None
        pold = None
        if plaintes_lst:
            precent = plaintes_lst[0]
            pold = plaintes_lst[-1]

        self.render('rapport-pour-le-ce.html',
                    plaintes_lst=plaintes_lst,
                    to_print=to_print,
                    precent=precent,
                    pold=pold)

    def post(self):
        checked_boxes = []
        i = 0
        while self.request.get("plaintenr%s" % i):
            if self.request.get("presenteauce%s" % i):
                checked_boxes.append(self.request.get("presenteauce%s" % i))
            i += 1
        checked_boxes_str = ('|').join(checked_boxes)
        checked_boxes = checked_boxes_str.split('|')
        print("checked boxes : ")
        print(checked_boxes_str)
        for checked_box in checked_boxes:
            num = str(checked_box)
            print("checked_box = ")
            print(checked_box)
            q = db.GqlQuery("select * from Plainte where numero = :1", num)
            p = q.get()
            print("p = ")
            print(p)
            p.presente_au_ce = datetime.datetime.now()
            db.put(p)
        self.redirect('/')


# MAIN PAGE
class MainPage(Handler):
    def get(self):
        try:
            plaintes = latest_plaintes()
            self.render('cea.html', plaintes=plaintes)
        except apiproxy_errors.OverQuotaError, message:
            commu = u"ATTENTION ! Le quota de la "
            commu += "base de données a été atteint. "
            commu += "Le système est inutilisable. "
            commu += "Veuillez travailler sur papier. Désolé."
            self.render('cea.html', commu=commu)


class Reglement(Handler):
    def get(self):
        regles = db.GqlQuery("select * from Regle order by nrdec asc")
        self.render('reglement.html', regles=regles)

app = webapp2.WSGIApplication([('/?', MainPage),
                               ('/([0-9]+)/?', PlaintePage),
                               ('/recherche/?', RecherchePage),
                               ('/nouvelleplainte/?', NouvellePlainte),
                               ('/nouveaumembre/?', NouveauMembre),
                               ('/nouvelleregle/?', NouvelleRegle),
                               ('/encours/?', EnCours),
                               ('/rapportpourlece/?', RapportPourLeCE),
                               ('/reglement/?', Reglement),
                               ('/json/?', RegleHandler)
                               ], debug=True)
