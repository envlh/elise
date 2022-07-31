import copy
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
    lemma = lexeme['lemmas']['fr']['value']
    # uniquement premier groupe pour l'instant
    if lemma[-2:] != 'er':
        return False
    if 'P5186' not in lexeme['claims']:
        return False
    if len(lexeme['claims']['P5186']) != 1:
        return False
    if lexeme['claims']['P5186'][0]['mainsnak']['datavalue']['value']['id'] != 'Q2993354':
        return False
    # exceptions https://fr.wikipedia.org/wiki/Conjugaison_des_verbes_du_premier_groupe
    if lemma[-3:] == 'yer':
        return False
    if lemma[-4:-3] == 'e':
        return False
    if lemma[-4:-3] == 'é':
        return False
    # multiples conjugaisons (exemple : copier-coller)
    if '-' in lexeme['lemmas']['fr']['value']:
        return False
    # orthographe 1990 https://dictionnaire.lerobert.com/guide/rectifications-de-l-orthographe-de-1990-regles
    if lemma[-4:] == 'eler' or lemma[-4:] == 'eter':
        return False
    return True


def clean_grammatical_features(forms, replacements):
    forms_copy = copy.deepcopy(forms)
    for form in forms_copy:
        features = []
        for feature in form['grammaticalFeatures']:
            if feature in replacements:
                features.extend(replacements[feature])
            else:
                features.append(feature)
        form['grammaticalFeatures'] = features
    return forms_copy


def generate_forms(features, patterns, lemma):
    radical = lemma[:-2]
    forms = []
    for pattern in patterns:
        if lemma[-3:-2] == 'c' and pattern['pattern'].replace('%r%', '')[0] in ('a', 'â', 'o'):
            representation = pattern['pattern'].replace('%r%', '{}ç'.format(radical[:-1]))
        elif lemma[-3:-2] == 'g' and pattern['pattern'].replace('%r%', '')[0] in ('a', 'â', 'o'):
            representation = pattern['pattern'].replace('%r%', '{}e'.format(radical))
        else:
            representation = pattern['pattern'].replace('%r%', radical)
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


def compute_forms(base_forms, generated_forms):
    error = 0
    computed_forms = []
    # existing forms
    for form_e in base_forms:
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
        for form_e in base_forms:
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
    replacements = utils.load_json_file('conf/fr_replacements.json')
    lid = 'L28927'
    lexeme = utils.fetch_url_json('https://www.wikidata.org/wiki/Special:EntityData/{}.json'.format(lid))['entities'][lid]
    if not is_valid_lexeme(lexeme):
        logging.error('Elise cannot handle Lexeme {} at the moment.'.format(lid))
    else:
        # clean existing forms
        clean_forms = clean_grammatical_features(lexeme['forms'], replacements)
        # print(json.dumps(clean_forms, ensure_ascii=False))
        # generate all forms
        generated_forms = generate_forms(features, patterns, lexeme['lemmas']['fr']['value'])
        # print(json.dumps(generated_forms, ensure_ascii=False))
        # merge forms
        error, computed_forms = compute_forms(clean_forms, generated_forms)
        # print(json.dumps(computed_forms, ensure_ascii=False))
        if error != 0:
            logging.error('Unrecognized forms in lexeme {}, no change applied.'.format(lid))
        elif computed_forms == lexeme['forms']:
            logging.info('No change needed to lexeme {}.'.format(lid))
        else:
            logging.info('Updating lexeme {}...'.format(lid))
            lexeme['forms'] = computed_forms
            site = utils.get_site()
            edit_lexeme(site, lid, lexeme)
            logging.info('Done.')


if __name__ == '__main__':
    main()
