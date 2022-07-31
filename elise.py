import json
import logging

import utils


def is_valid_lexeme(lexeme):
    if lexeme['language'] != 'Q150':
        return False
    if lexeme['lexicalCategory'] != 'Q24905':
        return False
    if 'fr' not in lexeme['lemmas']:
        return False
    # uniquement premier groupe pour l'instant
    if lexeme['lemmas']['fr']['value'][-2:] != 'er':
        return False
    if 'P5186' not in lexeme['claims']:
        return False
    if len(lexeme['claims']['P5186']) != 1:
        return False
    if lexeme['claims']['P5186'][0]['mainsnak']['datavalue']['value']['id'] != 'Q2993354':
        return False
    # exceptions https://fr.wikipedia.org/wiki/Conjugaison_des_verbes_du_premier_groupe
    if lexeme['lemmas']['fr']['value'][-3:] == 'yer':
        return False
    if lexeme['lemmas']['fr']['value'][-4:-3] == 'e':
        return False
    if lexeme['lemmas']['fr']['value'][-4:-3] == 'é':
        return False
    if lexeme['lemmas']['fr']['value'][-3:-2] == 'c' or lexeme['lemmas']['fr']['value'][-3:-2] == 'g':
        return False
    # multiples conjugaisons (exemple : copier-coller)
    if '-' in lexeme['lemmas']['fr']['value']:
        return False
    # orthographe 1990 https://dictionnaire.lerobert.com/guide/rectifications-de-l-orthographe-de-1990-regles
    if lexeme['lemmas']['fr']['value'][-4:] == 'eler' or lexeme['lemmas']['fr']['value'][-4:] == 'eter':
        return False
    return True


def generate_forms(features, patterns, lemma):
    r = lemma[:-2]
    forms = []
    for pattern in patterns:
        representation = pattern['pattern'].replace('%r%', r)
        grammatical_features = []
        for feature in pattern['features']:
            grammatical_features.append(features[feature])
        form = {'representations': {'fr': {'language': 'fr', 'value': representation}}, 'grammaticalFeatures': grammatical_features, 'claims': {}, 'add': ''}
        forms.append(form)
    return forms


def are_forms_equal(a, b):
    if a['representations']['fr']['value'] != b['representations']['fr']['value']:
        return False
    if set(a['grammaticalFeatures']) != set(b['grammaticalFeatures']):
        return False
    return True


def compute_forms(existing_forms, generated_forms):
    error = 0
    computed_forms = []
    # existing forms
    for form_e in existing_forms:
        computed_forms.append(form_e)
        found = False
        for form_g in generated_forms:
            if are_forms_equal(form_e, form_g):
                found = True
                break
        if not found:
            error += 1
            logging.error('This existing form has no match: {}'.format(form_e))
    # generated forms
    for form_g in generated_forms:
        found = False
        for form_e in existing_forms:
            if are_forms_equal(form_e, form_g):
                found = True
                break
        if not found:
            computed_forms.append(form_g)
    return error, computed_forms


def edit_lexeme(site, lid, lexeme):
    request = {
        'action': 'wbeditentity',
        'format': 'json',
        'summary': '[[Wikidata:Requests for permissions/Bot/EnvlhBot 4|Forms of French verbs]]',
        'token': site.tokens['edit'],
        'bot': '1',
        'id': lid,
        'baserevid': lexeme['lastrevid'],
        'data': json.dumps(lexeme, ensure_ascii=False),
    }
    site.simple_request(**request).submit()


def main():
    logging.getLogger().setLevel(logging.INFO)
    features = utils.load_json_file('conf/fr_features.json')
    patterns = utils.load_json_file('conf/fr_premier_groupe.json')
    lid = 'L17692'
    lexeme = utils.fetch_url_json('https://www.wikidata.org/wiki/Special:EntityData/{}.json'.format(lid))['entities'][lid]
    if is_valid_lexeme(lexeme):
        generated_forms = generate_forms(features, patterns, lexeme['lemmas']['fr']['value'])
        error, computed_forms = compute_forms(lexeme['forms'], generated_forms)
        if error != 0:
            logging.error('Unrecognized forms in lexeme {}, no change applied.'.format(lid))
        elif computed_forms == lexeme['forms']:
            logging.info('No change needed to lexeme {}.'.format(lid))
        else:
            logging.info('Updating lexeme {}...'.format(lid))
            lexeme['forms'] = computed_forms
            # site = utils.get_site()
            # edit_lexeme(site, lid, lexeme)
            logging.info('Done.')


if __name__ == '__main__':
    main()
